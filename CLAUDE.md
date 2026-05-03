# File Sharing Platform - Complete Documentation

## Project Overview

A feature-rich Django-based file sharing platform with support for both anonymous IP-based sharing and authenticated user accounts. The platform offers temporary quick sharing via IP groups alongside permanent storage through user accounts with advanced group collaboration features.

### Key Highlights
- **Anonymous Quick Share**: IP-based temporary file sharing without login
- **User Accounts**: Permanent storage with cross-device access
- **Group Collaboration**: Advanced permission-based file sharing
- **Smart File Management**: Versioning, deduplication, and trash system
- **Security First**: Rate limiting, storage quotas, and access controls

---

## Core Features

### 1. Default IP-Based Group (Temporary Quick Share)

**Feature Name:** IP Group / Auto IP Group / Local Network Share

**Description:**
- Automatically detects visitor's public IP address (no login required)
- All users from the same IP are considered members of the same temporary group
- Enables instant file sharing without signup/login
- Files are accessible only to users with the same IP
- Built-in expiry system (default 24 hours, max 7 days)

**Key Capabilities:**
- Anonymous file upload, view, and download
- Cookie-based anonymous identity for uploader tracking
- Admin dashboard control (enable/disable IP Group)
- Configurable file size limits and allowed types
- Total storage limit per IP
- Selectable expiry time (1h, 24h, 7d)
- Automatic cleanup of expired files

**Security & Limits:**
- Rate limiting per IP (uploads per minute)
- Maximum storage per IP (e.g., 500MB)
- Access restricted to same IP only
- Cookie deletion results in loss of delete rights

---

### 2. User Signup

**Feature Name:** User Registration System

**Description:**
- Standard registration with username, email, password
- Email uniqueness validation
- Optional profile photo upload
- Automatic merging of IP Group files into user profile upon signup

**Fields:**
- Username (unique)
- Email (unique)
- Password + Confirm Password
- Profile Photo (optional)

---

### 3. User Login

**Feature Name:** User Authentication

**Description:**
- Login with Email/Username + Password
- Access to IP Group files + private files + normal groups
- "Remember me" functionality
- Session management

---

### 4. User Profile & Dashboard

**Feature Name:** User Profile + Dashboard

**Description:**
- Profile photo and user statistics (files, groups, storage)
- Recent activity feed
- Multi-tab interface:
  - My Files
  - My Groups
  - IP Group Files
  - Activity Log
- Quick upload button for easy access

---

### 5. File Upload System

**Feature Name:** Advanced File Upload

**Description:**
- Drag & drop + traditional file selection
- Optional title and description
- Upload destination selection:
  - Private
  - Specific Group
  - IP Group
- Chunked upload for large files with progress bar
- Duplicate detection using file hash (SHA-256)

**Limits:**
- Per-user and per-IP storage quotas
- Configurable allowed file types
- Blocked dangerous file types (exe, scripts)

---

### 6. My Files & File Management

**Feature Name:** My Files Page

**Description:**
- Comprehensive file listing (Private + Group + IP Group)
- Advanced search, filter, and sort capabilities
- File preview support:
  - Images
  - PDFs
  - Videos
  - Audio files
- Download, delete, and version history
- Trash system with soft delete

---

### 7. Folder System

**Feature Name:** Folders & Organization

**Description:**
- Default root folder for all users
- Create sub-folders (private or within groups)
- Move files between folders
- Hierarchical folder structure

---

### 8. Group Creation & Management

**Feature Name:** Normal Groups

**Description:**
- Create groups with name, description, and privacy settings
- Owned Groups vs. Joined Groups separation
- Group detail page showing:
  - Files
  - Members
  - Settings

---

### 9. Group Roles & Permissions

**Feature Name:** Roles & Permissions

**Description:**
- **Admin**: Full control + ownership transfer capability
- **Moderator**: Add/remove members, delete files
- **Member**: Upload/download with sub-permissions:
  - Viewer (read-only)
  - Uploader (can add files)
  - Editor (can modify)
- File-level permission configuration
- Leave group and archive old groups functionality

---

### 10. Member & Join Management

**Feature Name:** Member Management

**Description:**
- Add members by username or email
- Join Request System:
  - Approve/reject requests
- Remove or ban members
- Invite links with expiry
- Member role assignment

---

### 11. File Sharing & Public Links

**Feature Name:** External Sharing

**Description:**
- Generate public shareable links
- Optional password protection
- Configurable expiry time (1h to 30 days)
- IP Group files can generate temporary public links
- View-only vs. download-allowed options

**Priority Rule:**
Public Link > IP/Group restrictions (link holders bypass IP restrictions)

---

### 12. Background & Maintenance Systems

**Feature Name:** Auto Systems

**Description:**
- Scheduled jobs for:
  - Auto expiry & cleanup of expired files
  - Background processing (thumbnails, virus scanning, indexing)
  - Rate limiting enforcement
  - Storage quota enforcement
- Comprehensive audit logs:
  - Upload events
  - Download events
  - Delete events
  - Group actions

---

### 13. Search & Notifications

**Feature Name:** Search + Notifications

**Description:**
- Global search across file names
- Future: Content-based search
- Real-time notification system:
  - New file uploads
  - Join requests
  - Group invitations
- Read/unread status tracking
- Email notification toggle

---

### 14. Security & Architecture Layers

**Feature Name:** Core Security & Scalability

**Description:**
- Centralized Permission Engine
- Storage Service abstraction (supports local disk and S3)
- Queue system for heavy tasks
- Proper folder structure management
- Versioning support
- Duplicate handling
- Trash system
- Multi-layered access control:
  - IP-based
  - Cookie-based
  - Login-based

---

## Critical Design Decisions

### 1. IP + Login Merge Logic

**Clear Rule:**
- IP Group files **never** merge into "My Files"
- Two separate sections maintained:
  - **My Files**: Logged-in user's private files + normal group files
  - **Local Network (IP Group)**: Files uploaded from same IP (including other anonymous users)
- After login, users see IP Group as a separate tab/section
- User's own IP uploads highlighted in "My IP Uploads" sub-section

**Distinction:**
- IP files = Network shared (visible to all with same IP)
- Private/Group files = Personal ownership (owner + allowed members only)

---

### 2. Duplicate Detection

**Feature Name:** Duplicate File Handling

**Process:**
1. Calculate SHA-256 hash for every uploaded file
2. If identical hash exists, show user options:
   - **Reuse existing file** (saves storage, adds reference)
   - **Upload as new copy** (allows duplicate)
   - **Cancel**
3. No silent skipping
4. Multiple ownership support if reused

**Rule:** Duplicate detection with user choice, no automatic actions

---

### 3. Versioning Logic

**Feature Name:** File Versioning

**Version Creation Triggers:**
Version is created ONLY when ALL conditions are met:
- Same user
- Same file name
- Same location (same folder OR same group/IP Group)

**If conditions not met:** Treated as new file (no versioning)

**Features:**
- Version history button on each file
- List, download, and restore old versions
- Maximum 10 versions per file (configurable)
- Version metadata tracking

---

### 4. Public Link vs IP Restriction

**Feature Name:** Public Sharing Links

**Access Rules:**
- **Normal access**: Follows IP restriction + login rules
- **Public Share Link**: Bypasses IP restrictions

**Public Link Options:**
- Password protection (optional)
- Expiry time (1h to 30 days)
- View-only or download-allowed

**Clear Priority:**
Public Link > IP/Group restrictions

---

### 5. Trash + Expiry Conflict Resolution

**Feature Name:** Delete & Expiry System

**IP Group Files:**
- Uses **Expiry system only** (no trash)
- Upon expiry: Permanent deletion from storage + database
- Reflects temporary nature

**Logged-in User Files (Private + Normal Groups):**
- Delete action → Moves to trash folder
- Restore option available from trash
- Auto-clean trash after 30 days
- Reflects permanent nature

**Rule:**
- IP Group = Temporary → Expiry only
- User files = Permanent → Trash system

---

### 6. Rate Limit + Chunk Upload

**Feature Name:** Upload Rate Limiting

**Smart Implementation:**
- Rate limit applies **per upload session**, not per chunk
- Large file uploads count as single upload
- Chunk requests exempt from rate limits (or very high limit)
- Progress bar + resume support maintained

**Result:** Large files upload smoothly without rate limit blocking

---

## Additional Clarifications

### 7. Anonymous ID
- Cookie-based identification
- Identity lost upon cookie deletion (accepted behavior)

### 8. File Ownership Transfer
- Group admins can change file owner
- Transfer requires confirmation

### 9. Storage Structure
- Abstract storage layer
- Supports both local disk and S3
- Easy migration between storage backends

### 10. Search Indexing
- Metadata indexed immediately after upload
- Background job for indexing
- Content-based search planned for future

---

## Final Architecture Rules

### Core Principles
- **IP Group**: Temporary, Anonymous, Network-only access
- **User Account**: Permanent, Private, Cross-device access
- **Expiry**: IP Group files only
- **Trash**: User files only
- **Public Link**: Full bypass of restrictions
- **Versioning**: Strict same-user + same-name + same-location rule
- **Duplicates**: User choice required

---

## Development Roadmap

### Phase 1: Core Setup + Authentication ⭐ **START HERE**
**Priority:** Must Have  
**Estimated Time:** 1-2 days

**Features:**
1. Django project setup + apps creation (`accounts`, `files`, `groups`, `ipgroup`)
2. Custom User Model (if needed)
3. Signup functionality
4. Login functionality
5. Logout functionality
6. User Profile Page (basic)
7. Base template + Navbar
8. Django Admin setup

**Why First?** All other features depend on user authentication system.

---

### Phase 2: Basic File Upload + My Files
**Priority:** Must Have  
**Estimated Time:** 2-3 days

**Features:**
8. File model creation
9. File Upload (Private only)
10. My Files Page (list, download, delete)
11. File Preview (images + PDFs)
12. Folder system (basic root folder)
13. File size limits + allowed types
14. Trash system (soft delete)

**Milestone:** Basic working file management app ready.

---

### Phase 3: IP Group (Anonymous Quick Share) 🌟 **UNIQUE FEATURE**
**Priority:** High  
**Estimated Time:** 2-3 days

**Features:**
15. IP detection middleware
16. Anonymous Identity (Cookie-based)
17. IP Group model (special group type)
18. Upload in IP Group (without login)
19. IP Group Files listing (same IP only)
20. Expiry system for IP files
21. Rate limiting + Storage limit per IP
22. Auto cleanup job (expired files)

**Milestone:** Anonymous file sharing fully functional. Main selling point ready.

---

### Phase 4: Normal Groups + Basic Members
**Priority:** High  
**Estimated Time:** 3-4 days

**Features:**
23. Group model
24. Create Group functionality
25. My Groups Page (Owned + Joined)
26. Group Detail Page
27. Upload file inside normal group
28. Group Files listing

**Milestone:** Basic group collaboration enabled.

---

### Phase 5: Advanced Group Features
**Priority:** Medium  
**Estimated Time:** 3-4 days

**Features:**
29. Group Roles (Admin, Moderator, Member)
30. Add / Remove / Ban Member
31. Join Request System
32. Group Invite Link
33. File permissions per member
34. Ownership transfer
35. Leave Group + Archive functionality

**Milestone:** Full-featured group collaboration system.

---

### Phase 6: Polish + Security + Extras
**Priority:** Medium  
**Estimated Time:** 2-3 days

**Features:**
36. Global Search
37. Notification system
38. Public Share Links (with expiry + password)
39. File versioning
40. Duplicate handling with user choice
41. Activity Log
42. Dashboard (Recent files, stats)
43. Responsive Design + UX improvements
44. Rate limiting implementation
45. Security hardening
46. Backup settings

**Milestone:** Production-ready application.

---

## Recommended Development Order

### MVP Strategy (Minimum Viable Product)
1. **Phase 1 + Phase 2** → Basic working app
2. **Phase 3** → Unique IP Group feature (main differentiator)
3. **Phase 4** → Group collaboration
4. **Phase 5** → Advanced features
5. **Phase 6** → Polish and production readiness

### Fast Track to Demo
- Complete **Phase 1 + Phase 2** first (3-5 days)
- Then **Phase 3** for unique selling point (2-3 days)
- You'll have a demo-ready app in 1 week

---

## Technology Stack

### Backend
- **Framework:** Django 4.x+
- **Database:** PostgreSQL (recommended) or SQLite (development)
- **Task Queue:** Celery + Redis (for background jobs)
- **Storage:** Local filesystem or AWS S3 (abstracted)

### Frontend
- **Template Engine:** Django Templates
- **CSS Framework:** TailwindCSS or Bootstrap 5
- **JavaScript:** Vanilla JS + optional Alpine.js/htmx for interactivity

### Additional Tools
- **File Hashing:** hashlib (SHA-256)
- **Rate Limiting:** Django-ratelimit or Django-axes
- **Caching:** Redis
- **File Preview:** PDF.js, image libraries

---

## Database Models (Overview)

### Core Models
1. **User** (Django's built-in or custom)
2. **File** (stores file metadata, ownership, location)
3. **Folder** (hierarchical folder structure)
4. **Group** (normal groups)
5. **IPGroup** (special IP-based groups)
6. **GroupMembership** (user-group relationships with roles)
7. **FileVersion** (version history)
8. **Notification** (notification system)
9. **AuditLog** (activity tracking)
10. **PublicLink** (shareable links)

### Key Relationships
- User → Files (one-to-many)
- User → Groups (many-to-many through GroupMembership)
- Group → Files (one-to-many)
- File → FileVersions (one-to-many)
- IPGroup → Files (one-to-many)

---

## Security Considerations

### Access Control
- IP-based access for anonymous users
- Cookie-based identity tracking
- Role-based permissions (RBAC)
- File-level permissions

### Data Protection
- Password hashing (Django's built-in)
- CSRF protection (Django middleware)
- SQL injection prevention (ORM)
- XSS prevention (template escaping)

### Rate Limiting
- Per-IP upload limits
- Per-user API limits
- Chunked upload exemptions

### File Security
- File type validation
- Blocked dangerous extensions
- Virus scanning (optional)
- Size limits enforcement

---

## Storage Architecture

### Abstraction Layer
```
StorageService (Abstract)
    ├── LocalStorageService
    └── S3StorageService
```

### Benefits
- Easy migration between storage backends
- Consistent API across storage types
- Support for multiple storage tiers

---

## API Endpoints (Future)

### Planned REST API
- `/api/files/` - File CRUD
- `/api/groups/` - Group management
- `/api/ipgroup/` - IP Group operations
- `/api/users/` - User management
- `/api/search/` - Global search

---

## Performance Optimization

### Implemented
- Chunked file uploads
- Background processing for heavy tasks
- Database indexing on frequently queried fields
- Caching for static data

### Future Enhancements
- CDN integration
- Database query optimization
- Frontend asset minification
- Image thumbnail caching

---

## Testing Strategy

### Test Coverage
1. **Unit Tests**: Models, views, utilities
2. **Integration Tests**: File upload flow, group operations
3. **Security Tests**: Permission checks, rate limiting
4. **Performance Tests**: Large file uploads, concurrent users

---

## Deployment Considerations

### Production Checklist
- [ ] Environment variables for sensitive data
- [ ] DEBUG = False
- [ ] Allowed hosts configuration
- [ ] Static files collection
- [ ] Database migrations
- [ ] SSL/TLS certificate
- [ ] Backup strategy
- [ ] Monitoring setup
- [ ] Log aggregation

### Recommended Hosting
- **Backend:** AWS EC2, DigitalOcean, Heroku
- **Database:** AWS RDS, managed PostgreSQL
- **Storage:** AWS S3, DigitalOcean Spaces
- **CDN:** CloudFront, CloudFlare

---

## Future Enhancements

### Phase 7+ (Post-Launch)
- Real-time collaboration (concurrent editing)
- File commenting system
- Advanced search with full-text indexing
- Mobile apps (iOS/Android)
- Desktop app (Electron)
- Integration with cloud storage (Google Drive, Dropbox)
- Advanced analytics dashboard
- Team/Organization accounts
- Custom branding options
- API for third-party integrations

---

## Success Metrics

### KPIs to Track
- **User Engagement**
  - Daily/Monthly Active Users
  - Files uploaded per user
  - Groups created per user

- **Performance**
  - Average upload time
  - Page load times
  - API response times

- **Growth**
  - New user signups
  - Retention rate
  - Feature adoption rate

---

## Support & Maintenance

### Regular Tasks
- Database backups (daily)
- Log rotation
- Security updates
- Performance monitoring
- User feedback collection

### Monitoring
- Application errors (Sentry)
- Server health (New Relic, DataDog)
- User analytics (Google Analytics)

---

## License & Credits

### Project License
[Specify your license - MIT, GPL, proprietary, etc.]

### Third-Party Libraries
- Django
- Celery
- PDF.js
- [Add as implemented]

---

## Contact & Support

### Documentation
- Full API documentation (coming soon)
- User guide (coming soon)
- Admin manual (coming soon)

### Support Channels
- GitHub Issues
- Email support
- Community forum (planned)

---

## Changelog

### Version 1.0.0 (Planned)
- Initial release with core features
- IP Group (anonymous sharing)
- User accounts
- Basic groups
- File management

---

**Last Updated:** May 2026  
**Document Version:** 1.0  
**Status:** Planning Phase

---

## Quick Start Guide (For Developers)

### Setup Steps
```bash
# Clone repository
git clone [repository-url]

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your settings

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

### First Steps After Setup
1. Access admin panel: http://localhost:8000/admin
2. Create test users
3. Upload test files
4. Create test groups
5. Test IP Group functionality

---

**End of Document**
