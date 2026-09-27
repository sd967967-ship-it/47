"""
47 free public-data lookups — currency, crypto, holidays, country facts.

No API keys. Cheap deterministic answers before falling back to web search
or the LLM. Endpoint/idea credit: bertrandmbanwi/Jarvis
jarvis/tools/public_data.py (MIT) — reimplemented here synchronously on
47's request_with_retry (theirs is async/httpx). See THIRD_PARTY_NOTICES.md.
"""
import re
from datetime import datetime

from net_utils import request_with_retry

_TIMEOUT = 12

CURRENCY_ALIASES = {
    "$": "USD", "dollar": "USD", "dollars": "USD", "usd": "USD",
    "eur": "EUR", "euro": "EUR", "euros": "EUR",
    "gbp": "GBP", "pound": "GBP", "pounds": "GBP", "sterling": "GBP",
    "inr": "INR", "rupee": "INR", "rupees": "INR",
    "yen": "JPY", "jpy": "JPY", "yuan": "CNY", "cny": "CNY",
}

CRYPTO_IDS = {
    "btc": "bitcoin", "bitcoin": "bitcoin",
    "eth": "ethereum", "ethereum": "ethereum",
    "sol": "solana", "solana": "solana",
    "doge": "dogecoin", "dogecoin": "dogecoin",
    "xrp": "ripple", "ripple": "ripple",
    "bnb": "binancecoin",
}

COUNTRY_CODES = {
    "india": "IN", "usa": "US", "america": "US", "united states": "US",
    "uk": "GB", "england": "GB", "britain": "GB", "united kingdom": "GB",
    "canada": "CA", "australia": "AU", "germany": "DE", "france": "FR",
    "japan": "JP", "china": "CN", "brazil": "BR", "mexico": "MX",
    "spain": "ES", "italy": "IT", "netherlands": "NL", "switzerland": "CH",
    "singapore": "SG", "uae": "AE", "saudi": "SA",
}


def _norm_currency(value: str) -> str:
    cleaned = value.strip().lower()
    return CURRENCY_ALIASES.get(cleaned, cleaned.upper())


def _norm_country(value: str) -> str:
    cleaned = value.strip().lower()
    if cleaned in COUNTRY_CODES:
        return COUNTRY_CODES[cleaned]
    if re.fullmatch(r"[a-zA-Z]{2}", cleaned):
        return cleaned.upper()
    return cleaned.upper()


def _fmt(value, digits: int = 2) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return f"{number:,.0f}"
    return f"{number:,.{digits}f}".rstrip("0").rstrip(".")


def convert_currency(amount: float, frm: str, to: str) -> str:
    """Convert money via Frankfurter (free, no key)."""
    base, target = _norm_currency(frm), _norm_currency(to)
    if amount <= 0:
        return "Give me an amount greater than zero."
    if base == target:
        return f"{_fmt(amount)} {base} is still {_fmt(amount)} {target}."
    try:
        data = request_with_retry(
            "GET", "https://api.frankfurter.dev/v1/latest",
            params={"amount": amount, "from": base, "to": target},
            timeout=_TIMEOUT,
        ).json()
        rate = data.get("rates", {}).get(target)
        if rate is None:
            return f"Couldn't convert {base} to {target} right now."
        return (f"{_fmt(amount)} {base} = {_fmt(rate)} {target} "
                f"(Frankfurter, {data.get('date', 'latest')}).")
    except Exception as e:
        return f"Currency lookup failed: {e}"


def crypto_price(asset: str) -> str:
    """Spot price via CoinGecko free API (no key)."""
    coin = CRYPTO_IDS.get(asset.strip().lower(), asset.strip().lower().replace(" ", "-"))
    try:
        data = request_with_retry(
            "GET", "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coin, "vs_currencies": "usd"},
            timeout=_TIMEOUT,
        ).json()
        price = data.get(coin, {}).get("usd")
        if price is None:
            return f"No CoinGecko price for {asset}."
        return f"{coin.replace('-', ' ').title()} is ${_fmt(price)} USD (CoinGecko)."
    except Exception as e:
        return f"Crypto lookup failed: {e}"


def next_holiday(place: str) -> str:
    """Next public holiday via Nager.Date (free, no key)."""
    code = _norm_country(place)
    today = datetime.now().date()
    try:
        holidays = []
        for year in (today.year, today.year + 1):
            data = request_with_retry(
                "GET", f"https://date.nager.at/api/v3/PublicHolidays/{year}/{code}",
                timeout=_TIMEOUT,
            ).json()
            if isinstance(data, list):
                holidays.extend(data)
        future = [(h.get("date", ""), h) for h in holidays
                  if isinstance(h, dict) and h.get("date", "") >= today.isoformat()]
        if not future:
            return f"No upcoming holidays found for {code}."
        day, item = sorted(future, key=lambda pair: pair[0])[0]
        return (f"Next holiday in {code}: {item.get('name') or item.get('localName')} "
                f"on {day}.")
    except Exception as e:
        return f"Holiday lookup failed: {e}"


def country_info(name: str) -> str:
    """Country facts via REST Countries (free, no key)."""
    if not name.strip():
        return "Tell me which country."
    try:
        data = request_with_retry(
            "GET", f"https://restcountries.com/v3.1/name/{name.strip()}",
            params={"fullText": "true"},
            timeout=_TIMEOUT,
        ).json()
        item = data[0] if isinstance(data, list) else data
        capital = ", ".join(item.get("capital", [])) or "not listed"
        pop = _fmt(item.get("population"), digits=0)
        curr = ", ".join(f"{c} ({d.get('name', '')})"
                         for c, d in item.get("currencies", {}).items()) or "not listed"
        langs = ", ".join(item.get("languages", {}).values()) or "not listed"
        return (f"{item.get('name', {}).get('common', name)} — capital {capital}, "
                f"pop {pop}, currency {curr}, languages {langs}.")
    except Exception as e:
        return f"Country lookup failed: {e}"
