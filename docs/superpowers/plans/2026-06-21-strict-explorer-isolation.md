# Strict Explorer Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Всегда завершать `explorer.exe` текущей сессии до Restore или явного выхода из киоска, включая ручной запуск launcher.

**Architecture:** Существующий `DesktopIsolation` остается без изменений и всегда создается со строгим режимом. Контракт состояний сохраняет desktop isolation после успешной авторизации; `LauncherSession` продолжает его tick в `ADMIN_SESSION`, а явная команда открытия рабочего стола завершает сессию и использует единый путь штатного восстановления Explorer.

**Tech Stack:** Python 3.8 modern runtime, Python 2.7 legacy runtime, Win32 API через `ctypes`, `unittest`, PowerShell/PyInstaller build scripts.

---

### Task 1: Удерживать Explorer выключенным до явного выхода

**Files:**
- Modify: `v2/contracts/behavior-cases.json`
- Modify: `v2/modern/kiosk_v2_modern/app/session.py`
- Modify: `v2/legacy/kiosk_v2_legacy/app/session.py`
- Test: `v2/tests/test_launcher_composition.py`

- [ ] **Step 1: Написать падающие parity-тесты**

Добавить recovery-spy с журналом вызовов и тесты для обеих реализаций:

```python
class FakeRecovery(object):
    def __init__(self, calls):
        self.calls = calls

    def restore_shell_surfaces(self):
        self.calls.append("recovery.restore_shell_surfaces")
        return ()

    def start_explorer(self):
        self.calls.append("recovery.start_explorer")
        return True


def test_admin_session_keeps_desktop_isolation_active(self):
    for family in ("modern", "legacy"):
        session, calls, _root, _clock = self._build(family)
        session.start()
        session.handle_action("unlock")
        session.submit_credentials("Administrator", "not-logged")
        del calls[:]
        session.tick()
        self.assertIn("desktop.tick", calls)
        self.assertNotIn("desktop.stop", calls)


def test_open_desktop_is_an_explicit_exit_that_restores_explorer(self):
    for family in ("modern", "legacy"):
        session, calls, root, _clock = self._build(family)
        session.start()
        session.handle_action("unlock")
        session.submit_credentials("Administrator", "not-logged")
        del calls[:]
        session.handle_action("unlockDesktop")
        self.assertFalse(session.running)
        self.assertIn("recovery.start_explorer", calls)
        self.assertIn("root.destroy", calls)
```

Обновить `FakeRoot.destroy()` так, чтобы он добавлял `"root.destroy"`, и создавать `FakeRecovery(calls)` в `_build`.

- [ ] **Step 2: Запустить тесты и подтвердить RED**

Run:

```powershell
& 'C:\Users\impal\AppData\Local\Python38-32\python.exe' -m unittest v2.tests.test_launcher_composition.SessionTests.test_admin_session_keeps_desktop_isolation_active v2.tests.test_launcher_composition.SessionTests.test_open_desktop_is_an_explicit_exit_that_restores_explorer -v
```

Expected: первый тест не видит `desktop.tick`, второй не завершает сессию через единый путь выхода.

- [ ] **Step 3: Минимально изменить контракт и session**

В `auth_succeeded` убрать только эффект `stop_desktop_isolation`:

```json
"effects": [
  "stop_keyboard_guard",
  "show_admin_session"
]
```

В `LauncherSession.handle_action` для обеих реализаций заменить действие `unlockDesktop`:

```python
if action == "unlockDesktop":
    self.close()
    self.root.destroy()
    return
```

В `LauncherSession.tick` выполнять desktop tick во всех защищенных состояниях:

```python
if state in ("OPERATOR", "ADMIN_DIALOG", "ADMIN_SESSION"):
```

В `LauncherSession.close` после остановки guard восстановить поверхности и запустить Explorer:

```python
try:
    self.keyboard.stop()
finally:
    self.desktop.stop()
self.recovery.restore_shell_surfaces()
self.recovery.start_explorer()
```

Restore-success уже выставляет `running=False`, поэтому последующий bootstrap cleanup не запускает второй Explorer; восстановлением управляет RestoreTool.

- [ ] **Step 4: Запустить parity-тесты и подтвердить GREEN**

Run:

```powershell
& 'C:\Users\impal\AppData\Local\Python38-32\python.exe' -m unittest v2.tests.test_launcher_composition -v
```

Expected: `OK`.

### Task 2: Всегда включать строгий Explorer guard

**Files:**
- Modify: `v2/modern/kiosk_v2_modern/launcher.py`
- Modify: `v2/legacy/kiosk_v2_legacy/launcher.py`
- Test: `v2/tests/test_launcher_composition.py`

- [ ] **Step 1: Написать падающий composition-тест**

```python
def test_native_launchers_always_enable_strict_explorer_isolation(self):
    paths = (
        os.path.join(V2_ROOT, "modern", "kiosk_v2_modern", "launcher.py"),
        os.path.join(V2_ROOT, "legacy", "kiosk_v2_legacy", "launcher.py"),
    )
    for path in paths:
        with open(path, "rb") as stream:
            source = stream.read().decode("utf-8")
        self.assertNotIn("CurrentShellMode", source)
        self.assertIn("terminate_explorer=True", source)
```

- [ ] **Step 2: Запустить тест и подтвердить RED**

Run:

```powershell
& 'C:\Users\impal\AppData\Local\Python38-32\python.exe' -m unittest v2.tests.test_launcher_composition.BootstrapTests.test_native_launchers_always_enable_strict_explorer_isolation -v
```

Expected: FAIL, потому что launcher еще использует `CurrentShellMode` и передает вычисляемый `strict_shell`.

- [ ] **Step 3: Минимально изменить обе композиции**

Удалить импорты `CurrentShellMode`/`CurrentShellRegistry`, удалить вычисление `strict_shell` и создать desktop guard так:

```python
desktop = DesktopIsolation(
    process_api,
    surface_api,
    terminate_explorer=True,
)
```

Legacy-вариант:

```python
desktop = DesktopIsolation(
    desktop_api,
    terminate_explorer=True,
)
```

- [ ] **Step 4: Запустить composition-тест и подтвердить GREEN**

Run:

```powershell
& 'C:\Users\impal\AppData\Local\Python38-32\python.exe' -m unittest v2.tests.test_launcher_composition -v
```

Expected: `OK`.

### Task 3: Полная проверка и сборка

**Files:**
- Verify: `v2/dist/modern/RezhimKioska-V2-Modern.exe`
- Verify: `v2/dist/legacy/RezhimKioska-V2-Legacy.exe`
- Verify: `v2/dist/SHA256SUMS.txt`

- [ ] **Step 1: Запустить все modern/parity тесты**

```powershell
& 'C:\Users\impal\AppData\Local\Python38-32\python.exe' -m unittest discover -s v2/tests -p 'test_*.py' -v
```

Expected: все тесты `OK`.

- [ ] **Step 2: Запустить legacy тесты**

```powershell
& 'C:\Users\impal\AppData\Local\Python27-x86-portable\python.exe' -m unittest discover -s v2/tests/legacy -p 'test_*.py' -v
```

Expected: все тесты `OK`.

- [ ] **Step 3: Собрать оба комплекта EXE**

```powershell
& 'v2\scripts\build-modern.ps1'
& 'v2\scripts\build-legacy.ps1'
```

Expected: оба скрипта завершаются с exit code 0 и обновляют `v2/dist/SHA256SUMS.txt`.

- [ ] **Step 4: Провести безопасный живой тест Modern**

Перед запуском записать PID текущего Explorer. Запустить Modern EXE, проверить исчезновение только Explorer текущей сессии, один экземпляр разрешенного приложения и отсутствие Explorer после успешной авторизации. Через явную кнопку открытия рабочего стола завершить киоск и подтвердить: один Explorer, нет процессов kiosk/notepad, панель задач видна.

- [ ] **Step 5: Аварийное восстановление при любом сбое теста**

```powershell
Start-Process "$env:WINDIR\explorer.exe"
```

Проверить один процесс Explorer текущей сессии и отсутствие процессов обоих launcher. Не завершать службы, драйверы, автозагрузку или процессы других сессий.
