# Kiosk V2 clean-room design

## Purpose

Kiosk V2 is a clean-room reimplementation of the Windows kiosk while preserving
all confirmed working behavior, the approved Russian interface, and the two-file
platform choice. Existing source remains available as a behavioral reference and
rollback path until V2 passes the complete VM acceptance matrix.

The rewrite does not modify the main Windows account, stop services, change
drivers, clear startup entries, mass-terminate processes, store Windows passwords,
or weaken Windows protection mechanisms.

## Supported builds

V2 ships as two independent executables:

```text
Windows XP SP1-SP3 / Windows Server 2003 x86 -> RezhimKioska-V2-Legacy.exe
Windows 7 SP1-Windows 11                     -> RezhimKioska-V2-Modern.exe
```

Modern uses Python 3.8 x86 so the frozen executable remains compatible with
Windows 7 SP1. Legacy uses Python 2.7 x86 and only APIs available on XP SP1 and
Server 2003. Neither runtime imports code from the other. Shared behavior is
defined by versioned JSON contracts and black-box acceptance tests rather than
shared Python modules.

## Repository layout

```text
v2/
  contracts/
    kiosk-config-v2.schema.json
    backup-v2.schema.json
    ui-layout-v2.json
    behavior-cases.json
  modern/
    app/
    platform/
    ui/
    cli.py
  legacy/
    app/
    platform/
    ui/
    cli.py
  migration/
    config_v1_to_v2.py
  tests/
    contracts/
    modern/
    legacy/
    acceptance/
  build/
    build-modern.ps1
    build-legacy.cmd
    package-release.ps1
```

The existing `python_kiosk`, `legacy_kiosk`, build scripts, tests, and release
artifacts stay untouched during development. V2 gets new entry points, new names,
new build directories, and a separate release package. Only after acceptance may
the production packaging script switch from V1 to V2.

## Application architecture

Each build implements the same ports and state model with platform-specific
adapters.

### Core state machine

`AppController` owns all transitions:

```text
STARTING
  -> OPERATOR
  -> ADMIN_DIALOG
  -> ADMIN_SESSION
  -> OPERATOR
  -> RESTORING
  -> STOPPED
```

No UI callback directly disables security controls or edits Windows state.
Transitions are atomic: a transition either completes and emits one audit event,
or rolls back to the previous safe state.

### Ports

- `KioskView`: renders state and emits button commands.
- `ProcessSupervisor`: adopts, starts, monitors, and restarts one exact executable.
- `WindowCoordinator`: positions the allowed application, detects minimization,
  and restores it only after the operator presses the restore button.
- `DesktopIsolation`: removes Explorer from the operator session and prevents its
  return while operator mode is active.
- `KeyboardGuard`: blocks only prohibited system shortcuts and forwards ordinary
  input.
- `WindowsAdminAuth`: verifies local Windows credentials and Administrators group
  membership.
- `PolicyTransaction`: applies operator-only shell and policy changes with rollback.
- `BackupRestore`: stores and restores exact previous values and ACLs.
- `ConfigRepository`: validates, migrates, and atomically stores configuration.
- `AuditLogger`: writes redacted rotating JSONL events.
- `PlatformProbe`: reports Windows version, architecture, edition, and supported
  capabilities.

The controller depends only on these interfaces. Modern and Legacy Win32 adapters
can differ internally without changing behavior.

## Operator-mode security

### Explorer isolation

Explorer is completely unavailable in the current operator session while kiosk
mode is active.

`DesktopIsolation` enumerates processes in the current session and acts only on a
process when all checks pass:

- normalized image basename is `explorer.exe`;
- process Session ID equals the KioskLauncher Session ID;
- process belongs to the current operator session;
- kiosk state is `OPERATOR` or `ADMIN_DIALOG`.

Every verified Explorer process in that operator session is terminated. The guard
continues monitoring and terminates Explorer again if Windows or the operator
restarts it. Explorer in the main account, another logged-on user, an RDP admin
session, or another Session ID is never touched. Termination is by exact PID with
minimal process rights; image-wide `taskkill /IM` is prohibited.

While termination is pending or unavailable, the fallback hides all shell surfaces,
including `Shell_TrayWnd`, `Shell_SecondaryTrayWnd`, `Progman`, `WorkerW`, the
separate Windows 7 Start `Button`, `DV2ControlHost`, and `BaseBar`. Fallback is
reapplied periodically and is not considered equivalent to successful isolation;
the UI and log report degraded mode.

After successful administrator authentication, both Explorer monitoring and the
fallback stop before Explorer is started exactly once. Returning to operator mode
terminates Explorer again. Restore/Undo permanently stops monitoring, restores
policy state, and starts Explorer exactly once when required.

### Keyboard guard

The keyboard guard remains active in `OPERATOR` and `ADMIN_DIALOG`. It blocks:

- Win, except Win+L;
- Win+R, Win+E, Win+X, Win+S, Win+D, Win+M, Win+Tab;
- Ctrl+Esc and Ctrl+Shift+Esc;
- Alt+Tab and Ctrl+Alt+Tab;
- Alt+Esc and Alt+F4.

Letters, digits, punctuation, Backspace, Delete, arrows, Tab, Enter, and all other
ordinary input are passed through `CallNextHookEx`. The hook does not record or log
keystrokes. Modifier state is cleared defensively after blocked sequences without
blocking key-up messages.

Opening or cancelling the login dialog never stops the guard. It stops only after
`WindowsAdminAuth` has validated credentials and local Administrators membership.
It starts again before the transition back to `OPERATOR`. Win+L calls the native
workstation-lock function and remains available.

### Administrator authentication

The dialog contains only local username and masked password. The username is
visible; each password character is displayed as `*`. The password exists only for
the synchronous `LogonUserW` call, is not stored in model state, configuration,
registry, files, network requests, exception text, or logs, and is released after
the call.

The returned token is checked against the local Administrators SID. All handles are
closed on success, failure, timeout, cancellation, and exceptions. Failed attempts
are rate-limited. An authenticated session has a configurable timeout and may:

- open the ordinary desktop;
- stop or resume application supervision;
- select another allowed `.exe`;
- return to kiosk mode;
- invoke Restore/Undo.

## Allowed application lifecycle

The configured application is identified by normalized full executable path, not
only by image name. Arguments and working directory are parsed as structured fields.

On entry to operator mode:

1. Adopt one already running exact-path process if present.
2. Otherwise start exactly one process.
3. Wait for input idle and discover all top-level windows owned by its PID.
4. Place its main window above the kiosk background without covering an admin dialog.

If the application exits or crashes, one replacement is started after bounded
backoff. Rapid crashes enter an explicit error state rather than an infinite launch
loop. If minimized, the process remains alive and minimized; the kiosk shows
`Приложение свернуто` and a `Развернуть приложение` button. No second instance is
created. Any ordinary Win32 executable may be selected after administrator
authentication and path validation.

The supervisor never terminates unrelated processes and never stops services or
drivers.

## Interface contract

The approved appearance and user workflow remain recognizable. The exact brand
signals are:

- square blue logo with `РК`;
- title `Режим киоска`;
- fixed year badge `2026`;
- developer line `разработал: Абдрахманов Амаль Даулетович`.

The screen retains the allowed-application panel, status and supervision indicators,
minimized notice and restore button, unlock panel, admin actions, and safety footer.
Russian text and button meaning remain unchanged except for clear error/degraded-mode
messages.

The UI is split into:

- versioned `ui-layout-v2.json` with logical 1440x900 coordinates and exact labels;
- pure layout engine that computes one uniform scale and centred offsets;
- Tk view that renders layout and sends commands to `AppController`;
- platform DPI service invoked before the first Tk root.

The uniform scale is:

```text
min(actual_width / 1440, actual_height / 900)
```

Coordinates, sizes, radii, fonts, and hit targets use that scale. The design surface
is centred, never independently stretched in X and Y, and never overlaps. Required
targets are 800x600, 1024x768, 1366x768, 1920x1080, and Windows DPI 100%, 125%, and
150%. The logo and fixed `2026` badge preserve their exact proportions at every
scale.

## Configuration and migration

V2 stores configuration in `config/kiosk.v2.json` with `schemaVersion: 2`. On first
run, the migrator reads the existing `config/kiosk.json`, validates it, and copies
only approved fields:

- operator user;
- allowed application path, arguments, working directory, and window behavior;
- restart and single-instance behavior;
- kiosk options and admin-session timeout;
- logging directory and level;
- test safety requirements.

Windows credentials, passwords, authentication tokens, transient process state,
and unknown fields are never migrated. The V1 file is copied unchanged into the V2
backup before any new file is written. V2 writes via temporary file, flush, atomic
replace, and administrator-only ACL. A failed migration leaves V1 untouched and
does not enable kiosk mode.

## Installation transaction

Installation is elevated and applies only to the named operator account:

1. Detect platform and select Modern or Legacy profile.
2. Confirm the operator exists and is not an administrator.
3. Validate allowed executable and protected installation paths.
4. Capture exact shell, policy values, relevant ACLs, and configuration.
5. Copy V2 files and apply administrator/operator ACLs.
6. Apply only supported operator-user policies.
7. Verify every reversible operation.
8. Set V2 as the operator shell last.
9. Persist versioned backup metadata with an integrity checksum and verify install state.

Any failure runs completed operations in reverse order. No partial install is
reported as success. Dry-run never changes the registry, ACLs, users, processes,
services, drivers, or startup.

## Restore and recovery

V2 Restore is a separate executable/command that does not import or require the
running launcher. It requires elevated Windows-admin rights and validates build
family, backup schema, operator SID, and target paths.

Restore stops only V2 guards in the operator session, restores exact backed-up
registry values and ACLs, returns the operator shell to its prior value (normally
`explorer.exe`), and starts Explorer once if needed. A `recover-desktop` command
provides an emergency current-session recovery path even when the launcher UI is
unavailable.

V1 executables, configs, backups, and Restore remain packaged separately until V2
passes all acceptance tests. Rollback from V2 never deletes V1 recovery material.

## Logging and diagnostics

Every component emits structured events through `AuditLogger`. Events include
session IDs, state transitions, exact result categories, platform profile, process
PID/path hash, policy operation IDs, backup IDs, and error codes. Logs exclude
passwords, tokens, typed text, full command arguments containing user data, and
secret configuration fields.

Logs rotate by size and count. When ProgramData is unavailable, dry-run and launcher
diagnostics may fall back to the operator profile; elevated apply and Restore do not
silently fall back to an unprotected location.

## Error handling

- Failure to verify the operator identity aborts before any write.
- Failure to remove Explorer keeps keyboard restrictions active, hides shell
  surfaces, reports degraded isolation, and retries with bounded delay.
- Failure to install the keyboard hook keeps the kiosk background active, reports a
  critical error, and does not claim secure operator mode.
- Failure to launch the allowed application shows a recoverable error and bounded
  retry controls.
- Authentication exceptions deny access and close all handles.
- Failed configuration or policy writes roll back the transaction.
- Failed Restore reports each unrecovered item and preserves backup evidence.

No exception path disables restrictions before administrator authentication.

## Test strategy

### Behavioral contracts

Before V2 production code, tests encode all confirmed V1 behavior and every listed
acceptance criterion. Both builds consume the same JSON behavior cases through
runtime-specific test adapters.

### TDD layers

1. Pure state-machine and layout tests.
2. Contract, migration, redaction, and transaction tests.
3. Win32 adapter tests with deterministic fake APIs.
4. Frozen-EXE smoke tests for correct/incorrect platform guards.
5. Snapshot-VM interactive tests.

Every production behavior follows RED -> GREEN -> refactor. Existing V1 tests are
not treated as proof of V2 behavior until equivalent V2 tests fail against missing
V2 code and then pass.

### VM matrix

- Windows XP SP1 x86.
- Windows XP SP3 x86.
- Windows Server 2003 x86.
- Windows 7 SP1 x86 and x64.
- Windows 8.1.
- Windows 10 Home and Professional.
- Windows 11 Home/Professional on the available VM or laptop only when safe.

Each interactive case starts from a snapshot, creates/uses a separate non-admin
operator, captures service/driver/startup baselines, tests install and operator mode,
tests authentication and Restore, compares baselines, and reverts the VM snapshot.
The main laptop account is never converted into a kiosk account.

Required display checks cover 800x600, 1024x768, 1366x768, 1920x1080, and DPI
100/125/150%. Required security checks cover Start, taskbar, Explorer restart,
keyboard bypasses during the login dialog, ordinary text input, exact application
restart/minimize behavior, and full Restore.

## Delivery and acceptance gates

V2 is delivered side-by-side with V1. Release promotion requires all of the
following:

- all V2 unit, contract, integration, and frozen smoke tests pass;
- both EXEs have the intended PE architecture and platform guard;
- required VM scenarios pass with screenshots and sanitized logs;
- install, repair, dry-run, test-mode, restore, uninstall, and recover-desktop work;
- no service, driver, startup, or unrelated-process baseline changes are detected;
- the operator cannot reach Explorer or shortcuts before administrator auth;
- ordinary input works in the allowed app and login dialog;
- UI has no overlaps and exact `РК`/`2026` branding is preserved;
- Restore returns the tested machine or VM to its pre-test desktop state;
- V1 remains available for rollback until the user explicitly accepts V2.

Until every gate is evidenced, V2 is reported as under development rather than
universally ready.
