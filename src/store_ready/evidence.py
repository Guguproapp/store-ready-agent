"""Sanitize generated quality evidence before it is tracked or shared."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

LOCAL_HOME = re.compile(r"(?:/Users/|/home/)[^/\s\"<]+")
WINDOWS_HOME = re.compile(r"[A-Za-z]:\\Users\\[^\\\s\"<]+")


def _sanitize(value: str) -> str:
    return WINDOWS_HOME.sub("[LOCAL_HOME]", LOCAL_HOME.sub("[LOCAL_HOME]", value))


def sanitize_junit(path: Path) -> None:
    """Normalize one JUnit file while retaining test and failure evidence."""

    tree = ET.parse(path)
    root = tree.getroot()
    for element in root.iter():
        element.attrib.pop("hostname", None)
        for key, value in tuple(element.attrib.items()):
            element.attrib[key] = _sanitize(value)
        if element.text:
            element.text = _sanitize(element.text)
        if element.tail:
            element.tail = _sanitize(element.tail)
    tree.write(path, encoding="utf-8", xml_declaration=True)
    sanitized = path.read_text(encoding="utf-8")
    forbidden = ("/Users/", "/home/", "\\Users\\", 'hostname="', ".local")
    if any(item in sanitized for item in forbidden):
        raise ValueError("JUNIT_LOCAL_IDENTITY_REMAINS")
