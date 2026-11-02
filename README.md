# Campus Lost & Found Hub

[![Django](https://img.shields.io/badge/Django-6.1-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/Neon%20PostgreSQL-Cloud-00E599?style=for-the-badge&logo=postgresql&logoColor=white)](https://neon.tech/)
[![pgvector](https://img.shields.io/badge/pgvector-Enabled-336791?style=for-the-badge)](https://github.com/pgvector/pgvector)
[![Bootstrap 5](https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![Phase 2 & 2.1 Status](https://img.shields.io/badge/Phase%202%20%26%202.1-AUDITED%20%26%20VERIFIED-success?style=for-the-badge)](#)

A centralized university platform engineered to reunite students, faculty, and campus staff with misplaced belongings through automated cataloging, verified ownership claims, and an AI semantic matching engine powered by Sentence Transformers and Neon PostgreSQL `pgvector`.

---

## 1. Technology Stack

- **Backend**: Python 3.11+ / 3.14, Django 6.1, Django REST Framework 3.18, Django ORM.
- **Database**: Neon Cloud Serverless PostgreSQL with `pgvector` extension and SSL (`sslmode=require`).
- **User Authentication**: Custom `CampusUser` model configured as `AUTH_USER_MODEL` with Role-Based Access Control (`STUDENT`, `ADMIN`, `SUPER_ADMIN`), brute-force login throttling, and case-insensitive email/username backends.
- **Frontend**: HTML5, CSS3, Bootstrap 5.3, Bootstrap Icons, Vanilla JavaScript, Django Templates.
- **Environment**: Virtual environment (`.venv`), `django-environ` (12-Factor App methodology).

---

## 2. Project Structure

```
Campus-Find/
│
├── manage.py                       # Django CLI executive script
├── requirements.txt                # Pinned project dependencies
├── README.md                       # Main documentation & setup guide
├── .gitignore                      # Git exclusion rules
├── .env.example                    # Environment variable template
│
├── config/                         # Core Project Configuration
│   ├── settings.py                 # Central settings & database config (Neon & CampusUser)
│   ├── urls.py                     # Master URL routing table
│   ├── views.py                    # Landing page view
│   └── tests.py                    # Landing page & integration tests
│
├── apps/                           # Modular Applications
│   ├── accounts/                   # CampusUser model, RBAC, backends, throttling, views
│   │   ├── models.py               # CampusUser with Role choices and conditional student_id
│   │   ├── backends.py             # EmailOrUsernameModelBackend
│   │   ├── throttling.py           # Cache-based sliding window rate-limiting
│   │   ├── permissions.py          # Mixins & decorators for STUDENT, ADMIN, SUPER_ADMIN
│   │   ├── forms.py                # Registration, login, profile, admin provisioning
│   │   ├── views.py                # Class-based auth & profile views
│   │   ├── urls.py                 # /accounts/* routes
│   │   └── tests.py                # 20+ automated unit tests
│   ├── items/                      # Lost/found reports, categories, locations (Phase 2)
│   ├── matching/                   # pgvector extension, embeddings, hybrid ranking (Phase 3)
│   ├── claims/                     # Proof submission, verification lifecycle (Phase 4)
│   ├── notifications/              # Alert dispatch, in-app notifications (Phase 5)
│   └── dashboard/                  # Student & administrative analytics
│       ├── views.py                # DashboardDispatcher & role-specific dashboards
│       ├── urls.py                 # /dashboard/* routes
│       └── tests.py                # Role dispatching tests
│
├── templates/                      # Modular HTML Templates
│   ├── base.html                   # Reusable foundation layout
│   ├── home.html                   # Public landing page
│   ├── components/                 # navbar (with dynamic auth & POST logout), footer, messages
│   ├── accounts/                   # register.html, login.html, profile.html, create_admin.html
│   └── dashboard/                  # student.html, admin.html, super_admin.html
│
├── static/                         # Static Assets
│   ├── css/main.css                # Global navy/white responsive design system (#0f2942)
│   ├── js/main.js                  # Vanilla JavaScript interactivity
│   └── images/logo.svg             # Campus Lost & Found brand logo
│
├── media/                          # Uploaded User Files
│   ├── profile_pics/               # Uploaded avatars (gitignored)
│   └── item_images/                # Uploaded item photos (gitignored)
│
└── docs/                           # Architectural Documentation
    ├── ARCHITECTURE.md             # System architecture & RBAC specifications
    ├── DATABASE_SCHEMA.md          # Relational & vector schema specifications
    ├── API_DOCUMENTATION.md        # Web and REST API endpoint specifications
    ├── MATCHING_ENGINE.md          # 384-dim embeddings & composite ranking formula
    ├── IMPLEMENTATION_STATUS.md    # Phased roadmap & verification checklist
    └── DEVELOPMENT_LOG.md          # Mandatory diagnostics policy & incident tracking
```

---

## 3. Quick Start & Setup Guide

### 3.1. Prerequisites
- Python 3.11 or newer (tested on Python 3.14)
- Neon PostgreSQL Account & Connection String
- Git

### 3.2. Setup Virtual Environment
```bash
# Clone the repository
git clone <repository-url>
cd Campus-Find

# Create and activate virtual environment
python -m venv .venv

# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# Linux / macOS:
source .venv/bin/activate
```

### 3.3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3.4. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```
Ensure `DATABASE_URL` is configured with your Neon PostgreSQL connection string:
```env
DATABASE_URL=postgresql://user:password@ep-autumn-art-bemiqhpr.c-9.us-east-2.aws.neon.tech/neondb?sslmode=require
SECRET_KEY=your-secure-random-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
UNIVERSITY_EMAIL_DOMAINS=university.edu,campus.ac.in
```

### 3.5. Run Migrations & Seed Initial Data
```bash
# Run Django system checks
python manage.py check

# Apply database migrations
python manage.py migrate

# Seed standard campus categories and locations (idempotent)
python manage.py seed_initial_data
```

### 3.6. Bootstrap Super Administrator
Promote an existing registered user to Super Administrator safely without hardcoded passwords:
```bash
python manage.py assign_super_admin admin@university.edu
```

### 3.7. Run Automated Test Suite
```bash
python manage.py test apps config
```
*All 76 test cases pass with status `OK` (0 failures, 0 errors across accounts, items, dashboard, and config).*

### 3.8. Start the Development Server
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser.

---

## 4. Key Security & Implementation Features

### 4.1. Authentication & Access Control (Phase 1)
1. **Role-Based Access Control**:
   - `STUDENT`: Self-service item reporting, claim submissions, student portal.
   - `ADMIN`: Operational staff console, claim review queue, staff moderation.
   - `SUPER_ADMIN`: Complete system governance, staff administrator provisioning portal (`/accounts/admin/provision/`).
2. **University Domain Restriction**:
   - Registration strictly verifies approved email domains via configurable `UNIVERSITY_EMAIL_DOMAINS`.
3. **Brute-Force Attack Throttling**:
   - Automatic 15-minute account lockout after 5 consecutive failed login attempts from an IP / identifier.
4. **Parameter Tamper Resistance**:
   - Role escalation, student ID tampering, and email spoofing are strictly prevented at form and model levels.
5. **POST-Only Safe Logout**:
   - Protected against CSRF attacks and pre-fetching browser hazards.

### 4.2. Lost & Found Core Features (Phase 2)
1. **Consolidated Item Model**:
   - Single clean data model for both `LOST` and `FOUND` reports with lifecycle states: `OPEN`, `CLAIM_PENDING`, `RESOLVED`, `CLOSED`.
2. **Student Privacy Protection**:
   - `reporter_display_name` strictly displays full name or username without leaking student emails, phone numbers, or registration IDs.
3. **Search & Multi-Parametric Filtering**:
   - Keyword search across title and description, filtering by item type, active category, campus location, date range, and status.
   - Default public browsing automatically excludes `RESOLVED` and `CLOSED` items.
4. **Secure Image Pipeline**:
   - Hard 5 MB limit, Pillow format verification (`JPEG`, `PNG`, `WEBP`), UUID upload path obfuscation, and disk cleanup upon item deletion or image replacement.
5. **Strict Authorization**:
   - Item editing and deletion restricted to the report owner or administrator. Non-owners receive HTTP 403 Forbidden.
   - Deletion endpoint is strictly POST-only (rejects GET with HTTP 405 Method Not Allowed).
6. **REST API**:
   - Full DRF endpoints under `/api/v1/items/`, `/api/v1/categories/`, `/api/v1/locations/`.

---

## 5. Development Diagnostics Policy

In compliance with the project's **Mandatory Development Diagnostics Policy**, all runtime errors, network anomalies, and operational failures are systematically tracked and classified in [`docs/DEVELOPMENT_LOG.md`](docs/DEVELOPMENT_LOG.md).
