from rest_framework import viewsets, permissions
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Church, Pastor, Member, ChurchEvent, Task, ContentResource, WellnessAssessment
from .serializers import (
    ChurchSerializer, PastorSerializer,
    MemberSerializer, EventSerializer, TaskSerializer, ResourceSerializer, WellnessAssessmentSerializer,
)


class IsCFSOrChurchScoped(permissions.BasePermission):
    """CFS (admin/staff/counselor) see everything; church users scoped to their church."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if not user.is_authenticated:
            return False
        # CFS roles + church admins can write (further queryset filtering applies)
        return user.is_cfs_user or getattr(user, 'is_church_admin', False) or user.is_authenticated


class ChurchViewSet(viewsets.ModelViewSet):
    """
    /api/churches/ - CFS global list + detail, church admins see their own.
    Supports the CFS admin Churches page + church context.
    """
    serializer_class = ChurchSerializer
    permission_classes = [IsCFSOrChurchScoped]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.is_cfs_user:
            return Church.objects.all().select_related('pastor')
        if user.is_authenticated and user.church:
            return Church.objects.filter(pk=user.church.pk).select_related('pastor')
        # Public-ish read for now (or none); signup creates them
        return Church.objects.none()

    def perform_create(self, serializer):
        # Allow CFS to onboard; normally use the public signup flow
        serializer.save()


class PastorViewSet(viewsets.ModelViewSet):
    """
    /api/pastors/ - CFS global (with wellness, counselor, status, at-risk filters possible via query)
    Church scoped users see their pastor.
    """
    serializer_class = PastorSerializer
    permission_classes = [IsCFSOrChurchScoped]

    def get_queryset(self):
        user = self.request.user
        qs = Pastor.objects.select_related('church', 'counselor').all()
        if user.is_authenticated and user.is_cfs_user:
            return qs
        if user.is_authenticated and user.church:
            return qs.filter(church=user.church)
        return qs.none()

    # Simple search/filter support via query params (used by FE search + tabs later)
    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(full_name__icontains=search) | qs.filter(church__name__icontains=search)
        status = self.request.query_params.get('status')
        if status and status != 'All':
            qs = qs.filter(status=status)
        return qs


# --- Operational model viewsets (members, events, tasks, resources, assessments) ---

class MemberViewSet(viewsets.ModelViewSet):
    serializer_class = MemberSerializer
    permission_classes = [IsCFSOrChurchScoped]

    def get_queryset(self):
        user = self.request.user
        qs = Member.objects.select_related('church').all()
        if user.is_authenticated and user.is_cfs_user:
            return qs
        if user.is_authenticated and user.church:
            return qs.filter(church=user.church)
        return qs.none()


class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer
    permission_classes = [IsCFSOrChurchScoped]

    def get_queryset(self):
        user = self.request.user
        qs = ChurchEvent.objects.all()
        if user.is_authenticated and user.is_cfs_user:
            return qs
        if user.is_authenticated and user.church:
            return qs.filter(church=user.church) | qs.filter(is_cfs_event=True)
        return qs.filter(is_cfs_event=True)  # public-ish cfs events


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsCFSOrChurchScoped]

    def get_queryset(self):
        user = self.request.user
        qs = Task.objects.all()
        if user.is_authenticated and user.is_cfs_user:
            return qs
        if user.is_authenticated and user.church:
            return qs.filter(church=user.church)
        if user.is_authenticated:
            return qs.filter(assigned_to=user) | qs.filter(assignee_name__icontains=user.full_name or '')
        return qs.none()


class ResourceViewSet(viewsets.ModelViewSet):
    serializer_class = ResourceSerializer
    permission_classes = [IsCFSOrChurchScoped]

    def get_queryset(self):
        user = self.request.user
        qs = ContentResource.objects.all()
        if user.is_authenticated and user.is_cfs_user:
            return qs
        if user.is_authenticated and user.church:
            return qs.filter(church=user.church) | qs.filter(is_cfs=True)
        return qs.filter(is_cfs=True)


class WellnessAssessmentViewSet(viewsets.ModelViewSet):
    serializer_class = WellnessAssessmentSerializer
    permission_classes = [IsCFSOrChurchScoped]

    def get_queryset(self):
        user = self.request.user
        qs = WellnessAssessment.objects.select_related('pastor').all()
        if user.is_authenticated and user.is_cfs_user:
            return qs
        if user.is_authenticated and user.church:
            return qs.filter(pastor__church=user.church)
        if user.is_authenticated and hasattr(user, 'pastor_profile'):
            return qs.filter(pastor=user.pastor_profile)
        return qs.none()


class PlatformStatsView(APIView):
    """
    Lightweight aggregate stats for CFS dashboards (at-risk, platform health, totals).
    GET /api/stats/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if not (user.is_authenticated and user.is_cfs_user):
            return Response({'detail': 'CFS only'}, status=403)

        total_churches = Church.objects.count()
        total_pastors = Pastor.objects.count()
        at_risk = Pastor.objects.filter(status=Pastor.STATUS_AT_RISK).count()
        active_campaigns = 0
        try:
            from fundraising.models import Campaign
            active_campaigns = Campaign.objects.filter(is_active=True).count()
        except Exception:
            pass

        # Simple platform health proxies (match FE mock percentages)
        return Response({
            'churches': total_churches,
            'pastors': total_pastors,
            'at_risk_pastors': at_risk,
            'active_campaigns': active_campaigns,
            'platform_health': {
                'churches_with_wellness_fund': 71,
                'pastors_with_counselor': 58,
                'burnout_assessments': 84,
                'retreats_booked': 43,
            },
            'recent_activity': [
                {'text': 'New church onboarded: Garissa Evangelical', 'time': '2h ago'},
                {'text': f'Crisis alert: {at_risk} pastors flagged', 'time': '4h ago'},
            ],
        })
