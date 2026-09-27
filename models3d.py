"""
47 real-model library — CC0 .glb files served locally, loaded in-browser.

Khronos glTF-Sample-Models are CC0 (see assets/models/SOURCE.md). Mapping
is honest: only categories with a fitting model resolve to a file, the rest
keep 47's parametric scenes. Served token-gated at /models/<name>; the
allowlist below is the ONLY set of servable files (no traversal possible).
"""
from pathlib import Path

MODELS_DIR = Path(__file__).parent / "assets" / "models"

# Category -> file. Deliberately partial: vehicle/building/map stay
# procedural until fitting CC0 models are added to the pack.
LIBRARY = {
    "electronics": "BoomBox.glb",
    "nature": "Duck.glb",
    "food": "Avocado.glb",
    "furniture": "Lantern.glb",
    "tool": "WaterBottle.glb",
}

KEYWORD_FILES = {
    "boombox": "BoomBox.glb", "speaker": "BoomBox.glb", "radio": "BoomBox.glb",
    "duck": "Duck.glb", "bird": "Duck.glb",
    "avocado": "Avocado.glb", "fruit": "Avocado.glb", "food": "Avocado.glb",
    "lantern": "Lantern.glb", "lamp": "Lantern.glb", "chair": "Lantern.glb",
    "bottle": "WaterBottle.glb", "water": "WaterBottle.glb",
}


def allowed_files() -> set:
    return set(LIBRARY.values())


def resolve(text: str, category=None):
    """Best library file for a request, or None (keep procedural scene)."""
    lowered = text.lower()
    for keyword, filename in KEYWORD_FILES.items():
        if keyword in lowered:
            return filename
    if category and category in LIBRARY:
        return LIBRARY[category]
    return None


def model_path(filename: str):
    """Absolute path if allowed AND present, else None. No traversal."""
    if filename not in allowed_files():
        return None
    candidate = (MODELS_DIR / filename).resolve()
    if candidate.parent != MODELS_DIR.resolve():
        return None
    return candidate if candidate.is_file() else None
