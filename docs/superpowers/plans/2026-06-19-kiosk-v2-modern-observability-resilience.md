# Kiosk V2 Modern observability and resilience plan

**Goal:** Add useful diagnostics without secrets, stop rapid application crash
loops, and delay repeated failed administrator-authentication attempts.

**Architecture:** Pure policy classes own redaction, restart limits, and
authentication throttling. Platform adapters only provide a monotonic clock and a
rotating UTF-8 JSONL sink. Runtime code emits structured categories and exception
types, never passwords, typed text, tokens, or command arguments.

**Tech Stack:** Python 3.8 x86, standard-library `logging`, `json`,
`RotatingFileHandler`, `unittest`, no V1 imports.

---

### Task 1: Redacted rotating JSONL audit logger

**Files:**
- Create: `v2/modern/kiosk_v2_modern/platform/audit_log.py`
- Create: `v2/tests/modern/test_audit_log.py`

- [x] Write RED tests proving nested keys containing `password`, `secret`,
  `token`, `credential`, `typedText`, `arguments`, or `commandLine` are replaced
  by `[REDACTED]`; ordinary event metadata remains intact.
- [x] Test one JSON object per line, UTF-8 Russian text, configured byte rotation,
  backup count, and clean handler shutdown.
- [x] Implement `SafeEvent`, recursive redaction, JSON-safe value conversion, and
  `AuditLogger`. The API accepts only `event_name`, `level`, and structured fields;
  it never formats arbitrary exception messages.
- [x] Run targeted tests on Python 3.8 x86 and commit.

### Task 2: Controller transition audit

**Files:**
- Modify: `v2/modern/kiosk_v2_modern/app/controller.py`
- Modify: `v2/tests/modern/test_controller.py`

- [x] Write RED tests for one successful transition event and one failed-effect
  event. Failure data may contain `errorType` but not `str(error)`.
- [x] Inject an optional audit port into `AppController`; preserve current atomic
  rollback behavior when the audit sink itself fails.
- [x] Run controller and full V2 tests, then commit.

### Task 3: Bounded restart circuit breaker

**Files:**
- Modify: `v2/contracts/kiosk-config-v2.schema.json`
- Modify: `v2/modern/kiosk_v2_modern/app/process_supervisor.py`
- Modify: `v2/tests/modern/test_process_supervisor.py`
- Modify: `v2/tests/contracts/test_contract_documents.py`

- [x] Add required `maxRestartAttempts` and `restartWindowSeconds` fields with
  conservative limits and future migration defaults.
- [x] Write RED tests where rapid exits or launch failures reach `crash_loop`, no
  additional process is opened, a stable run clears old failures, and explicitly
  restarting supervision clears the breaker without terminating a process.
- [x] Implement a monotonic rolling-window failure counter. Never log or expose
  process arguments in results.
- [x] Run targeted and full V2 tests, then commit.

### Task 4: Rate-limited administrator authentication

**Files:**
- Create: `v2/modern/kiosk_v2_modern/app/admin_auth_service.py`
- Create: `v2/tests/modern/test_admin_auth_service.py`

- [x] Write RED tests for three failed attempts, increasing delay, no Windows API
  call while locked, reset after success, and no retained password attribute.
- [x] Implement a synchronous wrapper around `WindowsAdminAuth` using only a
  monotonic clock, username, failure count, and next-allowed timestamp. Password is
  passed directly to one authentication call and never assigned to `self`.
- [x] Return safe result codes and integer `retryAfterSeconds`; never include a
  password or exception message.
- [x] Run targeted and full V2 tests, then commit.

### Task 5: Acceptance checkpoint

- [x] Run all V2 tests on Python 3.8 x86.
- [x] Run Legacy V2 state tests directly on Python 2.7 x86.
- [x] Run `compileall` for Modern and `git diff --check`.
- [x] Record exact results and leave a clean worktree before planning configuration
  repository and V1-to-V2 migration.
