# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))
sys.path.insert(0, os.path.join(V2_ROOT, "legacy"))

from kiosk_v2_legacy.ui.scene import build_operator_scene as legacy_scene
from kiosk_v2_legacy.ui.tk_view import SceneRenderer as LegacyRenderer
from kiosk_v2_legacy.ui.tk_view import dialog_entry_options as legacy_options

if sys.version_info[0] >= 3:
    from kiosk_v2_modern.ui.scene import build_operator_scene as modern_scene
    from kiosk_v2_modern.ui.tk_view import SceneRenderer as ModernRenderer
    from kiosk_v2_modern.ui.tk_view import dialog_entry_options as modern_options

    RENDERERS = (
        (ModernRenderer, modern_scene),
        (LegacyRenderer, legacy_scene),
    )
    OPTION_BUILDERS = (modern_options, legacy_options)
else:
    RENDERERS = ((LegacyRenderer, legacy_scene),)
    OPTION_BUILDERS = (legacy_options,)


class FakeCanvas(object):
    def __init__(self):
        self.calls = []
        self.bindings = []

    def delete(self, tag):
        self.calls.append(("delete", tag))

    def create_rectangle(self, *coordinates, **options):
        self.calls.append(("rectangle", coordinates, options))
        return len(self.calls)

    def create_polygon(self, *coordinates, **options):
        self.calls.append(("polygon", coordinates, options))
        return len(self.calls)

    def create_text(self, *coordinates, **options):
        self.calls.append(("text", coordinates, options))
        return len(self.calls)

    def tag_bind(self, tag, event, callback):
        self.bindings.append((tag, event, callback))


class DeferredRoot(object):
    def __init__(self):
        self.callbacks = []

    def after(self, milliseconds, callback):
        self.callbacks.append((milliseconds, callback))


class TaggedCanvas(object):
    def __init__(self, tags):
        self.tags = tuple(tags)

    def gettags(self, item):
        return self.tags

    def find_withtag(self, tag):
        if tag == "current" and self.tags:
            return (1,)
        return ()


class RendererTests(unittest.TestCase):
    def test_desktop_exit_runs_after_canvas_mouse_binding_returns(self):
        class IdleRoot(object):
            def after_idle(self, callback, *args):
                self.pending = lambda: callback(*args)

        for renderer_class, _scene in RENDERERS:
            module = __import__(renderer_class.__module__, fromlist=["KioskCanvasView"])
            view = module.KioskCanvasView.__new__(module.KioskCanvasView)
            view.root = IdleRoot()
            calls = []
            view.action_handler = calls.append
            view._dispatch("unlockDesktop")
            self.assertEqual([], calls)
            view.root.pending()
            self.assertEqual(["unlockDesktop"], calls)

    def test_buttons_are_bound_once_and_emit_only_their_action(self):
        for renderer_class, build_scene in RENDERERS:
            canvas = FakeCanvas()
            actions = []
            renderer = renderer_class(canvas, actions.append)
            scene = build_scene(r"C:\Tools\Allowed.exe", app_status="minimized")
            renderer.render(scene, 1024, 768)
            renderer.render(scene, 1024, 768)

            tags = [item[0] for item in canvas.bindings]
            self.assertEqual(tags.count("action:unlock"), 1)
            self.assertEqual(tags.count("action:restoreApplication"), 1)
            unlock_callback = dict((tag, callback) for tag, _, callback in canvas.bindings)[
                "action:unlock"
            ]
            unlock_callback(object())
            self.assertEqual(["unlock"], actions)

    def test_renderer_uses_uniform_layout_for_geometry_and_font_pixels(self):
        for renderer_class, build_scene in RENDERERS:
            canvas = FakeCanvas()
            renderer = renderer_class(canvas, lambda _action: None)
            renderer.render(build_scene(r"C:\Tools\Allowed.exe"), 800, 600)
            text_calls = [call for call in canvas.calls if call[0] == "text"]
            self.assertTrue(text_calls)
            for _, coordinates, options in text_calls:
                self.assertGreaterEqual(coordinates[0], 0)
                self.assertGreaterEqual(coordinates[1], 0)
                self.assertLessEqual(coordinates[0], 800)
                self.assertLessEqual(coordinates[1], 600)
                self.assertLess(options["font"][1], 0)

    def test_dialog_entry_options_show_username_and_mask_password(self):
        for build_options in OPTION_BUILDERS:
            username = build_options(masked=False)
            password = build_options(masked=True)
            self.assertNotIn("show", username)
            self.assertEqual("*", password["show"])
            self.assertEqual("#f4f6f8", username["fg"])
            self.assertEqual("#f4f6f8", username["insertbackground"])

    def test_button_clicks_do_not_schedule_shell_foreground_interaction(self):
        for renderer_class, _build_scene in RENDERERS:
            module = __import__(renderer_class.__module__, fromlist=["KioskCanvasView"])
            root = DeferredRoot()
            calls = []
            view = module.KioskCanvasView.__new__(module.KioskCanvasView)
            view.root = root
            view.canvas = TaggedCanvas(("action:unlock",))
            view.shell_interaction = lambda: calls.append("shell")

            view._on_shell_click(None)

            self.assertEqual([], root.callbacks)
            self.assertEqual([], calls)

    def test_background_clicks_schedule_shell_foreground_interaction(self):
        for renderer_class, _build_scene in RENDERERS:
            module = __import__(renderer_class.__module__, fromlist=["KioskCanvasView"])
            root = DeferredRoot()
            calls = []
            view = module.KioskCanvasView.__new__(module.KioskCanvasView)
            view.root = root
            view.canvas = TaggedCanvas(("background",))
            view.shell_interaction = lambda: calls.append("shell")

            view._on_shell_click(None)

            self.assertEqual(1, len(root.callbacks))
            self.assertEqual(0, root.callbacks[0][0])
            root.callbacks[0][1]()
            self.assertEqual(["shell"], calls)


if __name__ == "__main__":
    unittest.main()
