# Kiosk V2 Transactional Install and Restore Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install Kiosk V2 only for a verified non-administrator operator account and restore every changed value exactly, with no partial successful state.

**Architecture:** Modern and Legacy builds get independent transaction, backup, Windows account, registry, ACL, install, and restore modules. Both expose the same behavior but do not import each other or V1. Shell replacement is the final install operation; backup integrity and every applied operation are verified before success is reported.

**Tech Stack:** Python 3.8 x86 plus Win32/NetAPI/registry APIs for Modern, Python 2.7 x86 plus XP-compatible Win32/NetAPI/registry APIs for Legacy, `unittest`, JSON, SHA-256, PowerShell wrappers that default to dry-run.

---

## File Map

- Create `v2/modern/kiosk_v2_modern/app/transaction.py`: reversible operation runner and failure report.
- Create `v2/modern/kiosk_v2_modern/app/backup_store.py`: canonical backup metadata, SHA-256 integrity, atomic protected persistence.
- Create `v2/modern/kiosk_v2_modern/platform/operator_account.py`: elevation, local-user SID, existence, and indirect administrator-membership checks.
- Create `v2/modern/kiosk_v2_modern/platform/operator_registry.py`: exact HKU value capture/apply/restore and operator-hive mounting.
- Create `v2/modern/kiosk_v2_modern/platform/file_acl.py`: SDDL capture, protected ACL apply, and exact restore.
- Create `v2/modern/kiosk_v2_modern/app/install_service.py`: preflight, shell-last operation list, verification, repair, and dry-run.
- Create `v2/modern/kiosk_v2_modern/app/restore_service.py`: launcher-independent integrity-checked restore and recovery result.
- Create equivalent independent files under `v2/legacy/kiosk_v2_legacy/` without Modern imports or post-XP APIs.
- Create `v2/modern/kiosk_v2_modern/cli.py` and `v2/legacy/kiosk_v2_legacy/cli.py`: install, uninstall, repair, restore, dry-run, test-mode, and recover-desktop commands.
- Create `v2/scripts/install-modern.ps1`, `restore-modern.ps1`, `install-legacy.cmd`, and `restore-legacy.cmd`: safe command entry points.
- Create tests under `v2/tests/modern/` and `v2/tests/legacy/` matching each module.

### Task 1: Reversible Transaction and Integrity-Checked Backup

- [x] Write failing Modern tests proving dry-run invokes nothing, apply order is stable, failure rolls completed operations back in reverse order, rollback failures are reported, and shell cannot be placed before other operations.
- [x] Run `Python38-32\python.exe -m unittest v2.tests.modern.test_install_transaction -v`; expect missing-module failure.
- [x] Implement `Operation`, `TransactionResult`, `TransactionFailure`, and `InstallTransaction.execute(dry_run=False)` in `transaction.py`. `Operation` carries `operation_id`, `apply`, `rollback`, `verify`, and `is_shell`; constructor rejects more than one shell or a non-final shell.
- [x] Write failing backup tests proving the digest excludes only `integritySha256`, tampering is rejected, build family/SID are validated, writes are atomic, and ACL failure restores the prior bytes.
- [x] Implement canonical UTF-8 JSON with sorted keys and compact separators, SHA-256 over metadata without `integritySha256`, temp-file flush plus `os.fsync`, `os.replace`, and injected ACL protection.
- [x] Run targeted and full V2 tests, then commit `feat: add kiosk v2 transactional backup core`.

### Task 2: Elevated Local Operator Preflight

- [x] Write failing adapter tests for non-elevated denial, missing local user, local SID resolution, disabled-account denial, direct/indirect Administrators membership denial, and accepted standard user.
- [x] Run the tests and verify they fail because `operator_account.py` is absent.
- [x] Implement `OperatorIdentity`, `PreflightError`, `WindowsOperatorAccountApi`, and `OperatorPreflight`. Use `IsUserAnAdmin`, `NetUserGetInfo`, `LookupAccountNameW`, `NetUserGetLocalGroups(LG_INCLUDE_INDIRECT)`, and SID comparison with `S-1-5-32-544`; free every NetAPI buffer.
- [x] Add a source test forbidding `net.exe`, `wmic.exe`, PowerShell, password storage, user creation, or group mutation in preflight.
- [x] Run Modern/full tests and commit `feat: validate kiosk v2 operator account`.

### Task 3: Exact Registry and ACL Snapshots

- [x] Write failing registry tests for absent/present values, exact type/data capture, operator-SID-only paths, hive load/unload symmetry, apply verification, and restore deletion of originally absent values.
- [x] Implement registry value records and an operator hive context. Use `HKEY_USERS\\<operatorSid>` when mounted; otherwise load only `<ProfileImagePath>\\NTUSER.DAT`, always unload in `finally`, and never write HKCU of the administrative account.
- [x] Define only these operator values: per-user Winlogon `Shell`, `DisableTaskMgr`, `DisableRegistryTools`, `DisableCMD`, `NoRun`, `NoControlPanel`, `NoViewContextMenu`, `NoTrayContextMenu`, `NoSetTaskbar`, and `NoWinKeys`.
- [x] Write failing ACL tests for SDDL capture, administrator/system full control, operator read/execute, config write denial, exact restore, and paths outside approved installation/config targets.
- [x] Implement ACL capture/apply/restore with `GetNamedSecurityInfoW`, SDDL conversion, and `SetNamedSecurityInfoW`; do not change the allowed executable unless it is inside the protected installation roots supplied to the manager.
- [x] Run tests and commit `feat: snapshot kiosk v2 registry and acls`.

### Task 4: Modern Install, Repair, Restore, and Recovery

- [ ] Write failure-injection tests for every install boundary: preflight, backup, file ACL, policies, verification, shell-last, backup persistence, and final verification.
- [ ] Implement `InstallService.plan()` as a side-effect-free ordered description and `apply()` as one transaction. Capture backup before the first write, apply shell last, verify exact SID and values, and preserve backup evidence on failure.
- [ ] Write restore tests proving invalid digest/build/SID/path aborts before writes, exact values/ACLs return, originally absent values are deleted, all recoverable items are attempted, and failures remain reported.
- [ ] Implement independent `RestoreService`; it must not import launcher/controller/UI modules. `recover_desktop()` restores the current session surfaces and starts one Explorer only when no shell exists.
- [ ] Implement repair as verified re-application from current config without replacing the original pre-install backup. Implement uninstall as restore plus removal of V2-owned files only after successful restore.
- [ ] Run full V2 tests and commit `feat: install and restore kiosk v2 Modern`.

### Task 5: Independent XP/Server 2003 Install and Restore

- [ ] Recreate Task 1-4 tests against Legacy imports and run them on Python 2.7 x86 first.
- [ ] Implement independent Python 2.7-compatible modules with no `dataclasses`, `pathlib`, f-strings, `os.replace`, `subprocess.run`, or Modern imports. Use `MoveFileExW(MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)` for atomic replacement.
- [ ] Use only XP-compatible registry, NetAPI, Advapi32, and shell APIs; keep the same backup schema and behavior.
- [ ] Run Python 2.7 Legacy tests, Python 3.8 full parity tests, source compatibility scan, then commit `feat: install and restore kiosk v2 Legacy`.

### Task 6: Safe Commands, Scripts, and Acceptance Documentation

- [ ] Write CLI tests proving every mutating command defaults to dry-run, `--apply` requires elevation, `test-mode` requires a separate non-admin operator and backup, and its `finally` path always invokes Restore.
- [ ] Implement Modern and Legacy command parsers with commands `install`, `uninstall`, `repair`, `restore`, `dry-run`, `test-mode`, and `recover-desktop`. Return non-zero for incomplete rollback or Restore.
- [ ] Add PowerShell/CMD wrappers that pass structured arguments, never embed passwords, and never auto-apply.
- [ ] Update `INSTALL.md`, `RESTORE.md`, `TESTING.md`, `SECURITY.md`, and `COMPATIBILITY.md` with separate Modern/Legacy commands, emergency recovery, XP/Home limits, and the rule that no platform is ready without VM evidence.
- [ ] Run all tests and frozen-build smoke checks without applying shell/policy changes to the development laptop.
- [ ] Commit `docs: document kiosk v2 transactional recovery`.

## Self-Review

- Spec coverage: operator-only scope, non-admin validation, backup-before-write, ACL protection, reversible policies, shell-last, dry-run, repair, uninstall, test-mode, independent Restore, recovery, Legacy parity, and integrity verification each map to a task.
- Placeholder scan: no deferred implementation markers are present.
- Type consistency: `Operation`, `InstallTransaction`, backup metadata, `OperatorIdentity`, `InstallService`, and `RestoreService` names remain stable across tasks.
