# Campus Lost & Found Hub — Development Diagnostics Log

This document enforces and maintains the **Mandatory Development Diagnostics Policy**. It is updated across every development phase to record all runtime anomalies, test failures, database issues, environmental roadblocks, and their diagnostic verification lifecycles.

---

## 1. Diagnostics & Investigation Policy

### 1.1. Core Directives
1. **Systematic Capture**: Record the exact command, ISO timestamp, full exception type, and stack trace or error output.
2. **Strict Failure Taxonomy**: Every incident must be classified as one of:
   - `NETWORK`: DNS resolution, TCP timeouts, latency spikes, socket resets, TLS/SSL handshake failures.
   - `DATABASE`: Engine-level DDL locks, transaction aborts, relation conflicts, PgBouncer pooling limits.
   - `APPLICATION`: Python syntax/import errors, Django ORM schema bugs, view logic errors, test assertion failures.
   - `ENVIRONMENT`: Missing binaries, OS permission denials (e.g. Windows UAC), missing environment variables.
   - `UNKNOWN`: Unclassified issues undergoing active investigation.
3. **Database Diagnostic Decomposition**: When investigating database connection issues, separate and verify:
   - DNS Resolution (`Resolve-DnsName` / socket `gethostbyname`).
   - TCP Connectivity (Port `5432` reachability).
   - TLS/SSL Negotiation (`sslmode=require` handshake).
   - Authentication (Username / SCRAM-SHA-256 verification).
   - Query Execution (`SELECT 1;`).
4. **Code Protection**: Never modify working application code to bypass an unverified external or network issue.
5. **Retry Verification**: Always test retry after transient network restoration before code alteration, recording whether it succeeded without modification.
6. **Credential Hygiene**: Never log passwords, API secret keys, session tokens, or full connection strings with credentials. Mask host endpoints when appropriate.
7. **Infrastructure Boundary Distinction**: Explicitly distinguish between agent communication infrastructure (Antigravity/Google Cloud Code) and application-level connectivity to external services.
8. **Diagnostic Rigor**: Always differentiate between **Verified Failure**, **Suspected Cause**, and **Confirmed Root Cause**.

---

## 2. Phase 0 Diagnostic Incident Log (Foundation)

### Incident INC-001: Local PostgreSQL Extension Installation Denied
- **Timestamp**: `2026-11-02T19:17:20+05:30`
- **Command**: `nmake /F Makefile.win install`
- **Classification**: `ENVIRONMENT`
- **Verified Failure**:
  ```
  copy vector.dll "C:\Program Files\PostgreSQL\18\lib"
  Access is denied.
          0 file(s) copied.
  NMAKE : fatal error U1077: 'copy vector.dll "C:\Program Files\PostgreSQL\18\lib"' : return code '0x1'
  ```
- **Diagnostic Breakdown**:
  - *DNS / Network*: N/A (Local compilation).
  - *File System ACLs*: `Get-Acl "C:\Program Files\PostgreSQL\18\lib"` confirmed `BUILTIN\Users` possesses only `ReadAndExecute, Synchronize`.
  - *Elevation State*: Shell running with `Mandatory Label\Medium Mandatory Level` (non-elevated).
- **Suspected Cause**: Insufficient privileges to copy compiled `.dll` to system directory.
- **Confirmed Root Cause**: Windows User Account Control (UAC) restricts write operations to `C:\Program Files` without administrative elevation.
- **Resolution**: Documented native compilation instructions in `docs/ARCHITECTURE.md`. Resolved at system level in Phase 0.1 by migrating to Neon Serverless PostgreSQL where `pgvector` is pre-installed.

---

### Incident INC-002: HTML Entity Encoding Mismatch in Accounts Unit Test
- **Timestamp**: `2026-11-02T19:37:18+05:30`
- **Command**: `python manage.py test apps`
- **Classification**: `APPLICATION`
- **Verified Failure**:
  ```
  AssertionError: False is not true : Couldn't find 'Accounts & Authentication' in response
  ```
- **Diagnostic Breakdown**:
  - *Status Code*: HTTP 200 (Success).
  - *Rendered Body*: Examined HTTP response payload; title rendered as `Accounts &amp; Authentication`.
- **Suspected Cause**: Django template auto-escaping character entities.
- **Confirmed Root Cause**: Django templates automatically escape literal `&` characters into `&amp;` for HTML safety.
- **Resolution**: Updated `test_accounts_index_resolves` in `apps/accounts/tests.py` to assert against `Accounts` or escaped entities. Re-test passed immediately.

---

## 3. Phase 0.1 Diagnostic Incident Log (Neon Migration & User Model)

### Incident INC-003: Cold Start Latency on Initial Serverless Neon Handshake
- **Timestamp**: `2026-11-02T19:46:27+05:30`
- **Command**: `python manage.py verify_pgvector`
- **Classification**: `NETWORK`
- **Verified Failure**: Command execution exceeded default interactive timeout (~10s) on initial connection attempt.
- **Diagnostic Decomposition**:
  1. *DNS Resolution*: Host `ep-autumn-art-bemiqhpr-pooler.c-9.us-east-2.aws.neon.tech` resolved successfully to AWS IP endpoints.
  2. *TCP Connectivity*: Port 5432 reachable.
  3. *Latency Profile*: First TLS handshake took 18.90s due to Neon serverless compute node resume from cold standby state.
  4. *Retry Check*: Direct python probe run immediately after wake-up connected and executed `SELECT version();` in < 400ms without code modification.
- **Suspected Cause**: Transatlantic network latency combined with serverless compute cold activation.
- **Confirmed Root Cause**: Serverless compute endpoint cold wake-up behavior on initial inbound TCP connection.
- **Resolution**: No application code modified. Subsequent queries executed at normal sub-second latencies.

---

### Incident INC-004: PgBouncer Transaction Pooler Rejection of Test DDL
- **Timestamp**: `2026-11-02T20:02:38+05:30`
- **Command**: `python manage.py test apps config`
- **Classification**: `DATABASE`
- **Verified Failure**: Django test runner hung during `Creating test database for alias 'default' ...`. Subsequent rerun reported:
  ```
  DETAIL: There is 1 other session using the database.
  Got an error recreating the test database: database "test_neondb" is being accessed by other users
  ```
- **Diagnostic Decomposition**:
  1. *Endpoint Inspection*: Host `ep-autumn-art-bemiqhpr-pooler.c-9.us-east-2.aws.neon.tech` contains `-pooler`, designating Neon's PgBouncer proxy.
  2. *Protocol Inspection*: PgBouncer operating in transaction pooling mode prohibits administrative statements (`CREATE DATABASE`, `DROP DATABASE`) that require independent connection session states.
  3. *Session Inspection*: Querying `pg_stat_activity` confirmed a lingering connection hold on `test_neondb` following an interrupted process.
- **Suspected Cause**: Pooling proxy incompatibility with Django's administrative test database creation.
- **Confirmed Root Cause**: PgBouncer transaction pooling endpoints cannot execute `CREATE DATABASE` queries.
- **Resolution**:
  1. Terminated leftover session via `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'test_neondb';` and dropped `test_neondb`.
  2. Updated `config/settings.py` with an automated routing rule: when `test` is present in `sys.argv`, the host seamlessly strips `-pooler` to use Neon's direct endpoint (`ep-autumn-art-bemiqhpr.c-9.us-east-2.aws.neon.tech`).
  3. Re-executed tests using `--keepdb`; all 15 test cases completed with status `OK`.

---

## 4. Phase Summary & Health Matrix

| Phase | Total Failures | Network | Database | Application | Environment | Unresolved | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Phase 0** | 2 | 0 | 0 | 1 | 1 | 0 | **RESOLVED** |
| **Phase 0.1** | 2 | 1 | 1 | 0 | 0 | 0 | **RESOLVED** |
| **Phase 1** | — | — | — | — | — | — | **PENDING** |

### Current Environment Diagnostics
- **Primary Database**: Neon Cloud PostgreSQL 18.6 (fd34222) on aarch64-unknown-linux-gnu.
- **pgvector State**: Active version `0.8.6` (SQL verified: L2 distance query returned `5.1962`).
- **User Model State**: `accounts.CampusUser` established as `AUTH_USER_MODEL`.
- **System Check Status**: Clean (`0 issues identified`).
- **Unresolved Issues**: None.
