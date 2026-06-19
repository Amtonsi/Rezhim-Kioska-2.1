# Kiosk V2 configuration and migration plan

**Goal:** Load, validate, and atomically update `config/kiosk.v2.json`, and migrate
the working V1 configuration without changing or exposing the V1 source.

**Architecture:** The JSON contract is authoritative. A pure validator rejects
unknown V2 fields and invalid types/ranges. `ConfigRepository` owns BOM-tolerant
reads and same-directory atomic replacement. `V1ConfigMigrator` uses an explicit
field allowlist, stores the exact original bytes first, then delegates the V2 write
to the repository. ACL enforcement remains an injected port so unit tests never
change real permissions.

**Tech Stack:** Python 3.8 x86, `json`, `tempfile`, `os.replace`, `os.fsync`,
`unittest`, no V1 imports.

---

### Task 1: Complete the V2 configuration contract

**Files:**
- Modify: `v2/contracts/kiosk-config-v2.schema.json`
- Create: `config/kiosk.v2.default.json`
- Modify: `v2/tests/contracts/test_contract_documents.py`

- [x] Add required test-safety constants: backup before test, Restore after test,
  and separate non-admin operator only.
- [x] Create a complete default with Notepad, manual minimized-window restore,
  Win+L enabled, restart circuit-breaker defaults, and rotating-log defaults.
- [x] Test exact field parity between default and contract and absence of every
  credential/password/token field.

### Task 2: Strict validator and BOM-tolerant repository

**Files:**
- Create: `v2/modern/kiosk_v2_modern/app/config_repository.py`
- Create: `v2/tests/modern/test_config_repository.py`

- [ ] Write RED tests for valid default, UTF-8 BOM input, unknown fields, wrong
  booleans/ranges, non-absolute executable paths, and a missing executable when
  `require_existing_app=True`.
- [ ] Write failure-injection tests proving `save()` flushes and atomically replaces
  only after validation, preserves the old target when replace fails, removes temp
  files, and invokes the ACL port only after a successful replace.
- [ ] Implement `ConfigValidationError`, pure recursive validation, deep-copy load,
  and `ConfigRepository`. Never import V1 modules.
- [ ] Run targeted tests on Python 3.8 x86 and commit.

### Task 3: Allowlisted V1-to-V2 migration

**Files:**
- Create: `v2/migration/config_v1_to_v2.py`
- Create: `v2/tests/modern/test_config_migration.py`

- [ ] Write RED tests using current V1-shaped data plus unknown fields, password
  hashes, tokens, and BOM. Assert only approved values reach V2.
- [ ] Assert source bytes remain identical, exact backup bytes are written and
  flushed before V2 creation, an existing different backup is never overwritten,
  and any failure leaves the previous V2 target unchanged.
- [ ] Implement conservative defaults for new fields: 5 attempts/30 seconds,
  1 MiB/5 log backups, 500 ms Explorer guard, required keyboard guard, and all
  three test-safety flags true. `allowWinL` is always true.
- [ ] Run targeted/full V2 tests and commit.

### Task 4: Runtime settings mapping

**Files:**
- Create: `v2/modern/kiosk_v2_modern/app/runtime_settings.py`
- Create: `v2/tests/modern/test_runtime_settings.py`

- [ ] Parse the V2 argument string through an injected Windows command-line parser
  into an immutable sequence; never use `shell=True`.
- [ ] Map every supervisor/window/logging/admin-timeout setting and verify arbitrary
  executable paths with spaces are preserved exactly.
- [ ] Prove config dictionaries are not mutated and no password-like field can
  enter runtime settings.
- [ ] Run full V2/Legacy checkpoints, `compileall`, and `git diff --check`; leave a
  clean worktree before transactional installation planning.
