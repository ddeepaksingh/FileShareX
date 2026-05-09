import uuid

from django.conf import settings
from django.db import models


class Group(models.Model):
    PRIVACY_PRIVATE = 'private'
    PRIVACY_PUBLIC = 'public'
    PRIVACY_INVITE_ONLY = 'invite_only'
    PRIVACY_CHOICES = [
        (PRIVACY_PRIVATE, 'Private'),
        (PRIVACY_PUBLIC, 'Public'),
        (PRIVACY_INVITE_ONLY, 'Invite Only'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_groups',
    )

    privacy = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default=PRIVACY_PRIVATE)
    allow_join_requests = models.BooleanField(default=True)

    storage_quota = models.BigIntegerField(default=10 * 1024 ** 3)  # 10 GB
    storage_used = models.BigIntegerField(default=0)

    is_archived = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'groups_group'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner']),
            models.Index(fields=['privacy']),
        ]

    def __str__(self):
        return self.name

    def storage_used_percent(self):
        if self.storage_quota == 0:
            return 0
        return min(round((self.storage_used / self.storage_quota) * 100), 100)

    def storage_quota_display(self):
        return self._bytes_to_human(self.storage_quota)

    def storage_used_display(self):
        return self._bytes_to_human(self.storage_used)

    def storage_free_display(self):
        return self._bytes_to_human(max(self.storage_quota - self.storage_used, 0))

    @staticmethod
    def _bytes_to_human(size):
        for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    def member_count(self):
        return self.memberships.filter(is_active=True).count()

    def file_count(self):
        return self.files.filter(is_deleted=False).count()

    def is_member(self, user):
        if not user or not user.is_authenticated:
            return False
        return self.memberships.filter(user=user, is_active=True).exists()

    def get_membership(self, user):
        if not user or not user.is_authenticated:
            return None
        return self.memberships.filter(user=user, is_active=True).first()

    def can_manage(self, user):
        """True for owner or admin member."""
        if user == self.owner:
            return True
        m = self.get_membership(user)
        return m is not None and m.is_admin()


class GroupMembership(models.Model):
    ROLE_ADMIN = 'admin'
    ROLE_MEMBER = 'member'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_MEMBER, 'Member'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_memberships',
    )
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_MEMBER)

    can_upload = models.BooleanField(default=True)
    can_download = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'groups_membership'
        unique_together = [['user', 'group']]
        indexes = [
            models.Index(fields=['user', 'group']),
            models.Index(fields=['group', 'role']),
        ]

    def __str__(self):
        return f"{self.user.username} in {self.group.name} ({self.role})"

    def is_admin(self):
        return self.role == self.ROLE_ADMIN
