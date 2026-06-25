import uuid
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Campaign, Donation
from .serializers import (
    CampaignSerializer, PublicCampaignSerializer,
    InitiateDonationSerializer
)
from payments.services import initiate_payment, KeshoPayError, record_transaction
from payments.models import PaymentTransaction


class IsChurchAdminOrReadOnly(permissions.BasePermission):
    """Very simple tenant-aware permission for Phase 1."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        return bool(user.is_authenticated and (user.is_church_admin or user.is_cfs_user))


class CampaignViewSet(viewsets.ModelViewSet):
    """
    Authenticated access to campaigns (for church admins + CFS).
    Guest users should use the public_uuid endpoints.
    """
    serializer_class = CampaignSerializer
    permission_classes = [IsChurchAdminOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.is_cfs_user:
            return Campaign.objects.all()
        if user.is_authenticated and user.church:
            return Campaign.objects.filter(church=user.church)
        return Campaign.objects.none()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, church=self.request.user.church)


class PublicCampaignDetailView(APIView):
    """Read-only public campaign info for shareable links."""
    authentication_classes = []
    permission_classes = []

    def get(self, request, public_uuid):
        campaign = get_object_or_404(Campaign, public_uuid=public_uuid, is_active=True)
        serializer = PublicCampaignSerializer(campaign)
        return Response(serializer.data)


class CampaignLedgerView(APIView):
    """Simple transparent ledger view (can be made public per campaign)."""
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, pk):
        campaign = get_object_or_404(Campaign, pk=pk)
        # Basic tenant check for logged in church users
        user = request.user
        if user.is_authenticated and not user.is_cfs_user and user.church and user.church != campaign.church:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        donations = campaign.donations.filter(status=Donation.STATUS_SUCCESS).order_by('-received_at')[:50]
        disbursements = campaign.disbursements.filter(
            status__in=[campaign.disbursements.model.STATUS_APPROVED, campaign.disbursements.model.STATUS_PAID]
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
                } for d in donations
            ],
            'recent_disbursements': [
                {
                    'amount': d.amount,
                    'purpose': d.purpose[:120],
                    'status': d.get_status_display(),
                    'date': d.approved_at or d.requested_at,
                } for d in disbursements
            ]
        })


class InitiateDonationView(APIView):
    """
    Guest donation entry point (Phase 1 hero flow).
    No authentication required. Takes phone + amount + campaign public uuid.
    Creates pending Donation, calls KeshoPay, returns checkout info.
    """
    authentication_classes = []
    permission_classes = []

    @transaction.atomic
    def post(self, request):
        ser = InitiateDonationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        campaign = get_object_or_404(
            Campaign,
            public_uuid=data['campaign_public_uuid'],
            is_active=True
        )

        # Create our pending donation record first
        donation = Donation.objects.create(
            church=campaign.church,
            campaign=campaign,
            donor_phone=data['phone'],
            donor_name=data.get('donor_name', ''),
            is_anonymous=data.get('is_anonymous', False),
            amount=data['amount'],
            status=Donation.STATUS_PENDING,
            kesho_reference=f"CFS-CAMP-{campaign.id}-{uuid.uuid4().hex[:10]}",
            metadata={'source': 'api-guest'},
        )

        # Record audit tx (pending)
        record_transaction(
            church=campaign.church,
            direction=PaymentTransaction.DIRECTION_IN,
            amount=data['amount'],
            reference=donation.kesho_reference,
            phone_number=data['phone'],
            status=PaymentTransaction.STATUS_PENDING,
            related_donation=donation,
        )

        # Call KeshoPay
        try:
            # In real deployment the redirect should point to a nice thank-you / status page
            redirect_url = request.data.get(
                'redirect_url',
                f"https://your-frontend.example.com/campaigns/{campaign.public_uuid}/thank-you"
            )

            result = initiate_payment(
                amount=data['amount'],
                phone_number=data['phone'],
                reference=donation.kesho_reference,
                redirect_url=redirect_url,
                metadata={
                    'church_id': campaign.church.id,
                    'campaign_id': campaign.id,
                    'campaign_title': campaign.title,
                    'donor_phone': data['phone'],
                }
            )

            # If KeshoPay returns a checkout url, surface it
            checkout_url = result.get('data', {}).get('checkoutUrl') or result.get('checkoutUrl') or result.get('url')

            return Response({
                'success': True,
                'donation_id': donation.id,
                'reference': donation.kesho_reference,
                'checkout_url': checkout_url,
                'raw': result,   # useful during integration testing
            }, status=status.HTTP_200_OK)

        except KeshoPayError as e:
            # Mark donation failed for visibility
            donation.status = Donation.STATUS_FAILED
            donation.metadata['error'] = str(e)
            donation.save(update_fields=['status', 'metadata'])
            return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)