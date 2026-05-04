"""
Background tasks for file management.
These can be called directly or via Celery beat when Celery is configured.
"""
import os
from datetime import timedelta

from django.utils import timezone

# Gracefully degrade if Celery is not installed
try:
    from celery import shared_task
except ImportError:
    def shared_task(func):
        return func


@shared_task
def cleanup_trash():
    """
    Permanently delete files that have been in trash for 30+ days.
    Reclaims storage quota for each deleted file.
    """
    from .models import File
    from .services import TrashService

    cutoff = timezone.now() - timedelta(days=30)
    old_trash = File.objects.filter(
        is_deleted=True,
        deleted_at__lt=cutoff,
    ).select_related('owner')

    svc = TrashService()
    deleted = 0
    for file in old_trash:
        try:
            svc.permanent_delete(file, file.owner)
            deleted += 1
        except Exception:
            pass

    return f"Cleaned up {deleted} file(s) from trash."
