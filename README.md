# Campus Lost & Found Hub

[![Django](https://img.shields.io/badge/Django-6.1-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/Neon%20PostgreSQL-Cloud-00E599?style=for-the-badge&logo=postgresql&logoColor=white)](https://neon.tech/)
[![pgvector](https://img.shields.io/badge/pgvector-Enabled-336791?style=for-the-badge)](https://github.com/pgvector/pgvector)
[![Bootstrap 5](https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![Phase 0.1 Status](https://img.shields.io/badge/Phase%200.1-COMPLETED-success?style=for-the-badge)](#)

A centralized university platform engineered to reunite students, faculty, and campus staff with misplaced belongings through automated cataloging, verified ownership claims, and an AI semantic matching engine powered by Sentence Transformers and Neon PostgreSQL `pgvector`.

---

## 1. Technology Stack

- **Backend**: Python 3.11+ / 3.14, Django 6.1, Django REST Framework 3.18, Django ORM.
- **Database**: Neon Cloud Serverless PostgreSQL with `pgvector` extension and SSL (`sslmode=require`).
- **User Authentication**: Custom `CampusUser` model configured as `AUTH_USER_MODEL` in Phase 0.1 before dependent model creation.
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
│   ├── __init__.py
│   ├── asgi.py                     # ASGI entrypoint
│   ├── wsgi.py                     # WSGI entrypoint
│   ├── settings.py                 # Central settings & database config (Neon & CampusUser)
│   ├── urls.py                     # Master URL routing table
│   ├── views.py                    # Landing page view
│   └── tests.py                    # Landing page & integration tests
│
├── apps/                           # Modular Applications
│   ├── accounts/                   # CampusUser model, auth, profiles
│   │   └── migrations/0001_initial.py  # Initial CampusUser table migration
│   ├── items/                      # Lost/found reports, categories, locations
│   ├── matching/                   # pgvector extension, embeddings, hybrid ranking
│   │   └── migrations/0001_initial.py  # VectorExtension migration
│   ├── claims/                     # Proof submission, verification lifecycle
│   ├── notifications/              # Alert dispatch, in-app notifications
│   └── dashboard/                  # Student & administrative analytics
│
├── templates/                      # Modular HTML Templates
│   ├── base.html                   # Reusable foundation layout
│   ├── home.html                   # Public landing page
│   ├── components/                 # Reusable UI widgets (navbar, footer, messages)
│   └── */placeholder.html         # Application placeholders
│
├── static/                         # Static Assets
│   ├── css/main.css                # Global navy/white responsive design system
│   ├── js/main.js                  # Vanilla JavaScript interactivity
│   └── images/logo.svg             # Campus Lost & Found brand logo
│
├── media/                          # Uploaded User Files
│   └── item_images/                # Uploaded item photos (gitignored)
│
└── docs/                           # Architectural Documentation
    ├── ARCHITECTURE.md             # System architecture & Neon pgvector blueprint
    ├── DATABASE_SCHEMA.md          # Relational & vector schema specifications
    ├── API_DOCUMENTATION.md        # REST API endpoints & payload contracts
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
Copy the example environment file and customize your settings:
```bash
cp .env.example .env
```

Ensure your `.env` contains your Neon PostgreSQL connection string:
```ini
DEBUG=True
SECRET_KEY=your-secure-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
DATABASE_URL=postgresql://[user]:[password]@[endpoint].neon.tech/[dbname]?sslmode=require
```

### 3.5. Database Initialization & Verification
```bash
# Verify Neon connection & pgvector extension status
python manage.py verify_pgvector

# Run database migrations
python manage.py migrate
```

### 3.6. Run Development Server
```bash
python manage.py runserver
```
Visit **`http://127.0.0.1:8000/`** to view the live Campus Lost & Found Hub landing page.

---

## 4. Verification & Testing

Run the automated test suite:
```bash
python manage.py test apps config --keepdb
```

Verify Django system configuration:
```bash
python manage.py check
```

---

## 5. Architectural Documentation & Diagnostics

Detailed blueprints and runtime diagnostics are maintained in [`docs/`](file:///c:/nvm/COLLEGE/Campus-Find/docs):
- [Architecture Blueprint](file:///c:/nvm/COLLEGE/Campus-Find/docs/ARCHITECTURE.md)
- [Database Schema & Models](file:///c:/nvm/COLLEGE/Campus-Find/docs/DATABASE_SCHEMA.md)
- [REST API Specifications](file:///c:/nvm/COLLEGE/Campus-Find/docs/API_DOCUMENTATION.md)
- [Intelligent Matching Engine Design](file:///c:/nvm/COLLEGE/Campus-Find/docs/MATCHING_ENGINE.md)
- [Implementation Status Tracker](file:///c:/nvm/COLLEGE/Campus-Find/docs/IMPLEMENTATION_STATUS.md)
- [Development Diagnostics Log](file:///c:/nvm/COLLEGE/Campus-Find/docs/DEVELOPMENT_LOG.md)
