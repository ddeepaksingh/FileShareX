# Phase 4: Normal Groups — Technical Specification

**Phase:** 4  
**Feature:** Normal Groups  
**Status:** Ready for Implementation  
**Date:** May 2026  
**Builds On:** Phase 1 (Auth) + Phase 2 (File Management)

---

## Overview

Phase 4 adds a full group collaboration system. Users can create named groups with privacy settings, invite members, upload files scoped to a group, and archive groups they no longer need. This phase covers the core group scaffold; advanced permissions (roles, join requests, invite links, banning) are Phase 5.

**Deliverables:**
- `apps/groups` Django app with Group + GroupMembership models
- `group` FK added to `File` and `Folder` models
- URLs, views, forms, and templates for all group workflows
- Group storage quota enforcement
- Responsive templates consistent with existing `main.css` design system

---

## Scope

### In Scope (Phase 4)
- Group model with name, description, privacy, owner, storage quota, archive flag
- GroupMembership model with basic roles (admin, member)
- Create Group form + page
- My Groups page (Owned vs Joined tabs)
- Group Detail page (Files tab + Members tab)
- Upload file to group (reuses existing upload flow, adds group destination)
- Group storage quota display and enforcement
- Group files listing (search, filter, sort — mirrors My Files)
- Basic member display (avatars, roles, count)
- Archive / Unarchive group (owner-only)

### Out of Scope (Phase 5)
- Moderator role
- Join Request system
- Invite links
- Add/remove/ban members from within the group
- File-level permissions per member
- Ownership transfer
- Leave group

---

## New App: `apps/groups`

### 1. Register in Settings

**File:** `config/settings/base.py`

```python
LOCAL_APPS = [
    'apps.accounts',
    'apps.files',
    'apps/groups',   # ← add
]
```

### 2. Add URL Include

**File:** `config/urls.py`

```python
path('groups/', include('apps.groups.urls', namespace='groups')),
```

---

## Models

### `apps/groups/models.py`

#### Group

```python
import uuid
from django.db import models
from django.conf import settings


class Group(models.Model):
    PRIVACY_PRIVATE     = 'private'
    PRIVACY_PUBLIC      = 'public'
    PRIVACY_INVITE_ONLY = 'invite_only'
    PRIVACY_CHOICES = [
        (PRIVACY_PRIVATE,     'Private'),
        (PRIVACY_PUBLIC,      'Public'),
        (PRIVACY_INVITE_ONLY, 'Invite Only'),
    ]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name        = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_groups',
    )

    # Privacy
    privacy            = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default=PRIVACY_PRIVATE)
    allow_join_requests = models.BooleanField(default=True)   # Phase 5 enforcement

    # Storage quota (default 10 GB)
    storage_quota = models.BigIntegerField(default=10 * 1024 ** 3)
    storage_used  = models.BigIntegerField(default=0)

    # Status
    is_archived = models.BooleanField(default=False)

    # Timestamps
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'groups_group'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner']),
            models.Index(fields=['privacy']),
        ]

    def __str__(self):
        return self.name

    # ── Helpers ──────────────────────────────────────────────────────────────

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

    def is_member(self, user):
        if not user or not user.is_authenticated:
            return False
        return self.memberships.filter(user=user, is_active=True).exists()

    def get_membership(self, user):
        if not user or not user.is_authenticated:
            return None
        return self.memberships.filter(user=user, is_active=True).first()
```

#### GroupMembership

```python
class GroupMembership(models.Model):
    ROLE_ADMIN  = 'admin'
    ROLE_MEMBER = 'member'
    ROLE_CHOICES = [
        (ROLE_ADMIN,  'Admin'),
        (ROLE_MEMBER, 'Member'),
    ]

    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user      = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_memberships',
    )
    group     = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships')
    role      = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_MEMBER)

    # Basic permissions (Phase 5 will expand these)
    can_upload   = models.BooleanField(default=True)
    can_download = models.BooleanField(default=True)

    # Status
    is_active = models.BooleanField(default=True)

    # Timestamps
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
```

---

## File Model Changes

### `apps/files/models.py` — add `group` FK

Add to the `File` model (after the existing `folder` FK):

```python
group = models.ForeignKey(
    'groups.Group',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='files',
)
```

Add to `File.Meta.indexes`:

```python
models.Index(fields=['group', 'is_deleted']),
```

### `apps/files/models.py` — add `group` FK to Folder

Add to the `Folder` model:

```python
group = models.ForeignKey(
    'groups.Group',
    on_delete=models.CASCADE,
    null=True,
    blank=True,
    related_name='folders',
)
```

---

## Migration Plan

```
python manage.py makemigrations groups
python manage.py makemigrations files --name add_group_fk
python manage.py migrate
```

---

## URL Patterns

**File:** `apps/groups/urls.py`

```python
app_name = 'groups'

urlpatterns = [
    path('',                        views.my_groups,       name='my_groups'),
    path('create/',                 views.create_group,    name='create'),
    path('<uuid:group_id>/',        views.group_detail,    name='detail'),
    path('<uuid:group_id>/edit/',   views.edit_group,      name='edit'),
    path('<uuid:group_id>/archive/',views.archive_group,   name='archive'),   # POST
    path('<uuid:group_id>/add-member/', views.add_member,  name='add_member'),# POST (Phase 4: owner-only)
]
```

Update `config/urls.py`:
```python
path('groups/', include('apps.groups.urls', namespace='groups')),
```

Update navbar links in `templates/components/navbar.html` to include a **Groups** link for authenticated users.

---

## Views

**File:** `apps/groups/views.py`

### `my_groups(request)`

```
GET /groups/
```

- `login_required`
- Query: `owned = Group.objects.filter(owner=request.user, is_archived=False)`
- Query: `joined = Group.objects.filter(memberships__user=request.user, memberships__is_active=True, is_archived=False).exclude(owner=request.user)`
- Query: `archived = Group.objects.filter(owner=request.user, is_archived=True) | Group.objects.filter(memberships__user=request.user, memberships__is_active=True, is_archived=True).exclude(owner=request.user)`
- Context: `owned_groups`, `joined_groups`, `archived_groups`
- Template: `groups/my_groups.html`

### `create_group(request)`

```
GET + POST /groups/create/
```

- `login_required`
- **GET:** Render `GroupForm`
- **POST:** Validate → create `Group(owner=request.user)` → create `GroupMembership(user=request.user, group=group, role='admin')` → redirect to `groups:detail`
- On error: re-render form with errors
- Template: `groups/create_group.html`

### `group_detail(request, group_id)`

```
GET /groups/<uuid>/
```

- `login_required`
- Fetch group, 404 if not found
- Check `group.is_member(request.user)` or `group.owner == request.user`; if neither, 403
- `tab = request.GET.get('tab', 'files')` — either `'files'` or `'members'`
- **Files tab:** paginated `File.objects.filter(group=group, is_deleted=False)` with search + sort (same params as My Files)
- **Members tab:** `GroupMembership.objects.filter(group=group, is_active=True).select_related('user')`
- Context: `group`, `membership` (current user's membership), `tab`, `files`/`members`, pagination
- Template: `groups/group_detail.html`

### `edit_group(request, group_id)`

```
GET + POST /groups/<uuid>/edit/
```

- `login_required`
- Only group owner (or admin member) may edit
- Form fields: `name`, `description`, `privacy`, `storage_quota`
- On success: redirect to `groups:detail`
- Template: `groups/edit_group.html`

### `archive_group(request, group_id)`

```
POST /groups/<uuid>/archive/
```

- `login_required`
- Owner-only
- Toggles `group.is_archived` (archive if active, unarchive if archived)
- Redirect to `groups:my_groups`

### `add_member(request, group_id)`

```
POST /groups/<uuid>/add-member/
```

- `login_required`
- Owner / admin membership required
- Body: `username_or_email` (text field)
- Look up `User` by username or email; 404 on miss
- Reject if already a member
- Create `GroupMembership(user=target_user, group=group, role='member')`
- Redirect back to `groups:detail?tab=members`
- Template: no separate template — uses modal in `group_detail.html`

---

## Forms

**File:** `apps/groups/forms.py`

```python
class GroupForm(forms.ModelForm):
    class Meta:
        model  = Group
        fields = ['name', 'description', 'privacy']
        widgets = {
            'name':        forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Group name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'privacy':     forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if len(name) < 2:
            raise forms.ValidationError("Group name must be at least 2 characters.")
        return name


class AddMemberForm(forms.Form):
    username_or_email = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or email address',
        }),
    )
```

---

## Upload Integration

The existing upload flow (`files/views.py → finalize_upload`) needs a small extension to support group destination.

### Changes to `apps/files/services.py — FileUploadService.finalize_upload()`

```python
# existing:  folder = self._resolve_folder(...)
# add after:
group_id = data.get('group_id')
group = None
if group_id:
    from apps.groups.models import Group, GroupMembership
    group = get_object_or_404(Group, id=group_id)
    # permission: must be member with can_upload=True
    membership = GroupMembership.objects.filter(
        user=user, group=group, is_active=True, can_upload=True
    ).first()
    if not membership:
        raise PermissionDenied("You cannot upload to this group.")
    # quota check
    if group.storage_used + file_size > group.storage_quota:
        raise QuotaExceededError("Group storage quota exceeded.")

# pass group= to File.objects.create(...)
# after File created, if group: group.storage_used += file_size; group.save()
```

### Changes to Upload Template (`files/upload.html`)

Add a **Group** option to the destination selector:

```html
<!-- Destination: Private / Group -->
<div class="form-group">
  <label>Upload to</label>
  <select name="destination" id="destination-select" class="form-control">
    <option value="private">Private (My Files)</option>
    {% if user_groups %}
      <optgroup label="My Groups">
        {% for g in user_groups %}
          <option value="group" data-group-id="{{ g.id }}">{{ g.name }}</option>
        {% endfor %}
      </optgroup>
    {% endif %}
  </select>
</div>
```

Pass `user_groups` from `upload_page()` view:

```python
# files/views.py — upload_page()
from apps.groups.models import Group, GroupMembership

def upload_page(request):
    ...
    user_groups = Group.objects.filter(
        memberships__user=request.user,
        memberships__is_active=True,
        memberships__can_upload=True,
        is_archived=False,
    ) if request.user.is_authenticated else Group.objects.none()

    context = {
        ...,
        'user_groups': user_groups,
    }
```

The `finalize_upload` JSON endpoint receives `group_id` from the JS payload. No chunked upload logic changes needed.

---

## Templates

All templates extend `base.html` and use the existing `main.css` design system.

---

### `templates/groups/my_groups.html`

**Layout (desktop → mobile):**
- Page header: "My Groups" + "Create Group" button (right-aligned)
- Three tab pills: **Owned** · **Joined** · **Archived**
- Active tab shows a responsive grid of Group Cards

**Group Card** (`templates/groups/_group_card.html`):
```
┌─────────────────────────────────┐
│  [Group Icon / First Letter]    │
│  Group Name              [menu] │
│  Description (1-2 lines)        │
│  ────────────────────────────   │
│  👥 N members  📁 N files        │
│  Storage: ████░░░░ 2.4/10 GB   │
│  [View Group]                   │
└─────────────────────────────────┘
```

**Responsive:**
- Desktop ≥1024px → 3-column grid
- Tablet 768–1023px → 2-column grid
- Mobile <768px → 1-column stacked

**Empty state:** "You don't own any groups yet. [Create your first group →]"

---

### `templates/groups/create_group.html`

**Layout:**
- Centered card (max-width 600px)
- Fields: Group Name*, Description, Privacy (select with explanation labels)
- Privacy descriptions:
  - **Private** — Only members you invite can see and join
  - **Public** — Anyone can see and request to join
  - **Invite Only** — Hidden; only joinable via invite link (Phase 5)
- Submit: "Create Group" + Cancel link

---

### `templates/groups/group_detail.html`

**Layout:**
```
┌────────────────────────────────────────┐
│  [Back to Groups]                      │
│  Group Name           [Edit] [Archive] │
│  Description | Privacy badge           │
│  👥 5 members  📦 1.2 GB / 10 GB       │
│  Storage bar                           │
│                                        │
│  [Files tab] [Members tab]             │
│  ─────────────────────────────────     │
│  (tab content)                         │
└────────────────────────────────────────┘
```

**Files tab:**
- Search input + Sort dropdown (same as My Files)
- Responsive file grid using `_file_card.html` component (already exists)
- "Upload to this group" button → links to `/files/upload/?group=<id>`
- Empty state: "No files yet. Upload the first file →"
- Pagination

**Members tab:**
- Members list with avatar, username, role badge, join date
- "Add Member" button (admin/owner only) → inline form or small modal with username/email input
- Member row format:
  ```
  [Avatar] Username (email)     [Admin / Member badge]   Joined May 2026
  ```
- Mobile: stacked vertically, role badge below name

**Edit / Archive buttons:** visible only to group owner or admin membership.

---

### `templates/groups/edit_group.html`

- Same card layout as create_group.html
- Pre-populated with current values
- Extra section: **Storage Quota** (display-only in Phase 4; admin-configurable in Phase 6)
- Danger zone: **Archive Group** link (separate POST action)

---

## Navbar Update

**File:** `templates/components/navbar.html`

Add **Groups** link between "My Files" and "Profile" for authenticated users:

```html
<a href="{% url 'groups:my_groups' %}" class="nav-link {% if request.resolver_match.app_name == 'groups' %}active{% endif %}">
  Groups
</a>
```

Mobile hamburger menu: add same link in the mobile nav section.

---

## Storage Quota Enforcement

### Quota check on upload

In `FileUploadService.finalize_upload()`:

```python
if group:
    if group.storage_used + file_size > group.storage_quota:
        raise QuotaExceededError("Group storage quota exceeded.")
```

### Quota update on upload success

```python
if group:
    Group.objects.filter(id=group.id).update(
        storage_used=models.F('storage_used') + file.file_size
    )
```

### Quota update on file delete

In `TrashService.permanent_delete()` (already handles user quota). Add:

```python
if file.group_id:
    Group.objects.filter(id=file.group_id).update(
        storage_used=models.F('storage_used') - file.file_size
    )
```

---

## Permission Rules (Phase 4 Simplified)

| Action              | Owner | Admin member | Member | Non-member |
|---------------------|-------|--------------|--------|------------|
| View group detail   | ✅    | ✅           | ✅     | ❌ (private) / ✅ (public) |
| Edit group settings | ✅    | ✅           | ❌     | ❌         |
| Archive group       | ✅    | ❌           | ❌     | ❌         |
| Upload to group     | ✅    | ✅           | ✅ (if can_upload) | ❌ |
| Download from group | ✅    | ✅           | ✅ (if can_download) | ❌ |
| Delete group files  | ✅    | ✅           | ❌     | ❌         |
| Add member          | ✅    | ✅           | ❌     | ❌         |
| View members list   | ✅    | ✅           | ✅     | ❌         |

Enforce via a `get_group_or_403(request, group_id)` helper:

```python
# apps/groups/utils.py

def get_group_or_403(request, group_id, require_admin=False):
    group = get_object_or_404(Group, id=group_id)
    membership = group.get_membership(request.user)

    # Owner always passes
    if group.owner == request.user:
        return group, membership

    if not membership:
        raise PermissionDenied

    if require_admin and not membership.is_admin():
        raise PermissionDenied

    return group, membership
```

---

## CSS Extensions

The existing `main.css` already has card, button, tab, and grid classes. Phase 4 needs these additions in `static/css/groups.css` (new file, loaded via `extra_css` block):

```css
/* Group card grid */
.groups-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
}
@media (max-width: 1023px) { .groups-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 767px)  { .groups-grid { grid-template-columns: 1fr; } }

/* Group card */
.group-card { /* reuse .card styles + minor additions */ }
.group-card__icon {
  width: 48px; height: 48px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.5rem; font-weight: 700; color: #fff;
  background: var(--color-primary);
}

/* Storage progress bar (reuse existing .storage-bar if present) */
.storage-bar { height: 6px; border-radius: 3px; background: var(--color-gray-200); overflow: hidden; }
.storage-bar__fill { height: 100%; background: var(--color-primary); border-radius: 3px; transition: width 0.3s; }
.storage-bar__fill--warning { background: var(--color-warning, #f59e0b); }
.storage-bar__fill--danger  { background: var(--color-danger, #ef4444); }

/* Role badge */
.role-badge {
  display: inline-block; padding: 2px 8px; border-radius: 12px;
  font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
}
.role-badge--admin  { background: #dbeafe; color: #1d4ed8; }
.role-badge--member { background: #f3f4f6; color: #374151; }

/* Member row */
.member-row {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-3) 0; border-bottom: 1px solid var(--color-gray-100);
}
.member-row__avatar {
  width: 36px; height: 36px; border-radius: 50%; object-fit: cover;
  background: var(--color-gray-200); flex-shrink: 0;
}
.member-row__info { flex: 1; min-width: 0; }
.member-row__name { font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.member-row__email { font-size: 0.85rem; color: var(--color-gray-500); }
@media (max-width: 767px) {
  .member-row { flex-wrap: wrap; }
  .member-row__actions { width: 100%; margin-top: var(--space-2); }
}

/* Privacy badge */
.privacy-badge { display: inline-flex; align-items: center; gap: 4px; font-size: 0.8rem; }
.privacy-badge--private     { color: var(--color-gray-500); }
.privacy-badge--public      { color: #16a34a; }
.privacy-badge--invite_only { color: #7c3aed; }
```

---

## JavaScript

**File:** `static/js/groups.js`

Minimal JS needed:

1. **Tab switching** on group detail page (add/remove `.active` class, show/hide tab panels)
2. **Add Member modal** toggle
3. **Archive confirmation** dialog (simple `confirm()` before form submit is sufficient for Phase 4)
4. **Upload page group selector** — when user picks a group option, store `data-group-id` into a hidden `<input name="group_id">` that the finalize endpoint reads

```javascript
// Tab switching
document.querySelectorAll('[data-tab]').forEach(btn => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.tab;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.hidden = true);
    btn.classList.add('active');
    document.getElementById('tab-' + target).hidden = false;
    history.replaceState(null, '', '?tab=' + target);
  });
});

// Archive confirm
document.getElementById('archive-form')?.addEventListener('submit', e => {
  if (!confirm('Archive this group? Members will no longer be able to upload.')) e.preventDefault();
});

// Upload destination: sync hidden group_id input
const destSelect = document.getElementById('destination-select');
const groupIdInput = document.getElementById('group-id-input');
if (destSelect && groupIdInput) {
  destSelect.addEventListener('change', () => {
    const opt = destSelect.options[destSelect.selectedIndex];
    groupIdInput.value = opt.dataset.groupId || '';
  });
}
```

---

## Dashboard Integration

Update `accounts/views.py → DashboardView` to surface group data:

```python
from apps.groups.models import Group

class DashboardView(LoginRequiredMixin, View):
    def get(self, request):
        ...
        owned_groups = Group.objects.filter(
            owner=request.user, is_archived=False
        ).order_by('-updated_at')[:5]

        joined_groups = Group.objects.filter(
            memberships__user=request.user,
            memberships__is_active=True,
            is_archived=False,
        ).exclude(owner=request.user).order_by('-updated_at')[:5]

        context = {
            ...,
            'owned_groups': owned_groups,
            'joined_groups': joined_groups,
        }
```

Add a **Groups** section in `accounts/dashboard.html` showing owned/joined groups with a "View All" link to `groups:my_groups`.

---

## Admin Registration

**File:** `apps/groups/admin.py`

```python
from django.contrib import admin
from .models import Group, GroupMembership

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display  = ['name', 'owner', 'privacy', 'is_archived', 'member_count', 'storage_used_display', 'created_at']
    list_filter   = ['privacy', 'is_archived']
    search_fields = ['name', 'owner__username', 'owner__email']
    readonly_fields = ['storage_used', 'created_at', 'updated_at']

@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display  = ['user', 'group', 'role', 'is_active', 'joined_at']
    list_filter   = ['role', 'is_active']
    search_fields = ['user__username', 'group__name']
```

---

## Testing Requirements

### Unit Tests — `tests/groups/`

```
test_group_creation_creates_admin_membership.py
test_archive_group_only_owner.py
test_add_member_duplicate_rejected.py
test_storage_quota_enforced_on_upload.py
test_storage_updated_on_file_delete.py
test_permission_non_member_forbidden.py
test_upload_to_group_updates_quota.py
```

### Integration Tests

```
test_create_group_full_flow.py         # create → detail redirect → files tab
test_upload_to_group_appears_in_detail.py
test_add_member_can_see_group_detail.py
test_archive_hides_group_from_my_groups.py
```

### Manual QA Checklist

- [ ] Create group → redirected to detail page
- [ ] Group detail shows Files tab (empty) + Members tab (owner as Admin)
- [ ] Upload file to group → appears in group detail Files tab
- [ ] Upload respects group storage quota (quota exceeded error shown)
- [ ] Add member by username → member appears in Members tab
- [ ] Added member can see group in My Groups → Joined tab
- [ ] Added member can upload to group
- [ ] Owner sees Edit and Archive buttons; member does not
- [ ] Archive group → disappears from active groups → appears in Archived tab
- [ ] Unarchive group → returns to active
- [ ] Groups link in navbar active when on /groups/* routes
- [ ] Dashboard shows owned/joined groups section
- [ ] All pages responsive on mobile (375px), tablet (768px), desktop (1280px)
- [ ] No horizontal scroll on any screen size

---

## File Checklist

New files to create:

```
apps/groups/__init__.py
apps/groups/models.py
apps/groups/views.py
apps/groups/forms.py
apps/groups/urls.py
apps/groups/admin.py
apps/groups/utils.py
apps/groups/migrations/__init__.py
apps/groups/migrations/0001_initial.py      ← generated by makemigrations
templates/groups/my_groups.html
templates/groups/create_group.html
templates/groups/group_detail.html
templates/groups/edit_group.html
templates/groups/_group_card.html
static/css/groups.css
static/js/groups.js
tests/groups/__init__.py
tests/groups/test_models.py
tests/groups/test_views.py
```

Files to modify:

```
config/settings/base.py        ← add 'apps.groups' to LOCAL_APPS
config/urls.py                 ← include groups.urls
apps/files/models.py           ← add group FK to File + Folder
apps/files/services.py         ← group quota logic in finalize_upload + permanent_delete
apps/files/views.py            ← pass user_groups to upload_page context
apps/accounts/views.py         ← pass owned/joined groups to dashboard
templates/components/navbar.html ← add Groups link
templates/accounts/dashboard.html ← add groups section
templates/files/upload.html    ← add group destination selector
```

---

## Implementation Order

1. `apps/groups/models.py` + `apps/groups/migrations/`
2. Add `group` FK migration to `apps/files`
3. `apps/groups/admin.py` — verify models in admin
4. `apps/groups/forms.py` + `apps/groups/urls.py` + `apps/groups/utils.py`
5. `apps/groups/views.py` (my_groups + create_group first)
6. Templates: `my_groups.html` + `create_group.html` + `_group_card.html`
7. `group_detail.html` (files tab)
8. Members tab + add_member view
9. edit_group + archive_group
10. Upload integration (service + upload.html + JS)
11. Navbar + dashboard integration
12. `static/css/groups.css` + `static/js/groups.js`
13. Tests
14. Manual QA

---

**End of Phase 4 Specification**
