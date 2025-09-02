from rest_framework import permissions
from .models import UserProfile


class IsDriver(permissions.BasePermission):
    """Allows access only to users with driver role."""
    def has_permission(self, request, view):
        return bool(request.user and hasattr(request.user, "profile") and request.user.profile.role == UserProfile.DRIVER)
