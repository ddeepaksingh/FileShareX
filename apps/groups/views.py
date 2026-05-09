from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.files.models import File
from .forms import AddMemberForm, GroupForm
from .models import Group, GroupMembership
from .utils import get_group_or_403

User = get_user_model()

_SORT_MAP = {
    'name': 'title',
    '-name': '-title',
    'size': 'file_size',
    '-size': '-file_size',
    'date': 'created_at',
    '-date': '-created_at',
}


# ------------------------------------------------------------------ #
# My Groups                                                            #
# ------------------------------------------------------------------ #

@login_required
def my_groups(request):
    owned = Group.objects.filter(owner=request.user, is_archived=False)
    joined = Group.objects.filter(
        memberships__user=request.user,
        memberships__is_active=True,
        is_archived=False,
    ).exclude(owner=request.user)

    owned_archived = Group.objects.filter(owner=request.user, is_archived=True)
    joined_archived = Group.objects.filter(
        memberships__user=request.user,
        memberships__is_active=True,
        is_archived=True,
    ).exclude(owner=request.user)
    archived = (owned_archived | joined_archived).distinct()

    return render(request, 'groups/my_groups.html', {
        'owned_groups': owned,
        'joined_groups': joined,
        'archived_groups': archived,
        'active_tab': request.GET.get('tab', 'owned'),
    })


# ------------------------------------------------------------------ #
# Create Group                                                         #
# ------------------------------------------------------------------ #

@login_required
def create_group(request):
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.owner = request.user
            group.save()
            GroupMembership.objects.create(
                user=request.user,
                group=group,
                role=GroupMembership.ROLE_ADMIN,
            )
            messages.success(request, f'Group "{group.name}" created.')
            return redirect('groups:detail', group_id=group.id)
    else:
        form = GroupForm()

    return render(request, 'groups/create_group.html', {'form': form})


# ------------------------------------------------------------------ #
# Group Detail                                                         #
# ------------------------------------------------------------------ #

@login_required
def group_detail(request, group_id):
    group, membership = get_group_or_403(request, group_id)

    tab = request.GET.get('tab', 'files')

    # Files tab
    files_qs = File.objects.filter(group=group, is_deleted=False)
    q = request.GET.get('q', '').strip()
    if q:
        files_qs = files_qs.filter(
            Q(title__icontains=q) | Q(original_filename__icontains=q)
        )
    sort_key = request.GET.get('sort', '-date')
    files_qs = files_qs.order_by(_SORT_MAP.get(sort_key, '-created_at'))

    paginator = Paginator(files_qs, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    # Members tab
    members = GroupMembership.objects.filter(
        group=group, is_active=True
    ).select_related('user').order_by('joined_at')

    can_manage = group.can_manage(request.user)

    return render(request, 'groups/group_detail.html', {
        'group': group,
        'membership': membership,
        'tab': tab,
        'page_obj': page_obj,
        'members': members,
        'q': q,
        'sort_key': sort_key,
        'can_manage': can_manage,
        'add_member_form': AddMemberForm(),
    })


# ------------------------------------------------------------------ #
# Edit Group                                                           #
# ------------------------------------------------------------------ #

@login_required
def edit_group(request, group_id):
    group, _ = get_group_or_403(request, group_id, require_admin=True)

    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, 'Group settings updated.')
            return redirect('groups:detail', group_id=group.id)
    else:
        form = GroupForm(instance=group)

    return render(request, 'groups/edit_group.html', {
        'form': form,
        'group': group,
    })


# ------------------------------------------------------------------ #
# Archive / Unarchive                                                  #
# ------------------------------------------------------------------ #

@login_required
@require_POST
def archive_group(request, group_id):
    group = get_object_or_404(Group, id=group_id, owner=request.user)
    group.is_archived = not group.is_archived
    group.save(update_fields=['is_archived'])

    if group.is_archived:
        messages.success(request, f'"{group.name}" archived.')
    else:
        messages.success(request, f'"{group.name}" restored from archive.')

    return redirect('groups:my_groups')


# ------------------------------------------------------------------ #
# Add Member                                                           #
# ------------------------------------------------------------------ #

@login_required
@require_POST
def add_member(request, group_id):
    group, _ = get_group_or_403(request, group_id, require_admin=True)

    form = AddMemberForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Invalid input.')
        return redirect('groups:detail', group_id=group.id)

    identifier = form.cleaned_data['username_or_email'].strip()
    target_user = (
        User.objects.filter(username=identifier).first()
        or User.objects.filter(email=identifier).first()
    )

    members_url = reverse('groups:detail', kwargs={'group_id': group.id}) + '?tab=members'

    if not target_user:
        messages.error(request, f'No user found with username or email "{identifier}".')
        return redirect(members_url)

    if GroupMembership.objects.filter(user=target_user, group=group).exists():
        messages.warning(request, f'"{target_user.username}" is already a member of this group.')
        return redirect(members_url)

    GroupMembership.objects.create(
        user=target_user,
        group=group,
        role=GroupMembership.ROLE_MEMBER,
    )
    messages.success(request, f'"{target_user.username}" added to the group.')
    return redirect(members_url)
