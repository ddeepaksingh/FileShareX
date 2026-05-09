from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from .models import Group


def get_group_or_403(request, group_id, require_admin=False):
    """
    Return (group, membership) or raise 404/403.
    Owner always passes. Non-member gets 403 on private groups.
    """
    group = get_object_or_404(Group, id=group_id)
    membership = group.get_membership(request.user)

    if group.owner == request.user:
        return group, membership

    if not membership:
        raise PermissionDenied

    if require_admin and not membership.is_admin():
        raise PermissionDenied

    return group, membership
