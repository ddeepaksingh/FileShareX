import uuid
from django.db import models


class IPGroup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ip_address = models.GenericIPAddressField(unique=True, db_index=True)

    storage_quota = models.BigIntegerField(default=524288000)   # 500 MB
    storage_used = models.BigIntegerField(default=0)

    is_active = models.BooleanField(default=True)
    is_blocked = models.BooleanField(default=False)

    upload_count_today = models.IntegerField(default=0)
    last_upload = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ip_groups'
        indexes = [
            models.Index(fields=['ip_address'], name='ip_groups_ip_addr_idx'),
            models.Index(fields=['is_active', 'is_blocked'], name='ip_groups_active_idx'),
        ]

    def __str__(self):
        return f"IPGroup({self.ip_address})"

    def storage_used_percent(self):
        if not self.storage_quota:
            return 0
        return min(100, round(self.storage_used / self.storage_quota * 100, 1))

    def storage_available(self):
        return max(0, self.storage_quota - self.storage_used)

    @staticmethod
    def _fmt(size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def human_quota(self):
        return self._fmt(self.storage_quota)

    def human_used(self):
        return self._fmt(self.storage_used)

    def human_available(self):
        return self._fmt(self.storage_available())


class AnonymousUploader(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cookie_id = models.CharField(max_length=64, unique=True, db_index=True)
    ip_group = models.ForeignKey(
        IPGroup, on_delete=models.CASCADE, related_name='uploaders'
    )
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'anonymous_uploaders'

    def __str__(self):
        return f"Anon {self.cookie_id[:12]}… @ {self.ip_group.ip_address}"
