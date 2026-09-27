"""
47 home automation — Home Assistant REST (local network, user-owned).
Setup (free, local):
  HA_URL=http://homeassistant.local:8123 HA_TOKEN=<long-lived token>
No cloud: calls go to the user's own HA instance only.
"""
import os
import requests


def _cfg():
    base = os.environ.get("HA_URL", "").rstrip("/")
    token = os.environ.get("HA_TOKEN", "")
    return base, token


def call_service(domain: str, service: str, entity_id: str = "", data: dict | None = None) -> str:
    base, token = _cfg()
    if not base or not token:
        return "Home Assistant isn't configured (set HA_URL and HA_TOKEN)."
    body = dict(data or {})
    if entity_id:
        body["entity_id"] = entity_id
    try:
        r = requests.post(f"{base}/api/services/{domain}/{service}",
                          headers={"Authorization": f"Bearer {token}",
                                   "Content-Type": "application/json"},
                          json=body, timeout=10)
        r.raise_for_status()
        return f"Called {domain}.{service} on {entity_id or 'all'}."
    except Exception as e:
        return f"Home Assistant call failed: {e}"


def toggle(entity_id: str) -> str:
    return call_service("homeassistant", "toggle", entity_id)


def turn_on(entity_id: str) -> str:
    domain = (entity_id.split(".")[0] if "." in entity_id else "light")
    return call_service(domain, "turn_on", entity_id)


def turn_off(entity_id: str) -> str:
    domain = (entity_id.split(".")[0] if "." in entity_id else "light")
    return call_service(domain, "turn_off", entity_id)
