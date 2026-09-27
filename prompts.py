"""
47 structured prompt templates — research reports and bug-fix writeups.

Template files in prompts/*.yaml are vendored from bertrandmbanwi/Jarvis
templates/prompts/ (MIT licensed, see THIRD_PARTY_NOTICES.md). This loader
is 47's own code: it picks sections relevant to a chat answer (not the full
project-planning scaffold, which would bloat every turn).
"""
import re
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_cache = {}


def _load(name: str) -> str:
    if name in _cache:
        return _cache[name]
    text = (_PROMPTS_DIR / f"{name}.yaml").read_text(encoding="utf-8")
    # Keep section names + acceptance criteria; drop the YAML scaffolding.
    sections = re.findall(r"-\s*name:\s*(.+)\n\s*content:\s*\|(.*?)(?=\n\s*-\s*name:|\nacceptance_criteria:)",
                          text, re.DOTALL)
    criteria = re.findall(r"acceptance_criteria:\s*\n((?:\s*-\s*.+\n?)+)", text)
    out = "\n".join(f"## {s.strip()}\n{c.strip()}" for s, c in sections)
    if criteria:
        out += "\n## Must satisfy\n" + criteria[0]
    _cache[name] = out
    return out


def research_guide() -> str:
    """Compact research structure for 'research <topic>' answers."""
    try:
        return _load("research")
    except OSError:
        return "Structure: summary, findings, recommendations, sources."


def fix_guide() -> str:
    """Compact bug-fix structure for debugging writeups."""
    try:
        return _load("fix")
    except OSError:
        return "Structure: bug, expected vs actual, cause, fix, verification."
