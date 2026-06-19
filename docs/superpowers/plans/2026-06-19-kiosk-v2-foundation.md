# Kiosk V2 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish versioned V2 contracts and independent Modern/Legacy state machines that preserve the approved security and UI behavior before any Win32 implementation is written.

**Architecture:** Shared behavior is data-only JSON under `v2/contracts`; Modern and Legacy each implement their own parser and state machine without importing one another or V1. Tests execute the same behavior cases against both implementations and assert that Explorer/keyboard protection remains active until authentication succeeds.

**Tech Stack:** JSON Schema draft-07, Python 3.8-compatible unittest, Python 2.7-compatible unittest, UTF-8 JSON, no third-party runtime dependencies.

---

## File structure

- Create `v2/contracts/kiosk-config-v2.schema.json`: configuration schema without credentials.
- Create `v2/contracts/backup-v2.schema.json`: versioned backup metadata contract.
- Create `v2/contracts/ui-layout-v2.json`: exact brand and logical design metrics.
- Create `v2/contracts/behavior-cases.json`: state transitions and required effects.
- Create `v2/contracts/README.md`: contract ownership and compatibility rules.
- Create `v2/modern/kiosk_v2_modern/domain/state_machine.py`: Python 3 Modern implementation.
- Create `v2/legacy/kiosk_v2_legacy/domain/state_machine.py`: Python 2.7 Legacy implementation.
- Create package `__init__.py` files under both runtimes.
- Create `v2/tests/contracts/test_contract_documents.py`: contract validation.
- Create `v2/tests/modern/test_state_machine.py`: Modern transition tests.
- Create `v2/tests/legacy/test_state_machine.py`: Python 2.7-compatible Legacy tests.
- Create `v2/tests/test_behavior_parity.py`: both runtimes execute every shared case identically.

### Task 1: Lock the V2 JSON contracts

**Files:**
- Create: `v2/contracts/kiosk-config-v2.schema.json`
- Create: `v2/contracts/backup-v2.schema.json`
- Create: `v2/contracts/ui-layout-v2.json`
- Create: `v2/contracts/behavior-cases.json`
- Create: `v2/contracts/README.md`
- Create: `v2/tests/contracts/__init__.py`
- Create: `v2/tests/contracts/test_contract_documents.py`

- [ ] **Step 1: Write the failing contract tests**

Create `v2/tests/contracts/test_contract_documents.py`:

```python
# -*- coding: utf-8 -*-
import json
import os
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONTRACTS = os.path.join(ROOT, "contracts")


def load(name):
    with open(os.path.join(CONTRACTS, name), "r", encoding="utf-8") as stream:
        return json.load(stream)


class ContractDocumentTests(unittest.TestCase):
    def test_config_schema_is_version_two_and_contains_no_credentials(self):
        schema = load("kiosk-config-v2.schema.json")
        text = json.dumps(schema, ensure_ascii=False).lower()

        self.assertEqual(2, schema["properties"]["schemaVersion"]["const"])
        self.assertEqual(
            ["schemaVersion", "operatorUser", "allowedApplication", "kiosk", "logging"],
            schema["required"],
        )
        for forbidden in ("password", "credential", "token", "secret"):
            self.assertNotIn(forbidden, text)

    def test_backup_schema_binds_build_operator_and_original_shell(self):
        schema = load("backup-v2.schema.json")
        required = schema["required"]

        for name in (
            "schemaVersion",
            "buildFamily",
            "operatorSid",
            "operatorUser",
            "originalShell",
            "registryValues",
            "fileAcls",
            "configBackup",
            "integritySha256",
        ):
            self.assertIn(name, required)

    def test_ui_contract_preserves_exact_brand_and_design_surface(self):
        ui = load("ui-layout-v2.json")

        self.assertEqual({"width": 1440, "height": 900}, ui["designSurface"])
        self.assertEqual("РК", ui["brand"]["logoText"])
        self.assertEqual("Режим киоска", ui["brand"]["title"])
        self.assertEqual("2026", ui["brand"]["year"])
        self.assertEqual(
            "разработал: Абдрахманов Амаль Даулетович",
            ui["brand"]["developer"],
        )

    def test_behavior_contract_keeps_guards_active_in_admin_dialog(self):
        behavior = load("behavior-cases.json")
        unlock = next(
            item
            for item in behavior["transitions"]
            if item["from"] == "OPERATOR" and item["event"] == "unlock_requested"
        )

        self.assertEqual("ADMIN_DIALOG", unlock["to"])
        self.assertIn("show_admin_dialog", unlock["effects"])
        self.assertNotIn("stop_keyboard_guard", unlock["effects"])
        self.assertNotIn("stop_desktop_isolation", unlock["effects"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
& 'C:\Users\impal\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m unittest discover -s v2/tests/contracts -v
```

Expected: four errors or failures because the V2 contract files do not exist.

- [ ] **Step 3: Create the configuration schema**

Create `v2/contracts/kiosk-config-v2.schema.json` with these exact top-level rules:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://local.invalid/kiosk-config-v2.schema.json",
  "title": "Kiosk V2 configuration",
  "type": "object",
  "additionalProperties": false,
  "required": ["schemaVersion", "operatorUser", "allowedApplication", "kiosk", "logging"],
  "properties": {
    "schemaVersion": {"const": 2},
    "operatorUser": {"type": "string", "minLength": 1},
    "allowedApplication": {
      "type": "object",
      "additionalProperties": false,
      "required": ["path", "arguments", "workingDirectory", "restartOnExit", "singleInstance", "bringToFront", "startMaximized", "restoreIfMinimized", "restartDelayMs"],
      "properties": {
        "path": {"type": "string", "minLength": 1},
        "arguments": {"type": "string"},
        "workingDirectory": {"type": "string"},
        "restartOnExit": {"type": "boolean"},
        "singleInstance": {"type": "boolean"},
        "bringToFront": {"type": "boolean"},
        "startMaximized": {"type": "boolean"},
        "restoreIfMinimized": {"type": "boolean"},
        "restartDelayMs": {"type": "integer", "minimum": 250, "maximum": 60000}
      }
    },
    "kiosk": {
      "type": "object",
      "additionalProperties": false,
      "required": ["allowWinL", "adminSessionTimeoutSeconds", "explorerGuardIntervalMs", "keyboardGuardRequired"],
      "properties": {
        "allowWinL": {"const": true},
        "adminSessionTimeoutSeconds": {"type": "integer", "minimum": 30, "maximum": 3600},
        "explorerGuardIntervalMs": {"type": "integer", "minimum": 100, "maximum": 5000},
        "keyboardGuardRequired": {"const": true}
      }
    },
    "logging": {
      "type": "object",
      "additionalProperties": false,
      "required": ["logDirectory", "level", "maxBytes", "backupCount"],
      "properties": {
        "logDirectory": {"type": "string", "minLength": 1},
        "level": {"enum": ["Debug", "Info", "Warning", "Error"]},
        "maxBytes": {"type": "integer", "minimum": 65536},
        "backupCount": {"type": "integer", "minimum": 1, "maximum": 20}
      }
    }
  }
}
```

- [ ] **Step 4: Create backup, UI, and behavior contracts**

Create `backup-v2.schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://local.invalid/backup-v2.schema.json",
  "title": "Kiosk V2 backup metadata",
  "type": "object",
  "additionalProperties": false,
  "required": ["schemaVersion", "buildFamily", "operatorSid", "operatorUser", "originalShell", "registryValues", "fileAcls", "configBackup", "integritySha256"],
  "properties": {
    "schemaVersion": {"const": 2},
    "buildFamily": {"enum": ["modern", "legacy"]},
    "operatorSid": {"type": "string", "minLength": 1},
    "operatorUser": {"type": "string", "minLength": 1},
    "originalShell": {"type": "string"},
    "registryValues": {"type": "array", "items": {"type": "object"}},
    "fileAcls": {"type": "array", "items": {"type": "object"}},
    "configBackup": {"type": "object"},
    "integritySha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}
  }
}
```

Create `ui-layout-v2.json`:

```json
{
  "schemaVersion": 2,
  "designSurface": {"width": 1440, "height": 900},
  "brand": {
    "logoText": "РК",
    "title": "Режим киоска",
    "year": "2026",
    "developer": "разработал: Абдрахманов Амаль Даулетович"
  },
  "screens": ["operator", "adminDialog", "adminSession"],
  "requiredActions": ["unlock", "restoreApplication", "unlockDesktop", "toggleSupervision", "returnToKiosk", "changeApplication"]
}
```

Create `behavior-cases.json`:

```json
{
  "schemaVersion": 1,
  "initialState": "STARTING",
  "transitions": [
    {"from": "STARTING", "event": "boot_completed", "to": "OPERATOR", "effects": ["start_desktop_isolation", "start_keyboard_guard", "start_supervisor", "show_operator_ui"]},
    {"from": "OPERATOR", "event": "unlock_requested", "to": "ADMIN_DIALOG", "effects": ["show_admin_dialog"]},
    {"from": "ADMIN_DIALOG", "event": "auth_cancelled", "to": "OPERATOR", "effects": ["show_operator_ui"]},
    {"from": "ADMIN_DIALOG", "event": "auth_failed", "to": "OPERATOR", "effects": ["show_auth_error", "show_operator_ui"]},
    {"from": "ADMIN_DIALOG", "event": "auth_succeeded", "to": "ADMIN_SESSION", "effects": ["stop_keyboard_guard", "stop_desktop_isolation", "show_admin_session"]},
    {"from": "ADMIN_SESSION", "event": "return_to_kiosk", "to": "OPERATOR", "effects": ["start_desktop_isolation", "start_keyboard_guard", "show_operator_ui"]},
    {"from": "ADMIN_SESSION", "event": "restore_requested", "to": "RESTORING", "effects": ["stop_keyboard_guard", "stop_desktop_isolation", "run_restore"]},
    {"from": "RESTORING", "event": "restore_completed", "to": "STOPPED", "effects": ["show_restore_result"]}
  ]
}
```

Create `v2/contracts/README.md` with this contract:

```markdown
# Kiosk V2 contracts

These versioned JSON documents are the only artifacts shared by Modern and Legacy.
They contain no executable code, credentials, tokens, machine-specific paths, or
imports from V1. A contract change requires a schema-version decision and parity
tests under both Python runtimes.
```

- [ ] **Step 5: Run contract tests and verify GREEN**

Run the Step 2 command.

Expected: `Ran 4 tests` and `OK`.

- [ ] **Step 6: Commit contracts**

```powershell
git add v2/contracts v2/tests/contracts
git commit -m "test: define kiosk v2 behavior contracts"
```

### Task 2: Implement the independent Modern state machine

**Files:**
- Create: `v2/modern/kiosk_v2_modern/__init__.py`
- Create: `v2/modern/kiosk_v2_modern/domain/__init__.py`
- Create: `v2/modern/kiosk_v2_modern/domain/state_machine.py`
- Create: `v2/tests/modern/__init__.py`
- Create: `v2/tests/modern/test_state_machine.py`

- [ ] **Step 1: Write the failing Modern tests**

Create `v2/tests/modern/test_state_machine.py`:

```python
# -*- coding: utf-8 -*-
import json
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))

from kiosk_v2_modern.domain.state_machine import InvalidTransition, StateMachine


def behavior():
    with open(os.path.join(V2_ROOT, "contracts", "behavior-cases.json"), "r", encoding="utf-8") as stream:
        return json.load(stream)


class ModernStateMachineTests(unittest.TestCase):
    def test_walks_secure_unlock_flow(self):
        machine = StateMachine(behavior())

        boot = machine.dispatch("boot_completed")
        request = machine.dispatch("unlock_requested")
        failure = machine.dispatch("auth_failed")

        self.assertEqual("OPERATOR", boot.to_state)
        self.assertEqual("ADMIN_DIALOG", request.to_state)
        self.assertNotIn("stop_keyboard_guard", request.effects)
        self.assertNotIn("stop_desktop_isolation", request.effects)
        self.assertEqual("OPERATOR", failure.to_state)

    def test_stops_guards_only_after_authentication_success(self):
        machine = StateMachine(behavior())
        machine.dispatch("boot_completed")
        machine.dispatch("unlock_requested")

        result = machine.dispatch("auth_succeeded")

        self.assertEqual("ADMIN_SESSION", result.to_state)
        self.assertIn("stop_keyboard_guard", result.effects)
        self.assertIn("stop_desktop_isolation", result.effects)

    def test_rejects_undefined_transition_without_changing_state(self):
        machine = StateMachine(behavior())

        with self.assertRaises(InvalidTransition):
            machine.dispatch("auth_succeeded")

        self.assertEqual("STARTING", machine.state)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify RED**

```powershell
& 'C:\Users\impal\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m unittest discover -s v2/tests/modern -v
```

Expected: import error because `kiosk_v2_modern` does not exist.

- [ ] **Step 3: Implement the Modern state machine**

Create `state_machine.py`:

```python
# -*- coding: utf-8 -*-


class InvalidTransition(ValueError):
    pass


class TransitionResult(object):
    def __init__(self, from_state, event, to_state, effects):
        self.from_state = from_state
        self.event = event
        self.to_state = to_state
        self.effects = tuple(effects)


class StateMachine(object):
    def __init__(self, contract):
        self.state = contract["initialState"]
        self._transitions = {}
        for item in contract["transitions"]:
            key = (item["from"], item["event"])
            if key in self._transitions:
                raise ValueError("Duplicate transition: {0}/{1}".format(*key))
            self._transitions[key] = item

    def dispatch(self, event):
        key = (self.state, event)
        item = self._transitions.get(key)
        if item is None:
            raise InvalidTransition("Invalid transition: {0}/{1}".format(*key))
        previous = self.state
        self.state = item["to"]
        return TransitionResult(previous, event, self.state, item["effects"])
```

Add empty package `__init__.py` files.

- [ ] **Step 4: Run tests and verify GREEN**

Run the Step 2 command.

Expected: `Ran 3 tests` and `OK`.

- [ ] **Step 5: Commit Modern foundation**

```powershell
git add v2/modern v2/tests/modern
git commit -m "feat: add kiosk v2 Modern state machine"
```

### Task 3: Implement the independent Python 2.7 Legacy state machine

**Files:**
- Create: `v2/legacy/kiosk_v2_legacy/__init__.py`
- Create: `v2/legacy/kiosk_v2_legacy/domain/__init__.py`
- Create: `v2/legacy/kiosk_v2_legacy/domain/state_machine.py`
- Create: `v2/tests/legacy/__init__.py`
- Create: `v2/tests/legacy/test_state_machine.py`

- [ ] **Step 1: Write the failing Python 2.7 test**

Create `v2/tests/legacy/test_state_machine.py` using `io.open(..., encoding="utf-8")`,
`unittest`, and no annotations/f-strings. It contains the same three assertions as
the Modern test and imports only `kiosk_v2_legacy.domain.state_machine`.

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import io
import json
import os
import sys
import unittest

V2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(V2_ROOT, "legacy"))

from kiosk_v2_legacy.domain.state_machine import InvalidTransition, StateMachine


def behavior():
    with io.open(os.path.join(V2_ROOT, "contracts", "behavior-cases.json"), "r", encoding="utf-8") as stream:
        return json.load(stream)


class LegacyStateMachineTests(unittest.TestCase):
    def test_secure_unlock_and_return_flow(self):
        machine = StateMachine(behavior())
        machine.dispatch("boot_completed")
        request = machine.dispatch("unlock_requested")
        self.assertEqual("ADMIN_DIALOG", request.to_state)
        self.assertNotIn("stop_keyboard_guard", request.effects)
        success = machine.dispatch("auth_succeeded")
        self.assertEqual("ADMIN_SESSION", success.to_state)
        self.assertIn("stop_desktop_isolation", success.effects)
        returned = machine.dispatch("return_to_kiosk")
        self.assertEqual("OPERATOR", returned.to_state)
        self.assertIn("start_keyboard_guard", returned.effects)

    def test_invalid_event_preserves_state(self):
        machine = StateMachine(behavior())
        with self.assertRaises(InvalidTransition):
            machine.dispatch("restore_completed")
        self.assertEqual("STARTING", machine.state)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify RED**

```powershell
& 'C:\Users\impal\AppData\Local\Python27-x86-portable\python.exe' -m unittest discover -s v2/tests/legacy -v
```

Expected: import error because `kiosk_v2_legacy` does not exist.

- [ ] **Step 3: Implement the Legacy state machine independently**

Create a Python 2.7-compatible copy of the public API from Task 2. Use explicit
`object` bases, `.format()`, and tuple effects. Do not import anything from
`v2/modern`, `python_kiosk`, or `legacy_kiosk`.

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class InvalidTransition(ValueError):
    pass


class TransitionResult(object):
    def __init__(self, from_state, event, to_state, effects):
        self.from_state = from_state
        self.event = event
        self.to_state = to_state
        self.effects = tuple(effects)


class StateMachine(object):
    def __init__(self, contract):
        self.state = contract["initialState"]
        self._transitions = {}
        for item in contract["transitions"]:
            key = (item["from"], item["event"])
            if key in self._transitions:
                raise ValueError("Duplicate transition: {0}/{1}".format(*key))
            self._transitions[key] = item

    def dispatch(self, event):
        key = (self.state, event)
        item = self._transitions.get(key)
        if item is None:
            raise InvalidTransition("Invalid transition: {0}/{1}".format(*key))
        previous = self.state
        self.state = item["to"]
        return TransitionResult(previous, event, self.state, item["effects"])
```

- [ ] **Step 4: Run tests and verify GREEN**

Run the Step 2 command.

Expected: `Ran 2 tests` and `OK`.

- [ ] **Step 5: Commit Legacy foundation**

```powershell
git add v2/legacy v2/tests/legacy
git commit -m "feat: add kiosk v2 Legacy state machine"
```

### Task 4: Prove cross-build behavior parity and isolation

**Files:**
- Create: `v2/tests/__init__.py`
- Create: `v2/tests/test_behavior_parity.py`

- [ ] **Step 1: Write the parity test**

```python
# -*- coding: utf-8 -*-
import importlib
import json
import os
import sys
import unittest

V2_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))
sys.path.insert(0, os.path.join(V2_ROOT, "legacy"))


class BehaviorParityTests(unittest.TestCase):
    def test_every_contract_transition_matches_both_runtimes(self):
        with open(os.path.join(V2_ROOT, "contracts", "behavior-cases.json"), "r", encoding="utf-8") as stream:
            contract = json.load(stream)
        modern = importlib.import_module("kiosk_v2_modern.domain.state_machine")
        legacy = importlib.import_module("kiosk_v2_legacy.domain.state_machine")

        for item in contract["transitions"]:
            for module in (modern, legacy):
                machine = module.StateMachine(contract)
                machine.state = item["from"]
                result = machine.dispatch(item["event"])
                self.assertEqual(item["to"], result.to_state)
                self.assertEqual(tuple(item["effects"]), result.effects)

    def test_runtime_sources_do_not_import_v1_or_each_other(self):
        roots = (
            os.path.join(V2_ROOT, "modern"),
            os.path.join(V2_ROOT, "legacy"),
        )
        forbidden = ("python_kiosk", "legacy_kiosk", "kiosk_v2_modern", "kiosk_v2_legacy")
        for root in roots:
            own = "kiosk_v2_modern" if root.endswith("modern") else "kiosk_v2_legacy"
            for directory, _, files in os.walk(root):
                for name in files:
                    if not name.endswith(".py"):
                        continue
                    with open(os.path.join(directory, name), "r", encoding="utf-8") as stream:
                        text = stream.read()
                    for module_name in forbidden:
                        if module_name != own:
                            self.assertNotIn("import " + module_name, text)
                            self.assertNotIn("from " + module_name, text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run parity test**

```powershell
& 'C:\Users\impal\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m unittest v2.tests.test_behavior_parity -v
```

Expected: `Ran 2 tests` and `OK`.

- [ ] **Step 3: Run all Phase 1 suites**

```powershell
& 'C:\Users\impal\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m unittest discover -s v2/tests -v
& 'C:\Users\impal\AppData\Local\Python27-x86-portable\python.exe' -m unittest discover -s v2/tests/legacy -v
```

Expected: all V2 tests pass under Python 3; Legacy-specific tests pass under Python 2.7.

- [ ] **Step 4: Compile-check both new source trees**

```powershell
& 'C:\Users\impal\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m compileall -q v2/modern
& 'C:\Users\impal\AppData\Local\Python27-x86-portable\python.exe' -m compileall -q v2/legacy
```

Expected: exit 0 for both commands.

- [ ] **Step 5: Commit Phase 1 acceptance**

```powershell
git add v2/tests/__init__.py v2/tests/test_behavior_parity.py docs/superpowers/plans/2026-06-19-kiosk-v2-roadmap.md docs/superpowers/plans/2026-06-19-kiosk-v2-foundation.md
git commit -m "test: prove kiosk v2 cross-build state parity"
```

The worktree must be clean before writing the Phase 2 Modern runtime plan.
