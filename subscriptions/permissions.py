from rest_framework import permissions
from django.utils import timezone


class IsActiveSubscriber(permissions.BasePermission):
    """
    PRD §04 Access Control:
    Non-subscribers receive restricted access to platform features.
    Real-time subscription status check on every authenticated request.
    Handles active, cancelled, and lapsed subscription states.
    Staff members bypass subscriber restrictions for admin management.
    """
    message = 'An active subscription is required to access this feature.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True

        sub = getattr(request.user, 'subscription', None)
        if not sub:
            return False

        # Real-time status validation against renewal date
        sub.check_lapsed()
        return sub.status == 'active'
