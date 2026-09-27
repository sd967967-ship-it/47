"""
Decides whether a user's question is about a visualizable *object*
(building, tool, vehicle, map/ground path, electronics, nature/plant,
furniture, or generic thing) and, if so, what generic 3D scene to push to
the dashboard.

Honest limit, unchanged from before and still true: there's no offline
image-to-3D or 3D-asset-library pipeline in this free stack, so this can't
generate a photoreal or literally-accurate 3D model of anything you name.
What it does is recognize the *category* of object in your question and
hand the dashboard a labeled, parametric 3D representation of that
category — a quick spatial visual, not a literal replica.
Numeric/comparison questions still go to the existing bar/network charts.

FIX for "coverage is narrow / most things fall into a generic icosahedron
with no real connection to what was asked": added three more categories
(electronics, nature, furniture) covering common everyday-object
questions that previously all landed on the same fallback shape. This is
still a fixed keyword list, not real object recognition — "most objects
get a genuinely fitting shape" is a wider net, not a claim of completeness.
Anything not covered still correctly falls through to the generic shape
rather than guessing wrong.
"""

CATEGORY_KEYWORDS = {
    "building": ["building", "tower", "skyscraper", "house", "structure",
                 "architecture", "floor plan", "bridge", "stadium"],
    "tool": ["tool", "wrench", "hammer", "screwdriver", "drill", "pliers",
             "machine", "equipment"],
    "vehicle": ["car", "vehicle", "truck", "bike", "bicycle", "plane",
                "aircraft", "rocket", "ship", "boat", "drone", "train"],
    "map_path": ["map", "route", "path", "ground", "terrain", "trail",
                 "road", "directions", "navigate", "location"],
    "electronics": ["phone", "smartphone", "laptop", "computer", "monitor",
                     "screen", "tv", "television", "tablet", "gadget",
                     "device", "console", "camera", "speaker", "headphones"],
    "nature": ["tree", "plant", "flower", "leaf", "forest", "mountain",
               "river", "cloud", "sun", "moon", "planet", "animal"],
    "furniture": ["chair", "table", "desk", "sofa", "couch", "bed",
                   "shelf", "cabinet", "furniture"],
    "generic_object": ["object", "shape", "model", "diagram", "layout",
                        "look like", "looks like", "what does a"],
}

# Handled better by the existing bar/network chart renderers than by a 3D shape.
_GRAPH_KEYWORDS = ["compare", "comparison", "versus", " vs ", "trend",
                    "statistics", "stats", "how many", "numbers"]


import re


def _word_hit(text: str, keyword: str) -> bool:
    # Word-boundary match so "card" doesn't fire "car", "implant" doesn't
    # fire "plant", "sunscreen" doesn't fire "screen". Multi-word keywords
    # fall back to substring (boundaries around phrases are unreliable).
    kw = keyword.strip().lower()
    if " " in kw:
        return kw in text
    return re.search(r"\b" + re.escape(kw) + r"s?\b", text) is not None


def classify(text: str):
    """Return a category string, or None if nothing 3D-worthy was detected."""
    lowered = f" {text.lower()} "
    if any(kw in lowered for kw in _GRAPH_KEYWORDS):
        return None
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(_word_hit(lowered, kw) for kw in keywords):
            return category
    return None


def classify_or_generic(text: str):
    """Always-3D policy: named category when found, else generic_object for
    ask/show/model/render/3d-style questions so the dashboard never stays
    flat when the user asked to *see* something. Pure chat returns None."""
    cat = classify(text)
    if cat:
        return cat
    lowered = text.lower()
    ask_hints = ("what does", "what do", "look like", "looks like", "show",
                 "render", "model", "3d", "display", "visual", "diagram",
                 "draw", "picture", "image")
    if any(h in lowered for h in ask_hints):
        return "generic_object"
    return None


def build_payload(category: str, source_text: str):
    """Return (kind, payload) ready for push_to_dashboard(), or (None, None)."""
    if category is None:
        return None, None
    label = source_text.strip().capitalize()[:60]
    payload = {"type": category, "label": label}
    # Pass floor hints through when present ("12-story", "10 floors").
    m = re.search(r"(\d{1,2})\s*(?:-?\s*stor(?:y|ies)|floors?)", source_text.lower())
    if m:
        try:
            payload["floors"] = max(3, min(12, int(m.group(1))))
        except ValueError:
            pass
    return "object3d", payload
