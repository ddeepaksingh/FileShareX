import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    profile_photo = models.ImageField(upload_to='profiles/', null=True, blank=True)
    storage_quota = models.BigIntegerField(default=5_368_709_120)  # 5 GB
    storage_used = models.BigIntegerField(default=0)
    email_notifications = models.BooleanField(default=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
        ]

    def __str__(self):
        return self.email

    def storage_quota_display(self):
        return self._bytes_to_human(self.storage_quota)

    def storage_used_display(self):
        return self._bytes_to_human(self.storage_used)

    def storage_used_percent(self):
        if self.storage_quota == 0:
            return 0
        return round((self.storage_used / self.storage_quota) * 100, 1)

    @staticmethod
    def _bytes_to_human(size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
