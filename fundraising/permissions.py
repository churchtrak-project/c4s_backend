from rest_framework import permissions


class IsCampaignWriter(permissions.BasePermission):
    """Authenticated read; write for church_admin and CFS roles."""

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(user.is_church_admin or user.is_cfs_user)


class IsFundStaff(permissions.BasePermission):
    """church_admin, finance_officer (accountability), or CFS."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user.is_authenticated
            and (
                user.is_church_admin
                or user.is_finance_officer
                or user.is_cfs_user
            )
        )


class IsDisbursementCreator(permissions.BasePermission):
    """List: fund staff. Create: church_admin or CFS."""

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return bool(
                user.is_church_admin
                or user.is_finance_officer
                or user.is_cfs_user
            )
        return bool(user.is_church_admin or user.is_cfs_user)


class CanApproveDisbursement(permissions.BasePermission):
    """Second signature: finance_officer (accountability officer) or CFS."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user.is_authenticated
            and (user.is_finance_officer or user.is_cfs_user)
        )