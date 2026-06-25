from rest_framework import viewsets, permissions

from .models import Counselor, CounselingCase, CounselingSession
from .serializers import CounselorSerializer, CounselingCaseSerializer, CounselingSessionSerializer


class IsCFSOrRelevant(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        u = request.user
        return u.is_authenticated and (u.is_cfs_user or u.is_counselor or u.is_church_admin)


class CounselorViewSet(viewsets.ModelViewSet):
    serializer_class = CounselorSerializer
    permission_classes = [IsCFSOrRelevant]
    queryset = Counselor.objects.all()


class CounselingCaseViewSet(viewsets.ModelViewSet):
    serializer_class = CounselingCaseSerializer
    permission_classes = [IsCFSOrRelevant]

    def get_queryset(self):
        user = self.request.user
        qs = CounselingCase.objects.select_related('pastor', 'counselor', 'church').all()
        if user.is_authenticated and user.is_cfs_user:
            return qs
        if user.is_authenticated and user.church:
            return qs.filter(church=user.church)
        if user.is_authenticated and user.is_counselor:
            # counselor sees their cases
            try:
                c = user.counselor_profile
                return qs.filter(counselor=c)
            except Exception:
                return qs.none()
        return qs.none()


class CounselingSessionViewSet(viewsets.ModelViewSet):
    serializer_class = CounselingSessionSerializer
    permission_classes = [IsCFSOrRelevant]

    def get_queryset(self):
        user = self.request.user
        qs = CounselingSession.objects.select_related('case__pastor', 'case__counselor').all()
        if user.is_authenticated and user.is_cfs_user:
            return qs
        if user.is_authenticated and user.church:
            return qs.filter(case__church=user.church)
        if user.is_authenticated and user.is_counselor:
            try:
                c = user.counselor_profile
                return qs.filter(case__counselor=c)
            except Exception:
                return qs.none()
        return qs.none()
