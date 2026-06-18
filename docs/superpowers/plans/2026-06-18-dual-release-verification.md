# Dual Windows Release and Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package the independently built Legacy and Modern executables, prove their shared external contracts, and publish an honest verification matrix without adding a selector executable.

**Architecture:** `build_release.ps1` consumes already-tested artifacts from `release/legacy` and `release/modern`; it never rebuilds or substitutes them. Cross-build tests compare JSON fixtures, backup metadata, log redaction, and UI labels while each runtime remains isolated.

**Tech Stack:** Python 3.8+ contract tests, PowerShell packaging, SHA-256 manifests, unittest, snapshot Windows VMs.

---

## File Map

- Create `contracts/kiosk-config-v1.json`: canonical shared configuration fixture.
- Create `contracts/backup-metadata-v1.json`: canonical backup fields.
- Create `contracts/ui-labels-v1.json`: shared Russian text and header labels.
- Create `tests/test_cross_build_contracts.py`: Modern contract producer checks.
- Create `legacy_tests/test_cross_build_contracts.py`: Legacy contract consumer checks.
- Modify `build_release.ps1`: package both prebuilt artifacts and hashes.
- Create `tests/test_release_layout.py`: fail-closed release packaging tests.
- Modify `README.md`, `docs/INSTALL.md`, `docs/TESTING.md`, `docs/RESTORE.md`, `docs/SECURITY.md`, and `docs/AUDIT.md`.
- Create `docs/COMPATIBILITY.md`: target/verified matrix.

### Task 1: Lock Shared External Contracts

**Files:**
- Create: `contracts/kiosk-config-v1.json`
- Create: `contracts/backup-metadata-v1.json`
- Create: `contracts/ui-labels-v1.json`
- Create: `tests/test_cross_build_contracts.py`
- Create: `legacy_tests/test_cross_build_contracts.py`

- [ ] **Step 1: Create canonical fixtures from the approved design**

The config fixture includes every current key and no credentials. The backup fixture requires:

```json
{
  "schemaVersion": 1,
  "buildFamily": "modern",
  "windowsVersion": "10.0.0",
  "architecture": "x64",
  "operatorSid": "S-1-5-21-TEST-1001",
  "originalShell": "explorer.exe",
  "policyValues": []
}
```

The UI fixture contains `РК`, `Режим киоска`, `2026`, unlock labels, minimized notification, restore button, watchdog labels, and admin-session labels.

- [ ] **Step 2: Write failing Modern contract tests**

Load all fixtures with UTF-8 and assert Modern config parsing/serialization, backup output keys, log redaction, and layout labels conform exactly.

- [ ] **Step 3: Write failing Legacy contract tests**

Use Python 2.7-compatible `io.open` and assert the Legacy modules accept and produce the same external fields and labels.

- [ ] **Step 4: Run both suites**

```powershell
C:\Python38-32\python.exe -m unittest tests.test_cross_build_contracts -v
C:\Python27\python.exe -m unittest legacy_tests.test_cross_build_contracts -v
```

Expected: both pass after their corresponding build plans are complete.

- [ ] **Step 5: Commit**

```powershell
git add contracts tests/test_cross_build_contracts.py legacy_tests/test_cross_build_contracts.py
git commit -m "test: lock dual-build contracts"
```

### Task 2: Make Release Packaging Fail Closed

**Files:**
- Modify: `build_release.ps1`
- Create: `tests/test_release_layout.py`

- [ ] **Step 1: Write packaging tests**

Assert the script requires both exact paths, never copies the old `dist\RezhimKioska.exe`, never invokes PyInstaller, and creates `SHA256SUMS.txt` plus `build-manifest.json`.

- [ ] **Step 2: Run and confirm the old script fails expectations**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_release_layout -v
```

Expected: failures showing the old single-exe copy and PyInstaller invocation.

- [ ] **Step 3: Implement artifact validation before modifying release output**

Resolve and verify:

```powershell
$ModernExe = Join-Path $ProjectRoot 'release\modern\RezhimKioska-Modern.exe'
$LegacyExe = Join-Path $ProjectRoot 'release\legacy\RezhimKioska-Legacy.exe'
foreach ($Path in @($ModernExe, $LegacyExe)) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required tested artifact is missing: $Path"
    }
}
```

Stage in a temporary directory under `release`, compute SHA-256 with `Get-FileHash`, write a UTF-8 manifest, create the GitHub ZIP, then atomically replace only the packaging output. Preserve the two source artifact directories.

- [ ] **Step 4: Run packaging tests and package**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_release_layout -v
.\build_release.ps1
```

Expected: ZIP, manifest, and hashes exist; both executables remain in separate directories.

- [ ] **Step 5: Commit**

```powershell
git add build_release.ps1 tests/test_release_layout.py
git commit -m "build: package separate legacy and modern releases"
```

### Task 3: Execute the Windows Verification Matrix

**Files:**
- Create: `docs/COMPATIBILITY.md`
- Modify: `docs/TESTING.md`
- Modify: `docs/AUDIT.md`

- [ ] **Step 1: Define one result table**

Columns are OS, service pack/build, architecture, build family, frozen startup, install, shell, app/watchdog, keys/input, admin unlock, restore, baseline comparison, and result.

- [ ] **Step 2: Verify wrong-build behavior first**

On a disposable VM, run Legacy on a Modern OS and Modern on XP. Expected: a Russian compatibility message, nonzero exit, no registry/policy/config ACL changes, and no operator shell assignment.

- [ ] **Step 3: Run Legacy VM cases**

Run the complete checklist on XP SP1 x86, XP SP3 x86, and Server 2003 x86. Restore and revert snapshots after each test.

- [ ] **Step 4: Run Modern VM cases**

Run the complete checklist on Windows 7 SP1 x86/x64, Windows 8, Windows 8.1, Windows 10, and Windows 11. Use Home/Professional/Enterprise cases where available to validate fallback versus capability-backed profiles.

- [ ] **Step 5: Perform the permitted laptop test last**

Create a fresh backup, use only the `test` operator, run Modern checks, run Restore and `recover-desktop`, and verify:

```powershell
reg query 'HKCU\Software\Microsoft\Windows NT\CurrentVersion\Winlogon' /v Shell
reg query 'HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' /v Shell
```

Expected for `impal`: no HKCU override and HKLM `Shell` equals `explorer.exe`. Confirm Start, taskbar, keyboard, and ordinary desktop behavior.

- [ ] **Step 6: Record only observed results**

Unexecuted platforms remain `targeted, not verified`; any failing criterion marks that platform failed and blocks a universal-ready claim.

- [ ] **Step 7: Commit**

```powershell
git add docs/COMPATIBILITY.md docs/TESTING.md docs/AUDIT.md
git commit -m "test: record Windows compatibility matrix"
```

### Task 4: Publish Operator and Recovery Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/INSTALL.md`
- Modify: `docs/RESTORE.md`
- Modify: `docs/SECURITY.md`

- [ ] **Step 1: Put the two-file choice first**

Document exactly:

```text
XP SP1-SP3 / Server 2003 -> release\legacy\RezhimKioska-Legacy.exe
Windows 7 SP1-11         -> release\modern\RezhimKioska-Modern.exe
```

State that there is no selector or third loader.

- [ ] **Step 2: Document installation and Restore per build**

Give dry-run, install, restore, and recover-desktop commands for each executable. Put manual registry recovery commands after the normal Restore procedure and require an administrative account.

- [ ] **Step 3: Document security limits honestly**

State Python 2.7/old PyInstaller and NT 5.x are end-of-life; legacy shell/policies provide reduced assurance and cannot equal supported Enterprise controls. State that no password or keyboard input is logged.

- [ ] **Step 4: Generate the final source archive and listing**

Run full Modern and Legacy suites, run both build scripts, run `build_release.ps1`, and regenerate the full listing/diff artifact requested by the user. Do not include `.venv`, caches, VM images, logs, backups, or credentials.

- [ ] **Step 5: Final safety verification**

Confirm no KioskLauncher/allowed-app test processes remain, current desktop is restored, keyboard hook is gone with the process, services/startup baselines match, and both release hashes match `SHA256SUMS.txt`.

- [ ] **Step 6: Commit**

```powershell
git add README.md docs/INSTALL.md docs/RESTORE.md docs/SECURITY.md
git commit -m "docs: publish dual Windows kiosk release"
```

