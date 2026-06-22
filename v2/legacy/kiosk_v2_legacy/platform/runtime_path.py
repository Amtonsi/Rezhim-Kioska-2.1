# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys


try:
    text_type = unicode
    binary_type = str
except NameError:
    text_type = str
    binary_type = bytes


def _unique_encodings(*encodings):
    result = []
    for encoding in encodings:
        if encoding and encoding not in result:
            result.append(encoding)
    return result


def _runtime_directory_matches(directory, required_children):
    try:
        if not os.path.isdir(directory):
            return False
        for child in required_children:
            if not os.path.exists(os.path.join(directory, child)):
                return False
        return True
    except (OSError, TypeError, UnicodeError):
        return False


def coerce_runtime_directory(directory, required_children=()):
    if isinstance(directory, text_type):
        return directory

    candidates = []
    if isinstance(directory, binary_type):
        for encoding in _unique_encodings(
            "mbcs",
            sys.getfilesystemencoding(),
            "utf-8",
        ):
            try:
                candidate = directory.decode(encoding)
            except (AttributeError, LookupError, UnicodeError):
                continue
            if candidate not in candidates:
                candidates.append(candidate)

    candidates.append(directory)
    for candidate in candidates:
        if _runtime_directory_matches(candidate, required_children):
            return candidate
    return candidates[0]
