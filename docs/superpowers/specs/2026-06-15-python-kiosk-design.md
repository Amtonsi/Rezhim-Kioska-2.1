# PythonKiosk Design

## Goal

Build a Python-based Windows kiosk project that prepares files and tools for
locking a dedicated operator account to one fixed Win32 executable. The project
must not apply changes to the developer laptop unless an administrator
explicitly runs the installer/configurator on a target machine.

The operator must not get a normal Windows desktop. The kiosk application must
start before Explorer in the operator account, keep the allowed application
running, and restart it if it closes or crashes. Windows services, drivers,
system processes, and existing startup services must not be stopped or removed.

## Supported Windows Range

The project targets the broadest practical Windows range: Windows XP and newer.
Because kiosk capabilities differ by Windows version and edition, the project
uses a layered compatibility model instead of one mechanism for every system.

Supported policy profiles:

- `xp_legacy`: custom user shell, HKCU/HKLM registry policies, interface
  restrictions, and best-effort process supervision.
- `win7_srp`: legacy shell mode plus Software Restriction Policies when
  available.
- `win10_applocker`: legacy shell mode plus AppLocker when available.
- `win10_shelllauncher`: Shell Launcher enhancement on Enterprise, Education,
  and IoT editions where supported.
- `home_fallback`: custom shell and registry-policy fallback for Home editions,
  with reduced security guarantees.

## Security Model

The locked account must be a standard Windows user. The administrator account is
used only for installation, configuration, and recovery. A Windows administrator
can always recover the machine; the project is designed to restrict the
operator, not to defend against local administrators.

Allowed operator action:

- Use the single configured desktop executable.
- Lock the session or switch user with `Win+L`.

Blocked or restricted operator actions:

- Explorer desktop, Start menu, taskbar, Run dialog, Control Panel, Settings,
  Task Manager, command prompt, PowerShell where available, Registry Editor,
  and common Windows shell escape paths.
- Closing the allowed application as a way to reach the desktop.
- Changing kiosk configuration without the kiosk administrator password.

## Components

### Kiosk Launcher

`KioskLauncher` is the shell process for the operator account. It replaces
`explorer.exe` for that user. On sign-in it starts first, launches the configured
allowed application, watches its process, and restarts it when it exits.

The launcher stays resident while the operator session is active. If the
allowed application exits normally, crashes, or is closed by the user, the
launcher restarts it after a short configurable delay.

### Configuration Store

Configuration is stored in a local JSON file protected by Windows file
permissions where possible. It contains:

- path to the allowed executable;
- operator username or SID;
- selected policy profile;
- restart delay;
- admin password hash and salt;
- emergency restore metadata;
- feature flags for version-specific policy layers.

The password is never stored in plaintext. Modern systems use a strong
hashing/KDF option available in Python. Older Windows compatibility may require
a conservative hash fallback documented in the implementation.

### Admin Unlock

The launcher exposes a hidden administrator unlock prompt through a configurable
hotkey. After successful password entry, an administrator can:

- temporarily unlock the desktop and start `explorer.exe`;
- change the allowed executable path;
- enable or disable kiosk mode for the operator account;
- change the kiosk administrator password;
- restore the previous shell and policy configuration;
- view current status and logs.

Failed unlock attempts are delayed and logged to slow password guessing.

### Policy Engine

The policy engine detects Windows version, edition, architecture, and available
policy features. It then applies the strongest supported non-destructive policy
profile for the target machine.

Policy application must be reversible. Before writing registry or policy
settings, the tool saves the previous values needed for rollback.

### Restore Tool

The restore path must work outside the kiosk launcher from a Windows
administrator account. It restores the original shell, removes or reverts kiosk
policy values created by this project, and leaves unrelated services and startup
entries untouched.

## Safety Rules

- Never stop, disable, or delete existing services.
- Never remove existing startup entries.
- Never apply policies to all users unless the selected policy mechanism
  requires a machine-level setting and the effect is clearly documented.
- Prefer per-user settings for the operator account.
- Always create backups before changing shell or policy values.
- Always provide a restore command that can be run from an administrator
  account.
- Do not block `Win+L`.

## First Implementation Scope

The first Python version should implement a safe local project skeleton:

- launcher/watchdog logic;
- JSON configuration;
- password hashing and admin unlock flow;
- dry-run policy detection;
- generated install/restore plan;
- Windows registry writing only behind an explicit administrator command.

Actual policy application should be separated from normal launcher execution so
running `main.py` in PyCharm cannot accidentally lock the current laptop.

## Testing

Tests should cover:

- config load/save and validation;
- password hashing and verification;
- process restart decision logic;
- Windows version/profile selection from mocked system information;
- restore metadata generation;
- dry-run policy plan output.

Manual testing of real policy application must be done on a dedicated test
machine or virtual machine, not on the development laptop.
