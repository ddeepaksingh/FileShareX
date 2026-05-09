# FileShareX

A feature-rich Django file-sharing platform that supports both **anonymous IP-based quick sharing** and **full authenticated user accounts** with group collaboration, versioning, and a trash system.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Database Models](#database-models)
- [URL Reference](#url-reference)
- [Local Development Setup](#local-development-setup)
- [Docker Setup (Production-like)](#docker-setup-production-like)
- [Environment Variables](#environment-variables)
- [Settings Architecture](#settings-architecture)
- [Background Tasks (Celery)](#background-tasks-celery)
- [Running Tests](#running-tests)
- [Deployment Checklist](#deployment-checklist)
- [Roadmap](#roadmap)

---

## Overview

FileShareX offers two parallel sharing modes:

| Mode | Auth Required | Storage | Lifetime |
|---|---|---|---|
| **IP Group** (Quick Share) | No | 500 MB / IP | 1 h – 7 d (configurable) |
| **User Account** | Yes | 5 GB / user | Permanent (trash system) |

Users from the **same public IP** are automatically grouped for instant sharing — no login required. Logged-in users get private storage, group collaboration, file versioning, and a 30-day trash restore window.

---

## Features

### Implemented (Phases 1 – 4)

**Authentication (Phase 1)**
- Custom `User` model — email as primary login identifier, UUID primary key
- Signup with optional profile photo upload
- Login / Logout with session management
- Full password reset flow via email
- Password change for authenticated users
- User dashboard with storage stats

**File Management (Phase 2)**
- Private file upload with drag-and-drop
- Chunked upload for files up to 100 MB (5 MB chunks)
- SHA-256 deduplication check on every upload
- File preview: images, PDFs, video, audio
- Hierarchical folder system (root + sub-folders)
- Soft-delete trash with per-file restore
- Auto-clean trash after 30 days
- Download counter and view counter per file
- File type validation + blocked dangerous extensions

**IP Group — Anonymous Quick Share (Phase 3)**
- Zero-login file sharing scoped to the visitor's public IP
- Cookie-based anonymous uploader identity
- Configurable per-IP storage quota (default 500 MB)
- Configurable per-IP rate limit (default 20 uploads/hour)
- Expiry-only deletion (no trash for IP files)
- Admin can enable/disable IP Group globally
- Automatic cleanup of expired files via Celery beat
- Daily upload-counter reset at midnight

**Normal Groups (Phase 4)**
- Create groups with name, description, privacy setting
- Privacy modes: `private`, `public`, `invite_only`
- Group storage quota (default 10 GB)
- Roles: Admin (full control) and Member (upload/download)
- Per-member `can_upload` / `can_download` toggles
- Add members by username or email
- Archive groups
- Group file listing and upload

### Planned (Phases 5 – 6)

- Moderator role, join-request system, ban/remove, invite links
- File-level permissions per member
- Public shareable links with expiry and optional password
- File versioning (same user + same name + same location)
- Duplicate-detection prompt (reuse / new copy / cancel)
- Global search
- Notification system
- Activity log / audit trail
- Dashboard with recent files and storage charts
- Real-time notifications (WebSocket / SSE)

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | Django 4.2+ |
| **Database** | SQLite (dev) / PostgreSQL 15 (production) |
| **Task Queue** | Celery + Redis 7 |
| **Web Server** | Gunicorn |
| **Reverse Proxy** | Nginx 1.25 |
| **File Hashing** | `hashlib` SHA-256 |
| **MIME Detection** | `python-magic` / `python-magic-bin` (Windows) |
| **Image Processing** | Pillow |
| **Config Management** | `python-decouple` |
| **Containerisation** | Docker + Docker Compose |
| **Frontend** | Django Templates + Vanilla JS |

---

## Project Structure

```
Files-share-system/
├── apps/
│   ├── accounts/        # Custom User model, auth views, profile
│   ├── files/           # File upload, My Files, Folder, Trash
│   ├── groups/          # Normal groups + membership
│   └── ipgroup/         # IP-based anonymous quick share
├── config/
│   ├── settings/
│   │   ├── base.py      # Shared settings
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── nginx/
│   └── default.conf     # Nginx reverse-proxy config
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
├── static/              # CSS + JS source files
├── templates/           # Django HTML templates
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh        # migrate → collectstatic → gunicorn
├── .env.docker.example  # Docker env template
├── .env.example         # Local dev env template
└── manage.py
```

---

## Database Models

### `accounts.User`
Extends `AbstractUser`. Email is the login identifier.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `email` | EmailField | Unique, indexed — used as `USERNAME_FIELD` |
| `username` | CharField | Still required by Django admin |
| `profile_photo` | ImageField | Uploaded to `profiles/` |
| `storage_quota` | BigInt | Default 5 GB |
| `storage_used` | BigInt | Tracked on every upload/delete |
| `email_notifications` | Boolean | Toggle email alerts |

### `files.File`
Central model for all file types (private, group, IP group).

| Field | Notes |
|---|---|
| `owner` | FK → User (null for anonymous IP uploads) |
| `folder` | FK → Folder (optional) |
| `group` | FK → groups.Group (optional) |
| `ip_group` | FK → IPGroup (set for anonymous uploads) |
| `anonymous_uploader` | FK → AnonymousUploader (cookie identity) |
| `file_hash` | SHA-256 — used for duplicate detection |
| `is_deleted` / `deleted_at` | Soft-delete / trash system |
| `expires_at` | Set for IP Group files only |
| `is_latest_version` / `version_number` / `parent_file` | Versioning stubs (Phase 6) |

### `files.Folder`
Hierarchical folder tree, scoped to owner and optionally a group.

### `files.ChunkUpload`
Tracks in-progress chunked uploads until all chunks arrive.

### `groups.Group`

| Field | Notes |
|---|---|
| `privacy` | `private` / `public` / `invite_only` |
| `storage_quota` | Default 10 GB |
| `allow_join_requests` | Gate for join-request system |
| `is_archived` | Soft-archive flag |

### `groups.GroupMembership`
Joins `User` ↔ `Group` with roles (`admin`, `member`) and per-member `can_upload` / `can_download` flags.

### `ipgroup.IPGroup`
One record per unique public IP.

| Field | Notes |
|---|---|
| `ip_address` | Unique — identifies the network |
| `storage_quota` | Default 500 MB |
| `is_blocked` | Admin can block an IP |
| `upload_count_today` | Reset at midnight by Celery beat |

### `ipgroup.AnonymousUploader`
Cookie-based identity scoped to an IPGroup. Identity is lost when the browser cookie is cleared.

---

## URL Reference

| Prefix | App | Key endpoints |
|---|---|---|
| `/accounts/` | accounts | `signup/`, `login/`, `logout/`, `profile/`, `dashboard/`, `password/*` |
| `/files/` | files | `''` (my files), `upload/`, `<uuid>/`, `<uuid>/download/`, `trash/`, `folder/create/` |
| `/share/` | ipgroup | `''` (IP files), `upload/`, `<uuid>/`, `<uuid>/download/`, `<uuid>/delete/` |
| `/groups/` | groups | `''` (my groups), `create/`, `<uuid>/`, `<uuid>/edit/`, `<uuid>/add-member/`, `<uuid>/archive/` |
| `/admin/` | Django admin | Full model admin |
| `/` | — | Redirects to `accounts:dashboard` |

---

## Local Development Setup

**Requirements:** Python 3.11+, `uv` or `pip`

```bash
# 1. Clone the repo
git clone <repository-url>
cd Files-share-system

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements/development.txt

# On Windows, python-magic-bin is already in base.txt
# On Linux/Mac, ensure libmagic is installed:
#   sudo apt install libmagic1   # Debian/Ubuntu
#   brew install libmagic        # macOS

# 4. Configure environment
cp .env.example .env
# Edit .env — set SECRET_KEY at minimum

# 5. Apply migrations
python manage.py migrate

# 6. Create a superuser
python manage.py createsuperuser

# 7. Run the dev server
python manage.py runserver
```

Open **http://127.0.0.1:8000** in your browser.

> **Note:** The development settings use SQLite and Django's built-in development server. `DJANGO_SETTINGS_MODULE` defaults to `config.settings.development`.

---

## Docker Setup (Production-like)

The Docker stack runs: **PostgreSQL 15 → Redis 7 → Gunicorn (Django) → Nginx**.

```bash
# 1. Copy and fill the Docker env template
cp .env.docker.example .env
# Required: set SECRET_KEY and DB_PASSWORD at minimum

# 2. Build and start all services
docker compose up --build -d

# 3. Create a Django superuser (first time only)
docker compose exec web python manage.py createsuperuser

# 4. Open the app
# http://localhost  (Nginx on port 80)
```

**Service overview:**

| Service | Image | Role |
|---|---|---|
| `db` | `postgres:15-alpine` | Primary database |
| `redis` | `redis:7-alpine` | Session cache + Celery broker |
| `web` | (built from `Dockerfile`) | Gunicorn app server on port 8000 |
| `nginx` | `nginx:1.25-alpine` | Reverse proxy, serves static/media |

The `entrypoint.sh` automatically runs `migrate` and `collectstatic` before starting Gunicorn.

**Useful commands:**

```bash
# View logs
docker compose logs -f web

# Run a management command
docker compose exec web python manage.py <command>

# Stop everything
docker compose down

# Stop and delete volumes (wipes database!)
docker compose down -v
```

---

## Environment Variables

Copy `.env.docker.example` → `.env` for Docker, or `.env.example` → `.env` for local dev.

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | *(required)* | Django secret key — generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | `False` | Set `True` in development only |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated list of allowed hostnames |
| `DB_NAME` | `fileshare` | PostgreSQL database name |
| `DB_USER` | `fileshare` | PostgreSQL username |
| `DB_PASSWORD` | *(required)* | PostgreSQL password |
| `DB_HOST` | `db` | PostgreSQL host (use `db` inside Docker) |
| `DB_PORT` | `5432` | PostgreSQL port |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `EMAIL_BACKEND` | console backend | Use `smtp.EmailBackend` for real delivery |
| `EMAIL_HOST` | `smtp.gmail.com` | SMTP server |
| `EMAIL_PORT` | `587` | SMTP port |
| `EMAIL_USE_TLS` | `True` | Enable STARTTLS |
| `EMAIL_HOST_USER` | — | SMTP username |
| `EMAIL_HOST_PASSWORD` | — | SMTP password / app password |
| `IP_GROUP_ENABLED` | `True` | Enable/disable the anonymous IP share feature |
| `IP_GROUP_MAX_UPLOAD_MB` | `50` | Max file size for IP Group uploads (MB) |
| `IP_GROUP_RATE_LIMIT` | `20` | Max uploads per IP per hour |
| `SECURE_SSL_REDIRECT` | `False` | Set `True` only when HTTPS is terminated by Nginx |
| `GUNICORN_WORKERS` | `3` | Gunicorn worker count — rule of thumb: (2 × CPU cores) + 1 |

---

## Settings Architecture

Settings are split into three modules under `config/settings/`:

```
config/settings/
├── base.py         # Shared: apps, middleware, auth, storage, upload limits, IP Group config
├── development.py  # DEBUG=True, SQLite, verbose logging
└── production.py   # DEBUG=False, PostgreSQL, security headers, HTTPS settings
```

`DJANGO_SETTINGS_MODULE` is set to `config.settings.production` inside the `Dockerfile`. For local development it defaults to `config.settings.development`.

**Key base.py limits:**

| Setting | Value |
|---|---|
| `MAX_UPLOAD_SIZE` | 100 MB |
| `CHUNK_SIZE` | 5 MB |
| `DATA_UPLOAD_MAX_MEMORY_SIZE` | 5.5 MB (per-chunk Django limit) |
| Default user storage quota | 5 GB |
| Default group storage quota | 10 GB |
| Default IP Group storage quota | 500 MB |

---

## Background Tasks (Celery)

Celery is optional for local development but required in production for automatic cleanup.

**Scheduled tasks (Celery Beat):**

| Task | Schedule | Action |
|---|---|---|
| `apps.ipgroup.tasks.cleanup_expired_files` | Every 30 minutes | Permanently deletes IP Group files past their `expires_at` |
| `apps.ipgroup.tasks.reset_daily_upload_limits` | Daily at midnight UTC | Resets `upload_count_today` for all IPGroup records |

**Running Celery locally:**

```bash
# Worker
celery -A config worker -l info

# Scheduler (beat)
celery -A config beat -l info
```

> If Celery is not installed, the base settings gracefully skip the beat schedule via a `try/except ImportError`.

---

## Running Tests

```bash
# Run all tests
pytest

# Run a specific app
pytest tests/groups/

# Run with coverage
pytest --cov=apps --cov-report=term-missing
```

Test configuration is in `pytest.ini` and `conftest.py`.

---

## Deployment Checklist

- [ ] Generate a strong `SECRET_KEY` (50+ random characters)
- [ ] Set `DEBUG=False`
- [ ] Set `ALLOWED_HOSTS` to your domain / server IP
- [ ] Configure PostgreSQL credentials
- [ ] Configure Redis URL
- [ ] Set up SMTP for password reset emails
- [ ] Set `SECURE_SSL_REDIRECT=True` once HTTPS is active
- [ ] Obtain and configure an SSL/TLS certificate (Let's Encrypt recommended)
- [ ] Run `python manage.py migrate`
- [ ] Run `python manage.py collectstatic`
- [ ] Create a superuser
- [ ] Set up Celery worker + beat as system services (systemd / supervisor)
- [ ] Configure log rotation
- [ ] Set up regular PostgreSQL backups
- [ ] Add monitoring (Sentry for errors, server health checks)

---

## Roadmap

| Phase | Status | Scope |
|---|---|---|
| Phase 1 — Auth & Profile | Done | Signup, login, logout, profile, dashboard, password reset |
| Phase 2 — File Management | Done | Upload, My Files, Folder, Trash, Preview, Chunked upload |
| Phase 3 — IP Group | Done | Anonymous quick-share, rate limits, expiry, cleanup |
| Phase 4 — Normal Groups | Done | Group CRUD, membership, roles, group file upload |
| Phase 5 — Advanced Groups | Planned | Moderator role, join requests, invite links, bans, permissions |
| Phase 6 — Polish & Extras | Planned | Public links, versioning, deduplication prompt, search, notifications, activity log |

---

## License

[Specify your license here — MIT, GPL, proprietary, etc.]
