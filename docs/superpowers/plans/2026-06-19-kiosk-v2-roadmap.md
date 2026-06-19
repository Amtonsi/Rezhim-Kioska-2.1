# Kiosk V2 clean-room roadmap

This roadmap splits the approved V2 specification into independently testable
implementation plans. A phase starts only after the previous phase has a clean
commit and green tests.

## Phase 1: Contracts and state-machine foundation

Plan: `2026-06-19-kiosk-v2-foundation.md`

Deliverables:

- versioned configuration, backup, UI, and behavior JSON contracts;
- independent Modern and Legacy state machines consuming the same behavior cases;
- tests proving security remains active through `ADMIN_DIALOG`;
- exact `РК`, fixed `2026`, and developer-line UI contract.

Acceptance: Python 3 and Python 2.7 contract/state tests pass without importing V1.

## Phase 2: Modern runtime

Deliverables:

- Python 3.8 controller and ports;
- current-session Explorer isolation with continuous monitoring;
- keyboard guard, local admin auth, exact-path supervisor, and window coordinator;
- redacted logging and bounded restart/error states.

Acceptance: Modern unit/integration tests pass; Win7/Win11 Win32 adapter smoke tests
run without changing the development laptop's shell or policies.

## Phase 3: Legacy runtime

Deliverables:

- independent Python 2.7 controller and adapters;
- XP SP1/Server 2003 compatible process, window, keyboard, auth, and logging APIs;
- behavior parity with Modern through JSON acceptance cases.

Acceptance: Python 2.7 x86 tests and frozen wrong-platform smoke pass; no Modern
imports occur in the Legacy module graph.

## Phase 4: Migration, installation, and Restore

Deliverables:

- V1-to-V2 config migration with untouched source backup;
- operator validation, transactional policy application, ACL protection, and shell-last install;
- independent Restore/Undo, uninstall, repair, dry-run, test-mode, and recover-desktop;
- exact rollback and integrity-checked backup metadata.

Acceptance: failure-injection tests prove reverse rollback and no partial apply.

## Phase 5: UI, builds, release, and VM acceptance

Deliverables:

- approved Russian interface with exact `РК`, fixed `2026`, and responsive layout;
- separate Modern/Legacy frozen EXEs and GitHub archive;
- full diff, source listing, hashes, manuals, and VM checklists;
- snapshot evidence for supported platform matrix.

Acceptance: all automated tests pass, both EXEs are correct PE32 artifacts, and no
platform is declared ready without its required VM evidence and successful Restore.

