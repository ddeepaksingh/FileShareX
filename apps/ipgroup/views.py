import os

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.files.models import File
from .forms import IPGroupUploadForm
from .services import (
    IPGroupUploadService,
    IPGroupBlockedError,
    IPGroupQuotaError,
    IPGroupRateLimitError,
)

_svc = IPGroupUploadService()


# ------------------------------------------------------------------ #
# Guards                                                               #
# ------------------------------------------------------------------ #

def _require_ip_group(request):
    """Return (ip_group, error_response) — error_response is None when ok."""
    if not getattr(request, 'ip_group', None):
        return None, render(request, 'ipgroup/disabled.html')
    if request.ip_group.is_blocked:
        return None, render(request, 'ipgroup/blocked.html', status=403)
    return request.ip_group, None


def _active_files(ip_group):
    """Non-expired, non-deleted files for an IP group."""
    return File.objects.filter(
        ip_group=ip_group,
        is_deleted=False,
        expires_at__gt=timezone.now(),
    ).order_by('-created_at')


# ------------------------------------------------------------------ #
# Views                                                                #
# ------------------------------------------------------------------ #

def ip_files(request):
    ip_group, err = _require_ip_group(request)
    if err:
        return err

    qs = _active_files(ip_group)

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(original_filename__icontains=q))

    paginator = Paginator(qs, 20)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    # Identify files uploaded by this browser session (cookie match)
    my_upload_ids = set()
    uploader = getattr(request, 'anonymous_uploader', None)
    if uploader:
        my_upload_ids = set(
            _active_files(ip_group)
            .filter(anonymous_uploader=uploader)
            .values_list('id', flat=True)
        )

    return render(request, 'ipgroup/ip_files.html', {
        'page_obj':      page_obj,
        'ip_group':      ip_group,
        'q':             q,
        'my_upload_ids': my_upload_ids,
        'total_files':   paginator.count,
    })


def ip_upload_page(request):
    ip_group, err = _require_ip_group(request)
    if err:
        return err

    if request.method == 'POST':
        form = IPGroupUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                f = _svc.upload(
                    file_obj=form.cleaned_data['file'],
                    ip_group=ip_group,
                    anonymous_uploader=request.anonymous_uploader,
                    title=form.cleaned_data.get('title', ''),
                    description=form.cleaned_data.get('description', ''),
                    expiry=form.cleaned_data.get('expiry', '24h'),
                )
                messages.success(request, f'"{f.title}" uploaded successfully!')
                return redirect('ipgroup:ip_files')
            except (IPGroupBlockedError, IPGroupQuotaError, IPGroupRateLimitError) as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Upload failed: {e}')
    else:
        form = IPGroupUploadForm()

    return render(request, 'ipgroup/upload.html', {
        'form':     form,
        'ip_group': ip_group,
    })


def ip_file_detail(request, file_id):
    ip_group, err = _require_ip_group(request)
    if err:
        return err

    file = get_object_or_404(
        File, id=file_id, ip_group=ip_group, is_deleted=False
    )
    if file.expires_at and file.expires_at < timezone.now():
        raise Http404("This file has expired.")

    is_mine = (
        getattr(request, 'anonymous_uploader', None)
        and file.anonymous_uploader_id == request.anonymous_uploader.pk
    )

    File.objects.filter(pk=file.pk).update(view_count=file.view_count + 1)

    return render(request, 'ipgroup/detail.html', {
        'file':    file,
        'is_mine': is_mine,
    })


def ip_file_download(request, file_id):
    ip_group, err = _require_ip_group(request)
    if err:
        return err

    file = get_object_or_404(
        File, id=file_id, ip_group=ip_group, is_deleted=False
    )
    if file.expires_at and file.expires_at < timezone.now():
        raise Http404("This file has expired.")

    File.objects.filter(pk=file.pk).update(download_count=file.download_count + 1)

    try:
        fh = open(file.file.path, 'rb')
    except FileNotFoundError:
        raise Http404("File not found on disk.")

    return FileResponse(fh, as_attachment=True, filename=file.original_filename)


@require_POST
def ip_file_delete(request, file_id):
    ip_group, err = _require_ip_group(request)
    if err:
        return err

    file = get_object_or_404(
        File, id=file_id, ip_group=ip_group, is_deleted=False
    )
    title = file.title
    try:
        _svc.delete_file(
            file=file,
            ip_group=ip_group,
            anonymous_uploader=request.anonymous_uploader,
        )
        messages.success(request, f'"{title}" deleted.')
    except PermissionError as e:
        messages.error(request, str(e))

    return redirect('ipgroup:ip_files')
