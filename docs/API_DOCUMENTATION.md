# Campus Lost & Found Hub — API and Endpoint Specification

## 1. Overview & Conventions

**Campus Lost & Found Hub** supports standard HTTP web endpoints (Phase 1) and will expose a dedicated RESTful API powered by **Django REST Framework (DRF)** in subsequent phases.

---

## 2. Active Web & Application Endpoints (Phase 1)

### 2.1. Authentication & User Management (`/accounts/`)

| Method | URL Pattern | View Name | Description | Access Control |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/accounts/` | `accounts:index` | Smart dispatcher to `/accounts/profile/` or `/accounts/login/` | Public |
| `GET`, `POST` | `/accounts/register/` | `accounts:register` | Student self-service registration form with domain & ID checks | Anonymous Only |
| `GET`, `POST` | `/accounts/login/` | `accounts:login` | Case-insensitive email/username login with brute-force throttling | Anonymous Only |
| `POST` | `/accounts/logout/` | `accounts:logout` | POST-only session termination with CSRF validation | Authenticated |
| `GET`, `POST` | `/accounts/profile/` | `accounts:profile` | User profile overview and form to edit non-sensitive attributes | Authenticated |
| `GET`, `POST` | `/accounts/admin/provision/` | `accounts:create_admin` | Super Admin portal to provision staff administrator accounts | Super Admin Only |

### 2.2. Role-Based Dashboards (`/dashboard/`)

| Method | URL Pattern | View Name | Description | Access Control |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/dashboard/` | `dashboard:index` | Role dispatcher routing user to `/student/`, `/admin/`, or `/super-admin/` | Authenticated |
| `GET` | `/dashboard/student/` | `dashboard:student` | Student portal displaying reported items, active claims, and alerts | Student Role |
| `GET` | `/dashboard/admin/` | `dashboard:admin` | Operations console for lost & found desk moderators and security | Admin / Staff Role |
| `GET` | `/dashboard/super-admin/`| `dashboard:super_admin` | System command center with user counts and staff provisioning access | Super Admin Role |

---

## 3. Planned REST API Endpoints (`/api/v1/`)

### 3.1. Base URL & Response Standard
```
https://campus-hub.university.edu/api/v1/
```

JSON responses adhere to standard envelope structures:
```json
{
  "success": true,
  "data": {},
  "message": "Operation completed successfully.",
  "meta": {
    "timestamp": "2026-11-02T20:30:00+05:30",
    "version": "v1"
  }
}
```

### 3.2. Authentication (`/api/v1/auth/`)
- `POST /api/v1/auth/register/`: JSON payload student registration.
- `POST /api/v1/auth/login/`: Obtain session/auth token.
- `POST /api/v1/auth/logout/`: Invalidate token.
- `GET, PATCH /api/v1/auth/profile/`: Retrieve and update user profile.

### 3.3. Items, Matching, & Claims (Phases 2-5)
- `GET, POST /api/v1/items/`: Catalog search, filtering, and report creation.
- `GET /api/v1/matching/potential-matches/`: Semantic pgvector match candidates.
- `GET, POST /api/v1/claims/`: Verification challenge submissions and review queue.
- `GET /api/v1/notifications/`: In-app notification feed.
