# Legacy Windows Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an isolated `RezhimKioska-Legacy.exe` targeting Windows XP SP1-SP3 and Windows Server 2003 without destabilizing the Modern package.

**Architecture:** Implement a Python 2.7-compatible `legacy_kiosk/` package with no imports from `python_kiosk/`. It honors the same JSON, backup, logging, UI, launcher, watchdog, authentication, and restore contracts, while using only NT 5.x-compatible Win32 APIs and commands.

**Tech Stack:** Python 2.7.18 x86, Tkinter, ctypes, `_winreg`, unittest, PyInstaller 3.2.1, Win32 APIs available on XP/Server 2003, CMD build wrapper.

---

## File Map

- Create `legacy_main.py`: Legacy CLI and default UI entry point.
- Create `legacy_kiosk/compat.py`: Python 2.7 text, JSON, file, and Tkinter compatibility helpers.
- Create `legacy_kiosk/config.py`: current `kiosk.json` contract.
- Create `legacy_kiosk/platform_detect.py`: NT 5.x detector and strict build guard.
- Create `legacy_kiosk/logging_service.py`: rotating sanitized JSONL log.
- Create `legacy_kiosk/win32_accounts.py`: SID, token, local-group, and profile helpers.
- Create `legacy_kiosk/local_admin_auth.py`: `LogonUserW` plus Administrators SID membership.
- Create `legacy_kiosk/system_backend.py`: operator hive, policies, ACL, backup, rollback, and restore.
- Create `legacy_kiosk/process_watchdog.py`: one allowed process and restart throttling.
- Create `legacy_kiosk/window_control.py`: visible-window discovery and activation.
- Create `legacy_kiosk/keyboard_filter.py`: blocked escape combinations with `Win+L` allowed.
- Create `legacy_kiosk/shell_ui.py`: Russian Legacy shell and admin dialog.
- Create `legacy_tests/`: Python 2.7-compatible tests with fake Win32 backends.
- Create `requirements-legacy-build.txt`, `RezhimKioska.Legacy.spec`, and `build_legacy.cmd`.

### Task 1: Establish the Legacy Contract and Python 2.7 Harness

**Files:**
- Create: `legacy_kiosk/__init__.py`
- Create: `legacy_kiosk/compat.py`
- Create: `legacy_kiosk/config.py`
- Create: `legacy_tests/__init__.py`
- Create: `legacy_tests/test_config.py`

- [ ] **Step 1: Write a Python 2.7-compatible config test**

```python
# -*- coding: utf-8 -*-
import json
import os
import shutil
import tempfile
import unittest

from legacy_kiosk.config import load_config, save_config


class LegacyConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.path = os.path.join(self.temp_dir, "kiosk.json")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_round_trip_current_contract(self):
        source = {
            "operatorUser": "test",
            "allowedApplication": {
                "path": r"C:\Windows\notepad.exe",
                "arguments": "",
                "workingDirectory": r"C:\Windows",
                "restartOnExit": True,
                "bringToFront": True,
                "startMaximized": False,
                "singleInstance": True,
                "restoreIfMinimized": False
            },
            "kiosk": {"allowWinL": True, "adminSessionTimeoutSeconds": 300},
            "logging": {"logDirectory": r"C:\ProgramData\Kiosk\Logs", "level": "Info"}
        }
        save_config(source, self.path)
        self.assertEqual(source, load_config(self.path))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run and confirm missing package**

```cmd
C:\Python27\python.exe -m unittest legacy_tests.test_config
```

Expected: import failure for `legacy_kiosk.config`.

- [ ] **Step 3: Implement compatibility helpers**

Use `io.open` for UTF-8/UTF-8-BOM files and define text types without Python 3 syntax:

```python
# -*- coding: utf-8 -*-
import io
import json
import os

try:
    text_type = unicode
except NameError:
    text_type = str


def read_json(path):
    with io.open(path, "r", encoding="utf-8-sig") as stream:
        return json.load(stream)


def write_json(path, value):
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    temporary = path + ".tmp"
    with io.open(temporary, "w", encoding="utf-8") as stream:
        text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write(text_type(text))
    if os.path.exists(path):
        os.remove(path)
    os.rename(temporary, path)
```

- [ ] **Step 4: Implement strict config validation**

`load_config(path)` must require `operatorUser`, an absolute existing `.exe` path when applying, and the current allowed-application/kiosk/logging dictionaries. `save_config(data, path)` calls `write_json` and never stores Windows credentials.

- [ ] **Step 5: Run the Legacy config test**

```cmd
C:\Python27\python.exe -m unittest legacy_tests.test_config
```

Expected: pass.

- [ ] **Step 6: Commit**

```powershell
git add legacy_kiosk legacy_tests/test_config.py
git commit -m "feat: add legacy config contract"
```

### Task 2: Detect Only XP SP1+ and Server 2003

**Files:**
- Create: `legacy_kiosk/platform_detect.py`
- Create: `legacy_tests/test_platform_detect.py`

- [ ] **Step 1: Write the complete compatibility matrix test**

Test XP SP0 rejection, XP SP1/SP2/SP3 acceptance as `xp_legacy`, Server 2003 acceptance as `server2003_legacy`, and rejection of Windows 2000, Vista, and Windows 7+.

- [ ] **Step 2: Run and confirm missing detector**

```cmd
C:\Python27\python.exe -m unittest legacy_tests.test_platform_detect
```

Expected: import failure.

- [ ] **Step 3: Implement immutable result objects without dataclasses**

```python
class LegacyWindowsInfo(object):
    def __init__(self, major, minor, build, service_pack_major, product_type, architecture):
        self.major = int(major)
        self.minor = int(minor)
        self.build = int(build)
        self.service_pack_major = int(service_pack_major)
        self.product_type = int(product_type)
        self.architecture = architecture


class LegacyCompatibility(object):
    def __init__(self, supported, profile="", message=u""):
        self.supported = bool(supported)
        self.profile = profile
        self.message = message


def validate_legacy_platform(info):
    if info.architecture != "x86":
        return LegacyCompatibility(False, message=u"Legacy-сборка поддерживает только x86.")
    if info.major == 5 and info.minor == 1 and info.product_type == 1:
        if info.service_pack_major < 1:
            return LegacyCompatibility(False, message=u"Требуется Windows XP Service Pack 1 или новее.")
        return LegacyCompatibility(True, "xp_legacy")
    if info.major == 5 and info.minor == 2 and info.product_type != 1:
        return LegacyCompatibility(True, "server2003_legacy")
    return LegacyCompatibility(False, message=u"Запустите подходящую сборку программы.")
```

- [ ] **Step 4: Read `OSVERSIONINFOEXW` and native architecture**

Define the ctypes structure with `dwMajorVersion`, `dwMinorVersion`, `dwBuildNumber`, `wServicePackMajor`, and `wProductType`. Call `GetVersionExW` on NT 5.x and `GetNativeSystemInfo`; close no handles because these calls return process-owned data only.

- [ ] **Step 5: Run detector tests under Python 2.7**

Expected: all matrix tests pass.

- [ ] **Step 6: Commit**

```powershell
git add legacy_kiosk/platform_detect.py legacy_tests/test_platform_detect.py
git commit -m "feat: detect XP and Server 2003 targets"
```

### Task 3: Implement Local Administrator Authentication

**Files:**
- Create: `legacy_kiosk/win32_accounts.py`
- Create: `legacy_kiosk/local_admin_auth.py`
- Create: `legacy_tests/test_local_admin_auth.py`

- [ ] **Step 1: Write backend-injected authentication tests**

Cover bad credentials, valid non-admin, valid Administrators member, disabled account error, and guaranteed handle close. Assert the password is absent from captured logger fields.

- [ ] **Step 2: Run and confirm missing authenticator**

```cmd
C:\Python27\python.exe -m unittest legacy_tests.test_local_admin_auth
```

Expected: import failure.

- [ ] **Step 3: Implement the authentication result and orchestration**

```python
class WindowsAuthError(Exception):
    def __init__(self, api_name, error_code):
        Exception.__init__(self, "%s: %s" % (api_name, error_code))
        self.api_name = api_name
        self.error_code = int(error_code)


class AuthResult(object):
    def __init__(self, success, message, account_name=u""):
        self.success = bool(success)
        self.message = message
        self.account_name = account_name


class LocalAdminAuthenticator(object):
    def __init__(self, backend, logger=None):
        self.backend = backend
        self.logger = logger

    def authenticate(self, account_name, password):
        token = None
        try:
            token = self.backend.logon_local_user(account_name, password)
            if not self.backend.token_is_local_admin(token):
                return AuthResult(False, u"Отказано в доступе. Указанная учётная запись не является администратором Windows.")
            return AuthResult(True, u"Доступ разрешён.", account_name)
        except WindowsAuthError:
            return AuthResult(False, u"Отказано в доступе. Неверное имя пользователя или пароль.")
        finally:
            if token is not None:
                self.backend.close_handle(token)
```

- [ ] **Step 4: Implement Win32 calls with explicit ctypes signatures**

Use `LogonUserW` with local computer domain `.`, allocate the Administrators SID `S-1-5-32-544`, use `CheckTokenMembership` with token-group enumeration fallback, and call `CloseHandle`/`FreeSid` in `finally`. Do not retain password references after the call.

- [ ] **Step 5: Run authentication tests**

Expected: all pass under Python 2.7.

- [ ] **Step 6: Commit**

```powershell
git add legacy_kiosk/win32_accounts.py legacy_kiosk/local_admin_auth.py legacy_tests/test_local_admin_auth.py
git commit -m "feat: authenticate legacy local administrators"
```

### Task 4: Add Transactional Operator Policy and Restore Backend

**Files:**
- Create: `legacy_kiosk/system_backend.py`
- Create: `legacy_kiosk/backup_store.py`
- Create: `legacy_tests/test_system_backend.py`
- Create: `legacy_tests/test_restore.py`

- [ ] **Step 1: Write fake-registry transaction tests**

Verify backup occurs before writes, shell is written last, a middle failure restores earlier values in reverse order, restore changes only recorded values, and no forbidden service/driver/startup/process operation exists.

- [ ] **Step 2: Run and confirm missing backend**

```cmd
C:\Python27\python.exe -m unittest legacy_tests.test_system_backend legacy_tests.test_restore
```

Expected: import failures.

- [ ] **Step 3: Implement explicit operation sequencing**

```python
INSTALL_ORDER = (
    "validate_operator",
    "validate_allowed_app",
    "create_backup",
    "protect_files",
    "apply_operator_policies",
    "set_operator_shell",
    "verify_install",
)


class LegacyTransaction(object):
    def __init__(self, backend, logger):
        self.backend = backend
        self.logger = logger
        self.completed = []

    def apply(self, context):
        try:
            for name in INSTALL_ORDER:
                getattr(self.backend, name)(context)
                self.completed.append(name)
        except Exception:
            for name in reversed(self.completed):
                self.backend.rollback(name, context)
            raise
```

- [ ] **Step 4: Implement operator hive access without WMIC/PowerShell**

Use `LookupAccountNameW` and `ConvertSidToStringSidW`, read `ProfileImagePath` from `HKLM\...\ProfileList\<SID>`, and use `reg.exe load/unload` only for the selected operator's `NTUSER.DAT`. Write shell/policies under that mounted hive. Never modify current-user HKCU unless it is the selected operator SID.

- [ ] **Step 5: Protect files through Win32 security descriptors**

Build a DACL granting full control to SYSTEM and Administrators and read/execute to the operator SID. Apply it to the Legacy executable directory and config; do not use localized group names.

- [ ] **Step 6: Implement versioned backup and exact restore**

Store build family, schema version, OS tuple, operator SID, original shell, each original policy value/type/existence flag, and original security descriptor. Refuse a backup for another SID/build family.

- [ ] **Step 7: Run transaction tests**

Expected: all pass; fakes show zero service, driver, startup, or mass-process calls.

- [ ] **Step 8: Commit**

```powershell
git add legacy_kiosk/system_backend.py legacy_kiosk/backup_store.py legacy_tests/test_system_backend.py legacy_tests/test_restore.py
git commit -m "feat: add transactional legacy install and restore"
```

### Task 5: Add Legacy Watchdog, Window Control, and Keyboard Filter

**Files:**
- Create: `legacy_kiosk/process_watchdog.py`
- Create: `legacy_kiosk/window_control.py`
- Create: `legacy_kiosk/keyboard_filter.py`
- Create: `legacy_tests/test_runtime_controls.py`

- [ ] **Step 1: Write state-machine tests**

Cover exactly one launch, delayed restart after exit, no restart while minimized, manual restore of an iconic window, stop/start supervision, Alt+Tab and Ctrl+Alt+Tab blocking, ordinary key pass-through, and `Win+L` calling `LockWorkStation`.

- [ ] **Step 2: Run and confirm missing modules**

Expected: import failures.

- [ ] **Step 3: Implement one-process watchdog state**

```python
class WatchdogState(object):
    def __init__(self, restart_delay_seconds=2):
        self.restart_delay_seconds = int(restart_delay_seconds)
        self.process = None
        self.last_exit_time = 0
        self.enabled = True

    def may_restart(self, now):
        return self.enabled and now - self.last_exit_time >= self.restart_delay_seconds
```

The controller enumerates processes by executable path, adopts an existing matching process, and never terminates unrelated processes.

- [ ] **Step 4: Implement NT 5.x window control**

Use `EnumWindows`, `GetWindowThreadProcessId`, `IsIconic`, `ShowWindow(SW_RESTORE)`, `BringWindowToTop`, and `SetForegroundWindow`. A minimized app updates UI state and remains minimized until the user presses the restore button.

- [ ] **Step 5: Implement fail-open keyboard filtering**

For `WH_KEYBOARD_LL`, return nonzero only for the explicitly blocked combinations. Pass all other events to `CallNextHookEx`. Stop the hook during the credential dialog and authenticated admin session; reinstall it on return to kiosk. Do not record virtual-key events.

- [ ] **Step 6: Run runtime-control tests**

Expected: all pass under Python 2.7.

- [ ] **Step 7: Commit**

```powershell
git add legacy_kiosk/process_watchdog.py legacy_kiosk/window_control.py legacy_kiosk/keyboard_filter.py legacy_tests/test_runtime_controls.py
git commit -m "feat: add legacy kiosk runtime controls"
```

### Task 6: Add the Legacy Russian Shell UI

**Files:**
- Create: `legacy_kiosk/shell_ui.py`
- Create: `legacy_tests/test_shell_ui.py`

- [ ] **Step 1: Write layout-model tests**

Assert the same labels, admin controls, minimized notification, restore button, `РК` mark, `Режим киоска` title, and `2026` badge as Modern. Assert login and password entries accept input and password uses `show="*"`.

- [ ] **Step 2: Implement Tkinter compatibility imports**

```python
try:
    import Tkinter as tkinter
    import tkFileDialog as filedialog
    import tkMessageBox as messagebox
except ImportError:
    import tkinter
    from tkinter import filedialog, messagebox
```

- [ ] **Step 3: Implement the layout and event wiring**

Use the Modern design-space dimensions and labels but keep the module independent. Wire unlock, desktop start, supervision toggle, return-to-kiosk, application change, and minimized-app restore to injected controller methods.

- [ ] **Step 4: Run Legacy UI tests**

Expected: all pass without creating a real display by testing the layout model and fake root/canvas.

- [ ] **Step 5: Commit**

```powershell
git add legacy_kiosk/shell_ui.py legacy_tests/test_shell_ui.py
git commit -m "feat: add legacy Russian kiosk shell"
```

### Task 7: Add Legacy CLI and Frozen Build

**Files:**
- Create: `legacy_main.py`
- Create: `requirements-legacy-build.txt`
- Create: `RezhimKioska.Legacy.spec`
- Create: `build_legacy.cmd`
- Create: `legacy_tests/test_cli.py`

- [ ] **Step 1: Write CLI guard tests**

Test default launch, `install`, `restore`, `recover-desktop`, wrong-platform refusal, admin refusal, and external frozen config resolution.

- [ ] **Step 2: Implement command dispatch**

Use `optparse` or Python 2.7 `argparse`, resolve config beside `sys.executable` when frozen, validate Legacy platform before state-changing commands, and return integer exit codes. Default no-argument execution launches the shell.

- [ ] **Step 3: Pin the historical build environment**

Create:

```text
pyinstaller==3.2.1
pefile==2017.11.5
pypiwin32==223
```

- [ ] **Step 4: Create the Legacy spec**

Bundle `legacy_main.py`, `legacy_kiosk`, Tkinter, and the config template. Set `console=False`, x86 build environment, and `name="RezhimKioska-Legacy"`.

- [ ] **Step 5: Create the CMD builder**

`build_legacy.cmd` verifies Python 2.7 and 32-bit pointer size, runs `C:\Python27\python.exe -m unittest discover legacy_tests`, invokes PyInstaller 3.2.1, and stages only the resulting exe plus config under `release\legacy`.

- [ ] **Step 6: Run all Legacy tests and build**

```cmd
C:\Python27\python.exe -m unittest discover legacy_tests -v
build_legacy.cmd
```

Expected: all tests pass and `release\legacy\RezhimKioska-Legacy.exe` exists.

- [ ] **Step 7: Commit**

```powershell
git add legacy_main.py legacy_kiosk legacy_tests requirements-legacy-build.txt RezhimKioska.Legacy.spec build_legacy.cmd
git commit -m "build: add XP and Server 2003 kiosk artifact"
```

### Task 8: Verify on Snapshot VMs Before Claiming Support

**Files:**
- Create: `docs/LEGACY-TESTING.md`
- Modify: `docs/INSTALL.md`
- Modify: `docs/RESTORE.md`
- Modify: `docs/SECURITY.md`

- [ ] **Step 1: Record immutable VM baselines**

For XP SP1 x86, XP SP3 x86, and Server 2003 x86, record OS version, shell values, services, drivers, startup entries, and administrator/operator group membership before testing.

- [ ] **Step 2: Run the full operator workflow on each VM**

Create a separate standard operator, run dry-run, backup, apply, login, allowed app, watchdog, minimize/restore, keyboard restrictions, ordinary input, local-admin unlock, admin timeout, and return-to-kiosk.

- [ ] **Step 3: Run Restore and compare baselines**

Verify `explorer.exe` is restored, hooks stop with the process, policies return to recorded values, and services/drivers/startup/main admin account are unchanged. Revert the VM snapshot after collecting logs.

- [ ] **Step 4: Mark results accurately**

Use `targeted`, `failed`, or `verified` per OS. Do not label XP SP1 or Server 2003 supported if the frozen bootloader did not run there.

- [ ] **Step 5: Commit**

```powershell
git add docs/LEGACY-TESTING.md docs/INSTALL.md docs/RESTORE.md docs/SECURITY.md
git commit -m "docs: record legacy verification matrix"
```
