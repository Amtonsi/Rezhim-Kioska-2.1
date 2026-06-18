# -*- coding: utf-8 -*-

import io
import json
import os


try:
    text_type = unicode
    string_types = (basestring,)
except NameError:
    text_type = str
    string_types = (str,)


def read_json(path):
    with io.open(path, "r", encoding="utf-8-sig") as stream:
        return json.load(stream)


def write_json(path, value):
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)

    temporary = path + ".tmp"
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
    with io.open(temporary, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(text_type(text))
        stream.write(u"\n")

    if os.path.exists(path):
        os.remove(path)
    os.rename(temporary, path)
