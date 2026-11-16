# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import importlib
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))
sys.path.insert(0, os.path.join(V2_ROOT, "legacy"))

from kiosk_v2_modern.ui.scene import build_dialog_spec as modern_dialog
from kiosk_v2_modern.ui.scene import build_operator_scene as modern_scene
from kiosk_v2_legacy.ui.scene import build_dialog_spec as legacy_dialog
from kiosk_v2_legacy.ui.scene import build_operator_scene as legacy_scene


SCENE_BUILDERS = (modern_scene, legacy_scene)
DIALOG_BUILDERS = (modern_dialog, legacy_dialog)


def by_name(scene):
    return dict((item["name"], item) for item in scene)


def all_text(scene):
    return "\n".join(item.get("text", "") for item in scene)


class OperatorSceneTests(unittest.TestCase):
    def test_runtime_states_reach_the_operator_scene(self):
        cases = [
            ("start_failed", "Ошибка запуска", "OSError"),
            ("crash_loop", "Частые сбои", "4"),
            ("conflict", "Конфликт", "123, 456"),
            ("waiting_restart", "Перезапуск", "следующей попытки"),
            ("waiting_handoff", "Ожидание", "основной процесс"),
            ("stopped", "Без надзора", "наблюдение"),
        ]
        class App(object):
            enabled = True
        for family, build in zip(("modern", "legacy"), SCENE_BUILDERS):
            package = "kiosk_v2_" + family
            session_type = importlib.import_module(package + ".app.session").LauncherSession
            result_type = importlib.import_module(package + ".app.application_runtime").ApplicationRuntimeResult
            app = App()
            session = session_type(None, None, app, None, None, None, None, None, None, 60)
            for status, label, detail in cases:
                app.latest_result = result_type(status, error_code="OSError", conflict_pids=(123, 456), failure_count=4)
                items = by_name(build(**session.model()))
                self.assertEqual(label, items["application_status"]["text"])
                self.assertIn(detail, items["application_hint"]["text"])
                self.assertNotIn("restore_application_button", items)
            app.latest_result = result_type("adopted", pid=123, window_status="minimized")
            self.assertIn("restore_application_button", by_name(build(**session.model())))

    def test_operator_scene_has_exact_brand_status_and_unlock_action(self):
        for build in SCENE_BUILDERS:
            scene = build(r"C:\Windows\System32\notepad.exe")
            items = by_name(scene)
            self.assertEqual("РК", items["header_mark_text"]["text"])
            self.assertEqual("Режим киоска", items["header_title"]["text"])
            self.assertEqual("2026", items["header_year_text"]["text"])
            self.assertEqual("Работает", items["application_status"]["text"])
            self.assertEqual("unlock", items["unlock_button"]["action"])
            self.assertEqual(
                "разработал: Абдрахманов Амаль Даулетович",
                items["developer_credit"]["text"],
            )

    def test_minimized_notice_and_restore_action_only_exist_when_minimized(self):
        for build in SCENE_BUILDERS:
            normal = by_name(build(r"C:\Tools\Allowed.exe", app_status="running"))
            minimized = by_name(
                build(r"C:\Tools\Allowed.exe", app_status="minimized")
            )
            self.assertNotIn("minimized_alert", normal)
            self.assertNotIn("restore_application_button", normal)
            self.assertEqual(
                "Приложение свернуто",
                minimized["minimized_alert"]["text"],
            )
            self.assertEqual(
                "restoreApplication",
                minimized["restore_application_button"]["action"],
            )

    def test_admin_session_exposes_only_required_controller_actions(self):
        expected = {
            "unlockDesktop",
            "toggleSupervision",
            "returnToKiosk",
            "changeApplication",
            "restore",
        }
        for build in SCENE_BUILDERS:
            scene = build(
                r"C:\Tools\Allowed.exe",
                admin_session_active=True,
                supervision_enabled=True,
            )
            actions = set(
                item["action"] for item in scene if item.get("action") is not None
            )
            self.assertEqual(expected, actions - {"unlock"})
            self.assertEqual(
                "Остановить надзор",
                by_name(scene)["toggle_supervision_button"]["text"],
            )

    def test_unconfigured_scene_guides_admin_without_exposing_picker(self):
        for build in SCENE_BUILDERS:
            scene = build(
                r"F:\Missing\Telegram.exe",
                application_configured=False,
            )
            items = by_name(scene)
            self.assertEqual("Не выбрано", items["application_name"]["text"])
            self.assertEqual("Не настроено", items["application_status"]["text"])
            self.assertEqual(
                "Надзор: ожидает настройки",
                items["supervision_status"]["text"],
            )
            self.assertIn(
                "Разблокируйте режим и выберите разрешенное приложение.",
                all_text(scene),
            )
            actions = set(
                item["action"] for item in scene if item.get("action") is not None
            )
            self.assertEqual({"unlock"}, actions)

    def test_unconfigured_admin_session_exposes_selection_without_supervision(self):
        expected = {
            "unlockDesktop",
            "returnToKiosk",
            "changeApplication",
            "restore",
        }
        for build in SCENE_BUILDERS:
            scene = build(
                r"F:\Missing\Telegram.exe",
                admin_session_active=True,
                application_configured=False,
            )
            actions = set(
                item["action"] for item in scene if item.get("action") is not None
            )
            self.assertEqual(expected, actions)
            self.assertNotIn("toggle_supervision_button", by_name(scene))

    def test_degraded_isolation_is_explicit_and_does_not_claim_full_protection(self):
        for build in SCENE_BUILDERS:
            normal_text = all_text(build(r"C:\Tools\Allowed.exe"))
            degraded_text = all_text(
                build(r"C:\Tools\Allowed.exe", isolation_degraded=True)
            )
            self.assertNotIn("Защита ограничена", normal_text)
            self.assertIn("Защита ограничена", degraded_text)
            self.assertIn("Киоск обнаружил Explorer", degraded_text)

    def test_all_scene_rectangles_stay_inside_design_surface(self):
        for build in SCENE_BUILDERS:
            for scene in (
                build(r"C:\Tools\Allowed.exe"),
                build(r"C:\Tools\Allowed.exe", app_status="minimized"),
                build(r"C:\Tools\Allowed.exe", admin_session_active=True),
            ):
                for item in scene:
                    x, y, width, height = item["rect"]
                    self.assertGreaterEqual(x, 0)
                    self.assertGreaterEqual(y, 0)
                    self.assertLessEqual(x + width, 1440)
                    self.assertLessEqual(y + height, 900)

    def test_actions_are_bound_once(self):
        for build in SCENE_BUILDERS:
            scene = build(
                r"C:\Tools\Allowed.exe",
                app_status="minimized",
                admin_session_active=True,
            )
            action_items = [item for item in scene if item.get("action")]
            names = [item["name"] for item in action_items]
            self.assertEqual(len(names), len(set(names)))


class AdminDialogSpecTests(unittest.TestCase):
    def test_dialog_contains_only_local_username_and_masked_password(self):
        for build in DIALOG_BUILDERS:
            spec = build()
            fields = dict((item["name"], item) for item in spec["fields"])
            self.assertEqual({"username", "password"}, set(fields))
            self.assertEqual("", fields["username"].get("show", ""))
            self.assertEqual("*", fields["password"]["show"])
            combined = " ".join(
                [spec["title"], spec["message"]]
                + [item["label"] for item in spec["fields"]]
            ).lower()
            self.assertNotIn("домен", combined)
            self.assertNotIn("компьютер", combined)
            self.assertNotIn("ctrl", combined)
            self.assertNotIn("alt", combined)
            self.assertTrue(spec["modal"])
            self.assertTrue(spec["keepKeyboardGuard"])


if __name__ == "__main__":
    unittest.main()
