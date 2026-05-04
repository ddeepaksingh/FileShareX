# File Sharing Platform - Technical Specification

**Project Name:** IP-Based File Sharing Platform  
**Version:** 1.0.0  
**Last Updated:** May 2026  
**Author:** Development Team  
**Status:** Specification Phase

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Architecture Overview](#architecture-overview)
3. [Database Schema](#database-schema)
4. [API Specifications](#api-specifications)
5. [File Structure](#file-structure)
6. [Models & Relationships](#models--relationships)
7. [Business Logic](#business-logic)
8. [Security Specifications](#security-specifications)
9. [Storage Architecture](#storage-architecture)
10. [Background Jobs](#background-jobs)
11. [Frontend Specifications](#frontend-specifications)
12. [Testing Requirements](#testing-requirements)

---

## System Requirements

### Technology Stack

#### Backend
```yaml
Framework: Django 4.2+
Python: 3.10+
Database: PostgreSQL 14+
Cache: Redis 7+
Task Queue: Celery 5+
Message Broker: Redis / RabbitMQ
```

#### Frontend
```yaml
Template Engine: Django Templates
CSS Framework: TailwindCSS 3+
JavaScript: Vanilla ES6+ / Alpine.js (optional)
File Upload: Dropzone.js / Uppy.js
```

#### Development Tools
```yaml
Version Control: Git
Code Quality: Black, Flake8, isort
Testing: pytest, pytest-django
Documentation: Sphinx
```

### Server Requirements

#### Production
```yaml
CPU: 4+ cores
RAM: 8GB minimum, 16GB recommended
Storage: 100GB+ SSD (application + database)
File Storage: S3 / Separate storage volume
Bandwidth: 100Mbps+ recommended
```

#### Development
```yaml
CPU: 2+ cores
RAM: 4GB minimum
Storage: 20GB+
```

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Load Balancer                        │
│                    (Nginx / Caddy)                       │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
│  Web Server  │ │ Web Server  │ │ Web Server │
│  (Gunicorn)  │ │ (Gunicorn)  │ │ (Gunicorn) │
└───────┬──────┘ └──────┬──────┘ └─────┬──────┘
        │               │               │
        └───────────────┼───────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
│  PostgreSQL  │ │    Redis    │ │   Celery   │
│   Database   │ │    Cache    │ │   Workers  │
└──────────────┘ └─────────────┘ └─────┬──────┘
                                        │
                                ┌───────▼──────┐
                                │ File Storage │
                                │  (S3/Local)  │
                                └──────────────┘
```

### Application Architecture

```
Django Project
├── accounts/          # User management
├── files/             # File operations
├── groups/            # Normal groups
├── ipgroup/           # IP-based groups
├── notifications/     # Notification system
├── core/              # Shared utilities
└── api/               # REST API (future)
```

---

## Database Schema

### 1. User Model

```python
# accounts/models.py

class User(AbstractUser):
    """Extended Django User model"""
    
    # Fields
    email = EmailField(unique=True, db_index=True)
    username = CharField(max_length=150, unique=True, db_index=True)
    profile_photo = ImageField(upload_to='profiles/', null=True, blank=True)
    storage_quota = BigIntegerField(default=5368709120)  # 5GB in bytes
    storage_used = BigIntegerField(default=0)
    
    # Timestamps
    date_joined = DateTimeField(auto_now_add=True)
    last_login = DateTimeField(null=True)
    
    # Settings
    email_notifications = BooleanField(default=True)
    is_active = BooleanField(default=True)
    
    # Metadata
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
        ]
```

### 2. File Model

```python
# files/models.py

class File(models.Model):
    """Main file storage model"""
    
    # Identification
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Ownership
    owner = ForeignKey('accounts.User', on_delete=CASCADE, related_name='files')
    
    # File Information
    title = CharField(max_length=255)
    description = TextField(blank=True, null=True)
    file = FileField(upload_to='uploads/%Y/%m/%d/')
    original_filename = CharField(max_length=255)
    file_hash = CharField(max_length=64, db_index=True)  # SHA-256
    
    # File Metadata
    file_size = BigIntegerField()  # in bytes
    mime_type = CharField(max_length=100)
    extension = CharField(max_length=10)
    
    # Location
    folder = ForeignKey('Folder', on_delete=CASCADE, related_name='files', null=True)
    
    # Group Association
    group = ForeignKey('groups.Group', on_delete=CASCADE, null=True, blank=True, related_name='files')
    ip_group = ForeignKey('ipgroup.IPGroup', on_delete=CASCADE, null=True, blank=True, related_name='files')
    
    # Visibility
    is_private = BooleanField(default=True)
    is_deleted = BooleanField(default=False)  # Soft delete
    deleted_at = DateTimeField(null=True, blank=True)
    
    # Versioning
    is_latest_version = BooleanField(default=True)
    version_number = IntegerField(default=1)
    parent_file = ForeignKey('self', on_delete=SET_NULL, null=True, blank=True, related_name='versions')
    
    # Expiry (for IP Group files)
    expires_at = DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    # Stats
    download_count = IntegerField(default=0)
    view_count = IntegerField(default=0)
    
    class Meta:
        db_table = 'files'
        indexes = [
            models.Index(fields=['owner', 'is_deleted']),
            models.Index(fields=['file_hash']),
            models.Index(fields=['created_at']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['group']),
            models.Index(fields=['ip_group']),
        ]
        ordering = ['-created_at']
```

### 3. Folder Model

```python
# files/models.py

class Folder(models.Model):
    """Hierarchical folder structure"""
    
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = CharField(max_length=255)
    owner = ForeignKey('accounts.User', on_delete=CASCADE, related_name='folders')
    
    # Hierarchy
    parent = ForeignKey('self', on_delete=CASCADE, null=True, blank=True, related_name='subfolders')
    
    # Group Association
    group = ForeignKey('groups.Group', on_delete=CASCADE, null=True, blank=True, related_name='folders')
    
    # Metadata
    is_private = BooleanField(default=True)
    is_deleted = BooleanField(default=False)
    
    # Timestamps
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'folders'
        unique_together = [['owner', 'name', 'parent']]
        indexes = [
            models.Index(fields=['owner', 'parent']),
        ]
```

### 4. Group Model

```python
# groups/models.py

class Group(models.Model):
    """Normal user groups"""
    
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = CharField(max_length=255)
    description = TextField(blank=True)
    
    # Ownership
    owner = ForeignKey('accounts.User', on_delete=CASCADE, related_name='owned_groups')
    
    # Privacy
    PRIVACY_CHOICES = [
        ('private', 'Private'),
        ('public', 'Public'),
        ('invite_only', 'Invite Only'),
    ]
    privacy = CharField(max_length=20, choices=PRIVACY_CHOICES, default='private')
    
    # Settings
    allow_join_requests = BooleanField(default=True)
    storage_quota = BigIntegerField(default=10737418240)  # 10GB
    storage_used = BigIntegerField(default=0)
    
    # Status
    is_active = BooleanField(default=True)
    is_archived = BooleanField(default=False)
    
    # Timestamps
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'groups'
        ordering = ['-created_at']
```

### 5. GroupMembership Model

```python
# groups/models.py

class GroupMembership(models.Model):
    """User-Group relationship with roles"""
    
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = ForeignKey('accounts.User', on_delete=CASCADE, related_name='group_memberships')
    group = ForeignKey('Group', on_delete=CASCADE, related_name='memberships')
    
    # Role
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('member', 'Member'),
    ]
    role = CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    
    # Permissions
    can_upload = BooleanField(default=True)
    can_download = BooleanField(default=True)
    can_delete = BooleanField(default=False)
    can_view_only = BooleanField(default=False)
    
    # Status
    is_active = BooleanField(default=True)
    is_banned = BooleanField(default=False)
    
    # Timestamps
    joined_at = DateTimeField(auto_now_add=True)
    last_activity = DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'group_memberships'
        unique_together = [['user', 'group']]
        indexes = [
            models.Index(fields=['user', 'group']),
            models.Index(fields=['group', 'role']),
        ]
```

### 6. IPGroup Model

```python
# ipgroup/models.py

class IPGroup(models.Model):
    """IP-based temporary groups"""
    
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ip_address = GenericIPAddressField(unique=True, db_index=True)
    
    # Storage
    storage_quota = BigIntegerField(default=524288000)  # 500MB
    storage_used = BigIntegerField(default=0)
    
    # Settings
    is_active = BooleanField(default=True)
    is_blocked = BooleanField(default=False)
    
    # Rate Limiting
    upload_count_today = IntegerField(default=0)
    last_upload = DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    last_activity = DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ip_groups'
        indexes = [
            models.Index(fields=['ip_address']),
            models.Index(fields=['is_active']),
        ]
```

### 7. AnonymousUploader Model

```python
# ipgroup/models.py

class AnonymousUploader(models.Model):
    """Cookie-based anonymous user tracking"""
    
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cookie_id = CharField(max_length=64, unique=True, db_index=True)
    ip_group = ForeignKey('IPGroup', on_delete=CASCADE, related_name='uploaders')
    
    # Metadata
    user_agent = CharField(max_length=255, blank=True)
    
    # Timestamps
    created_at = DateTimeField(auto_now_add=True)
    last_seen = DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'anonymous_uploaders'
```

### 8. JoinRequest Model

```python
# groups/models.py

class JoinRequest(models.Model):
    """Group join requests"""
    
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = ForeignKey('accounts.User', on_delete=CASCADE, related_name='join_requests')
    group = ForeignKey('Group', on_delete=CASCADE, related_name='join_requests')
    
    # Request
    message = TextField(blank=True)
    
    # Status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    status = CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Processing
    processed_by = ForeignKey('accounts.User', on_delete=SET_NULL, null=True, blank=True, related_name='processed_requests')
    processed_at = DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'join_requests'
        unique_together = [['user', 'group', 'status']]
        indexes = [
            models.Index(fields=['group', 'status']),
        ]
```

### 9. PublicLink Model

```python
# files/models.py

class PublicLink(models.Model):
    """Shareable public links"""
    
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = ForeignKey('File', on_delete=CASCADE, related_name='public_links')
    created_by = ForeignKey('accounts.User', on_delete=CASCADE, related_name='created_links')
    
    # Link Configuration
    token = CharField(max_length=32, unique=True, db_index=True)
    password = CharField(max_length=128, blank=True, null=True)  # Hashed
    
    # Access Control
    allow_download = BooleanField(default=True)
    max_downloads = IntegerField(null=True, blank=True)
    download_count = IntegerField(default=0)
    
    # Expiry
    expires_at = DateTimeField(null=True, blank=True)
    
    # Status
    is_active = BooleanField(default=True)
    
    # Timestamps
    created_at = DateTimeField(auto_now_add=True)
    last_accessed = DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'public_links'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['expires_at']),
        ]
```

### 10. Notification Model

```python
# notifications/models.py

class Notification(models.Model):
    """User notifications"""
    
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = ForeignKey('accounts.User', on_delete=CASCADE, related_name='notifications')
    
    # Content
    NOTIFICATION_TYPES = [
        ('file_upload', 'File Uploaded'),
        ('join_request', 'Join Request'),
        ('member_added', 'Added to Group'),
        ('file_shared', 'File Shared'),
        ('comment', 'Comment'),
    ]
    notification_type = CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = CharField(max_length=255)
    message = TextField()
    
    # Links
    link_url = URLField(blank=True, null=True)
    
    # Related Objects
    related_file = ForeignKey('files.File', on_delete=CASCADE, null=True, blank=True)
    related_group = ForeignKey('groups.Group', on_delete=CASCADE, null=True, blank=True)
    related_user = ForeignKey('accounts.User', on_delete=CASCADE, null=True, blank=True, related_name='caused_notifications')
    
    # Status
    is_read = BooleanField(default=False)
    is_emailed = BooleanField(default=False)
    
    # Timestamps
    created_at = DateTimeField(auto_now_add=True)
    read_at = DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'notifications'
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
```

### 11. AuditLog Model

```python
# core/models.py

class AuditLog(models.Model):
    """System audit log"""
    
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Actor
    user = ForeignKey('accounts.User', on_delete=SET_NULL, null=True, blank=True)
    ip_address = GenericIPAddressField()
    user_agent = CharField(max_length=255)
    
    # Action
    ACTION_TYPES = [
        ('file_upload', 'File Upload'),
        ('file_download', 'File Download'),
        ('file_delete', 'File Delete'),
        ('group_create', 'Group Create'),
        ('member_add', 'Member Add'),
        ('member_remove', 'Member Remove'),
        ('login', 'Login'),
        ('logout', 'Logout'),
    ]
    action = CharField(max_length=50, choices=ACTION_TYPES)
    details = JSONField(default=dict)
    
    # Related Objects
    related_file = ForeignKey('files.File', on_delete=SET_NULL, null=True, blank=True)
    related_group = ForeignKey('groups.Group', on_delete=SET_NULL, null=True, blank=True)
    
    # Timestamp
    created_at = DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'audit_logs'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action']),
            models.Index(fields=['ip_address']),
        ]
```

### 12. InviteLink Model

```python
# groups/models.py

class InviteLink(models.Model):
    """Group invite links"""
    
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = ForeignKey('Group', on_delete=CASCADE, related_name='invite_links')
    created_by = ForeignKey('accounts.User', on_delete=CASCADE)
    
    # Link
    token = CharField(max_length=32, unique=True, db_index=True)
    
    # Settings
    max_uses = IntegerField(null=True, blank=True)
    use_count = IntegerField(default=0)
    expires_at = DateTimeField(null=True, blank=True)
    
    # Role Assignment
    default_role = CharField(max_length=20, default='member')
    
    # Status
    is_active = BooleanField(default=True)
    
    # Timestamps
    created_at = DateTimeField(auto_now_add=True)
    last_used = DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'invite_links'
```

---

## API Specifications

### Authentication Endpoints

#### POST /api/auth/signup
```json
Request:
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "confirm_password": "SecurePass123!"
}

Response (201):
{
  "user": {
    "id": "uuid",
    "username": "john_doe",
    "email": "john@example.com"
  },
  "token": "jwt_token_here"
}
```

#### POST /api/auth/login
```json
Request:
{
  "email": "john@example.com",
  "password": "SecurePass123!"
}

Response (200):
{
  "user": {...},
  "token": "jwt_token_here"
}
```

### File Endpoints

#### POST /api/files/upload
```json
Request (multipart/form-data):
{
  "file": <binary>,
  "title": "My Document",
  "description": "Important file",
  "destination": "private|group|ipgroup",
  "group_id": "uuid" (if destination=group),
  "folder_id": "uuid" (optional)
}

Response (201):
{
  "file": {
    "id": "uuid",
    "title": "My Document",
    "file_size": 1024000,
    "mime_type": "application/pdf",
    "created_at": "2026-05-01T10:00:00Z"
  }
}
```

#### GET /api/files/
```json
Query Parameters:
- page: int (default: 1)
- page_size: int (default: 20)
- search: string (optional)
- folder_id: uuid (optional)
- group_id: uuid (optional)

Response (200):
{
  "count": 100,
  "next": "url",
  "previous": "url",
  "results": [...]
}
```

#### DELETE /api/files/:id
```json
Response (204): No content
```

### Group Endpoints

#### POST /api/groups/
```json
Request:
{
  "name": "Project Team",
  "description": "Team collaboration space",
  "privacy": "private|public|invite_only"
}

Response (201):
{
  "group": {...}
}
```

#### POST /api/groups/:id/members
```json
Request:
{
  "user_id": "uuid",
  "role": "admin|moderator|member",
  "permissions": {
    "can_upload": true,
    "can_download": true,
    "can_delete": false
  }
}

Response (201):
{
  "membership": {...}
}
```

---

## File Structure

### Django Project Structure

```
file_sharing_platform/
│
├── config/                      # Project configuration
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py             # Base settings
│   │   ├── development.py      # Dev settings
│   │   └── production.py       # Prod settings
│   ├── urls.py                 # Root URL config
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/                        # Django apps
│   │
│   ├── accounts/               # User management
│   │   ├── migrations/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── signals.py
│   │   └── tests/
│   │
│   ├── files/                  # File operations
│   │   ├── migrations/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── urls.py
│   │   ├── utils.py
│   │   ├── services.py         # Business logic
│   │   ├── validators.py
│   │   └── tests/
│   │
│   ├── groups/                 # Normal groups
│   │   ├── migrations/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── urls.py
│   │   ├── permissions.py
│   │   └── tests/
│   │
│   ├── ipgroup/                # IP-based groups
│   │   ├── migrations/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── middleware.py
│   │   ├── utils.py
│   │   └── tests/
│   │
│   ├── notifications/          # Notification system
│   │   ├── migrations/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── tasks.py           # Celery tasks
│   │   └── tests/
│   │
│   └── core/                   # Shared utilities
│       ├── __init__.py
│       ├── models.py
│       ├── utils.py
│       ├── permissions.py
│       ├── storage.py
│       └── tasks.py
│
├── templates/                   # Django templates
│   ├── base.html
│   ├── accounts/
│   ├── files/
│   ├── groups/
│   └── ipgroup/
│
├── static/                      # Static files
│   ├── css/
│   ├── js/
│   ├── images/
│   └── vendor/
│
├── media/                       # User uploads
│   ├── uploads/
│   ├── profiles/
│   └── temp/
│
├── storage/                     # Storage abstraction
│   ├── __init__.py
│   ├── base.py
│   ├── local.py
│   └── s3.py
│
├── requirements/                # Python dependencies
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
│
├── tests/                       # Test suites
│   ├── integration/
│   ├── unit/
│   └── fixtures/
│
├── scripts/                     # Utility scripts
│   ├── cleanup.py
│   └── migrate_storage.py
│
├── manage.py
├── pytest.ini
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

---

## Business Logic

### File Upload Workflow

```python
# files/services.py

class FileUploadService:
    """Handles file upload logic"""
    
    def upload_file(self, file_obj, user, destination, **kwargs):
        """
        Upload file with validation and processing
        
        Args:
            file_obj: UploadedFile object
            user: User instance or None (anonymous)
            destination: 'private', 'group', 'ipgroup'
            **kwargs: Additional parameters (group_id, folder_id, etc.)
        
        Returns:
            File instance
        """
        # 1. Validate file
        self._validate_file(file_obj)
        
        # 2. Calculate hash
        file_hash = self._calculate_hash(file_obj)
        
        # 3. Check for duplicates
        duplicate = self._check_duplicate(file_hash, user, destination)
        if duplicate:
            return self._handle_duplicate(duplicate, user)
        
        # 4. Check storage quota
        self._check_quota(user, file_obj.size, destination)
        
        # 5. Check versioning
        version_info = self._check_versioning(
            file_obj.name, user, destination, kwargs
        )
        
        # 6. Upload to storage
        storage_path = self.storage_service.upload(file_obj)
        
        # 7. Create File record
        file_instance = self._create_file_record(
            file_obj, user, storage_path, file_hash, 
            destination, version_info, **kwargs
        )
        
        # 8. Update storage usage
        self._update_storage_usage(user, file_obj.size, destination)
        
        # 9. Create thumbnail (async)
        if self._is_image(file_obj):
            create_thumbnail.delay(file_instance.id)
        
        # 10. Log action
        self._log_upload(file_instance, user)
        
        return file_instance
```

### IP Group Access Control

```python
# ipgroup/middleware.py

class IPGroupMiddleware:
    """Middleware for IP group detection and cookie management"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Get client IP
        ip_address = self._get_client_ip(request)
        
        # Get or create IP Group
        ip_group, created = IPGroup.objects.get_or_create(
            ip_address=ip_address,
            defaults={'is_active': True}
        )
        
        # Handle anonymous cookie
        cookie_id = request.COOKIES.get('anonymous_id')
        if not cookie_id:
            cookie_id = self._generate_anonymous_id()
            
        # Get or create anonymous uploader
        uploader, _ = AnonymousUploader.objects.get_or_create(
            cookie_id=cookie_id,
            defaults={
                'ip_group': ip_group,
                'user_agent': request.META.get('HTTP_USER_AGENT', '')
            }
        )
        
        # Attach to request
        request.ip_group = ip_group
        request.anonymous_uploader = uploader
        
        response = self.get_response(request)
        
        # Set cookie
        if not request.COOKIES.get('anonymous_id'):
            response.set_cookie(
                'anonymous_id',
                cookie_id,
                max_age=365*24*60*60,  # 1 year
                httponly=True,
                samesite='Lax'
            )
        
        return response
```

### Permission Engine

```python
# core/permissions.py

class PermissionEngine:
    """Centralized permission checking"""
    
    @staticmethod
    def can_access_file(user, file, request=None):
        """
        Check if user can access file
        
        Priority:
        1. Public link (bypasses all)
        2. IP Group access
        3. Owner
        4. Group membership
        5. Private access
        """
        # Check public link
        if request and 'token' in request.GET:
            return PublicLink.objects.filter(
                token=request.GET['token'],
                file=file,
                is_active=True
            ).exists()
        
        # Check IP Group
        if file.ip_group:
            if request and request.ip_group == file.ip_group:
                return True
            return False
        
        # Check owner
        if user and file.owner == user:
            return True
        
        # Check group membership
        if file.group:
            membership = GroupMembership.objects.filter(
                user=user,
                group=file.group,
                is_active=True,
                is_banned=False
            ).first()
            
            if membership:
                return membership.can_download or membership.can_view_only
        
        # Private file
        return False
    
    @staticmethod
    def can_delete_file(user, file, anonymous_uploader=None):
        """Check if user can delete file"""
        
        # IP Group file - check anonymous uploader cookie
        if file.ip_group:
            if anonymous_uploader:
                return file.owner == anonymous_uploader.user or \
                       AnonymousUploader.objects.filter(
                           cookie_id=anonymous_uploader.cookie_id,
                           ip_group=file.ip_group
                       ).exists()
            return False
        
        # Owner can always delete
        if user and file.owner == user:
            return True
        
        # Group admin/moderator
        if file.group:
            membership = GroupMembership.objects.filter(
                user=user,
                group=file.group,
                role__in=['admin', 'moderator'],
                is_active=True
            ).exists()
            return membership
        
        return False
```

### Duplicate Detection

```python
# files/utils.py

def handle_duplicate_upload(file_hash, user, filename, destination):
    """
    Handle duplicate file detection
    
    Returns:
        tuple: (should_upload, existing_file)
    """
    # Find existing file with same hash
    existing_file = File.objects.filter(
        file_hash=file_hash,
        is_deleted=False
    ).first()
    
    if not existing_file:
        return True, None
    
    # Show user options:
    # 1. Reuse (create reference)
    # 2. Upload new copy
    # 3. Cancel
    
    # This will be handled in the view with user interaction
    return False, existing_file
```

### Versioning Logic

```python
# files/services.py

def create_version(original_file, new_file_obj, user):
    """
    Create a new version of existing file
    
    Conditions for versioning:
    - Same user
    - Same filename
    - Same location (folder/group)
    """
    # Check if conditions met
    if (original_file.owner == user and 
        original_file.original_filename == new_file_obj.name and
        original_file.folder == kwargs.get('folder')):
        
        # Mark old version as not latest
        original_file.is_latest_version = False
        original_file.save()
        
        # Create new version
        new_version_number = File.objects.filter(
            parent_file=original_file
        ).count() + 1
        
        return {
            'is_version': True,
            'version_number': new_version_number,
            'parent_file': original_file
        }
    
    return {'is_version': False}
```

---

## Security Specifications

### Rate Limiting

```python
# core/decorators.py

from django.core.cache import cache
from django.http import HttpResponse

def rate_limit(key_prefix, limit=10, period=60):
    """
    Rate limiting decorator
    
    Args:
        key_prefix: Cache key prefix
        limit: Max requests
        period: Time period in seconds
    """
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            # Build cache key
            if request.user.is_authenticated:
                key = f"{key_prefix}:{request.user.id}"
            else:
                key = f"{key_prefix}:{request.ip_group.ip_address}"
            
            # Get current count
            count = cache.get(key, 0)
            
            if count >= limit:
                return HttpResponse(
                    "Rate limit exceeded",
                    status=429
                )
            
            # Increment
            cache.set(key, count + 1, period)
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator
```

### File Validation

```python
# files/validators.py

ALLOWED_EXTENSIONS = {
    'image': ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
    'document': ['.pdf', '.doc', '.docx', '.txt', '.md'],
    'archive': ['.zip', '.tar', '.gz', '.rar'],
    'video': ['.mp4', '.avi', '.mov', '.mkv'],
    'audio': ['.mp3', '.wav', '.flac', '.aac'],
}

BLOCKED_EXTENSIONS = [
    '.exe', '.bat', '.cmd', '.sh', '.ps1',
    '.dll', '.so', '.dylib',
    '.js', '.vbs', '.jar'
]

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

def validate_file(file_obj):
    """Validate uploaded file"""
    
    # Check size
    if file_obj.size > MAX_FILE_SIZE:
        raise ValidationError("File too large")
    
    # Check extension
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext in BLOCKED_EXTENSIONS:
        raise ValidationError("File type not allowed")
    
    # Check mime type
    mime_type = magic.from_buffer(file_obj.read(1024), mime=True)
    file_obj.seek(0)
    
    if mime_type in BLOCKED_MIME_TYPES:
        raise ValidationError("File type not allowed")
    
    return True
```

---

## Storage Architecture

### Storage Abstraction

```python
# storage/base.py

from abc import ABC, abstractmethod

class BaseStorageService(ABC):
    """Abstract storage service"""
    
    @abstractmethod
    def upload(self, file_obj, path):
        """Upload file"""
        pass
    
    @abstractmethod
    def download(self, path):
        """Download file"""
        pass
    
    @abstractmethod
    def delete(self, path):
        """Delete file"""
        pass
    
    @abstractmethod
    def exists(self, path):
        """Check if file exists"""
        pass
    
    @abstractmethod
    def get_url(self, path, expires=3600):
        """Get signed URL"""
        pass
```

```python
# storage/local.py

class LocalStorageService(BaseStorageService):
    """Local filesystem storage"""
    
    def __init__(self, base_path):
        self.base_path = base_path
    
    def upload(self, file_obj, path):
        full_path = os.path.join(self.base_path, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)
        
        return path
    
    def download(self, path):
        full_path = os.path.join(self.base_path, path)
        return open(full_path, 'rb')
    
    def delete(self, path):
        full_path = os.path.join(self.base_path, path)
        if os.path.exists(full_path):
            os.remove(full_path)
    
    def exists(self, path):
        full_path = os.path.join(self.base_path, path)
        return os.path.exists(full_path)
    
    def get_url(self, path, expires=3600):
        return f"/media/{path}"
```

```python
# storage/s3.py

import boto3
from botocore.exceptions import ClientError

class S3StorageService(BaseStorageService):
    """AWS S3 storage"""
    
    def __init__(self, bucket_name, region='us-east-1'):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3', region_name=region)
    
    def upload(self, file_obj, path):
        try:
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                path
            )
            return path
        except ClientError as e:
            raise StorageError(f"S3 upload failed: {e}")
    
    def download(self, path):
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=path
            )
            return response['Body']
        except ClientError as e:
            raise StorageError(f"S3 download failed: {e}")
    
    def delete(self, path):
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=path
            )
        except ClientError as e:
            raise StorageError(f"S3 delete failed: {e}")
    
    def exists(self, path):
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=path
            )
            return True
        except ClientError:
            return False
    
    def get_url(self, path, expires=3600):
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': path
                },
                ExpiresIn=expires
            )
            return url
        except ClientError as e:
            raise StorageError(f"URL generation failed: {e}")
```

---

## Background Jobs

### Celery Tasks

```python
# files/tasks.py

from celery import shared_task
from PIL import Image
import os

@shared_task
def create_thumbnail(file_id):
    """Create thumbnail for image files"""
    from apps.files.models import File
    
    file_obj = File.objects.get(id=file_id)
    
    if not file_obj.mime_type.startswith('image/'):
        return
    
    # Open image
    img = Image.open(file_obj.file.path)
    
    # Create thumbnail
    img.thumbnail((300, 300))
    
    # Save thumbnail
    thumb_path = f"thumbnails/{file_id}.jpg"
    img.save(thumb_path, "JPEG")
    
    file_obj.thumbnail = thumb_path
    file_obj.save()

@shared_task
def cleanup_expired_files():
    """Delete expired IP Group files"""
    from apps.files.models import File
    from django.utils import timezone
    
    expired_files = File.objects.filter(
        expires_at__lt=timezone.now(),
        ip_group__isnull=False
    )
    
    for file in expired_files:
        # Delete from storage
        storage_service.delete(file.file.name)
        
        # Delete from database
        file.delete()

@shared_task
def cleanup_trash():
    """Delete old trash files"""
    from apps.files.models import File
    from django.utils import timezone
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=30)
    
    old_trash = File.objects.filter(
        is_deleted=True,
        deleted_at__lt=cutoff_date
    )
    
    for file in old_trash:
        storage_service.delete(file.file.name)
        file.delete()

@shared_task
def send_notification_email(notification_id):
    """Send email notification"""
    from apps.notifications.models import Notification
    from django.core.mail import send_mail
    
    notification = Notification.objects.get(id=notification_id)
    
    if notification.user.email_notifications:
        send_mail(
            subject=notification.title,
            message=notification.message,
            from_email='noreply@example.com',
            recipient_list=[notification.user.email],
            fail_silently=False,
        )
        
        notification.is_emailed = True
        notification.save()
```

### Celery Beat Schedule

```python
# config/settings/base.py

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'cleanup-expired-files': {
        'task': 'apps.files.tasks.cleanup_expired_files',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    'cleanup-trash': {
        'task': 'apps.files.tasks.cleanup_trash',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'reset-daily-limits': {
        'task': 'apps.ipgroup.tasks.reset_daily_limits',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
}
```

---

## Frontend Specifications

### JavaScript File Upload

```javascript
// static/js/file-upload.js

class FileUploader {
    constructor(options) {
        this.uploadUrl = options.uploadUrl;
        this.chunkSize = 5 * 1024 * 1024; // 5MB chunks
        this.maxRetries = 3;
    }
    
    async uploadFile(file, metadata) {
        const totalChunks = Math.ceil(file.size / this.chunkSize);
        const fileId = this.generateFileId();
        
        for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
            const start = chunkIndex * this.chunkSize;
            const end = Math.min(start + this.chunkSize, file.size);
            const chunk = file.slice(start, end);
            
            await this.uploadChunk(chunk, {
                fileId,
                chunkIndex,
                totalChunks,
                fileName: file.name,
                ...metadata
            });
            
            // Update progress
            const progress = ((chunkIndex + 1) / totalChunks) * 100;
            this.onProgress(progress);
        }
        
        return await this.finalizeUpload(fileId);
    }
    
    async uploadChunk(chunk, metadata) {
        const formData = new FormData();
        formData.append('chunk', chunk);
        formData.append('metadata', JSON.stringify(metadata));
        
        let retries = 0;
        while (retries < this.maxRetries) {
            try {
                const response = await fetch(this.uploadUrl, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': this.getCsrfToken()
                    }
                });
                
                if (response.ok) {
                    return await response.json();
                }
                
                throw new Error('Upload failed');
            } catch (error) {
                retries++;
                if (retries >= this.maxRetries) {
                    throw error;
                }
                await this.delay(1000 * retries); // Exponential backoff
            }
        }
    }
    
    onProgress(percent) {
        // Override this method
        console.log(`Upload progress: ${percent}%`);
    }
    
    generateFileId() {
        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }
    
    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }
    
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}
```


 

“I want my entire website to be fully responsive across all devices.

### Requirements:

* The layout must adapt smoothly to **mobile, tablet, and desktop screens**
* Use **CSS Grid or Flexbox** for layout (no fixed positioning hacks)
* Avoid fixed widths/heights; use **responsive units (%, rem, vw, vh)**
* Implement proper **breakpoints**:

  * Mobile (<768px)
  * Tablet (768px–1024px)
  * Desktop (>1024px)

---

### UI Behavior:

* On desktop → multiple columns/grid layout
* On tablet → reduced columns
* On mobile → single column (stacked layout)
* Images should scale properly (no overflow or distortion)
* Text should remain readable without zooming
* Buttons should be touch-friendly (proper spacing and size)

---

### Components to Fix:

* Navbar should collapse into menu (hamburger) on small screens
* File cards should resize and stack properly
* Forms and inputs should fit screen width
* Tables (if any) should scroll or adapt

---

### Goal:

Create a clean, fluid, mobile-first responsive design where no element breaks, overflows, or requires horizontal scrolling.”

---


---

## Testing Requirements

### Unit Tests

```python
# tests/files/test_upload.py

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.files.services import FileUploadService

@pytest.mark.django_db
class TestFileUpload:
    
    def test_upload_valid_file(self, user):
        """Test uploading valid file"""
        file = SimpleUploadedFile(
            "test.txt",
            b"file_content",
            content_type="text/plain"
        )
        
        service = FileUploadService()
        result = service.upload_file(
            file,
            user,
            destination='private'
        )
        
        assert result.owner == user
        assert result.file_size == 12
    
    def test_upload_exceeds_quota(self, user):
        """Test upload exceeding quota"""
        user.storage_quota = 100
        user.save()
        
        large_file = SimpleUploadedFile(
            "large.txt",
            b"x" * 200
        )
        
        service = FileUploadService()
        
        with pytest.raises(QuotaExceededError):
            service.upload_file(large_file, user, 'private')
    
    def test_duplicate_detection(self, user):
        """Test duplicate file detection"""
        # Upload first file
        file1 = SimpleUploadedFile("test.txt", b"content")
        service = FileUploadService()
        result1 = service.upload_file(file1, user, 'private')
        
        # Try uploading duplicate
        file2 = SimpleUploadedFile("test2.txt", b"content")
        result2 = service.upload_file(file2, user, 'private')
        
        # Should detect duplicate
        assert result1.file_hash == result2.file_hash
```

### Integration Tests

```python
# tests/integration/test_group_workflow.py

@pytest.mark.django_db
class TestGroupWorkflow:
    
    def test_complete_group_workflow(self, user1, user2):
        """Test complete group creation and file sharing"""
        
        # Create group
        group = Group.objects.create(
            name="Test Group",
            owner=user1
        )
        
        # Add member
        GroupMembership.objects.create(
            user=user2,
            group=group,
            role='member'
        )
        
        # Upload file to group
        file = SimpleUploadedFile("shared.txt", b"content")
        service = FileUploadService()
        result = service.upload_file(
            file,
            user1,
            destination='group',
            group_id=group.id
        )
        
        # Check access
        engine = PermissionEngine()
        assert engine.can_access_file(user2, result)
```

---

## Deployment Configuration

### Docker Setup

```dockerfile
# Dockerfile

FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

```yaml
# docker-compose.yml

version: '3.8'

services:
  web:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - .:/app
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db
      - redis

  db:
    image: postgres:14
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=fileplatform
      - POSTGRES_USER=admin
      - POSTGRES_PASSWORD=secret

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  celery:
    build: .
    command: celery -A config worker -l info
    volumes:
      - .:/app
    depends_on:
      - db
      - redis

  celery-beat:
    build: .
    command: celery -A config beat -l info
    volumes:
      - .:/app
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
  static_volume:
  media_volume:
```

### Environment Variables

```bash
# .env.example

# Django
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Redis
REDIS_URL=redis://localhost:6379/0

# Storage
STORAGE_BACKEND=local  # or 's3'
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=
AWS_S3_REGION_NAME=us-east-1

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# File Upload
MAX_UPLOAD_SIZE=104857600  # 100MB
CHUNK_SIZE=5242880  # 5MB
```

---

## Performance Optimization

### Database Indexing

```python
# Add these to respective models

class File(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['owner', '-created_at']),
            models.Index(fields=['file_hash']),
            models.Index(fields=['group', 'is_deleted']),
            models.Index(fields=['expires_at']),
        ]

class GroupMembership(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['user', 'group', 'is_active']),
            models.Index(fields=['group', 'role']),
        ]
```

### Caching Strategy

```python
# core/cache.py

from django.core.cache import cache

def get_user_files_cached(user_id):
    """Cache user files list"""
    cache_key = f"user_files:{user_id}"
    
    files = cache.get(cache_key)
    if not files:
        files = File.objects.filter(
            owner_id=user_id,
            is_deleted=False
        ).values('id', 'title', 'created_at')
        
        cache.set(cache_key, list(files), timeout=300)  # 5 minutes
    
    return files

def invalidate_user_files_cache(user_id):
    """Invalidate cache on file upload/delete"""
    cache_key = f"user_files:{user_id}"
    cache.delete(cache_key)
```

---

## API Rate Limiting

```python
# settings/base.py

REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'upload': '50/hour',
    }
}
```

---

**End of Technical Specification**

---

## Next Steps

1. Review and approve this specification
2. Set up development environment
3. Create database migrations
4. Implement Phase 1 features
5. Write unit tests
6. Deploy to staging
7. Conduct security audit
8. Launch MVP

---

**Document Status:** Draft  
**Requires Review:** Yes  
**Estimated Implementation:** 3-4 weeks for MVP
