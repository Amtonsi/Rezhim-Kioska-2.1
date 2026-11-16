# -*- coding: utf-8 -*-
import os
import sys
import unittest

tests = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, tests)
sys.path.insert(0, os.path.join(os.path.dirname(tests), "modern"))

from operator_safety_cases import OperatorSafetyCases


class OperatorSafetyTests(OperatorSafetyCases, unittest.TestCase):
    package = "kiosk_v2_modern"
