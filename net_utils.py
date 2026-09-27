"""
Shared network resilience helper.

Every outbound call in this project (Grok, weather, page fetch,
DuckDuckGo) used to be a single `requests.*` call with no retry — one
dropped packet or a 429 and the whole turn just failed with a raw
exception string. This wraps that in a small, boring retry-with-backoff
so transient failures (timeouts, 429s, 5xxs) get a couple of quiet
second chances before we give up and tell the user.

Not trying to be a generic HTTP client — just enough to stop "the wifi
blipped for one second" from being indistinguishable from "the service
is down."
"""

import time
import random

import requests


class RetryableError(Exception):
    """Raised internally to signal 'worth retrying', then unwrapped."""


def request_with_retry(method: str, url: str, *, max_attempts: int = 3,
                        base_delay: float = 0.6, **kwargs) -> requests.Response:
    """requests.request() with retry on timeouts, connection errors, 429s,
    and 5xx responses. Raises the last exception (or returns the last
    response) if every attempt fails. Honors a Retry-After header on 429s.
    Never retries on 4xx other than 429 — those are the caller's fault, not
    a transient blip, so retrying just wastes time before the same error.
    """
    last_exc = None
    last_resp = None
    for attempt in range(max_attempts):
        try:
            resp = requests.request(method, url, **kwargs)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_exc = e
        else:
            if resp.status_code == 429:
                last_resp = resp
                retry_after = resp.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else _backoff(attempt, base_delay)
                if attempt < max_attempts - 1:
                    time.sleep(delay)
                    continue
                return resp
            if 500 <= resp.status_code < 600:
                last_resp = resp
                if attempt < max_attempts - 1:
                    time.sleep(_backoff(attempt, base_delay))
                    continue
                return resp
            return resp  # success or a non-retryable 4xx — hand it back as-is

        if attempt < max_attempts - 1:
            time.sleep(_backoff(attempt, base_delay))

    if last_exc:
        raise last_exc
    return last_resp  # exhausted retries on a 429/5xx; caller checks status_code


def _backoff(attempt: int, base_delay: float) -> float:
    """Exponential backoff with a little jitter so concurrent retries don't
    all land on the same tick."""
    return base_delay * (2 ** attempt) + random.uniform(0, base_delay)
