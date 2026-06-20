# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import io
import os
import sys
import unittest


V2_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(V2_ROOT, "modern"))
sys.path.insert(0, os.path.join(V2_ROOT, "legacy"))

from kiosk_v2_modern.ui.layout import LayoutTransform as ModernLayout
from kiosk_v2_legacy.ui.layout import LayoutTransform as LegacyLayout


class LayoutTests(unittest.TestCase):
    def test_uniform_scale_and_centering_match_in_both_builds(self):
        cases = (
            (800, 600),
            (1024, 768),
            (1366, 768),
            (1920, 1080),
        )
        for cls in (ModernLayout, LegacyLayout):
            for width, height in cases:
                layout = cls(1440, 900, width, height)
                expected = min(float(width) / 1440.0, float(height) / 900.0)
                self.assertAlmostEqual(expected, layout.scale)
                self.assertAlmostEqual((width - 1440 * expected) / 2.0, layout.offset_x)
                self.assertAlmostEqual((height - 900 * expected) / 2.0, layout.offset_y)
                self.assertAlmostEqual(expected, layout.scale_x)
                self.assertAlmostEqual(expected, layout.scale_y)

    def test_points_rectangles_and_fonts_use_the_same_scale(self):
        for cls in (ModernLayout, LegacyLayout):
            layout = cls(1440, 900, 1366, 768)
            point = layout.point(100, 50)
            rectangle = layout.rectangle(100, 50, 300, 150)
            self.assertEqual(point, rectangle[:2])
            self.assertAlmostEqual(200 * layout.scale, rectangle[2] - rectangle[0])
            self.assertAlmostEqual(100 * layout.scale, rectangle[3] - rectangle[1])
            self.assertEqual(max(1, int(round(24 * layout.scale))), layout.font_size(24))

    def test_brand_contract_contains_exact_russian_text(self):
        with io.open(
            os.path.join(V2_ROOT, "contracts", "ui-layout-v2.json"),
            "r",
            encoding="utf-8",
        ) as stream:
            brand = json.load(stream)["brand"]

        self.assertEqual([0x420, 0x41A], [ord(item) for item in brand["logoText"]])
        self.assertEqual("Режим киоска", brand["title"])
        self.assertEqual("2026", brand["year"])
        self.assertEqual(
            "разработал: Абдрахманов Амаль Даулетович",
            brand["developer"],
        )


if __name__ == "__main__":
    unittest.main()
