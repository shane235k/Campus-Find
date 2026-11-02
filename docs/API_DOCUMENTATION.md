# Campus Lost & Found Hub — Planned REST API Specification

## 1. Overview & Conventions

The platform will expose a RESTful API powered by **Django REST Framework (DRF)**. In Phase 0, DRF is installed and registered in `settings.py`. Full serializers, viewsets, and token-based endpoints will be exposed starting from Phase 1 through Phase 5.

### 1.1. Base URL
All API endpoints will be versioned under the `/api/v1/` prefix:
```
https://campus-hub.university.edu/api/v1/
```

### 1.2. Authentication Methods
1. **Session Authentication** (default for browser interactions and Django frontend).
2. **Token / Bearer Authentication** (for mobile application and programmatic integrations).

### 1.3. Standard Response Format
All JSON responses follow a consistent envelope structure:

```json
{
  "success": true,
  "data": {},
  "message": "Operation completed successfully.",
  "meta": {
    "timestamp": "2026-11-02T19:30:00+05:30",
    "version": "v1"
  }
}
```

### 1.4. Standard Error Response
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "The submitted payload contains validation errors.",
    "details": {
      "campus_id": ["A valid student or staff roll number is required."]
    }
  }
}
```

---

## 2. Planned API Endpoints

### 2.1. Authentication (`/api/v1/auth/`) — Phase 1

| Method | Endpoint | Description | Access |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register/` | Register student account with campus email | Public |
| `POST` | `/auth/login/` | Authenticate and obtain session/auth token | Public |
| `POST` | `/auth/logout/` | Invalidate current session/token | Authenticated |
| `GET` | `/auth/profile/` | Retrieve current user profile and role | Authenticated |
| `PUT/PATCH` | `/auth/profile/` | Update profile information | Authenticated |

### 2.2. Categories & Locations (`/api/v1/categories/`, `/api/v1/locations/`) — Phase 2

| Method | Endpoint | Description | Access |
| :--- | :--- | :--- | :--- |
| `GET` | `/categories/` | List all active item categories | Public |
| `GET` | `/locations/` | List campus buildings and designated recovery points | Public |

### 2.3. Lost & Found Items (`/api/v1/items/`) — Phase 2

| Method | Endpoint | Description | Access |
| :--- | :--- | :--- | :--- |
| `GET` | `/items/` | Filterable list of lost and found items (pagination support) | Public |
| `POST` | `/items/` | Submit a new lost or found item report (multipart image support) | Authenticated |
| `GET` | `/items/{id}/` | Retrieve item details and verification fields | Public |
| `PUT/PATCH` | `/items/{id}/` | Update report (creator or campus security) | Authenticated (Owner/Admin) |
| `DELETE` | `/items/{id}/` | Withdraw or close report | Authenticated (Owner/Admin) |

#### Query Parameters for `/items/`:
- `item_type`: `LOST` or `FOUND`
- `category`: Category slug (e.g., `electronics`, `keys`)
- `location`: Building name or ID
- `search`: Full-text title and description search
- `date_after` / `date_before`: ISO 8601 date range filters
- `status`: `REPORTED`, `MATCHED`, `CLAIMED`, `RESOLVED`

### 2.4. Semantic Matching Engine (`/api/v1/matching/`) — Phase 3

| Method | Endpoint | Description | Access |
| :--- | :--- | :--- | :--- |
| `GET` | `/matching/potential-matches/` | Retrieve list of algorithmic matches for logged-in user | Authenticated |
| `GET` | `/matching/item/{item_id}/candidates/` | Query top-$k$ nearest neighbors for a specific item | Authenticated |
| `POST` | `/matching/matches/{id}/action/` | Accept or dismiss match suggestion | Authenticated (Owner/Admin) |
| `POST` | `/matching/recalculate/` | Admin trigger to regenerate embeddings and matches | Admin Only |

### 2.5. Claims & Verification (`/api/v1/claims/`) — Phase 4

| Method | Endpoint | Description | Access |
| :--- | :--- | :--- | :--- |
| `GET` | `/claims/` | List claims submitted by user or pending admin queue | Authenticated |
| `POST` | `/claims/` | Submit ownership claim for a found item with proof | Authenticated |
| `GET` | `/claims/{id}/` | Retrieve claim details, proof documents, review history | Claimant / Admin |
| `POST` | `/claims/{id}/verify/` | Approve or reject claim with resolution note | Security / Admin |

### 2.6. Notifications (`/api/v1/notifications/`) — Phase 5

| Method | Endpoint | Description | Access |
| :--- | :--- | :--- | :--- |
| `GET` | `/notifications/` | Retrieve paginated list of user notifications | Authenticated |
| `POST` | `/notifications/{id}/read/` | Mark specific notification as read | Authenticated |
| `POST` | `/notifications/read-all/` | Mark all notifications as read | Authenticated |

### 2.7. Dashboard & Metrics (`/api/v1/dashboard/`) — Phase 5

| Method | Endpoint | Description | Access |
| :--- | :--- | :--- | :--- |
| `GET` | `/dashboard/student/` | Personal item summary, active claims, recent alerts | Authenticated |
| `GET` | `/dashboard/admin/metrics/` | Platform recovery rate, open items, monthly volume | Admin Only |
