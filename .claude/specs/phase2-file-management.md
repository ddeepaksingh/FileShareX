# Phase 2: File Management System — Feature Specification

**Phase:** 2 of 6  
**Feature Area:** File Upload, Listing, Search, Preview, Download, Trash & Quota  
**Estimated Time:** 2–3 days  
**Status:** Ready for Implementation  
**Date:** May 2026  
**Depends On:** Phase 1 (User System)

---

## Scope

This phase delivers the complete file management layer for authenticated users — private file uploads, listing, browsing, searching, previewing, downloading, soft deletion (trash), and storage quota enforcement.

**Included:**
- `files` app scaffolding (`File`, `Folder`, `ChunkUpload` models)
- Chunked upload with progress bar (5MB chunks, retry logic)
- Drag-and-drop upload UI
- Upload destination: Private only (group/IP Group upload in later phases)
- My Files page (list, grid view toggle, sort, filter)
- Global search across file names
- File preview (images, PDFs, videos, audio)
- File download (direct + streaming for large files)
- Soft delete → Trash → 30-day auto-cleanup
- Storage quota display and enforcement (hard block at limit)
- Root Folder auto-creation on signup
- Basic folder creation and navigation

**Not included in this phase:**
- Group file upload (Phase 4)
- IP Group / anonymous upload (Phase 3)
- File versioning (Phase 6)
- Duplicate detection UI (Phase 6)
- Public share links (Phase 6)
- Notifications (Phase 6)

---

## Project Structure to Create/Extend

```
apps/
└── files/
    ├── migrations/
    ├── __init__.py
    ├── models.py          # File, Folder, ChunkUpload
    ├── views.py           # Upload, list, detail, delete, download, trash
    ├── forms.py           # UploadForm, FolderForm
    ├── urls.py
    ├── utils.py           # hash calculation, mime detection, quota helpers
    ├── services.py        # FileUploadService, TrashService
    ├── validators.py      # File type, size, extension validation
    └── tests/
        ├── __init__.py
        ├── test_models.py
        ├── test_upload.py
        ├── test_views.py
        └── test_validators.py

templates/
└── files/
    ├── my_files.html      # Main file listing page
    ├── upload.html        # Upload page / modal
    ├── detail.html        # File detail / preview
    ├── trash.html         # Trash listing page
    └── _file_card.html    # Reusable file card partial

static/
├── js/
│   ├── file-upload.js     # Chunked upload + drag-drop
│   └── file-preview.js    # Inline preview logic
└── css/
    └── files.css          # Upload zone, progress bar, grid/list styles
```

---

## Models

### File Model

```python
# apps/files/models.py

import uuid
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

    def __str__(self):
        return self.name


class File(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='files')
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
    file_size = models.BigIntegerField()          # bytes
    mime_type = models.CharField(max_length=100)
    extension = models.CharField(max_length=20)

    # Soft delete / trash
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Versioning (populated in Phase 6 — columns created now)
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
            models.Index(fields=['owner', '-created_at']),
            models.Index(fields=['folder']),
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
    def human_size(self):
        """Return human-readable file size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024
        return f"{self.file_size:.1f} TB"


class ChunkUpload(models.Model):
    """Tracks in-progress chunked uploads."""
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
```

---

## Validators

```python
# apps/files/validators.py

import os
import magic
from django.core.exceptions import ValidationError

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

BLOCKED_EXTENSIONS = {
    '.exe', '.bat', '.cmd', '.sh', '.ps1', '.msi',
    '.dll', '.so', '.dylib', '.jar', '.vbs', '.js',
}

BLOCKED_MIME_TYPES = {
    'application/x-msdownload',
    'application/x-sh',
    'text/x-shellscript',
    'application/x-executable',
}


def validate_file_upload(file_obj):
    """Run all validation checks on an uploaded file. Raises ValidationError on failure."""

    if file_obj.size > MAX_FILE_SIZE:
        raise ValidationError(
            f"File exceeds maximum size of 100 MB. Your file is "
            f"{file_obj.size / (1024*1024):.1f} MB."
        )

    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext in BLOCKED_EXTENSIONS:
        raise ValidationError(f"File type '{ext}' is not allowed.")

    header = file_obj.read(2048)
    file_obj.seek(0)
    detected_mime = magic.from_buffer(header, mime=True)

    if detected_mime in BLOCKED_MIME_TYPES:
        raise ValidationError(f"File content type '{detected_mime}' is not allowed.")
```

---

## Services

### FileUploadService

```python
# apps/files/services.py

import hashlib
import os
import shutil
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import File, ChunkUpload, Folder
from .validators import validate_file_upload


class QuotaExceededError(Exception):
    pass


class FileUploadService:

    # ------------------------------------------------------------------ #
    # Chunked upload                                                       #
    # ------------------------------------------------------------------ #

    def receive_chunk(self, upload_id, chunk_index, chunk_data, owner,
                      original_filename, total_chunks, file_size):
        """
        Save one chunk to a temp directory.
        Returns ChunkUpload with updated received_chunks count.
        """
        upload, _ = ChunkUpload.objects.get_or_create(
            upload_id=upload_id,
            defaults={
                'owner': owner,
                'original_filename': original_filename,
                'total_chunks': total_chunks,
                'file_size': file_size,
                'temp_dir': os.path.join(
                    settings.MEDIA_ROOT, 'temp', upload_id
                ),
            }
        )
        os.makedirs(upload.temp_dir, exist_ok=True)

        chunk_path = os.path.join(upload.temp_dir, f'chunk_{chunk_index:05d}')
        with open(chunk_path, 'wb') as f:
            f.write(chunk_data)

        upload.received_chunks += 1
        upload.save(update_fields=['received_chunks'])
        return upload

    def finalize_upload(self, upload_id, owner, destination='private',
                        title=None, description='', folder_id=None):
        """
        Assemble chunks, validate the assembled file, check quota, save File record.
        Returns the saved File instance.
        """
        try:
            upload = ChunkUpload.objects.get(upload_id=upload_id, owner=owner)
        except ChunkUpload.DoesNotExist:
            raise ValidationError("Upload session not found.")

        if upload.received_chunks != upload.total_chunks:
            raise ValidationError(
                f"Incomplete upload: received {upload.received_chunks} "
                f"of {upload.total_chunks} chunks."
            )

        assembled_path = os.path.join(upload.temp_dir, 'assembled')
        self._assemble_chunks(upload.temp_dir, assembled_path, upload.total_chunks)

        # Validate assembled file (mime, extension, size)
        with open(assembled_path, 'rb') as f:
            class _FakeFile:
                def __init__(self, fh, name, size):
                    self._fh = fh
                    self.name = name
                    self.size = size
                def read(self, n=-1): return self._fh.read(n)
                def seek(self, pos): self._fh.seek(pos)
            fake = _FakeFile(f, upload.original_filename, upload.file_size)
            validate_file_upload(fake)

        self._check_quota(owner, upload.file_size)

        file_hash = self._hash_file(assembled_path)
        folder = self._resolve_folder(owner, folder_id)
        saved_path = self._move_to_media(assembled_path, upload.original_filename)

        import magic as _magic
        with open(os.path.join(settings.MEDIA_ROOT, saved_path), 'rb') as f:
            mime = _magic.from_buffer(f.read(2048), mime=True)

        import os as _os
        ext = _os.path.splitext(upload.original_filename)[1].lower()

        file_instance = File.objects.create(
            owner=owner,
            folder=folder,
            title=title or upload.original_filename,
            description=description,
            file=saved_path,
            original_filename=upload.original_filename,
            file_hash=file_hash,
            file_size=upload.file_size,
            mime_type=mime,
            extension=ext,
        )

        owner.storage_used = (owner.storage_used or 0) + upload.file_size
        owner.save(update_fields=['storage_used'])

        shutil.rmtree(upload.temp_dir, ignore_errors=True)
        upload.delete()

        return file_instance

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _assemble_chunks(self, temp_dir, output_path, total_chunks):
        with open(output_path, 'wb') as out:
            for i in range(total_chunks):
                chunk_path = os.path.join(temp_dir, f'chunk_{i:05d}')
                with open(chunk_path, 'rb') as c:
                    out.write(c.read())

    def _hash_file(self, path):
        sha256 = hashlib.sha256()
        with open(path, 'rb') as f:
            for block in iter(lambda: f.read(65536), b''):
                sha256.update(block)
        return sha256.hexdigest()

    def _check_quota(self, user, new_file_size):
        if (user.storage_used or 0) + new_file_size > user.storage_quota:
            raise QuotaExceededError(
                "Storage quota exceeded. Free up space or upgrade your plan."
            )

    def _resolve_folder(self, owner, folder_id):
        if folder_id:
            return Folder.objects.get(id=folder_id, owner=owner)
        return Folder.objects.filter(owner=owner, parent=None).first()

    def _move_to_media(self, assembled_path, original_filename):
        from django.utils import timezone
        now = timezone.now()
        rel_dir = f"uploads/{now.year}/{now.month:02d}/{now.day:02d}"
        abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)

        unique_name = f"{uuid.uuid4().hex}_{original_filename}"
        dest = os.path.join(abs_dir, unique_name)
        shutil.move(assembled_path, dest)
        return f"{rel_dir}/{unique_name}"


class TrashService:

    def soft_delete(self, file: File, user):
        """Move file to trash (soft delete)."""
        if file.owner != user:
            raise PermissionError("You do not own this file.")
        file.is_deleted = True
        file.deleted_at = timezone.now()
        file.save(update_fields=['is_deleted', 'deleted_at'])

    def restore(self, file: File, user):
        """Restore file from trash."""
        if file.owner != user:
            raise PermissionError("You do not own this file.")
        file.is_deleted = False
        file.deleted_at = None
        file.save(update_fields=['is_deleted', 'deleted_at'])

    def permanent_delete(self, file: File, user):
        """Permanently delete file from storage and DB, reclaim quota."""
        if file.owner != user:
            raise PermissionError("You do not own this file.")
        storage_path = file.file.path
        reclaim = file.file_size

        file.delete()

        if os.path.exists(storage_path):
            os.remove(storage_path)

        user.storage_used = max(0, (user.storage_used or 0) - reclaim)
        user.save(update_fields=['storage_used'])
```

---

## URL Configuration

```python
# apps/files/urls.py

from django.urls import path
from . import views

app_name = 'files'

urlpatterns = [
    # Upload
    path('upload/', views.upload_page, name='upload'),
    path('upload/chunk/', views.receive_chunk, name='upload_chunk'),
    path('upload/finalize/', views.finalize_upload, name='upload_finalize'),

    # Listing & detail
    path('', views.my_files, name='my_files'),
    path('<uuid:file_id>/', views.file_detail, name='detail'),
    path('<uuid:file_id>/download/', views.file_download, name='download'),

    # Folder
    path('folder/create/', views.create_folder, name='create_folder'),
    path('folder/<uuid:folder_id>/', views.folder_view, name='folder'),

    # Trash
    path('trash/', views.trash, name='trash'),
    path('<uuid:file_id>/delete/', views.delete_file, name='delete'),
    path('<uuid:file_id>/restore/', views.restore_file, name='restore'),
    path('<uuid:file_id>/destroy/', views.destroy_file, name='destroy'),
]
```

---

## Views

```python
# apps/files/views.py

import json
import mimetypes
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import (
    FileResponse, Http404, JsonResponse, StreamingHttpResponse
)
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import File, Folder
from .services import FileUploadService, QuotaExceededError, TrashService

upload_service = FileUploadService()
trash_service = TrashService()


# ------------------------------------------------------------------ #
# Upload                                                               #
# ------------------------------------------------------------------ #

@login_required
def upload_page(request):
    folders = Folder.objects.filter(owner=request.user, is_deleted=False)
    return render(request, 'files/upload.html', {'folders': folders})


@login_required
@require_POST
def receive_chunk(request):
    data = request.POST
    chunk = request.FILES.get('chunk')
    if not chunk:
        return JsonResponse({'error': 'No chunk data'}, status=400)

    try:
        upload = upload_service.receive_chunk(
            upload_id=data['upload_id'],
            chunk_index=int(data['chunk_index']),
            chunk_data=chunk.read(),
            owner=request.user,
            original_filename=data['file_name'],
            total_chunks=int(data['total_chunks']),
            file_size=int(data['file_size']),
        )
        return JsonResponse({
            'received': upload.received_chunks,
            'total': upload.total_chunks,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def finalize_upload(request):
    data = json.loads(request.body)
    try:
        file_instance = upload_service.finalize_upload(
            upload_id=data['upload_id'],
            owner=request.user,
            title=data.get('title', ''),
            description=data.get('description', ''),
            folder_id=data.get('folder_id'),
        )
        return JsonResponse({'file_id': str(file_instance.id), 'success': True})
    except QuotaExceededError as e:
        return JsonResponse({'error': str(e), 'quota_exceeded': True}, status=413)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ------------------------------------------------------------------ #
# Listing                                                              #
# ------------------------------------------------------------------ #

@login_required
def my_files(request):
    qs = File.objects.filter(owner=request.user, is_deleted=False)

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(original_filename__icontains=q))

    # Filter by type
    file_type = request.GET.get('type', '')
    type_map = {
        'image': 'image/',
        'video': 'video/',
        'audio': 'audio/',
        'document': 'application/pdf',
    }
    if file_type in type_map:
        qs = qs.filter(mime_type__startswith=type_map[file_type])

    # Sort
    sort = request.GET.get('sort', '-created_at')
    allowed_sorts = {
        'name': 'title', '-name': '-title',
        'size': 'file_size', '-size': '-file_size',
        'date': 'created_at', '-date': '-created_at',
    }
    qs = qs.order_by(allowed_sorts.get(sort, '-created_at'))

    # Folder context
    folder_id = request.GET.get('folder')
    current_folder = None
    if folder_id:
        current_folder = get_object_or_404(Folder, id=folder_id, owner=request.user)
        qs = qs.filter(folder=current_folder)
    else:
        qs = qs.filter(folder__isnull=True) if not q else qs

    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page', 1))

    folders = Folder.objects.filter(
        owner=request.user,
        parent=current_folder,
        is_deleted=False
    )

    user = request.user
    quota_pct = round((user.storage_used / user.storage_quota) * 100, 1) if user.storage_quota else 0

    return render(request, 'files/my_files.html', {
        'page_obj': page,
        'folders': folders,
        'current_folder': current_folder,
        'search_query': q,
        'file_type': file_type,
        'sort': sort,
        'quota_pct': quota_pct,
        'storage_used': user.storage_used,
        'storage_quota': user.storage_quota,
    })


# ------------------------------------------------------------------ #
# Detail & Preview                                                     #
# ------------------------------------------------------------------ #

@login_required
def file_detail(request, file_id):
    file = get_object_or_404(File, id=file_id, owner=request.user, is_deleted=False)
    file.view_count += 1
    file.save(update_fields=['view_count'])
    return render(request, 'files/detail.html', {'file': file})


# ------------------------------------------------------------------ #
# Download                                                             #
# ------------------------------------------------------------------ #

@login_required
def file_download(request, file_id):
    file = get_object_or_404(File, id=file_id, owner=request.user, is_deleted=False)

    file.download_count += 1
    file.save(update_fields=['download_count'])

    response = FileResponse(
        open(file.file.path, 'rb'),
        as_attachment=True,
        filename=file.original_filename,
    )
    return response


# ------------------------------------------------------------------ #
# Folder                                                               #
# ------------------------------------------------------------------ #

@login_required
@require_POST
def create_folder(request):
    name = request.POST.get('name', '').strip()
    parent_id = request.POST.get('parent_id')

    if not name:
        messages.error(request, 'Folder name is required.')
        return redirect('files:my_files')

    parent = None
    if parent_id:
        parent = get_object_or_404(Folder, id=parent_id, owner=request.user)

    Folder.objects.get_or_create(owner=request.user, name=name, parent=parent)
    return redirect('files:my_files')


@login_required
def folder_view(request, folder_id):
    return redirect(f"{request.path_info}?folder={folder_id}")


# ------------------------------------------------------------------ #
# Trash                                                                #
# ------------------------------------------------------------------ #

@login_required
def trash(request):
    qs = File.objects.filter(owner=request.user, is_deleted=True).order_by('-deleted_at')
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'files/trash.html', {'page_obj': page})


@login_required
@require_POST
def delete_file(request, file_id):
    file = get_object_or_404(File, id=file_id, owner=request.user, is_deleted=False)
    trash_service.soft_delete(file, request.user)
    messages.success(request, f'"{file.title}" moved to trash.')
    return redirect('files:my_files')


@login_required
@require_POST
def restore_file(request, file_id):
    file = get_object_or_404(File, id=file_id, owner=request.user, is_deleted=True)
    trash_service.restore(file, request.user)
    messages.success(request, f'"{file.title}" restored.')
    return redirect('files:trash')


@login_required
@require_POST
def destroy_file(request, file_id):
    file = get_object_or_404(File, id=file_id, owner=request.user, is_deleted=True)
    title = file.title
    trash_service.permanent_delete(file, request.user)
    messages.success(request, f'"{title}" permanently deleted.')
    return redirect('files:trash')
```

---

## Frontend: JavaScript Chunked Upload

```javascript
// static/js/file-upload.js

class FileUploader {
    constructor(options) {
        this.uploadUrl   = options.uploadUrl;
        this.finalizeUrl = options.finalizeUrl;
        this.csrfToken   = options.csrfToken;
        this.chunkSize   = 5 * 1024 * 1024;  // 5 MB
        this.maxRetries  = 3;
        this.onProgress  = options.onProgress  || (() => {});
        this.onSuccess   = options.onSuccess   || (() => {});
        this.onError     = options.onError     || ((e) => console.error(e));
    }

    generateUploadId() {
        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    async upload(file, metadata = {}) {
        const uploadId    = this.generateUploadId();
        const totalChunks = Math.ceil(file.size / this.chunkSize);

        for (let i = 0; i < totalChunks; i++) {
            const start = i * this.chunkSize;
            const chunk = file.slice(start, start + this.chunkSize);
            await this._sendChunk(chunk, {
                upload_id:    uploadId,
                chunk_index:  i,
                total_chunks: totalChunks,
                file_name:    file.name,
                file_size:    file.size,
            });
            this.onProgress(Math.round(((i + 1) / totalChunks) * 100));
        }

        const result = await this._finalize(uploadId, { ...metadata, file_name: file.name });
        this.onSuccess(result);
        return result;
    }

    async _sendChunk(chunkBlob, meta) {
        const formData = new FormData();
        formData.append('chunk', chunkBlob);
        Object.entries(meta).forEach(([k, v]) => formData.append(k, v));

        return this._retry(() =>
            fetch(this.uploadUrl, {
                method: 'POST',
                headers: { 'X-CSRFToken': this.csrfToken },
                body: formData,
            }).then(r => { if (!r.ok) throw new Error('Chunk upload failed'); return r.json(); })
        );
    }

    async _finalize(uploadId, metadata) {
        const resp = await fetch(this.finalizeUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken,
            },
            body: JSON.stringify({ upload_id: uploadId, ...metadata }),
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || 'Finalize failed');
        return data;
    }

    async _retry(fn, attempt = 0) {
        try {
            return await fn();
        } catch (err) {
            if (attempt >= this.maxRetries - 1) throw err;
            await new Promise(r => setTimeout(r, 1000 * (attempt + 1)));
            return this._retry(fn, attempt + 1);
        }
    }
}


// Drag-and-drop wiring
function initDropZone(zoneEl, uploader) {
    zoneEl.addEventListener('dragover', e => {
        e.preventDefault();
        zoneEl.classList.add('drag-over');
    });
    zoneEl.addEventListener('dragleave', () => zoneEl.classList.remove('drag-over'));
    zoneEl.addEventListener('drop', e => {
        e.preventDefault();
        zoneEl.classList.remove('drag-over');
        [...e.dataTransfer.files].forEach(file => uploader.upload(file));
    });
}
```

---

## Frontend: Key Templates (Skeleton)

### my_files.html

```html
{% extends "base.html" %}
{% block content %}

<!-- Storage quota bar -->
<div class="quota-bar">
  <span>{{ storage_used|filesizeformat }} of {{ storage_quota|filesizeformat }} used</span>
  <div class="bar"><div class="fill" style="width: {{ quota_pct }}%"></div></div>
</div>

<!-- Search + filter toolbar -->
<form method="get">
  <input name="q" value="{{ search_query }}" placeholder="Search files…">
  <select name="type">
    <option value="">All types</option>
    <option value="image" {% if file_type == "image" %}selected{% endif %}>Images</option>
    <option value="video" {% if file_type == "video" %}selected{% endif %}>Videos</option>
    <option value="audio" {% if file_type == "audio" %}selected{% endif %}>Audio</option>
    <option value="document" {% if file_type == "document" %}selected{% endif %}>Documents</option>
  </select>
  <select name="sort">
    <option value="-date">Newest first</option>
    <option value="date">Oldest first</option>
    <option value="name">Name A–Z</option>
    <option value="-size">Largest first</option>
  </select>
  <button type="submit">Filter</button>
</form>

<!-- Folder breadcrumb -->
{% if current_folder %}
  <nav>
    <a href="{% url 'files:my_files' %}">My Files</a> / {{ current_folder.name }}
  </nav>
{% endif %}

<!-- Sub-folders -->
{% for folder in folders %}
  <a href="{% url 'files:my_files' %}?folder={{ folder.id }}">📁 {{ folder.name }}</a>
{% endfor %}

<!-- File grid -->
<div class="file-grid">
  {% for file in page_obj %}
    {% include "files/_file_card.html" with file=file %}
  {% empty %}
    <p>No files yet. <a href="{% url 'files:upload' %}">Upload one →</a></p>
  {% endfor %}
</div>

{% include "includes/pagination.html" with page_obj=page_obj %}
{% endblock %}
```

### _file_card.html

```html
<div class="file-card">
  <!-- Thumbnail / icon -->
  {% if file.is_image %}
    <img src="{{ file.file.url }}" alt="{{ file.title }}" loading="lazy">
  {% else %}
    <span class="icon icon-{{ file.extension }}"></span>
  {% endif %}

  <h4><a href="{% url 'files:detail' file.id %}">{{ file.title }}</a></h4>
  <p>{{ file.human_size }} · {{ file.created_at|date:"d M Y" }}</p>

  <div class="actions">
    <a href="{% url 'files:download' file.id %}">Download</a>
    <form method="post" action="{% url 'files:delete' file.id %}">
      {% csrf_token %}
      <button type="submit" onclick="return confirm('Move to trash?')">Delete</button>
    </form>
  </div>
</div>
```

### detail.html (preview)

```html
{% extends "base.html" %}
{% block content %}
<h2>{{ file.title }}</h2>
<p>{{ file.description }}</p>
<p>{{ file.human_size }} · {{ file.mime_type }} · {{ file.created_at|date }}</p>

{% if file.is_image %}
  <img src="{{ file.file.url }}" style="max-width:100%">

{% elif file.is_pdf %}
  <iframe src="{{ file.file.url }}" width="100%" height="800px"></iframe>

{% elif file.is_video %}
  <video controls style="max-width:100%">
    <source src="{{ file.file.url }}" type="{{ file.mime_type }}">
  </video>

{% elif file.is_audio %}
  <audio controls>
    <source src="{{ file.file.url }}" type="{{ file.mime_type }}">
  </audio>

{% else %}
  <p>No preview available.</p>
{% endif %}

<a href="{% url 'files:download' file.id %}">⬇ Download</a>
{% endblock %}
```

---

## Background Task: Trash Cleanup

```python
# apps/files/tasks.py

import os
from celery import shared_task
from django.utils import timezone
from datetime import timedelta


@shared_task
def cleanup_trash():
    """Permanently delete files that have been in trash for 30+ days."""
    from .models import File
    from django.conf import settings

    cutoff = timezone.now() - timedelta(days=30)
    old_trash = File.objects.filter(
        is_deleted=True,
        deleted_at__lt=cutoff,
        ip_group__isnull=True,   # IP Group files have their own expiry (Phase 3)
    )

    for file in old_trash:
        path = file.file.path
        owner = file.owner
        size = file.file_size

        file.delete()

        if os.path.exists(path):
            os.remove(path)

        owner.storage_used = max(0, (owner.storage_used or 0) - size)
        owner.save(update_fields=['storage_used'])
```

---

## Celery Beat Schedule (add to existing)

```python
# config/settings/base.py — append to CELERY_BEAT_SCHEDULE

'cleanup-trash': {
    'task': 'apps.files.tasks.cleanup_trash',
    'schedule': crontab(hour=2, minute=0),   # Daily at 2 AM
},
```

---

## Signup Signal: Create Root Folder

```python
# apps/accounts/signals.py  (add to existing)

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()


@receiver(post_save, sender=User)
def create_root_folder(sender, instance, created, **kwargs):
    if created:
        from apps.files.models import Folder
        Folder.objects.get_or_create(
            owner=instance,
            name='My Files',
            parent=None,
        )
```

---

## Settings Additions

```python
# config/settings/base.py

# File upload
MAX_UPLOAD_SIZE = 100 * 1024 * 1024   # 100 MB
CHUNK_SIZE      = 5  * 1024 * 1024   # 5 MB

# Media
MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Temp chunk storage
CHUNK_TEMP_DIR = MEDIA_ROOT / 'temp'
```

---

## URL Root Registration

```python
# config/urls.py  (add)

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    ...
    path('files/', include('apps.files.urls', namespace='files')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

---

## Tests

```python
# apps/files/tests/test_upload.py

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.files.services import FileUploadService, QuotaExceededError


@pytest.mark.django_db
class TestChunkUpload:

    def test_receive_and_finalize(self, user, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        service = FileUploadService()

        content = b'hello world'
        upload = service.receive_chunk(
            upload_id='test-001',
            chunk_index=0,
            chunk_data=content,
            owner=user,
            original_filename='hello.txt',
            total_chunks=1,
            file_size=len(content),
        )
        assert upload.received_chunks == 1

        file_instance = service.finalize_upload(
            upload_id='test-001',
            owner=user,
            title='Hello',
        )
        assert file_instance.owner == user
        assert file_instance.file_size == len(content)
        assert file_instance.file_hash != ''

    def test_quota_enforcement(self, user, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        user.storage_quota = 100
        user.storage_used = 90
        user.save()

        service = FileUploadService()
        content = b'x' * 20

        service.receive_chunk(
            upload_id='test-002', chunk_index=0, chunk_data=content,
            owner=user, original_filename='big.txt',
            total_chunks=1, file_size=len(content),
        )

        with pytest.raises(QuotaExceededError):
            service.finalize_upload('test-002', owner=user)


@pytest.mark.django_db
class TestTrash:

    def test_soft_delete_and_restore(self, user, uploaded_file):
        from apps.files.services import TrashService
        svc = TrashService()

        svc.soft_delete(uploaded_file, user)
        uploaded_file.refresh_from_db()
        assert uploaded_file.is_deleted is True
        assert uploaded_file.deleted_at is not None

        svc.restore(uploaded_file, user)
        uploaded_file.refresh_from_db()
        assert uploaded_file.is_deleted is False
```

```python
# apps/files/tests/test_validators.py

import pytest
from io import BytesIO
from django.core.exceptions import ValidationError
from apps.files.validators import validate_file_upload, MAX_FILE_SIZE


def test_blocked_extension():
    class FakeFile:
        name = 'virus.exe'
        size = 100
        def read(self, n=-1): return b'\x4d\x5a'  # MZ header
        def seek(self, pos): pass

    with pytest.raises(ValidationError, match="not allowed"):
        validate_file_upload(FakeFile())


def test_file_too_large():
    class FakeFile:
        name = 'big.txt'
        size = MAX_FILE_SIZE + 1
        def read(self, n=-1): return b'a'
        def seek(self, pos): pass

    with pytest.raises(ValidationError, match="exceeds maximum"):
        validate_file_upload(FakeFile())
```

---

## Security Checklist

| Concern | Mitigation |
|---|---|
| Path traversal in filenames | UUID-prefixed storage path, never use raw filename on disk |
| Extension spoofing | MIME type verified from file header via `python-magic`, not just extension |
| Quota bypass via concurrent uploads | Quota check happens at finalize; race condition risk is low for MVP — add DB-level constraint in Phase 6 |
| Oversized chunks | Django's `DATA_UPLOAD_MAX_MEMORY_SIZE` limits individual request body |
| Unauthenticated upload | All upload endpoints behind `@login_required` |
| Serving user files | Always serve via `FileResponse`, never expose raw paths in URLs |
| CSRF on POST endpoints | `@require_POST` + Django CSRF middleware; JS sends `X-CSRFToken` header |

---

## New Dependencies

Add to `requirements/base.txt`:

```
python-magic==0.4.27        # MIME type detection from file header
Pillow>=10.0                 # Thumbnail generation (used in Phase 6, model ready now)
celery>=5.3                  # Background tasks
```

---

## Migrations to Run

```bash
python manage.py makemigrations files
python manage.py migrate
```

---

## Implementation Checklist

### Models & DB
- [ ] Create `apps/files/` app, add to `INSTALLED_APPS`
- [ ] Define `Folder`, `File`, `ChunkUpload` models
- [ ] Run migrations
- [ ] Register models in `apps/files/admin.py`

### Upload Backend
- [ ] Implement `validate_file_upload` in `validators.py`
- [ ] Implement `FileUploadService.receive_chunk` and `finalize_upload`
- [ ] Wire chunk upload views + URLs
- [ ] Test chunk assembly and hash calculation

### My Files Page
- [ ] Implement `my_files` view with search, filter, sort, pagination
- [ ] Build `my_files.html`, `_file_card.html` templates
- [ ] Render storage quota bar

### File Detail & Preview
- [ ] Implement `file_detail` view + template
- [ ] Image preview (`<img>`)
- [ ] PDF preview (`<iframe>`)
- [ ] Video preview (`<video>`)
- [ ] Audio preview (`<audio>`)

### Download
- [ ] Implement `file_download` view using `FileResponse`
- [ ] Increment `download_count`

### Folders
- [ ] Auto-create root folder via `post_save` signal on User
- [ ] `create_folder` view
- [ ] Folder navigation in `my_files` view

### Trash
- [ ] `TrashService` (soft delete, restore, permanent delete)
- [ ] Trash listing page
- [ ] `cleanup_trash` Celery task + Beat schedule

### Frontend JS
- [ ] `FileUploader` class with chunked upload and retry
- [ ] Drag-and-drop zone wiring (`initDropZone`)
- [ ] Progress bar UI

### Tests
- [ ] `test_upload.py` — chunk receive, finalize, quota enforcement
- [ ] `test_validators.py` — blocked extension, oversized file
- [ ] `test_views.py` — auth required, soft delete, restore
- [ ] `test_models.py` — `human_size`, `is_image`, `is_pdf` properties

---

## Phase 2 → Phase 3 Handoff

When Phase 3 (IP Group) starts, the `File` model already has:
- `ip_group = ForeignKey(...)` — currently `null=True` — just populate it
- `expires_at` field — IP Group expiry will use this

No model changes needed in Phase 3 for the file table.

---

**Document Status:** Ready for Implementation  
**Estimated Time:** 2–3 days  
**Next Phase:** Phase 3 — IP Group Anonymous Sharing
