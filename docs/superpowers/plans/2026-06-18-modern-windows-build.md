# Modern Windows Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve the working kiosk while producing a guarded `RezhimKioska-Modern.exe` for Windows 7 SP1 through Windows 11 and applying the approved compact title.

**Architecture:** Keep `main.py` and `python_kiosk/` as the working baseline. Add a small compatibility result API to `platform_detect.py`, call it before frozen runtime actions, and add a separate pinned Modern build without restructuring launcher, watchdog, authentication, or restore behavior.

**Tech Stack:** Python 3.8.10 x86, Python standard library, Tkinter, ctypes Win32 API, unittest, PyInstaller 5.13.2, PowerShell build scripts.

---

## File Map

- Modify `python_kiosk/platform_detect.py`: richer Windows model and Modern compatibility guard.
- Modify `main.py`: reject a wrong Modern platform before launch/install/restore mutation.
- Modify `python_kiosk/shell_ui.py`: compact `РК`, `Режим киоска`, and `2026` header.
- Modify `tests/test_platform_detect.py`: compatibility matrix tests.
- Modify `tests/test_cli.py`: command guard tests.
- Modify `tests/test_shell_ui.py`: header layout and overlap tests.
- Create `requirements-modern-build.txt`: pinned Modern freezer.
- Create `RezhimKioska.Modern.spec`: Modern executable manifest.
- Create `build_modern.ps1`: tested Modern build entry point.
- Modify `tests/test_project_structure.py`: required Modern artifacts.
- Modify `docs/INSTALL.md`, `docs/TESTING.md`, and `docs/SECURITY.md`: Modern support statement and limits.

### Task 1: Protect the Working Baseline

**Files:**
- Modify: `.gitignore`
- Verify: all current files under `tests/`

- [ ] **Step 1: Extend generated-output exclusions**

Add these exact entries without removing existing exclusions:

```gitignore
.venv/
build/
dist/
release/
__pycache__/
*.pyc
*.pyo
```

- [ ] **Step 2: Run the existing suite before code changes**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover tests -v
```

Expected: all existing tests pass. Record the test count in the implementation log. If any test fails, stop and debug the baseline before continuing.

- [ ] **Step 3: Initialize a local repository only after confirming exclusions**

Run with the bundled Git executable:

```powershell
& 'C:\Users\impal\AppData\Local\GitHubDesktop\app-3.5.12\resources\app\git\cmd\git.exe' init
& 'C:\Users\impal\AppData\Local\GitHubDesktop\app-3.5.12\resources\app\git\cmd\git.exe' add .
& 'C:\Users\impal\AppData\Local\GitHubDesktop\app-3.5.12\resources\app\git\cmd\git.exe' commit -m 'chore: preserve working kiosk baseline'
```

Expected: a root commit containing source and docs, with no `.venv`, `build`, `dist`, or `release` files.

### Task 2: Add a Modern Platform Compatibility Result

**Files:**
- Modify: `python_kiosk/platform_detect.py`
- Test: `tests/test_platform_detect.py`

- [ ] **Step 1: Write failing matrix tests**

Add these tests:

```python
from python_kiosk.platform_detect import validate_modern_platform


def _info(major, minor, service_pack=0, product_type=1, architecture="x86"):
    return WindowsInfo(
        major=major,
        minor=minor,
        build=0,
        edition="Professional",
        service_pack_major=service_pack,
        product_type=product_type,
        architecture=architecture,
    )


class ModernCompatibilityTests(unittest.TestCase):
    def test_rejects_xp(self):
        result = validate_modern_platform(_info(5, 1, service_pack=3))
        self.assertFalse(result.supported)

    def test_rejects_windows_7_without_sp1(self):
        result = validate_modern_platform(_info(6, 1, service_pack=0))
        self.assertFalse(result.supported)

    def test_accepts_windows_7_sp1(self):
        result = validate_modern_platform(_info(6, 1, service_pack=1))
        self.assertTrue(result.supported)

    def test_accepts_windows_8_to_11(self):
        for version in [(6, 2), (6, 3), (10, 0)]:
            self.assertTrue(validate_modern_platform(_info(*version)).supported)

    def test_rejects_modern_windows_server(self):
        result = validate_modern_platform(_info(10, 0, product_type=3))
        self.assertFalse(result.supported)

    def test_rejects_arm64(self):
        result = validate_modern_platform(_info(10, 0, architecture="arm64"))
        self.assertFalse(result.supported)
```

- [ ] **Step 2: Run the tests and confirm the missing API**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_platform_detect -v
```

Expected: import or constructor failures for the new compatibility fields.

- [ ] **Step 3: Implement the compatibility data and guard**

Add this API while preserving existing constructor call sites through defaults:

```python
class CompatibilityResult(object):
    def __init__(self, supported, message=""):
        self.supported = bool(supported)
        self.message = message or ""


class WindowsInfo(object):
    def __init__(
        self,
        major,
        minor,
        build,
        edition,
        product_name="",
        service_pack_major=0,
        product_type=1,
        architecture="x86",
    ):
        self.major = int(major)
        self.minor = int(minor)
        self.build = int(build)
        self.edition = edition or ""
        self.product_name = product_name or ""
        self.service_pack_major = int(service_pack_major or 0)
        self.product_type = int(product_type or 1)
        self.architecture = (architecture or "x86").lower()

    @property
    def edition_lower(self):
        return (self.edition + " " + self.product_name).lower()


def validate_modern_platform(info):
    if info.product_type != 1:
        return CompatibilityResult(False, "Эта сборка не поддерживает Windows Server.")
    if info.architecture not in ("x86", "x64", "amd64"):
        return CompatibilityResult(False, "Архитектура Windows не поддерживается этой сборкой.")
    if info.major < 6 or (info.major == 6 and info.minor < 1):
        return CompatibilityResult(False, "Используйте RezhimKioska-Legacy.exe.")
    if info.major == 6 and info.minor == 1 and info.service_pack_major < 1:
        return CompatibilityResult(False, "Для Windows 7 требуется Service Pack 1.")
    return CompatibilityResult(True, "")
```

- [ ] **Step 4: Populate service pack, product type, and architecture**

Implement a private Win32 reader using `RtlGetVersion` with `platform.version()` as a non-Windows/test fallback. Map `wProductType == 1` to client and processor architecture values `0`/`9` to `x86`/`x64`. Keep `_read_windows_caption()` only as optional display metadata.

- [ ] **Step 5: Run focused and full tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_platform_detect -v
.\.venv\Scripts\python.exe -m unittest discover tests
```

Expected: both commands pass.

- [ ] **Step 6: Commit**

```powershell
git add python_kiosk/platform_detect.py tests/test_platform_detect.py
git commit -m "feat: validate modern Windows targets"
```

### Task 3: Guard Frozen Modern Commands

**Files:**
- Modify: `main.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests for mutation and launch guards**

Add tests that inject a detector and assert that unsupported systems return `2`, emit the compatibility message, do not call `shell_runner`, and do not invoke a Configurator or RestoreTool backend. Keep `--help` and pure configuration parsing available.

Use this public helper in tests:

```python
def test_modern_guard_rejects_xp_before_launch(self):
    output = io.StringIO()
    info = WindowsInfo(5, 1, 2600, "Professional", service_pack_major=3)
    code = main_module.main(
        ["launch", "--config", self.config_path],
        stdout=output,
        shell_runner=lambda launcher: self.fail("shell must not start"),
        platform_detector=lambda: info,
        enforce_platform=True,
    )
    self.assertEqual(2, code)
    self.assertIn("Legacy", output.getvalue())
```

- [ ] **Step 2: Run the test and confirm signature failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_cli -v
```

Expected: `main()` rejects the new keyword arguments.

- [ ] **Step 3: Implement an injectable guard**

Change the signature and guard only Windows-changing/runtime commands:

```python
def main(
    argv=None,
    stdout=None,
    shell_runner=None,
    platform_detector=None,
    enforce_platform=None,
):
    stdout = stdout or sys.stdout
    platform_detector = platform_detector or detect_windows_info
    if enforce_platform is None:
        enforce_platform = bool(getattr(sys, "frozen", False))
    # Parse first so help remains available.
    args = build_parser().parse_args(argv)
    guarded = {"launch", "install", "restore", "recover-desktop", "set-app"}
    if enforce_platform and args.command in guarded:
        result = validate_modern_platform(platform_detector())
        if not result.supported:
            _emit(stdout, result.message)
            return 2
```

Preserve the current default `argv = ["launch"]` behavior before parsing.

- [ ] **Step 4: Run CLI and full regression suites**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_cli -v
.\.venv\Scripts\python.exe -m unittest discover tests
```

Expected: all tests pass and no real registry action occurs.

- [ ] **Step 5: Commit**

```powershell
git add main.py tests/test_cli.py
git commit -m "feat: guard modern executable by Windows version"
```

### Task 4: Apply the Approved Compact Header

**Files:**
- Modify: `python_kiosk/shell_ui.py`
- Test: `tests/test_shell_ui.py`

- [ ] **Step 1: Write failing header layout tests**

Add assertions for named primitives and fixed design-space geometry:

```python
def test_header_matches_approved_compact_brand(self):
    layout = build_shell_layout(r"C:\App\Allowed.exe")
    by_name = {item["name"]: item for item in layout}
    self.assertEqual("РК", by_name["header_mark_text"]["text"])
    self.assertEqual("Режим киоска", by_name["header_title"]["text"])
    self.assertEqual("2026", by_name["header_year_text"]["text"])
    self.assertEqual((34, 28, 34, 34, 7), by_name["header_mark"]["rect"])
    self.assertLess(
        by_name["header_year_badge"]["rect"][0] + by_name["header_year_badge"]["rect"][2],
        by_name["header_subtitle"]["rect"][0],
    )
```

- [ ] **Step 2: Run the test and confirm missing primitives**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_shell_ui.ShellWindowTests.test_header_matches_approved_compact_brand -v
```

Expected: failure because `header_mark` and year badge do not exist.

- [ ] **Step 3: Add header primitives without moving page panels**

Replace only the header primitive block in `build_shell_layout()` with:

```python
_round_rect("header_mark", 34, 28, 34, 34, 7, "#0f8bd7"),
_text("header_mark_text", "РК", 34, 28, 34, 34, ("Segoe UI", 11, "bold"), "#ffffff", anchor="center"),
_text("header_title", "Режим киоска", 80, 29, 150, 32, ("Segoe UI", 15, "bold"), "#f4f6f8"),
_round_rect("header_year_badge", 236, 22, 58, 46, 12, "#102126", outline="#397080"),
_text("header_year_text", "2026", 236, 22, 58, 46, ("Segoe UI", 10, "normal"), "#67e8f9", anchor="center"),
```

Place the existing subtitle after x=320 so it cannot overlap the badge. Do not change card geometry, control tags, or click handlers.

- [ ] **Step 4: Run UI and full tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_shell_ui -v
.\.venv\Scripts\python.exe -m unittest discover tests
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add python_kiosk/shell_ui.py tests/test_shell_ui.py
git commit -m "feat: add compact kiosk header"
```

### Task 5: Add the Reproducible Modern Build

**Files:**
- Create: `requirements-modern-build.txt`
- Create: `RezhimKioska.Modern.spec`
- Create: `build_modern.ps1`
- Modify: `tests/test_project_structure.py`

- [ ] **Step 1: Write failing artifact-structure tests**

Require all three new files and assert the spec names `RezhimKioska-Modern` while the script stages to `release\modern`.

- [ ] **Step 2: Run the structure test**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_project_structure -v
```

Expected: missing-file failures.

- [ ] **Step 3: Pin the build dependency**

Create:

```text
pyinstaller==5.13.2
```

- [ ] **Step 4: Create the Modern spec from the working manifest**

Copy the existing analysis inputs but set:

```python
name="RezhimKioska-Modern"
```

Keep `console=False`, bundle `config/kiosk.json`, and do not add new runtime hooks.

- [ ] **Step 5: Create a fail-closed build script**

The script accepts `-PythonExe`, verifies Python 3.8 and 32-bit pointer size, runs the complete suite, builds the Modern spec, and copies only the resulting exe plus config to `release\modern`. Any failed check exits nonzero before replacing an existing release.

- [ ] **Step 6: Run structure and full tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_project_structure -v
.\.venv\Scripts\python.exe -m unittest discover tests
```

Expected: all tests pass.

- [ ] **Step 7: Build with the pinned Python 3.8 x86 environment**

Run:

```powershell
.\build_modern.ps1 -PythonExe 'C:\Python38-32\python.exe'
```

Expected: `release\modern\RezhimKioska-Modern.exe` and `release\modern\config\kiosk.json` exist. If the interpreter is not installed, the script must fail with a clear message and must not reuse the Python 3.14 artifact.

- [ ] **Step 8: Commit**

```powershell
git add requirements-modern-build.txt RezhimKioska.Modern.spec build_modern.ps1 tests/test_project_structure.py
git commit -m "build: add Windows 7 to 11 artifact"
```

### Task 6: Document and Verify Modern Without Changing the Main Account

**Files:**
- Modify: `docs/INSTALL.md`
- Modify: `docs/TESTING.md`
- Modify: `docs/SECURITY.md`
- Modify: `docs/AUDIT.md`

- [ ] **Step 1: Document the exact Modern matrix**

State Windows 7 SP1 through Windows 11 x86/x64, reject modern Server and ARM64, and explain that runtime capability checks decide SRP/AppLocker/Shell Launcher availability.

- [ ] **Step 2: Run a non-mutating frozen smoke test**

Run the executable with `--help` and `plan` only. Expected: Russian output, no registry changes, no new operator shell.

- [ ] **Step 3: Run an operator-account test only after backup**

Use the existing `test` account, capture baseline shell/policies/services/startup, run dry-run, apply, launch, watchdog/minimize/unlock checks, Restore, and `recover-desktop`. Verify the `impal` shell remains unset in HKCU and HKLM shell remains `explorer.exe`.

- [ ] **Step 4: Run final automated verification**

```powershell
.\.venv\Scripts\python.exe -m unittest discover tests -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add docs/INSTALL.md docs/TESTING.md docs/SECURITY.md docs/AUDIT.md
git commit -m "docs: define modern Windows support"
```

