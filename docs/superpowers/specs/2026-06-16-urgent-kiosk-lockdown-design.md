# Urgent Kiosk Lockdown Fix Design

## Goal

Fix the tested kiosk shell so the operator session cannot reach the Windows desktop, Start menu, Run, Explorer, task switching, Task Manager shortcuts, command shells, or arbitrary applications, while still leaving Windows services, drivers, system processes, existing startup items, and the main user account untouched.

## Root Causes Found

- The launcher still uses the old flat `kiosk_config.json` by default instead of the required `config/kiosk.json` shape.
- The test/run shell can be launched inside an existing Windows desktop session, but it does not remove the current operator's desktop Explorer window first, so Start and taskbar remain visible.
- The keyboard filter blocks raw Win key presses, but `Win+L` is simulated through `LockWorkStation`; this is acceptable as a fallback but should be explicit and should block Win combinations without logging keystrokes.
- The allowed application foreground control exists, but the watchdog starts the process without waiting for its input window and without start options from config.
- The admin unlock dialog and Windows admin credential check exist, but the UI needs clearer modal behavior and admin actions for changing the allowed app path from the kiosk session.

## Design

`config/kiosk.json` becomes the primary configuration file. If it is missing, startup creates a default template that runs `C:\Windows\System32\notepad.exe`. The loader keeps backwards compatibility with the old flat config while normalizing to the new nested model: `operatorUser`, `allowedApplication`, `kiosk`, and `logging`.

`KioskLauncher` validates the allowed exe path before launch and creates a watchdog command using the configured path, arguments, working directory, restart behavior, foreground behavior, and maximized setting. It never stores Windows admin credentials.

`ShellWindow` is a fullscreen background layer, not a topmost foreground owner. During operator-mode startup it starts `WindowsSessionLockdown`, which is allowed to close only the current user's desktop Explorer shell during a test launch. It does not touch services, drivers, foreign processes, or startup. After successful admin authentication, restrictions can be released and `explorer.exe` can be started temporarily.

`WindowsKeyFilter` blocks Win, Win+R, Win+E, Win+X, Win+S, Ctrl+Esc, Alt+Tab, Alt+Esc, and Alt+F4 inside operator mode only. It does not record or log keystrokes. `Win+L` remains available by calling `LockWorkStation` when the hook consumes the Win chord.

`AppWindowController` waits for the allowed app window, restores it if minimized, optionally maximizes it, sets it topmost briefly, brings it foreground, and releases shell topmost state. The kiosk window remains fullscreen background and must not cover the app.

Configurator and Restore continue to require elevated Windows administrator rights for real apply. CLI commands that change allowed app configuration require admin rights when configured to enforce Windows writes, and config writes go through the new model.

## Testing

Add unit tests for:

- creating `config/kiosk.json` default template;
- reading allowed app path from nested config;
- refusing missing allowed exe;
- watchdog command arguments and working directory;
- session lockdown operation boundaries;
- keyboard filter blocking required shortcuts while allowing `Win+L`;
- admin unlock modal flow and admin session actions;
- foreground window restore/maximize path;
- Configurator/Restore denial message.

Manual tests remain limited to a separate non-admin operator account. No real policy/shell changes are applied to the main account during automated verification.
