import hashlib
import mimetypes
import os
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.files.validators import validate_file_upload

IP_GROUP_MAX_UPLOAD_MB = getattr(settings, 'IP_GROUP_MAX_UPLOAD_MB', 50)
IP_GROUP_RATE_LIMIT    = getattr(settings, 'IP_GROUP_RATE_LIMIT', 20)   # per hour

EXPIRY_CHOICES = {
    '1h':  timedelta(hours=1),
    '24h': timedelta(hours=24),
    '7d':  timedelta(days=7),
}


class IPGroupQuotaError(Exception):
    pass


class IPGroupBlockedError(Exception):
    pass


class IPGroupRateLimitError(Exception):
    pass


class IPGroupUploadService:

    def upload(self, file_obj, ip_group, anonymous_uploader,
               title='', description='', expiry='24h'):
        """
        Validate, save, and record a file uploaded to an IP group.
        Returns the created File instance.
        """
        from apps.files.models import File

        if ip_group.is_blocked:
            raise IPGroupBlockedError("Your IP has been blocked from uploading.")
        if not ip_group.is_active:
            raise IPGroupBlockedError("IP sharing is currently disabled.")

        self._check_rate_limit(ip_group)

        validate_file_upload(file_obj)

        max_bytes = IP_GROUP_MAX_UPLOAD_MB * 1024 * 1024
        if file_obj.size > max_bytes:
            raise ValidationError(
                f"File too large for IP sharing. Maximum is {IP_GROUP_MAX_UPLOAD_MB} MB."
            )

        if ip_group.storage_used + file_obj.size > ip_group.storage_quota:
            avail = ip_group.storage_quota - ip_group.storage_used
            raise IPGroupQuotaError(
                f"IP group storage full. "
                f"Available: {avail / (1024*1024):.1f} MB, "
                f"needed: {file_obj.size / (1024*1024):.1f} MB."
            )

        file_hash  = self._hash_file(file_obj)
        mime_type  = self._detect_mime(file_obj)
        ext        = os.path.splitext(file_obj.name)[1].lower()
        saved_path = self._save_to_media(file_obj)
        expires_at = timezone.now() + EXPIRY_CHOICES.get(expiry, EXPIRY_CHOICES['24h'])

        file_instance = File.objects.create(
            owner=None,
            ip_group=ip_group,
            anonymous_uploader=anonymous_uploader,
            title=title.strip() if title and title.strip() else file_obj.name,
            description=description or '',
            file=saved_path,
            original_filename=file_obj.name,
            file_hash=file_hash,
            file_size=file_obj.size,
            mime_type=mime_type,
            extension=ext,
            expires_at=expires_at,
        )

        from apps.ipgroup.models import IPGroup as _IPGroup
        _IPGroup.objects.filter(pk=ip_group.pk).update(
            storage_used=ip_group.storage_used + file_obj.size,
            last_upload=timezone.now(),
        )
        ip_group.refresh_from_db()

        self._increment_rate_limit(ip_group)
        return file_instance

    def delete_file(self, file, ip_group, anonymous_uploader):
        """
        Permanently delete a file from an IP group.
        Only the original uploader (matched by cookie) may delete.
        """
        if file.ip_group_id != ip_group.pk:
            raise PermissionError("You cannot delete this file.")

        if (file.anonymous_uploader_id and
                file.anonymous_uploader_id != anonymous_uploader.pk):
            raise PermissionError("Only the original uploader can delete this file.")

        size = file.file_size
        try:
            path = file.file.path
            file.delete()
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            file.delete()

        from apps.ipgroup.models import IPGroup as _IPGroup
        _IPGroup.objects.filter(pk=ip_group.pk).update(
            storage_used=max(0, ip_group.storage_used - size)
        )

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _check_rate_limit(self, ip_group):
        try:
            from django.core.cache import cache
            key = f"ip_upload_rate:{ip_group.ip_address}"
            if cache.get(key, 0) >= IP_GROUP_RATE_LIMIT:
                raise IPGroupRateLimitError(
                    f"Rate limit reached: {IP_GROUP_RATE_LIMIT} uploads per hour. "
                    "Please wait before uploading again."
                )
        except IPGroupRateLimitError:
            raise
        except Exception:
            pass  # Don't block uploads if cache is unavailable

    def _increment_rate_limit(self, ip_group):
        try:
            from django.core.cache import cache
            key = f"ip_upload_rate:{ip_group.ip_address}"
            cache.set(key, cache.get(key, 0) + 1, timeout=3600)
        except Exception:
            pass

    def _hash_file(self, file_obj):
        sha256 = hashlib.sha256()
        file_obj.seek(0)
        for block in iter(lambda: file_obj.read(65536), b''):
            sha256.update(block)
        file_obj.seek(0)
        return sha256.hexdigest()

    def _detect_mime(self, file_obj):
        try:
            import magic as _magic
            file_obj.seek(0)
            mime = _magic.from_buffer(file_obj.read(2048), mime=True)
            file_obj.seek(0)
            return mime
        except ImportError:
            guessed, _ = mimetypes.guess_type(file_obj.name)
            return guessed or 'application/octet-stream'

    def _save_to_media(self, file_obj):
        now = timezone.now()
        rel_dir = f"ipgroup/{now.year}/{now.month:02d}/{now.day:02d}"
        abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)

        safe_name = f"{uuid.uuid4().hex}_{file_obj.name}"
        dest = os.path.join(abs_dir, safe_name)

        file_obj.seek(0)
        with open(dest, 'wb') as fh:
            for chunk in file_obj.chunks():
                fh.write(chunk)

        return f"{rel_dir}/{safe_name}"
