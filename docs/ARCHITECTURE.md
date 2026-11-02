# Campus Lost & Found Hub — System Architecture

## 1. Architectural Overview

**Campus Lost & Found Hub** is designed as a modular, monolithic Django application with high cohesion, loose coupling, and clean domain boundaries. The system prioritizes simplicity, reliability, and security, eschewing complex distributed microservices in favor of Django's battle-tested application structure backed by **Neon Cloud PostgreSQL** and the **pgvector** extension.

```mermaid
graph TD
    Client["Client Browser (Desktop / Mobile)"]
    
    subgraph Presentation_Layer["Presentation & API Layer"]
        DT["Django Templates (Bootstrap 5, Vanilla JS)"]
        DRF["Django REST Framework (Future API)"]
    end
    
    subgraph Application_Layer["Core Django Applications (apps/)"]
        Accounts["accounts<br>(Auth, CampusUser, RBAC, Throttling)"]
        Items["items<br>(Catalog, Reports, Locations)"]
        Matching["matching<br>(pgvector, Sentence Transformers)"]
        Claims["claims<br>(Proof Submission, Verification)"]
        Notifications["notifications<br>(In-app Alerts, Emails)"]
        Dashboard["dashboard<br>(Role-Based Dispatcher & Views)"]
    end
    
    subgraph Data_Layer["Data & Persistence Layer"]
        NeonDB[("Neon Serverless PostgreSQL (Cloud)<br>SSL Enabled (sslmode=require)")]
        PGV[("pgvector Extension<br>384-dim HNSW Index")]
        Media[("Media Storage<br>/media/profile_pics/ & item_images/")]
    end
    
    Client -->|HTTPS / HTTP| Presentation_Layer
    Presentation_Layer --> Application_Layer
    Accounts --> NeonDB
    Accounts --> Media
    Items --> NeonDB
    Matching --> PGV
    Claims --> NeonDB
    Notifications --> NeonDB
    Dashboard --> NeonDB
```

---

## 2. Technology Stack

| Layer | Technology | Specification | Rationale |
| :--- | :--- | :--- | :--- |
| **Language** | Python | 3.11+ (running 3.14.3) | Standard modern Python with strong typing, performance improvements, and ecosystem support. |
| **Framework** | Django | 6.1.x / 5.1+ | Robust, secure, batteries-included web framework with native ORM, authentication, and templating. |
| **API Engine** | Django REST Framework | 3.18.x | Modular REST API capabilities for future mobile client and single-page integrations. |
| **Database** | Neon PostgreSQL | Hosted Serverless PostgreSQL | Cloud-native serverless PostgreSQL with autoscaling, SSL encryption, and native pgvector support. |
| **Vector Engine** | pgvector | Built-in Extension / 0.8.6 (Cloud) | High-performance vector similarity search natively in PostgreSQL, eliminating separate vector database infrastructure. |
| **User Identity** | `CampusUser` | `AbstractUser` Subclass | Configured as `AUTH_USER_MODEL` with RBAC (`STUDENT`, `ADMIN`, `SUPER_ADMIN`), conditional unique `student_id`, and email normalization. |
| **Styling** | Bootstrap 5 | 5.3.x & Bootstrap Icons | Responsive, accessible CSS framework with customized campus navy/blue design tokens (`#0f2942`). |
| **Interactivity**| Vanilla JavaScript | ES6+ | Lightweight, dependency-free DOM manipulation without bloated node_modules or frontend builds. |
| **Configuration**| django-environ | 0.14.x | Strictly 12-Factor App compliant environment variable management via `DATABASE_URL`. |
| **Imaging** | Pillow | 13.x | Profile avatar validation (max 2MB, format validation) and future item image uploads. |

---

## 3. Authentication & User Management Architecture (Phase 1)

### 3.1. Role-Based Access Control (RBAC) Hierarchy

The platform defines three strictly segregated user tiers:

```mermaid
graph TD
    SUPER_ADMIN["Super Administrator (SUPER_ADMIN)<br>Full system access, admin provisioning, Django admin"]
    ADMIN["Staff Administrator (ADMIN)<br>Moderation console, claim reviews, Django admin staff"]
    STUDENT["Student (STUDENT)<br>Item reporting, search, claim filing, student portal"]

    SUPER_ADMIN -->|Inherits staff & provisions| ADMIN
    ADMIN -->|Oversees items & claims of| STUDENT
```

- **STUDENT**: The self-service tier. Created exclusively through student registration. Automatically assigned `role=STUDENT`, `is_staff=False`, `is_superuser=False`.
- **ADMIN**: Operational staff (campus lost & found desk, security, facility leads). Can only be provisioned by a Super Admin via `/accounts/admin/provision/`. Automatically assigned `is_staff=True`, `is_superuser=False`.
- **SUPER_ADMIN**: Complete system governance, staff provisioning, and full Django administrative access (`is_staff=True`, `is_superuser=True`).

### 3.2. Authentication Flow & Security Mechanisms

```mermaid
sequenceDiagram
    autonumber
    actor User as Campus User
    participant Browser as Web Browser
    participant Throttle as Cache Throttle
    participant Backend as EmailOrUsername Backend
    participant Dispatcher as Dashboard Dispatcher
    participant Neon as Neon PostgreSQL

    User->>Browser: Enters email/username & password
    Browser->>Throttle: Check failed attempts (5 max / 15m window)
    alt Rate Limited
        Throttle-->>Browser: Lockout error (wait 15 min)
    else Under Limit
        Browser->>Backend: authenticate(email/username, password)
        Backend->>Neon: Query user case-insensitively & verify hash
        alt Invalid Credentials
            Backend-->>Throttle: Record failed attempt
            Backend-->>Browser: Error: Invalid credentials
        else Deactivated Account
            Backend-->>Browser: Error: Account deactivated
        else Valid Credentials
            Backend-->>Throttle: Reset failure counter
            Backend-->>Browser: Establish session & issue CSRF cookie
            Browser->>Dispatcher: Redirect to /dashboard/
            Dispatcher-->>Browser: 302 Redirect to role dashboard (/student/, /admin/, /super-admin/)
        end
    end
```

### 3.3. Key Security Controls

1. **Email Normalization & Case-Insensitive Auth**:
   - `clean()` and `save()` on `CampusUser` systematically normalize email addresses to lowercase.
   - `EmailOrUsernameModelBackend` queries using case-insensitive matching (`email__iexact` or `username__iexact`).

2. **University Email Domain Gating**:
   - Environment-driven configuration via `UNIVERSITY_EMAIL_DOMAINS` (default: `university.edu`).
   - Self-service registration rejects any unauthorized external email domains.

3. **Conditional Student ID Uniqueness**:
   - `student_id` is required and enforced unique for students using a PostgreSQL conditional constraint:
     `UniqueConstraint(fields=['student_id'], condition=Q(student_id__isnull=False) & ~Q(student_id=''))`.
   - Admin accounts can leave `student_id` blank without triggering collision.

4. **Brute-Force Lockout (Throttling)**:
   - Evaluated by `apps.accounts.throttling`.
   - Client IP + normalized identifier tracked in Django cache with a sliding 15-minute window.
   - Account login locked after 5 consecutive failed attempts.

5. **Strict Parameter Tamper Resistance**:
   - `ProfileUpdateForm` explicitly restricts editable fields to `first_name`, `last_name`, `phone_number`, and `profile_picture`.
   - Security-critical fields (`role`, `student_id`, `email`, `is_email_verified`, `is_staff`, `is_superuser`) cannot be modified through the profile view.

6. **POST-Only Safe Logout**:
   - User logout requires a valid POST request with an accompanying CSRF token.
   - GET requests to `/accounts/logout/` are redirected safely to `home` without destroying the session.

---

## 4. Lost & Found Core Architecture (Phase 2)

### 4.1. Item Domain Model & Operational State Machine

All lost belongings and found items are consolidated in a single `Item` model within `apps.items`. The operational lifecycle of an item transitions through four explicit states:

```mermaid
stateDiagram-v2
    [*] --> OPEN: Student Reports Item (Lost or Found)
    OPEN --> CLAIM_PENDING: Ownership Claim Filed (Phase 4)
    CLAIM_PENDING --> OPEN: Claim Rejected / Withdrawn
    CLAIM_PENDING --> RESOLVED: Claim Verified & Belonging Returned
    OPEN --> RESOLVED: Direct Return via Campus Desk
    OPEN --> CLOSED: Expired / Disposed / Withdrawn by Reporter
    CLAIM_PENDING --> CLOSED: Admin Closed
    RESOLVED --> [*]
    CLOSED --> [*]
```

- **OPEN**: Active lost or found report awaiting discovery or verification. Visible in default public catalog.
- **CLAIM_PENDING**: A potential owner has filed an active claim; item is held in verification.
- **RESOLVED**: Belonging successfully returned to owner. Automatically excluded from default public catalog.
- **CLOSED**: Report withdrawn or archived without match. Automatically excluded from default public catalog.

#### Allowed Operational Transitions
The system enforces strict transition validation via `Item.VALID_STATUS_TRANSITIONS` and `can_transition_to()`:
- `OPEN` $\rightarrow$ `CLAIM_PENDING`, `RESOLVED`, `CLOSED`.
- `CLAIM_PENDING` $\rightarrow$ `OPEN`, `RESOLVED`, `CLOSED`.
- `RESOLVED` $\rightarrow$ `OPEN` (reopened by administrator), `CLOSED`.
- `CLOSED` $\rightarrow$ `OPEN` (reopened by administrator).
- Illegal transitions (such as `CLOSED` directly to `CLAIM_PENDING` or `RESOLVED`) are rejected with `ValidationError`.

### 4.2. Reporting Pipeline & Tamper-Proof Ingestion
- **Separate Dedicated Entrypoints**:
  - `/items/report/lost/` (`ReportLostItemView`): Pre-sets `item_type=LOST`.
  - `/items/report/found/` (`ReportFoundItemView`): Pre-sets `item_type=FOUND`.
- **Server-Side Enforcement**:
  - `reported_by` is assigned strictly from `request.user` in the view/form `save()` method. The field is never exposed as an editable HTML input.
  - Initial `status` is automatically set to `OPEN`. Attempts to pass alternative statuses via POST payloads are discarded.
  - Active relations only: Form validation verifies that both `category` and `location` are `is_active=True`.
  - Future date prevention: `date_lost_or_found` cannot exceed current date (`date.today()`).

### 4.3. Catalog Browsing, Query Filtering, and Visibility Pipeline
- **Search Engine**: Multi-term text matching across `title` and `description` using Django ORM `Q` expressions.
- **Parametric Filtering**:
  - `type`: `LOST` or `FOUND`.
  - `category`: Filter by foreign key ID or name.
  - `location`: Filter by campus location ID or name.
  - `date_from` / `date_to` (or `start_date` / `end_date`): Incident date range bounding.
  - `status`: Explicit filter allowing admins and students to review `RESOLVED` or `CLOSED` items.
- **Default Public Visibility Rule**:
  - When no explicit `status` filter is passed, queries for non-administrators automatically filter `status__in=[OPEN, CLAIM_PENDING]`, preventing resolved or closed reports from cluttering active searches.
- **Pagination**: 12 items per page with query string preservation via `{% query_transform %}` template tag.

### 4.4. Image Validation & Lifecycle Management
- **Upload Path Obfuscation**: Unique UUID-based paths generated by `item_image_upload_path`: `item_images/%Y/%m/<uuid4><ext>`. Prevents original filename exposure, directory traversal, and namespace collisions.
- **Pillow Verification**:
  - Hard 5 MB size limit enforced before disk write.
  - Deep inspection via `PIL.Image.open(image_file).verify()` within context manager.
  - Format restriction strictly to `JPEG`, `PNG`, and `WEBP`.
- **Disk Cleanup**:
  - When an item is deleted, its image file is safely unlinked from disk.
  - When an image is replaced or removed in `ItemEditForm`, the previous image file is removed from storage while releasing all open file handles.

### 4.5. Student Privacy & Security Controls
- **Anonymized Reporter Identity**:
  - `reporter_display_name` property returns `get_full_name()` or `username`.
  - Sensitive personal data (`email`, `phone_number`, `student_id`) is strictly excluded from item cards, detail views, and API serializers.
- **Authorization Boundaries**:
  - Edit view (`/items/<uuid:pk>/edit/`): Strictly restricted to report owner or administrator. Non-owners receive HTTP 403 Forbidden.
  - Deletion (`/items/<uuid:pk>/delete/`): Strictly POST-only (`http_method_names = ["post"]`). GET requests are rejected with HTTP 405 Method Not Allowed. Non-owners receive HTTP 403 Forbidden.
  - Operational status update (`/items/<uuid:pk>/status/`): Restricted to staff admins.

### 4.6. REST API Engine (`/api/v1/`)
- Built using Django REST Framework:
  - `GET /api/v1/items/`: List items with search, filters, and pagination.
  - `POST /api/v1/items/`: Create item with authenticated user automatically assigned as `reported_by`.
  - `GET /api/v1/items/<uuid:pk>/`: Detailed item payload.
  - `PUT/PATCH /api/v1/items/<uuid:pk>/`: Owner-restricted update.
  - `DELETE /api/v1/items/<uuid:pk>/`: Owner-restricted deletion.
  - `GET /api/v1/categories/`: Active categories listing.
  - `GET /api/v1/locations/`: Active locations listing.

### 4.7. System Bootstrapping & Administrative CLI
- **Super Administrator Elevation** (`python manage.py assign_super_admin <email|username>`):
  - Promotes an existing user to `role=SUPER_ADMIN`, `is_staff=True`, `is_superuser=True`.
  - Strictly requires an existing account identifier (does not handle or generate default passwords).
  - Prompts for interactive confirmation (or accepts `--no-input` for scripted pipelines).
- **Foundational Data Seeding** (`python manage.py seed_initial_data`):
  - Idempotently populates standard university item categories and campus recovery locations using `get_or_create`.
  - Supports `--dry-run` to inspect data population without committing changes.

---

## 5. Application Directory & Module Structure

```
campus_lost_found/
    manage.py
    config/
        settings.py          # Unified settings, DB routing, auth backends, domain configs
        urls.py              # Root router connecting apps
        wsgi.py / asgi.py    # Deployment gateways
    apps/
        accounts/            # Identity, CampusUser, backends, forms, throttling, views
            models.py
            backends.py      # Case-insensitive email/username backend
            throttling.py    # Sliding window brute-force lockout
            permissions.py   # RBAC mixins and decorators
            forms.py         # Registration, login, profile, admin provisioning
            views.py         # Auth views (CBVs)
            urls.py          # /accounts/*
            tests.py         # 25+ automated unit tests
        items/               # Future item reporting and catalog (Phase 2)
        matching/            # Semantic pgvector engine (Phase 3)
        claims/              # Ownership verification (Phase 4)
        notifications/       # Notification delivery (Phase 5)
        dashboard/           # Role dispatching and dashboards
            views.py         # DashboardDispatcher, Student, Admin, SuperAdmin views
            urls.py          # /dashboard/*
            tests.py         # Dashboard role tests
    templates/
        base.html            # Global skeleton (Bootstrap 5, main.css)
        components/          # navbar, footer, messages
        accounts/            # register.html, login.html, profile.html, create_admin.html
        dashboard/           # student.html, admin.html, super_admin.html
    static/
        css/main.css         # Navy theme design tokens
        js/main.js           # Client interactions
    docs/
        ARCHITECTURE.md      # Architecture and security specifications
        DATABASE_SCHEMA.md   # Model definitions and ER diagrams
        DEVELOPMENT_LOG.md   # Mandatory development diagnostics log
        IMPLEMENTATION_STATUS.md # Roadmaps and phase checklist
```
