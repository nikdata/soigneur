"""Sync Cursor rule files into CLAUDE.md for Claude Code compatibility.

Scans .cursor/rules/ for .mdc files, extracts their YAML frontmatter
description, and generates a references section in CLAUDE.md. Any
hand-written content above the auto-generated marker is preserved.

Usage:
    uv run python scripts/sync_claude_md.py

Works with any project — not Soigneur-specific.
"""

from __future__ import annotations

import re
from pathlib import Path

MARKER = "<!-- AUTO-GENERATED BELOW - DO NOT EDIT -->"
RULES_DIR = Path(".cursor/rules")
CLAUDE_MD = Path("CLAUDE.md")


def extract_description(path: Path) -> str | None:
    """Extract the description field from YAML frontmatter in an .mdc file.

    Reads the file, looks for YAML frontmatter delimited by '---' lines,
    and pulls out the description value. Returns None if no frontmatter
    or no description field is found.

    Args:
        path: Path to the .mdc file to read.

    Returns:
        The description string, or None if not found.
    """
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return None

    for line in match.group(1).splitlines():
        if line.strip().startswith("description:"):
            value = line.split(":", 1)[1].strip()
            return value.strip("\"'")

    return None


def get_header() -> str:
    """Read the existing hand-written header from CLAUDE.md.

    Everything above the auto-generated marker is considered the header.
    If CLAUDE.md doesn't exist or has no marker, returns an empty string
    so the user knows they need to add a header.

    Returns:
        The header content as a string, or empty string if not found.
    """
    if not CLAUDE_MD.exists():
        return ""

    text = CLAUDE_MD.read_text(encoding="utf-8")
    if MARKER in text:
        return text.split(MARKER)[0].rstrip("\n")

    # File exists but no marker — treat entire content as the header
    return text.rstrip("\n")


def build_references() -> str:
    """Scan .cursor/rules/ and build the auto-generated references section.

    Each .mdc file gets a line with its path and description. Files are
    sorted alphabetically for stable output.

    Returns:
        Formatted markdown string with file references.
    """
    if not RULES_DIR.exists():
        return "No .cursor/rules/ directory found.\n"

    files = sorted(RULES_DIR.glob("*.mdc"))
    if not files:
        return "No .mdc files found in .cursor/rules/.\n"

    lines = []
    for f in files:
        desc = extract_description(f) or "No description"
        lines.append(f"- **`{f}`** — {desc}")

    return "\n".join(lines)


def sync() -> None:
    """Generate or update CLAUDE.md with references to Cursor rule files.

    Preserves any hand-written content above the marker. Regenerates
    everything below it. Creates CLAUDE.md with a placeholder header
    if it doesn't exist yet.
    """
    header = get_header()

    if not header:
        print(
            "No header found in CLAUDE.md. Creating with placeholder.\n"
            "Edit the section above the marker with your project summary."
        )
        header = "# Project Name\n\nAdd your project summary here."

    references = build_references()

    content = (
        f"{header}\n\n"
        f"{MARKER}\n\n"
        f"## Project Rules\n\n"
        f"Read the referenced files before starting work.\n\n"
        f"{references}\n"
    )

    CLAUDE_MD.write_text(content, encoding="utf-8")
    print(f"Updated {CLAUDE_MD}")


if __name__ == "__main__":
    sync()
