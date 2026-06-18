# Windows Multi-Version Builds Design

## Goal

Deliver two manually selected standalone kiosk executables while preserving the
currently working modern implementation:

- `RezhimKioska-Legacy.exe` for Windows XP SP1, SP2, SP3, and Windows Server
  2003;
- `RezhimKioska-Modern.exe` for Windows 7 SP1, Windows 8, Windows 8.1,
  Windows 10, and Windows 11.

There is no bootstrapper, installer selector, or automatic hand-off between
the two files. The administrator chooses the appropriate executable. Each
executable still validates the operating system before changing configuration,
the registry, policies, ACLs, or the operator shell.

## Non-Goals

- Linux and macOS support.
- UWP or Microsoft Store applications.
- Windows Vista, Windows 2000, Windows RT, Windows on ARM, or Itanium.
- One binary that runs on the complete XP-to-11 range.
- Refactoring the working modern launcher without a compatibility need.
- Changing services, drivers, system processes, or existing Windows startup
  entries.

## Compatibility Matrix

| Build | Supported systems | Runtime target | Policy profiles |
| --- | --- | --- | --- |
| Legacy | XP SP1-SP3, Server 2003 | 32-bit Python 2.7 and PyInstaller 3.2.1 | `xp_legacy`, `server2003_legacy` |
| Modern | Windows 7 SP1, 8, 8.1, 10, 11 | 32-bit Python 3.8.10 and a pinned compatible PyInstaller | `win7_srp`, `home_fallback`, `win10_applocker`, `win10_shelllauncher` |

The 32-bit executables target both 32-bit Windows and x64 Windows through
WOW64. Registry access must explicitly select the intended 32-bit or 64-bit
view where required. ARM64 is outside this design and must not be reported as
verified.

The historical PyInstaller 3.2.1 documentation states that it runs on Windows
XP or newer. XP SP1 and Server 2003 remain release gates: support is not marked
verified until the frozen executable starts and completes the required test
matrix on those systems. Python 2.7 and its freezer are end-of-life software;
they are isolated to the Legacy build, are never used by the Modern build, and
do not make an obsolete operating system secure.

References:

- <https://pyinstaller.org/en/v3.2.1/requirements.html>
- <https://www.python.org/downloads/release/python-2718/>

## Delivery Layout

The release output contains two self-contained directories so their runtime
and configuration files cannot be mixed accidentally:

```text
release/
  modern/
    RezhimKioska-Modern.exe
    config/kiosk.json
  legacy/
    RezhimKioska-Legacy.exe
    config/kiosk.json
  PythonKiosk-GitHub.zip
```

Launching either executable opens the existing Russian kiosk interface. A
wrong-system launch displays a Russian compatibility error and exits before
any administrative operation.

## Source Boundaries

The existing `main.py` and `python_kiosk/` package remain the Modern baseline.
Modern changes are limited to:

- Python 3.8 compatibility fixes;
- platform validation before administrative actions;
- the new build manifest and release layout;
- the approved title treatment;
- tests needed to prevent regressions.

Legacy code lives in a separate `legacy_kiosk/` package with its own entry
point and build manifest. It follows the same externally visible contract but
does not force Python 2.7 compatibility changes throughout the modern package.
The two implementations share contracts, not runtime imports:

- the `config/kiosk.json` schema;
- log event names and password-redaction rules;
- backup metadata format;
- install, restore, launcher, watchdog, and admin-session behavior;
- the Russian UI labels and layout dimensions.

Contract tests load representative output from both implementations and fail
when these formats diverge.

## Platform Detection

Detection occurs before configuration mutation.

The Legacy detector uses APIs available on NT 5.x and registry information. It
accepts only:

- client version 5.1 with service pack 1 or newer as `xp_legacy`;
- server version 5.2 as `server2003_legacy`.

The Modern detector accepts Windows client versions beginning with Windows 7
SP1. Modern Windows Server releases are outside this design and are rejected.
The detector determines edition and available capabilities, then chooses the
existing policy profile. Product names are diagnostic information only;
security decisions use version, product type, edition, and capability checks.

Both builds log the detected version, edition, architecture, and selected
profile without recording credentials or keyboard input.

## Legacy Backend

The Legacy build must not depend on PowerShell, WMIC, modern Task Scheduler
features, AppLocker, Shell Launcher, or APIs introduced after Server 2003.
Administrative work is performed by compatible Win32 APIs and registry access.

Legacy provides:

- per-operator shell replacement;
- compatible HKCU/HKLM policy values;
- fixed executable validation and watchdog restart;
- low-level keyboard filtering only during operator mode, with `Win+L`
  preserved;
- local Windows credential validation and Administrators-group membership
  checks;
- configuration ACL protection using APIs available on the target OS;
- backup, transaction log, restore, and desktop recovery from the executable;
- rotating logs without passwords or typed text.

Because XP and Server 2003 do not provide current Enterprise kiosk controls,
the UI and documentation label this as a legacy, reduced-assurance profile.

## Modern Backend

The working Modern behavior remains unchanged unless required for Windows 7
compatibility. It keeps:

- the existing shell UI and allowed-application workflow;
- one allowed process with duplicate prevention;
- minimize detection and manual restore button;
- watchdog stop/start controls in an authenticated admin session;
- Windows administrator credential validation;
- keyboard restrictions with ordinary text input and `Win+L` preserved;
- backup, restore, dry-run, logging, and safe desktop recovery;
- profile selection for SRP, Home fallback, AppLocker, and Shell Launcher.

Capabilities are detected at runtime. An edition name alone is not sufficient
to claim AppLocker or Shell Launcher enforcement.

## Configuration and State

Both builds use the current `config/kiosk.json` format. Configuration resides
beside the selected executable under its own `config` directory and never in a
temporary PyInstaller extraction directory.

The operator receives read/execute access only. Windows administrators retain
modify access. The configured application path is validated before kiosk mode
is enabled. Existing backups are versioned with:

- build family (`legacy` or `modern`);
- configuration schema version;
- Windows version and architecture;
- operator SID;
- original shell and policy values.

A build refuses to restore an incompatible backup automatically and displays a
manual recovery command instead. It never guesses registry values.

## Transaction and Recovery Flow

Administrative installation follows this order:

1. Validate the executable against the current Windows family.
2. Verify administrator rights appropriate to that Windows version.
3. Validate the separate operator account and confirm it is not an
   administrator.
4. Validate the configured allowed executable.
5. Create and verify the backup.
6. Protect program and configuration files.
7. Apply operator policies.
8. Assign the kiosk executable as the operator shell last.
9. Verify the written values and record transaction completion.

If a step fails, applied steps are reversed in order. Restore remains callable
from an administrative account without the operator session or KioskLauncher.
It restores the previous shell and only the policy values recorded in the
backup.

## Header Design

The top-left header in both builds uses the approved compact composition:

- a small blue/cyan rounded icon containing `РК`;
- the white semibold title `Режим киоска`;
- an outlined `2026` badge to the right;
- proportions and spacing matching the supplied reference image.

The rest of the working shell layout, controls, hit targets, colors, and
behavior remain unchanged. The header must fit at supported display scales and
must not overlap the application status area.

## Error Handling and Logging

All expected failures produce Russian messages and nonzero command results
without leaving partial settings. Required cases include:

- wrong executable for the current Windows version;
- unsupported service pack or architecture;
- missing administrative rights;
- missing operator profile or allowed executable;
- inaccessible configuration, backup, or registry hive;
- unavailable policy capability;
- failed shell write or failed rollback.

Logs rotate and include timestamps, process/session identifiers, build family,
platform profile, operation names, and sanitized error codes. Passwords,
credential buffers, and keyboard input are never logged. Credential buffers
and Win32 handles are released immediately after authentication.

## Build Strategy

Separate reproducible scripts produce the artifacts:

- `build_modern.ps1` runs the complete Modern test suite under Python 3.8,
  builds `RezhimKioska-Modern.exe`, and stages its configuration;
- `build_legacy.cmd` runs the Python 2.7-compatible Legacy tests and builds
  `RezhimKioska-Legacy.exe` without requiring PowerShell on the target system;
- `build_release.ps1` assembles both already-built artifacts and the GitHub
  archive without silently substituting one for the other.

Build scripts record interpreter, freezer, architecture, and source revision
in a manifest. Missing runtimes or failed tests stop the build.

## Verification Matrix

Existing Modern tests remain mandatory. New contract, platform-guard, build,
and header-layout tests are added before implementation changes.

VM tests use snapshots and a separate standard operator account:

- XP SP1 x86;
- XP SP3 x86;
- Server 2003 x86;
- Windows 7 SP1 x86 and x64;
- Windows 8/8.1;
- Windows 10;
- Windows 11.

Each VM verifies dry-run, backup, install, operator login, shell replacement,
allowed-app launch, watchdog restart, minimize/restore behavior, blocked escape
keys, working ordinary input, working `Win+L`, Windows-admin unlock, timeout,
and Restore. Services, drivers, system startup, unrelated processes, and the
administrative account are compared before and after.

After every laptop test, `recover-desktop` and Restore are run and the current
administrative desktop is verified. A platform is reported as targeted but not
verified until its VM matrix passes. The project is not declared universally
ready while any required platform remains untested.
