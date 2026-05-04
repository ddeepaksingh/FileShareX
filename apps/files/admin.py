from django.contrib import admin
from django.utils.html import format_html

from .models import ChunkUpload, File, Folder


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'parent', 'is_deleted', 'created_at']
    list_filter = ['is_deleted', 'created_at']
    search_fields = ['name', 'owner__email', 'owner__username']
    raw_id_fields = ['owner', 'parent']


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'owner', 'mime_type', 'human_size_display',
        'is_deleted', 'download_count', 'created_at',
    ]
    list_filter = ['is_deleted', 'mime_type', 'created_at']
    search_fields = ['title', 'original_filename', 'owner__email', 'file_hash']
    readonly_fields = ['file_hash', 'file_size', 'mime_type', 'extension',
                       'download_count', 'view_count', 'created_at', 'updated_at']
    raw_id_fields = ['owner', 'folder', 'parent_file']

    def human_size_display(self, obj):
        return obj.human_size()
    human_size_display.short_description = 'Size'


@admin.register(ChunkUpload)
class ChunkUploadAdmin(admin.ModelAdmin):
    list_display = ['upload_id', 'owner', 'original_filename', 'progress', 'created_at']
    list_filter = ['created_at']

    def progress(self, obj):
        pct = int(obj.received_chunks / obj.total_chunks * 100) if obj.total_chunks else 0
        return format_html(
            '<span>{}/{} chunks ({}%)</span>',
            obj.received_chunks, obj.total_chunks, pct,
        )
    progress.short_description = 'Progress'
