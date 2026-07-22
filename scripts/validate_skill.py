#!/usr/bin/env python3
"""Dependency-free structural validation for the bundled Agent Skill."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill", type=Path)
    args = parser.parse_args()
    skill = args.skill.resolve(strict=False)
    errors: list[str] = []

    entry = skill / "SKILL.md"
    if not entry.is_file():
        errors.append("S001 missing SKILL.md")
    else:
        text = entry.read_text(encoding="utf-8")
        lines = text.split("\n")
        if len(lines) > 500:
            errors.append("S002 SKILL.md exceeds 500 lines")
        frontmatter = _frontmatter(text)
        name = frontmatter.get("name", "")
        description = frontmatter.get("description", "")
        if not NAME_PATTERN.fullmatch(name):
            errors.append("S003 invalid skill name")
        if name != skill.name:
            errors.append("S004 skill name does not match parent directory")
        if not description.strip():
            errors.append("S005 missing description")
        if _contains_absolute_user_path(text):
            errors.append("S006 absolute user path in SKILL.md")
        for reference in re.findall(r"\]\((references/[^)]+)\)", text):
            if not (skill / reference).is_file():
                errors.append(f"S007 missing reference: {reference}")

    metadata = skill / "agents" / "openai.yaml"
    if not metadata.is_file():
        errors.append("S008 missing agents/openai.yaml")
    else:
        text = metadata.read_text(encoding="utf-8")
        if f"${skill.name}" not in text:
            errors.append("S009 default prompt does not mention the skill")

    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"skill validation: passed ({skill.name})")
    return 0


def _frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    result: dict[str, str] = {}
    for line in text[4:end].split("\n"):
        key, separator, value = line.partition(":")
        if separator:
            result[key.strip()] = value.strip()
    return result


def _contains_absolute_user_path(text: str) -> bool:
    patterns = (
        re.compile("/" + "Users" + r"/[^/\s]+/"),
        re.compile("/" + "home" + r"/[^/\s]+/"),
        re.compile(r"[A-Za-z]:\\" + "Users" + r"\\"),
    )
    return any(pattern.search(text) for pattern in patterns)


if __name__ == "__main__":
    raise SystemExit(main())
