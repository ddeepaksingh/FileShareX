import uuid
import os
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Folder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='folders')
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True, related_name='subfolders'
    )
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'folders'
        unique_together = [['owner', 'name', 'parent']]
        indexes = [models.Index(fields=['owner', 'parent'])]
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_path(self):
        parts = [self.name]
        node = self.parent
        while node:
            parts.insert(0, node.name)
            node = node.parent
        return ' / '.join(parts)


class File(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='files', null=True, blank=True
    )
    folder = models.ForeignKey(
        Folder, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='files'
    )

    # File info
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255)
    file_hash = models.CharField(max_length=64, db_index=True)  # SHA-256
    file_size = models.BigIntegerField()      # bytes
    mime_type = models.CharField(max_length=100)
    extension = models.CharField(max_length=20)

    # Soft delete / trash
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # IP group association (anonymous quick-share files)
    ip_group = models.ForeignKey(
        'ipgroup.IPGroup', on_delete=models.CASCADE,
        null=True, blank=True, related_name='files'
    )
    anonymous_uploader = models.ForeignKey(
        'ipgroup.AnonymousUploader', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='files'
    )
    expires_at = models.DateTimeField(null=True, blank=True)

    # Versioning stubs — logic added in Phase 6
    is_latest_version = models.BooleanField(default=True)
    version_number = models.IntegerField(default=1)
    parent_file = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='versions'
    )

    # Stats
    download_count = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'files'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'is_deleted']),
            models.Index(fields=['file_hash']),
            models.Index(fields=['owner', 'folder']),
            models.Index(fields=['ip_group']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return self.title

    @property
    def is_image(self):
        return self.mime_type.startswith('image/')

    @property
    def is_video(self):
        return self.mime_type.startswith('video/')

    @property
    def is_audio(self):
        return self.mime_type.startswith('audio/')

    @property
    def is_pdf(self):
        return self.mime_type == 'application/pdf'

    @property
    def is_previewable(self):
        return self.is_image or self.is_video or self.is_audio or self.is_pdf

    @property
    def icon(self):
        if self.is_image:
            return '🖼'
        if self.is_video:
            return '🎬'
        if self.is_audio:
            return '🎵'
        if self.is_pdf:
            return '📄'
        ext = self.extension.lower()
        if ext in {'.zip', '.tar', '.gz', '.rar', '.7z'}:
            return '📦'
        if ext in {'.doc', '.docx', '.txt', '.md'}:
            return '📝'
        if ext in {'.xls', '.xlsx', '.csv'}:
            return '📊'
        return '📁'

    def human_size(self):
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class ChunkUpload(models.Model):
    upload_id = models.CharField(max_length=64, unique=True, db_index=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chunk_uploads')
    original_filename = models.CharField(max_length=255)
    total_chunks = models.IntegerField()
    received_chunks = models.IntegerField(default=0)
    file_size = models.BigIntegerField(default=0)
    temp_dir = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chunk_uploads'

    def __str__(self):
        return f"{self.original_filename} ({self.received_chunks}/{self.total_chunks})"
