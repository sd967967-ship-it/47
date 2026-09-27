"""Active-brain selection for 47 — exactly ONE provider is ever live.

Precedence: Groq (free tier, key present) -> Grok/xAI (key present) ->
None (degraded local-only mode). The pick is by key presence, shown to
the user via the voice greeting and `brain status`. No multi-provider
switching UI, no fallbacks between providers.
"""
import vault


def get_active_provider():
    """Return (module, display-name) or (None, None). Never raises."""
    try:
        if vault.get("GROQ_API_KEY"):
            from providers import groq as _groq
            return _groq, "Groq"
        if vault.get("XAI_API_KEY"):
            from providers import grok as _grok
            return _grok, "Grok"
    except Exception:
        pass
    return None, None
