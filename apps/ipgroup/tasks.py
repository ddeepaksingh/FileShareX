"""
Background tasks for IP group maintenance.
Functions are plain callables so they work without Celery.
When Celery is installed, they are automatically wrapped as shared tasks.
"""
import os


def cleanup_expired_files():
    """Delete all expired IP group files and reclaim their storage quota."""
    from django.utils import timezone
    from apps.files.models import File
    from apps.ipgroup.models import IPGroup

    expired = File.objects.filter(
        ip_group__isnull=False,
        expires_at__lt=timezone.now(),
        is_deleted=False,
    ).select_related('ip_group')

    deleted = 0
    for file in expired:
        ip_group = file.ip_group
        size     = file.file_size
        try:
            path = file.file.path
            file.delete()
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            file.delete()

        IPGroup.objects.filter(pk=ip_group.pk).update(
            storage_used=max(0, ip_group.storage_used - size)
        )
        deleted += 1

    return deleted


def reset_daily_upload_limits():
    """Reset upload_count_today on all IP groups (run at midnight)."""
    from apps.ipgroup.models import IPGroup
    return IPGroup.objects.update(upload_count_today=0)


# Wrap as Celery shared tasks when Celery is available
try:
    from celery import shared_task
    cleanup_expired_files    = shared_task(cleanup_expired_files)
    reset_daily_upload_limits = shared_task(reset_daily_upload_limits)
except ImportError:
    pass
