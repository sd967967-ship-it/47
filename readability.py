"""
47 readability — human-style replies for display and speech text.

The brain often answers in markdown (tables, **bold**, headers). The
dashboard shows plain text, so raw markdown reads badly. style_reply()
keeps the words and structure but drops the markup: short paragraphs,
no tables-as-pipes, no symbol noise. One seam: ask_brain styles every
brain reply before logging, pushing, or speaking it.
"""
import re


def style_reply(text: str) -> str:
    """Paragraph-style plain text for humans. Idempotent-ish and safe."""
    if not text:
        return text
    t = text
    t = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"^#{1,6}\s*", "", t, flags=re.M)
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"__(.+?)__", r"\1", t)
    t = t.replace("`", "")
    t = re.sub(r"^\s*[-*_]{3,}\s*$", "", t, flags=re.M)
    t = re.sub(r"^\s*\|?[\s:\-|]+\|?\s*$", "", t, flags=re.M)
    t = re.sub(r"^\s*\|\s?", "", t, flags=re.M)
    t = re.sub(r"\s?\|\s?", ", ", t)
    t = re.sub(r"^\s*(?:[-*]|\d+[.)])\s+", "- ", t, flags=re.M)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()
