import hashlib
import mimetypes
import os
import shutil
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import ChunkUpload, File, Folder
from .validators import validate_file_upload


class QuotaExceededError(Exception):
    pass


class FileUploadService:

    # ------------------------------------------------------------------ #
    # Chunked upload                                                       #
    # ------------------------------------------------------------------ #

    def receive_chunk(self, upload_id, chunk_index, chunk_data,
                      owner, original_filename, total_chunks, file_size):
        """
        Persist one chunk to a temp directory.
        Returns the ChunkUpload record with updated received_chunks.
        """
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp', str(owner.pk), upload_id)

        upload, _ = ChunkUpload.objects.get_or_create(
            upload_id=upload_id,
            defaults={
                'owner': owner,
                'original_filename': original_filename,
                'total_chunks': total_chunks,
                'file_size': file_size,
                'temp_dir': temp_dir,
            },
        )

        os.makedirs(upload.temp_dir, exist_ok=True)

        chunk_path = os.path.join(upload.temp_dir, f'chunk_{chunk_index:05d}')
        with open(chunk_path, 'wb') as f:
            f.write(chunk_data)

        ChunkUpload.objects.filter(pk=upload.pk).update(
            received_chunks=upload.received_chunks + 1
        )
        upload.refresh_from_db()
        return upload

    def finalize_upload(self, upload_id, owner, destination='private',
                        title=None, description='', folder_id=None):
        """
        Assemble chunks → validate → quota check → save File record.
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

        assembled_path = os.path.join(upload.temp_dir, '_assembled')
        self._assemble_chunks(upload.temp_dir, assembled_path, upload.total_chunks)

        # Validate the assembled file
        class _AssembledFile:
            def __init__(self, path, name, size):
                self._path = path
                self.name = name
                self.size = size
                self._fh = open(path, 'rb')

            def read(self, n=-1):
                return self._fh.read(n)

            def seek(self, pos):
                self._fh.seek(pos)

            def close(self):
                self._fh.close()

        fake_file = _AssembledFile(assembled_path, upload.original_filename, upload.file_size)
        try:
            validate_file_upload(fake_file)
        finally:
            fake_file.close()

        self._check_quota(owner, upload.file_size)

        file_hash = self._hash_file(assembled_path)
        mime_type = self._detect_mime(assembled_path, upload.original_filename)
        ext = os.path.splitext(upload.original_filename)[1].lower()
        folder = self._resolve_folder(owner, folder_id)
        saved_relative = self._move_to_media(assembled_path, upload.original_filename)

        file_instance = File.objects.create(
            owner=owner,
            folder=folder,
            title=title.strip() if title and title.strip() else upload.original_filename,
            description=description,
            file=saved_relative,
            original_filename=upload.original_filename,
            file_hash=file_hash,
            file_size=upload.file_size,
            mime_type=mime_type,
            extension=ext,
        )

        # Update storage usage
        owner.refresh_from_db(fields=['storage_used'])
        owner.storage_used += upload.file_size
        owner.save(update_fields=['storage_used'])

        # Clean up temp files
        shutil.rmtree(upload.temp_dir, ignore_errors=True)
        upload.delete()

        return file_instance

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _assemble_chunks(self, temp_dir, output_path, total_chunks):
        with open(output_path, 'wb') as out:
            for i in range(total_chunks):
                chunk_path = os.path.join(temp_dir, f'chunk_{i:05d}')
                with open(chunk_path, 'rb') as c:
                    shutil.copyfileobj(c, out)

    def _hash_file(self, path):
        sha256 = hashlib.sha256()
        with open(path, 'rb') as f:
            for block in iter(lambda: f.read(65536), b''):
                sha256.update(block)
        return sha256.hexdigest()

    def _detect_mime(self, path, filename):
        try:
            import magic as _magic
            with open(path, 'rb') as f:
                return _magic.from_buffer(f.read(2048), mime=True)
        except ImportError:
            guessed, _ = mimetypes.guess_type(filename)
            return guessed or 'application/octet-stream'

    def _check_quota(self, user, new_size):
        if user.storage_used + new_size > user.storage_quota:
            available = user.storage_quota - user.storage_used
            raise QuotaExceededError(
                f"Storage quota exceeded. "
                f"Available: {available / (1024*1024):.1f} MB, "
                f"needed: {new_size / (1024*1024):.1f} MB."
            )

    def _resolve_folder(self, owner, folder_id):
        if folder_id:
            try:
                return Folder.objects.get(id=folder_id, owner=owner, is_deleted=False)
            except Folder.DoesNotExist:
                pass
        # Default to root folder
        return Folder.objects.filter(owner=owner, parent=None, is_deleted=False).first()

    def _move_to_media(self, assembled_path, original_filename):
        now = timezone.now()
        rel_dir = f"uploads/{now.year}/{now.month:02d}/{now.day:02d}"
        abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)

        safe_name = f"{uuid.uuid4().hex}_{original_filename}"
        dest = os.path.join(abs_dir, safe_name)
        shutil.move(assembled_path, dest)
        return f"{rel_dir}/{safe_name}"


class TrashService:

    def soft_delete(self, file: File, user):
        if file.owner != user:
            raise PermissionError("You do not own this file.")
        file.is_deleted = True
        file.deleted_at = timezone.now()
        file.save(update_fields=['is_deleted', 'deleted_at'])

    def restore(self, file: File, user):
        if file.owner != user:
            raise PermissionError("You do not own this file.")
        file.is_deleted = False
        file.deleted_at = None
        file.save(update_fields=['is_deleted', 'deleted_at'])

    def permanent_delete(self, file: File, user):
        if file.owner != user:
            raise PermissionError("You do not own this file.")
        size = file.file_size

        try:
            storage_path = file.file.path
            file.delete()
            if os.path.exists(storage_path):
                os.remove(storage_path)
        except Exception:
            file.delete()

        user.refresh_from_db(fields=['storage_used'])
        user.storage_used = max(0, user.storage_used - size)
        user.save(update_fields=['storage_used'])
