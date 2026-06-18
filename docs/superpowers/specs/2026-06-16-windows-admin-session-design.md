# Windows Admin Session Design

## Goal

Strengthen the kiosk shell so the operator cannot reach the Windows desktop until a local Windows administrator successfully authenticates, while keeping the allowed application usable above the kiosk background layer.

## Authentication

Windows administrator unlock uses local Win32 authentication only. The password is passed directly to `LogonUserW`, never stored in config, logs, registry, files, or temporary files. Authentication returns a structured result:

- `success` when credentials are valid and the token belongs to local Administrators;
- `bad_credentials` when Windows rejects the username/password;
- `not_admin` when credentials are valid but the account is not a local administrator;
- `windows_error` when a Win32/API call fails unexpectedly.

Handles are closed after every attempt. API error codes are logged without password, token, or secret data.

## Shell And Window Behavior

`KioskLauncher` starts as the operator shell instead of `explorer.exe`. The kiosk window remains fullscreen and blocks the desktop, Start menu, taskbar and shell escape routes. It does not use topmost over the allowed app. The allowed application window is restored and placed topmost above the kiosk shell on every watchdog tick. If it is minimized, the shell shows a restore button. If it exits or crashes, watchdog restarts it.

## Admin Session

After successful Windows administrator authentication, the kiosk enters a time-limited administrative session. During this session the administrator can unlock the desktop, start `explorer.exe`, stop watchdog, change the allowed application path, run restore/undo, inspect status, or return to kiosk mode. If the session times out, kiosk restrictions are restored unless kiosk mode was explicitly disabled.

## Administrative Rights

Configurator and RestoreTool require the current Windows process to run as an elevated administrator before any apply-mode system action. If the process is not elevated/admin, they return the message:

`Отказано в доступе. Для выполнения действия требуются права администратора Windows.`

No partial install, restore, rollback, shell change, HKLM change, or policy change is allowed after this denial.

## Compatibility

The implementation keeps XP-compatible Win32 mechanisms where possible: `LogonUserW`, token membership check against the Administrators SID, explicit handle close, and fallback error reporting. Modern APIs are not required for authentication.

## Logging

The log records admin dialog open, successful Windows admin authentication, denial reasons, Windows API errors, explorer launch, temporary unlock, return to kiosk mode, allowed application start/restart, and apply/restore denials. The log must never contain passwords, password hashes, full tokens, or secret authentication data.
