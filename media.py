"""
47 media actions — open sites AND act in them.

Deep module, small interface: play/search/open verbs that resolve to direct
URLs (no brittle DOM automation). YouTube playback resolves a song name to a
watch URL with autoplay via DDG video results; Google opens a real search.
Falls back to search-result pages when resolvers are rate-limited.
"""
import webbrowser
from urllib.parse import quote_plus


def google_search_url(query: str) -> str:
    return f"https://www.google.com/search?q={quote_plus(query)}"


def youtube_search_url(query: str) -> str:
    return f"https://www.youtube.com/results?search_query={quote_plus(query)}"


def google_search(query: str) -> str:
    """Open a real Google search in the default browser."""
    if not query.strip():
        return "Tell me what to search Google for."
    webbrowser.open(google_search_url(query))
    return f"Searching Google for {query}."


def _resolve_youtube_watch(query: str):
    """Best-effort song name -> direct watch URL (None when blocked)."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as d:
            for hit in d.videos(query, max_results=4):
                url = hit.get("content", "")
                if "youtube.com/watch" in url or "youtu.be/" in url:
                    sep = "&" if "?" in url else "?"
                    return f"{url}{sep}autoplay=1"
    except Exception:
        pass
    return None


def play_youtube(query: str) -> str:
    """Open YouTube and play the top match for `query` (song name, etc.)."""
    if not query.strip():
        return "Tell me which song or video to play."
    watch = _resolve_youtube_watch(query)
    if watch:
        webbrowser.open(watch)
        return f"Playing {query} on YouTube."
    webbrowser.open(youtube_search_url(query))
    return (f"YouTube search opened for {query} — "
            "pick the video (auto-resolve was rate-limited).")


def open_software(name: str) -> str:
    """Open local software by name (notepad, calculator, ...)."""
    import actions
    return actions.open_app_or_site(name)
