# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class LayoutTransform(object):
    def __init__(self, design_width, design_height, actual_width, actual_height):
        values = (design_width, design_height, actual_width, actual_height)
        if any(float(value) <= 0 for value in values):
            raise ValueError("layout dimensions must be positive")
        self.design_width = float(design_width)
        self.design_height = float(design_height)
        self.actual_width = float(actual_width)
        self.actual_height = float(actual_height)
        self.scale = min(
            self.actual_width / self.design_width,
            self.actual_height / self.design_height,
        )
        self.scale_x = self.scale
        self.scale_y = self.scale
        self.offset_x = (self.actual_width - self.design_width * self.scale) / 2.0
        self.offset_y = (self.actual_height - self.design_height * self.scale) / 2.0

    def point(self, x, y):
        return (
            self.offset_x + float(x) * self.scale,
            self.offset_y + float(y) * self.scale,
        )

    def rectangle(self, left, top, right, bottom):
        x1, y1 = self.point(left, top)
        x2, y2 = self.point(right, bottom)
        return x1, y1, x2, y2

    def font_size(self, logical_size):
        return max(1, int(round(float(logical_size) * self.scale)))

