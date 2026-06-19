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
        with open(
            os.path.join(V2_ROOT, "contracts", "behavior-cases.json"),
            "r",
            encoding="utf-8",
        ) as stream:
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
        forbidden = (
            "python_kiosk",
            "legacy_kiosk",
            "kiosk_v2_modern",
            "kiosk_v2_legacy",
        )
        for root in roots:
            own = "kiosk_v2_modern" if root.endswith("modern") else "kiosk_v2_legacy"
            for directory, _, files in os.walk(root):
                for name in files:
                    if not name.endswith(".py"):
                        continue
                    with open(
                        os.path.join(directory, name),
                        "r",
                        encoding="utf-8",
                    ) as stream:
                        text = stream.read()
                    for module_name in forbidden:
                        if module_name != own:
                            self.assertNotIn("import " + module_name, text)
                            self.assertNotIn("from " + module_name, text)


if __name__ == "__main__":
    unittest.main()
