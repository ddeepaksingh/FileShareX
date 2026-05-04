import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import File, Folder
from .services import FileUploadService, QuotaExceededError, TrashService

_upload_service = FileUploadService()
_trash_service = TrashService()

_SORT_MAP = {
    'name': 'title',
    '-name': '-title',
    'size': 'file_size',
    '-size': '-file_size',
    'date': 'created_at',
    '-date': '-created_at',
}

_TYPE_MAP = {
    'image': 'image/',
    'video': 'video/',
    'audio': 'audio/',
    'document': 'application/pdf',
    'archive': 'application/zip',
}


# ------------------------------------------------------------------ #
# Upload                                                               #
# ------------------------------------------------------------------ #

@login_required
def upload_page(request):
    folders = Folder.objects.filter(owner=request.user, is_deleted=False, parent=None)
    return render(request, 'files/upload.html', {'folders': folders})


@login_required
@require_POST
def receive_chunk(request):
    chunk = request.FILES.get('chunk')
    if not chunk:
        return JsonResponse({'error': 'No chunk data provided.'}, status=400)

    try:
        upload = _upload_service.receive_chunk(
            upload_id=request.POST['upload_id'],
            chunk_index=int(request.POST['chunk_index']),
            chunk_data=chunk.read(),
            owner=request.user,
            original_filename=request.POST['file_name'],
            total_chunks=int(request.POST['total_chunks']),
            file_size=int(request.POST['file_size']),
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
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)

    try:
        file_instance = _upload_service.finalize_upload(
            upload_id=data['upload_id'],
            owner=request.user,
            title=data.get('title', ''),
            description=data.get('description', ''),
            folder_id=data.get('folder_id'),
        )
        return JsonResponse({
            'success': True,
            'file_id': str(file_instance.id),
            'title': file_instance.title,
        })
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
        qs = qs.filter(
            Q(title__icontains=q) | Q(original_filename__icontains=q)
        )

    # Type filter
    file_type = request.GET.get('type', '').strip()
    if file_type in _TYPE_MAP:
        qs = qs.filter(mime_type__startswith=_TYPE_MAP[file_type])

    # Sort
    sort_key = request.GET.get('sort', '-date')
    qs = qs.order_by(_SORT_MAP.get(sort_key, '-created_at'))

    # Folder navigation (skip folder filter when searching)
    folder_id = request.GET.get('folder', '').strip()
    current_folder = None
    if folder_id:
        current_folder = get_object_or_404(Folder, id=folder_id, owner=request.user, is_deleted=False)
        if not q:
            qs = qs.filter(folder=current_folder)
    elif not q:
        qs = qs.filter(folder__parent=None)

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    sub_folders = Folder.objects.filter(
        owner=request.user,
        parent=current_folder,
        is_deleted=False,
    )

    user = request.user
    quota_pct = user.storage_used_percent()

    return render(request, 'files/my_files.html', {
        'page_obj': page_obj,
        'sub_folders': sub_folders,
        'current_folder': current_folder,
        'q': q,
        'file_type': file_type,
        'sort_key': sort_key,
        'quota_pct': quota_pct,
        'storage_used_display': user.storage_used_display(),
        'storage_quota_display': user.storage_quota_display(),
        'total_files': qs.count(),
    })


# ------------------------------------------------------------------ #
# Detail & Preview                                                     #
# ------------------------------------------------------------------ #

@login_required
def file_detail(request, file_id):
    file = get_object_or_404(File, id=file_id, owner=request.user, is_deleted=False)
    File.objects.filter(pk=file.pk).update(view_count=file.view_count + 1)
    return render(request, 'files/detail.html', {'file': file})


# ------------------------------------------------------------------ #
# Download                                                             #
# ------------------------------------------------------------------ #

@login_required
def file_download(request, file_id):
    file = get_object_or_404(File, id=file_id, owner=request.user, is_deleted=False)
    File.objects.filter(pk=file.pk).update(download_count=file.download_count + 1)

    try:
        fh = open(file.file.path, 'rb')
    except FileNotFoundError:
        raise Http404("File not found on disk.")

    return FileResponse(fh, as_attachment=True, filename=file.original_filename)


# ------------------------------------------------------------------ #
# Folder                                                               #
# ------------------------------------------------------------------ #

@login_required
@require_POST
def create_folder(request):
    name = request.POST.get('name', '').strip()
    parent_id = request.POST.get('parent_id', '').strip()

    if not name:
        messages.error(request, 'Folder name cannot be empty.')
        return redirect('files:my_files')

    parent = None
    if parent_id:
        parent = get_object_or_404(Folder, id=parent_id, owner=request.user)

    _, created = Folder.objects.get_or_create(
        owner=request.user, name=name, parent=parent,
        defaults={'is_deleted': False},
    )
    if not created:
        messages.warning(request, f'A folder named "{name}" already exists here.')
    else:
        messages.success(request, f'Folder "{name}" created.')

    if parent_id:
        return redirect(f"{'/files/'}?folder={parent_id}")
    return redirect('files:my_files')


# ------------------------------------------------------------------ #
# Trash                                                                #
# ------------------------------------------------------------------ #

@login_required
def trash(request):
    qs = File.objects.filter(owner=request.user, is_deleted=True).order_by('-deleted_at')
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'files/trash.html', {'page_obj': page_obj})


@login_required
@require_POST
def delete_file(request, file_id):
    file = get_object_or_404(File, id=file_id, owner=request.user, is_deleted=False)
    title = file.title
    _trash_service.soft_delete(file, request.user)

    # AJAX callers get JSON; regular form submits get a safe redirect to My Files.
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'title': title})

    messages.success(request, f'"{title}" moved to trash.')
    return redirect('files:my_files')


@login_required
@require_POST
def restore_file(request, file_id):
    file = get_object_or_404(File, id=file_id, owner=request.user, is_deleted=True)
    _trash_service.restore(file, request.user)
    messages.success(request, f'"{file.title}" restored.')
    return redirect('files:trash')


@login_required
@require_POST
def destroy_file(request, file_id):
    file = get_object_or_404(File, id=file_id, owner=request.user, is_deleted=True)
    title = file.title
    _trash_service.permanent_delete(file, request.user)
    messages.success(request, f'"{title}" permanently deleted.')
    return redirect('files:trash')


@login_required
@require_POST
def empty_trash(request):
    trashed = File.objects.filter(owner=request.user, is_deleted=True)
    count = trashed.count()
    for file in trashed:
        _trash_service.permanent_delete(file, request.user)
    messages.success(request, f'{count} file(s) permanently deleted.')
    return redirect('files:trash')
