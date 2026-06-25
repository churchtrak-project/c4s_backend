from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum, Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Campaign, CampaignUpdate, Donation, Disbursement
from .permissions import (
    IsCampaignWriter,
    IsFundStaff,
    IsDisbursementCreator,
    CanApproveDisbursement,
)
from .serializers import (
    CampaignSerializer,
    CampaignCreateSerializer,
    CampaignUpdateSerializer,
    PublicCampaignSerializer,
    DonationSerializer,
    DisbursementSerializer,
    DisbursementCreateSerializer,
    DisbursementRejectSerializer,
    InitiateDonationSerializer,
    ResendReceiptSerializer,
)
from .services import send_donation_receipt


def _campaign_queryset_for_user(user):
    if user.is_authenticated and user.is_cfs_user:
        return Campaign.objects.select_related('church', 'pastor').all()
    if user.is_authenticated and user.church_id:
        return Campaign.objects.select_related('church', 'pastor').filter(church=user.church)
    return Campaign.objects.none()


def _donation_queryset_for_user(user):
    qs = Donation.objects.select_related('campaign', 'church').all()
    if user.is_authenticated and user.is_cfs_user:
        return qs
    if user.is_authenticated and user.church_id:
        return qs.filter(church=user.church)
    return qs.none()


def _disbursement_queryset_for_user(user):
    qs = Disbursement.objects.select_related(
        'campaign', 'church', 'requested_by', 'approved_by'
    ).all()
    if user.is_authenticated and user.is_cfs_user:
        return qs
    if user.is_authenticated and user.church_id:
        return qs.filter(church=user.church)
    return qs.none()


class CampaignViewSet(viewsets.ModelViewSet):
    """Authenticated campaign management for church_admin and CFS."""
    permission_classes = [IsCampaignWriter]

    def get_queryset(self):
        qs = _campaign_queryset_for_user(self.request.user)
        status_filter = self.request.query_params.get('status')
        if status_filter == 'Active':
            qs = qs.filter(is_active=True).exclude(end_date__lt=date.today())
        elif status_filter == 'Completed':
            qs = qs.filter(Q(is_active=False) | Q(end_date__lt=date.today()))
        return qs

    def get_serializer_class(self):
        if self.action == 'create':
            return CampaignCreateSerializer
        return CampaignSerializer

    def perform_create(self, serializer):
        user = self.request.user
        church = user.church
        pastor = serializer.validated_data.get('pastor')
        if not pastor and church:
            pastor = getattr(church, 'pastor', None)
        if not pastor:
            from churches.models import Pastor
            pastor = Pastor.objects.filter(church=church).first()
        serializer.save(created_by=user, church=church, pastor=pastor)


class CampaignUpdateViewSet(viewsets.ModelViewSet):
    serializer_class = CampaignUpdateSerializer
    permission_classes = [IsCampaignWriter]

    def get_queryset(self):
        qs = CampaignUpdate.objects.select_related('campaign').all()
        campaign_id = self.request.query_params.get('campaign')
        if campaign_id:
            qs = qs.filter(campaign_id=campaign_id)
        user = self.request.user
        if user.is_authenticated and user.is_cfs_user:
            return qs
        if user.is_authenticated and user.church_id:
            return qs.filter(campaign__church=user.church)
        return qs.none()

    def perform_create(self, serializer):
        user = self.request.user
        name = user.full_name or user.email or user.phone
        serializer.save(author=user, author_name=name)


class DonationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DonationSerializer
    permission_classes = [IsFundStaff]

    def get_queryset(self):
        qs = _donation_queryset_for_user(self.request.user)
        campaign_id = self.request.query_params.get('campaign')
        if campaign_id:
            qs = qs.filter(campaign_id=campaign_id)
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(donor_name__icontains=search)
                | Q(donor_phone__icontains=search)
                | Q(kesho_reference__icontains=search)
            )
        return qs.order_by('-received_at', '-created_at')


class DisbursementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsDisbursementCreator]

    def get_queryset(self):
        qs = _disbursement_queryset_for_user(self.request.user)
        status_filter = self.request.query_params.get('status')
        if status_filter == 'pending':
            qs = qs.filter(status=Disbursement.STATUS_REQUESTED)
        elif status_filter == 'released':
            qs = qs.filter(status__in=[Disbursement.STATUS_APPROVED, Disbursement.STATUS_PAID])
        return qs

    def get_serializer_class(self):
        if self.action == 'create':
            return DisbursementCreateSerializer
        if self.action == 'reject':
            return DisbursementRejectSerializer
        return DisbursementSerializer

    def perform_create(self, serializer):
        user = self.request.user
        campaign = serializer.validated_data['campaign']
        serializer.save(
            church=campaign.church,
            requested_by=user,
            status=Disbursement.STATUS_REQUESTED,
        )

    @action(detail=True, methods=['post'], permission_classes=[CanApproveDisbursement])
    def approve(self, request, pk=None):
        disbursement = self.get_object()
        if disbursement.status != Disbursement.STATUS_REQUESTED:
            return Response(
                {'detail': 'Only pending disbursements can be approved.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if disbursement.requested_by_id == request.user.id and not request.user.is_cfs_user:
            return Response(
                {'detail': 'Initiator cannot provide the second signature.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        disbursement.status = Disbursement.STATUS_APPROVED
        disbursement.approved_by = request.user
        disbursement.approved_at = timezone.now()
        disbursement.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
        return Response(DisbursementSerializer(disbursement).data)

    @action(detail=True, methods=['post'], permission_classes=[CanApproveDisbursement])
    def reject(self, request, pk=None):
        disbursement = self.get_object()
        if disbursement.status != Disbursement.STATUS_REQUESTED:
            return Response(
                {'detail': 'Only pending disbursements can be rejected.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ser = DisbursementRejectSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        disbursement.status = Disbursement.STATUS_REJECTED
        disbursement.rejected_by = request.user
        disbursement.rejection_reason = ser.validated_data.get('reason', '')
        disbursement.save(update_fields=['status', 'rejected_by', 'rejection_reason', 'updated_at'])
        return Response(DisbursementSerializer(disbursement).data)


class PublicCampaignDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, public_uuid):
        campaign = get_object_or_404(
            Campaign.objects.select_related('church', 'pastor'),
            public_uuid=public_uuid,
        )
        return Response(PublicCampaignSerializer(campaign).data)


class PublicCampaignLedgerView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, public_uuid):
        campaign = get_object_or_404(
            Campaign.objects.select_related('church', 'pastor'),
            public_uuid=public_uuid,
        )
        donations = campaign.donations.filter(status=Donation.STATUS_SUCCESS).order_by('-received_at')[:50]
        disbursements = campaign.disbursements.filter(
            status__in=[Disbursement.STATUS_APPROVED, Disbursement.STATUS_PAID]
        ).order_by('-approved_at')[:30]
        return Response({
            'campaign': PublicCampaignSerializer(campaign).data,
            'total_raised': campaign.total_raised,
            'total_disbursed': campaign.total_disbursed,
            'current_balance': campaign.current_balance,
            'recent_donations': [
                {
                    'amount': d.amount,
                    'donor': 'Anonymous' if d.is_anonymous else d.donor_name or d.donor_phone,
                    'date': d.received_at,
                }
                for d in donations
            ],
            'recent_disbursements': [
                {
                    'amount': d.amount,
                    'purpose': d.purpose[:120],
                    'status': d.status_display_frontend,
                    'date': d.approved_at or d.requested_at,
                }
                for d in disbursements
            ],
        })


class CampaignLedgerView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, pk):
        campaign = get_object_or_404(Campaign, pk=pk)
        user = request.user
        if user.is_authenticated and not user.is_cfs_user and user.church and user.church != campaign.church:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        ledger_view = PublicCampaignLedgerView()
        return ledger_view.get(request, public_uuid=campaign.public_uuid)


class FundDashboardView(APIView):
    """Church-scoped wellness fund overview for the admin dashboard."""
    permission_classes = [IsFundStaff]

    def get(self, request):
        user = request.user
        campaigns = _campaign_queryset_for_user(user)
        primary = campaigns.filter(is_active=True).first()
        donations = _donation_queryset_for_user(user).filter(status=Donation.STATUS_SUCCESS)
        disbursements = _disbursement_queryset_for_user(user)

        total_raised = donations.aggregate(t=Sum('amount'))['t'] or Decimal('0')
        total_disbursed = disbursements.filter(
            status__in=[Disbursement.STATUS_APPROVED, Disbursement.STATUS_PAID]
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0')
        fund_balance = total_raised - total_disbursed
        donor_count = donations.values('donor_phone').distinct().count()
        pending = disbursements.filter(status=Disbursement.STATUS_REQUESTED)
        pending_total = pending.aggregate(t=Sum('amount'))['t'] or Decimal('0')

        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        raised_today = donations.filter(received_at__gte=today_start).aggregate(t=Sum('amount'))['t'] or Decimal('0')
        week_start = today_start - timedelta(days=7)
        donors_this_week = donations.filter(received_at__gte=week_start).values('donor_phone').distinct().count()

        recent_donations = donations.order_by('-received_at')[:5]
        pending_approvals = pending[:5]
        activity = []

        for d in recent_donations[:3]:
            when = d.received_at or d.created_at
            delta = timezone.now() - when
            time_label = f"{max(int(delta.total_seconds() // 3600), 1)}h ago" if delta.days == 0 else f"{delta.days}d ago"
            name = 'Anonymous' if d.is_anonymous else (d.donor_name or 'Donor')
            activity.append({
                'text': f"KES {d.amount:,.0f} donation received — {name}",
                'time': time_label,
                'type': 'income',
            })

        for p in pending_approvals[:2]:
            activity.append({
                'text': f"Disbursement request pending approval — KES {p.amount:,.0f}",
                'time': 'recent',
                'type': 'alert',
            })

        return Response({
            'church': user.church.name if user.church else None,
            'primary_campaign': CampaignSerializer(primary).data if primary else None,
            'kpis': {
                'total_raised': total_raised,
                'donor_count': donor_count,
                'fund_balance': fund_balance,
                'pending_approval_count': pending.count(),
                'pending_approval_amount': pending_total,
                'raised_today': raised_today,
                'donors_this_week': donors_this_week,
            },
            'recent_donations': DonationSerializer(recent_donations, many=True).data,
            'pending_approvals': DisbursementSerializer(pending_approvals, many=True).data,
            'activity_feed': activity,
            'campaigns': CampaignSerializer(campaigns[:10], many=True).data,
        })


class InitiateDonationView(APIView):
    """
    Guest donation entry point. KeshoPay is not wired yet — returns 502.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        ser = InitiateDonationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        campaign = get_object_or_404(
            Campaign,
            public_uuid=data['campaign_public_uuid'],
            is_active=True,
        )
        return Response(
            {
                'error': 'KeshoPay payment processing is not yet configured.',
                'detail': 'not_implemented',
                'campaign_id': campaign.id,
                'campaign_title': campaign.title,
                'amount': str(data['amount']),
                'phone': data['phone'],
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )


class ResendReceiptView(APIView):
    permission_classes = [IsFundStaff]

    def post(self, request, pk):
        donation = get_object_or_404(_donation_queryset_for_user(request.user), pk=pk)
        ser = ResendReceiptSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = send_donation_receipt(donation, channels=ser.validated_data['channels'])
        return Response({
            'success': True,
            'stub': True,
            'message': 'Receipt delivery stub invoked. No real SMS/email sent.',
            'delivery': result,
            'donation': DonationSerializer(donation).data,
        })