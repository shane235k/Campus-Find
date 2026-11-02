# Campus Lost & Found Hub — System Architecture

## 1. Architectural Overview

**Campus Lost & Found Hub** is designed as a modular, monolithic Django application with high cohesion, loose coupling, and clean domain boundaries. The system prioritizes simplicity, reliability, and security, eschewing complex distributed microservices in favor of Django's battle-tested application structure backed by **PostgreSQL** and the **pgvector** extension.

```mermaid
graph TD
    Client["Client Browser (Desktop / Mobile)"]
    
    subgraph Presentation_Layer["Presentation & API Layer"]
        DT["Django Templates (Bootstrap 5, Vanilla JS)"]
        DRF["Django REST Framework (Future API)"]
    end
    
    subgraph Application_Layer["Core Django Applications (apps/)"]
        Accounts["accounts<br>(Auth, Campus SSO, Profiles)"]
        Items["items<br>(Catalog, Reports, Locations)"]
        Matching["matching<br>(pgvector, Sentence Transformers)"]
        Claims["claims<br>(Proof Submission, Verification)"]
        Notifications["notifications<br>(In-app Alerts, Emails)"]
        Dashboard["dashboard<br>(Student & Admin KPI Hub)"]
    end
    
    subgraph Data_Layer["Data & Persistence Layer"]
        PG[("PostgreSQL 18 Database")]
        PGV[("pgvector Extension<br>384-dim HNSW Index")]
        Media[("Media Storage<br>/media/item_images/")]
    end
    
    Client -->|HTTPS / HTTP| Presentation_Layer
    Presentation_Layer --> Application_Layer
    Accounts --> PG
    Items --> PG
    Items --> Media
    Matching --> PGV
    Claims --> PG
    Notifications --> PG
    Dashboard --> PG
```

---

## 2. Technology Stack

| Layer | Technology | Version / Specification | Rationale |
| :--- | :--- | :--- | :--- |
| **Language** | Python | 3.11+ (running 3.14.3) | Standard modern Python with strong typing, performance improvements, and ecosystem support. |
| **Framework** | Django | 6.1.x / 5.1+ | Robust, secure, batteries-included web framework with native ORM, authentication, and templating. |
| **API Engine** | Django REST Framework | 3.18.x | Modular REST API capabilities for future mobile client and single-page integrations. |
| **Database** | PostgreSQL | 18.x | Enterprise relational database with transactional integrity, JSON support, and full ACID compliance. |
| **Vector Engine** | pgvector | 0.8.x / 0.5.x (Python) | High-performance vector similarity search within PostgreSQL, eliminating separate vector database infrastructure. |
| **Styling** | Bootstrap 5 | 5.3.x & Bootstrap Icons | Responsive, accessible CSS framework with customized campus navy/blue design tokens. |
| **Interactivity**| Vanilla JavaScript | ES6+ | Lightweight, dependency-free DOM manipulation without bloated node_modules or frontend builds. |
| **Configuration**| django-environ | 0.14.x | Strictly 12-Factor App compliant environment variable management. |
| **Imaging** | Pillow | 13.x | Image processing, thumbnail generation, and metadata sanitization for item uploads. |

---

## 3. Application Responsibilities

The codebase organizes distinct campus business domains into dedicated applications under `apps/`:

### 3.1. `apps/accounts`
- **Scope**: Identity and access management.
- **Responsibilities**:
  - Custom student/staff user model (`CampusUser`) extending `AbstractUser`.
  - University email validation (`@university.edu`) and role-based permissions (`STUDENT`, `STAFF`, `SECURITY_ADMIN`).
  - Session and token-based authentication.
  - Student profile management (department, phone number, notification preferences).

### 3.2. `apps/items`
- **Scope**: Core Lost & Found reporting and directory.
- **Responsibilities**:
  - CRUD operations for Lost and Found reports.
  - Multi-category hierarchy (`Category`: Electronics, Cards, Books, etc.).
  - Campus spatial tagging (`CampusLocation`: Building, Floor, Room).
  - Image uploads and thumbnail generation via Pillow.
  - Public search and filtering by date, status, category, and location.

### 3.3. `apps/matching`
- **Scope**: Artificial intelligence and semantic matching engine.
- **Responsibilities**:
  - PostgreSQL extension initialization (`VectorExtension`).
  - Text embedding generation using `all-MiniLM-L6-v2` (384-dimensional dense vectors).
  - Vector similarity calculation via pgvector cosine distance operator (`<=>`).
  - Hybrid scoring pipeline integrating semantic text match with structured heuristics (category, location proximity, date proximity).
  - Generation and storage of `PotentialMatch` candidate pairs.

### 3.4. `apps/claims`
- **Scope**: Ownership dispute resolution and item reclamation.
- **Responsibilities**:
  - Claim submission workflow by students claiming lost belongings.
  - Secure verification evidence collection (receipts, unique scratches, unlock passwords, serial numbers).
  - Multi-step status state machine (`SUBMITTED`, `UNDER_REVIEW`, `APPROVED`, `REJECTED`, `COLLECTED`).
  - Administrative audit logging and resolution notes.

### 3.5. `apps/notifications`
- **Scope**: In-app and outbound communication.
- **Responsibilities**:
  - Delivery of automated match alerts when potential items are reported.
  - Status updates on submitted claims.
  - Campus security broadcasts regarding high-value lost items.
  - In-app notification center with read/unread tracking.

### 3.6. `apps/dashboard`
- **Scope**: User and administrator analytics and command center.
- **Responsibilities**:
  - Student dashboard: active lost reports, found items submitted, and claim progress.
  - Security / Admin console: item recovery rates, unresolved claim queues, inventory aging metrics.

---

## 4. Request-Response Flow

```mermaid
sequenceDiagram
    autonumber
    actor Student as Student / User
    participant Router as Django URL Dispatcher (config/urls.py)
    participant Middleware as Django Middleware Stack
    participant View as Application View (apps.*.views)
    participant ORM as Django ORM
    participant DB as PostgreSQL (with pgvector)
    participant Template as Django Templates / Static Engine

    Student->>Router: GET /items/ (HTTP Request)
    Router->>Middleware: Execute Request Middleware (Security, Session, Auth)
    Middleware->>View: Dispatch to ItemsIndexView
    View->>ORM: Query Item.objects.filter(status='REPORTED')
    ORM->>DB: SELECT * FROM items_item WHERE status = 'REPORTED'
    DB-->>ORM: QuerySet records
    ORM-->>View: Model instances
    View->>Template: Render items/list.html with context
    Template-->>View: Compiled HTML5 string
    View->>Middleware: Execute Response Middleware
    Middleware-->>Student: 200 OK HTML Response
```

---

## 5. Database Architecture & Vector Strategy

### 5.1. Connection Management
- Credentials read dynamically from environment variables (`DATABASE_URL` or discrete `DB_*` variables).
- Persistent connection pooling configured via `CONN_MAX_AGE=600` (10 minutes) for high throughput.
- Enforced UTF-8 character encoding and standardized `Asia/Kolkata` timezone timestamps.

### 5.2. Vector Integration Strategy
- Integrated via the `pgvector` Python library (`pgvector.django`).
- The matching app maintains the database extension migration `apps/matching/migrations/0001_initial.py` which executes `CREATE EXTENSION IF NOT EXISTS vector;`.
- Employs 384-dimensional dense vectors generated by the lightweight Sentence Transformer model `all-MiniLM-L6-v2`.
- Indexing will leverage PostgreSQL HNSW (Hierarchical Navigable Small World) indices for sub-millisecond approximate nearest neighbor (ANN) retrieval once item volume scales.

---

## 6. pgvector Installation & Setup Guide

When deploying to a PostgreSQL instance where the `vector` extension binary is not yet installed:

### Windows Native Compilation (Visual Studio Developer Prompt):
```cmd
# 1. Open 'x64 Native Tools Command Prompt for VS' as Administrator
# 2. Set the PostgreSQL root directory
set "PGROOT=C:\Program Files\PostgreSQL\18"

# 3. Clone and build pgvector
cd %TEMP%
git clone https://github.com/pgvector/pgvector.git
cd pgvector
nmake /F Makefile.win
nmake /F Makefile.win install

# 4. Verify in Django
python manage.py verify_pgvector
```

### Docker Container (Alternative Deployment):
```bash
docker run --name campus-find-pg \
  -e POSTGRES_DB=campus_lost_found \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  -d pgvector/pgvector:pg16
```

### Linux (Ubuntu / Debian):
```bash
sudo apt install postgresql-16-pgvector
```
