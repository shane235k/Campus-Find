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

### 2.3. Lost & Found Items (`/items/`) (Implemented in Phase 2)

| Method | URL Pattern | View Name | Description | Access Control |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/items/` | `items:list`, `items:index` | Public catalog browsing with keyword search, multi-field filters, and pagination | Public (Hides RESOLVED/CLOSED by default) |
| `GET`, `POST` | `/items/report/lost/` | `items:report_lost` | Report lost belongings form with active category/location selection | Authenticated |
| `GET`, `POST` | `/items/report/found/` | `items:report_found` | Report found item form with active category/location selection | Authenticated |
| `GET` | `/items/<uuid:pk>/` | `items:detail` | Item detail view with safe reporter display name and action buttons | Public |
| `GET`, `POST` | `/items/<uuid:pk>/edit/` | `items:edit` | Edit item report details or replace/remove photograph | Owner or Admin Only (403 for others) |
| `POST` | `/items/<uuid:pk>/delete/` | `items:delete` | Strictly POST-only deletion of report with image disk cleanup | Owner or Admin Only (405 for GET, 403 for non-owners) |
| `POST` | `/items/<uuid:pk>/status/` | `items:update_status` | Staff admin endpoint to advance report status | Staff Admin Only (403 for regular students) |

### 2.4. AI Semantic Matching Endpoints (`/matching/`) (Implemented in Phase 3)

| Method | URL Pattern | View Name | Description | Access Control |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/matching/` | `matching:hub`, `matching:index` | Matching hub with telemetry cards, status filters, and ranked match list | Authenticated (User-scoped; Admin platform-wide) |
| `GET` | `/matching/item/<uuid:item_id>/` | `matching:item_matches` | Candidate matches for a specific item report | Item Owner or Admin Only |
| `GET` | `/matching/<uuid:match_id>/` | `matching:match_detail` | Detailed side-by-side comparison with 5-component scoring progress bars | Match Participant or Admin Only |
| `POST` | `/matching/<uuid:match_id>/action/` | `matching:match_action` | Update match status (`interested`, `dismiss`, `reset`) | Match Participant or Admin Only |
| `POST` | `/matching/trigger/` | `matching:trigger_all` | Trigger on-demand match scan across active reports | Authenticated |
| `POST` | `/matching/item/<uuid:item_id>/trigger/` | `matching:trigger_item` | Re-scan candidate reports for a specific item | Item Owner or Admin Only |

---

## 3. Active REST API Endpoints (`/api/v1/`) (Implemented in Phase 2)

### 3.1. Items Endpoints (`/api/v1/items/`)

#### List Items
- **Endpoint**: `GET /api/v1/items/`
- **Permissions**: Public (`AllowAny`)
- **Query Parameters**:
  - `q`: Search keyword across title and description.
  - `type`: Filter by type (`LOST` or `FOUND`).
  - `category`: Filter by category ID.
  - `location`: Filter by location ID.
  - `status`: Filter by status (`OPEN`, `CLAIM_PENDING`, `RESOLVED`, `CLOSED`). By default, `RESOLVED` and `CLOSED` items are hidden from public queries.
  - `start_date` / `date_from`: Filter incident date $\ge$ start date (`YYYY-MM-DD`).
  - `end_date` / `date_to`: Filter incident date $\le$ end date (`YYYY-MM-DD`).
- **Response Format**:
  ```json
  [
    {
      "id": "7b0a7082-f54f-4d3f-9174-884ecb5a4ce2",
      "title": "Silver Dell XPS 15",
      "description": "Left on 2nd floor study carrel with stickers.",
      "item_type": "LOST",
      "category": 1,
      "category_name": "Electronics",
      "location": 2,
      "location_name": "Main Library",
      "date_lost_or_found": "2026-11-02",
      "image": "/media/item_images/2026/11/a3c10f...jpg",
      "status": "OPEN",
      "reporter_display_name": "Jane Doe",
      "created_at": "2026-11-02T18:45:00Z",
      "updated_at": "2026-11-02T18:45:00Z"
    }
  ]
  ```

#### Create Item
- **Endpoint**: `POST /api/v1/items/`
- **Permissions**: Authenticated (`IsAuthenticated`)
- **Request Body (JSON or Multipart Form)**:
  ```json
  {
    "title": "Found Car Keys with Blue Lanyard",
    "description": "Found near parking lot B entrance.",
    "item_type": "FOUND",
    "category": 3,
    "location": 5,
    "date_lost_or_found": "2026-11-02"
  }
  ```
- **Behavior**:
  - `reported_by` is automatically assigned to `request.user`.
  - `status` is automatically assigned to `OPEN`.
- **Response**: `201 Created` with created item payload.

#### Retrieve Item
- **Endpoint**: `GET /api/v1/items/<uuid:pk>/`
- **Permissions**: Public (`AllowAny`)
- **Response**: `200 OK`

#### Update Item
- **Endpoint**: `PUT /api/v1/items/<uuid:pk>/` or `PATCH /api/v1/items/<uuid:pk>/`
- **Permissions**: Report Owner or Administrator (`IsOwnerOrAdmin`)
- **Validation & Business Rules**:
  - `item_type` (`LOST`/`FOUND`) is immutable once created. Any attempt to modify `item_type` returns `400 Bad Request`.
  - `status` is read-only for standard users/owners. Submitting a `status` change as a regular student is rejected / ignored.
  - For Administrators, `status` changes must follow valid state machine transitions:
    - `OPEN` $\rightarrow$ `CLAIM_PENDING`, `RESOLVED`, `CLOSED`
    - `CLAIM_PENDING` $\rightarrow$ `OPEN`, `RESOLVED`, `CLOSED`
    - `RESOLVED` $\rightarrow$ `OPEN` (reopen), `CLOSED`
    - `CLOSED` $\rightarrow$ `OPEN` (reopen)
    - Any invalid transition (e.g., `CLOSED` $\rightarrow$ `CLAIM_PENDING`) returns `400 Bad Request`.
  - `reported_by` cannot be modified.
- **Response**: `200 OK` or `403 Forbidden` for non-owners, `400 Bad Request` on invalid transitions/immutable fields.

#### Delete Item
- **Endpoint**: `DELETE /api/v1/items/<uuid:pk>/`
- **Permissions**: Report Owner or Administrator (`IsOwnerOrAdmin`)
- **Safety Mechanism**: Database record deletion is executed inside an atomic transaction (`transaction.atomic()`). Associated media images are safely unlinked from disk only after database deletion succeeds.
- **Response**: `204 No Content` or `403 Forbidden` for non-owners.

---

### 3.2. Categories & Locations Endpoints
- **Endpoints**:
  - `GET /api/v1/categories/`: Returns list of active categories (`id`, `name`, `description`, `is_active`).
  - `GET /api/v1/locations/`: Returns list of active campus locations (`id`, `name`, `description`, `is_active`).
- **Permissions**: Public (`AllowAny`)

---

## 4. Planned REST API Endpoints (Phases 3-5)

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
