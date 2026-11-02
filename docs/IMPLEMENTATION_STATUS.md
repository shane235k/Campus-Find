# Campus Lost & Found Hub — Implementation Status Roadmap

## 1. Project Phase Tracker

| Phase | Title | Status | Completion Target |
| :--- | :--- | :--- | :--- |
| **Phase 0** | **Project Foundation & Architecture** | **COMPLETED** | Completed |
| **Phase 0.1** | **Database Migration to Neon & Custom User Model Setup** | **COMPLETED** | Completed |
| **Phase 1** | **Authentication & User Management** | **COMPLETED** | Completed |
| **Phase 2** | **Lost & Found Core (Reporting, Items, Images)** | **NOT STARTED** | Phase 2 Milestone |
| **Phase 3** | **Intelligent Matching Engine (Sentence Transformers & pgvector)**| **NOT STARTED** | Phase 3 Milestone |
| **Phase 4** | **Ownership Claims & Administrative Verification** | **NOT STARTED** | Phase 4 Milestone |
| **Phase 5** | **Dashboards, Notifications & Live Telemetry** | **NOT STARTED** | Phase 5 Milestone |
| **Phase 6** | **Comprehensive Testing, Hardening & Deployment** | **NOT STARTED** | Phase 6 Milestone |

---

## 2. Phase 1 Implementation Checklist

- [x] **Extended `CampusUser` Model**:
  - Inherits from `django.contrib.auth.models.AbstractUser`.
  - Added `role` choices: `STUDENT`, `ADMIN`, `SUPER_ADMIN`.
  - Added unique and normalized `email` with custom validation.
  - Added optional `phone_number` (CharField).
  - Added optional `profile_picture` (ImageField upload to `profile_pics/%Y/%m/`).
  - Added conditional unique constraint `unique_student_id_when_provided` on `student_id`.
  - Added `is_email_verified` (BooleanField, default False).
  - Added non-prompting `created_at` (DateTimeField with `timezone.now`) and `updated_at` (`auto_now=True`).
  - Added automatic role-to-staff/superuser synchronization on model save.
  - Added role helper properties: `is_student`, `is_admin_user`, `is_super_admin`.
- [x] **Django Admin Customization**:
  - Customized `CampusUserAdmin` with search fields, list filters, fieldsets, and add_fieldsets in `apps/accounts/admin.py`.
- [x] **Authentication Backend**:
  - Created `EmailOrUsernameModelBackend` in `apps/accounts/backends.py` supporting case-insensitive login via email or username.
- [x] **Security & Rate Limiting (Throttling)**:
  - Created `apps/accounts/throttling.py` enforcing brute-force protection (5 failed attempts per 15-minute sliding window).
- [x] **Forms & Validation**:
  - `StudentRegistrationForm`: Student-only self-service, university domain whitelist enforcement (`UNIVERSITY_EMAIL_DOMAINS`), duplicate checks, password confirmation and strength validation.
  - `LoginForm`: Authenticates via email or username, rate-limiting integration, clear validation messages.
  - `ProfileUpdateForm`: Safe user profile edits (`first_name`, `last_name`, `phone_number`, `profile_picture` with max 2MB and Pillow image verification). Excludes and strictly protects security-critical fields (`role`, `student_id`, `email`, `is_email_verified`).
  - `AdminProvisioningForm`: Super Admin portal to provision staff administrator accounts without allowing public admin registration.
- [x] **Role-Based Access Control (RBAC)**:
  - Created decorators and CBV mixins in `apps/accounts/permissions.py`: `StudentRequiredMixin`, `AdminRequiredMixin`, `SuperAdminRequiredMixin`.
- [x] **Class-Based Views & Routing**:
  - `StudentRegistrationView` at `/accounts/register/`.
  - `UserLoginView` with role-based redirection at `/accounts/login/`.
  - `UserLogoutView` (POST-only with CSRF) at `/accounts/logout/`.
  - `ProfileView` at `/accounts/profile/`.
  - `AdminProvisioningView` at `/accounts/admin/provision/`.
  - `DashboardDispatcher` at `/dashboard/`.
  - `StudentDashboardView` at `/dashboard/student/`.
  - `AdminDashboardView` at `/dashboard/admin/`.
  - `SuperAdminDashboardView` at `/dashboard/super-admin/`.
- [x] **Frontend Templates**:
  - Created `templates/accounts/register.html`, `login.html`, `profile.html`, `create_admin.html`.
  - Created `templates/dashboard/student.html`, `admin.html`, `super_admin.html`.
  - Updated `templates/components/navbar.html` with dynamic authentication state, role badges, dropdown navigation, and POST logout form.
- [x] **Automated Test Suite**:
  - 38 automated test cases covering registration, authentication, permissions, profiles, throttling, routing, and home page branding. All 38 tests passing.
- [x] **Diagnostics & Documentation**:
  - Documented incidents INC-005 and INC-006 in `docs/DEVELOPMENT_LOG.md`.
  - Updated `docs/DATABASE_SCHEMA.md`, `docs/ARCHITECTURE.md`, `docs/API_DOCUMENTATION.md`, and `README.md`.

---

## 3. Deliberately Deferred Scope

- **Phase 2**: `Item`, `Category`, `CampusLocation`, and `ItemImage` models; item reporting forms, Pillow image thumbnails, and directory search filters.
- **Phase 3**: Sentence Transformers model inference (`all-MiniLM-L6-v2`), 384-dim vector generation, and nearest-neighbor cosine similarity queries.
- **Phase 4**: `Claim` model, ownership proof uploads, and administrative claim dispute resolution.
- **Phase 5**: Real-time notifications, email dispatches, and live telemetry.
- **Infrastructure**: Celery, Redis, Elasticsearch, and microservices (specifically excluded by specification).
