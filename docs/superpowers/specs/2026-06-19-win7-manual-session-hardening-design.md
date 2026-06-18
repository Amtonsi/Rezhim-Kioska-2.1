# Win7 manual-session hardening design

## Scope

This change hardens only the Modern launcher (Windows 7 SP1 through Windows 11).
Legacy remains unchanged. The target failure is a manual launch inside an already
open Windows 7 operator desktop where Explorer, the taskbar, and the separate
Windows 7 Start button already exist.

## Confirmed root causes

1. `WindowsDesktopBackend` hides `Shell_TrayWnd`, `Progman`, and `WorkerW` only
   once. Windows 7 exposes its Start button as a separate top-level window, so
   the button remains clickable and can recreate/open the Start menu.
2. `handle_admin_unlock()` stops the keyboard filter before credentials are
   validated. This creates an unauthenticated interval in which task switching,
   shell shortcuts, and kiosk minimization are available.
3. Tk receives DPI-scaled font metrics while the canvas independently stretches
   X and Y coordinates. On a scaled Windows 7 display this makes text larger than
   its allocated rectangles and causes overlaps.

## Explorer handling

When operator mode starts inside an existing desktop, the backend will identify
the exact process that owns `Shell_TrayWnd`. It may terminate only that process
and only when all of these checks pass:

- the process image basename is `explorer.exe`;
- its session ID equals the current KioskLauncher session ID;
- it owns the discovered `Shell_TrayWnd` window;
- the kiosk is currently entering operator mode.

The backend must not enumerate and terminate every `explorer.exe`, use `taskkill
/IM`, affect another user/session, or touch services, drivers, startup entries,
or unrelated processes. The selected process is opened with the minimum required
query/terminate rights, terminated, and its handle is always closed.

If the exact shell PID, image path, or session cannot be verified, termination is
skipped. The fallback hides all known current-desktop shell windows, including
the Windows 7 Start button and Start-menu classes. The periodic operator guard
reapplies this fallback while kiosk mode is active.

On authenticated desktop unlock or Restore/Undo, hidden shell windows are shown
and `explorer.exe` is started if no shell window exists. Normal install still
writes KioskLauncher as the operator's shell so Explorer does not start at the
next operator logon.

## Keyboard authorization boundary

The keyboard filter remains installed while the local administrator login dialog
is open. It continues to block Win, Win shortcuts, Ctrl+Esc, Ctrl+Shift+Esc,
Alt+Tab, Ctrl+Alt+Tab, Alt+Esc, and Alt+F4 while passing letters, digits,
Backspace, Tab, Enter, and other ordinary input through `CallNextHookEx`.

Opening, cancelling, or failing the dialog never stops and restarts the hook.
The hook is stopped only after Windows credentials have been validated and the
account has been confirmed as a member of the local Administrators group. Returning
to kiosk mode starts the filter again. Win+L remains available.

## DPI and layout

Before the first Tk root is created, Modern enables process DPI awareness using
the newest API available and falls back through older APIs to Win7-compatible
`SetProcessDPIAware`. Missing APIs or `ACCESS_DENIED` are logged but do not abort
the kiosk.

Canvas coordinates, dimensions, corner radii, and fonts use one uniform scale:

```text
scale = min(screen_width / 1440, screen_height / 900)
```

The 1440x900 design surface is centred inside the actual canvas. This preserves
aspect ratio and prevents font/rectangle divergence. The login dialog is scaled
uniformly, clamped to the work area, and centred when its original mockup position
would fall outside the display.

## Error handling and logging

Logs record only shell PID/session verification outcomes, DPI API selection,
fallback use, and success/failure categories. No keyboard input or passwords are
logged. Failure to terminate the verified shell immediately activates the hide
fallback and leaves the watchdog running.

## Tests

Automated regression tests must prove:

- a verified `Shell_TrayWnd` owner in the current session is the only PID passed
  to the termination backend;
- a different-session or non-Explorer owner is never terminated;
- fallback includes the separate Win7 Start button and Start-menu window classes;
- Restore starts Explorer when the shell process was stopped;
- the keyboard filter is still active inside the credential provider;
- failed/cancelled authorization produces no stop/start gap;
- successful authorization stops the filter only after validation;
- ordinary login/password input still passes through the filter;
- uniform scaling fits 1024x768, 1366x768, 1920x1080, and 150% DPI scenarios;
- the Modern manifest/build retains Windows 7 compatibility.

The local Windows 11 laptop must not receive live kiosk policies during these
tests. Final interactive verification is performed in the Windows 7 VM, followed
by Restore/Undo.
