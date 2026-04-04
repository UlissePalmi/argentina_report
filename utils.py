"""Shared utilities: caching, retry logic, logging setup."""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent
CACHE_DIR = ROOT / "cache"
OUTPUT_DIR = ROOT / "output"

CACHE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------
def cache_path(key: str) -> Path:
    """Return the cache file path for a given cache key."""
    safe_key = key.replace("/", "_").replace(":", "_").replace("?", "_").replace("&", "_")
    return CACHE_DIR / f"{safe_key}.json"


def load_cache(key: str):
    """Return cached JSON data if it exists, else None."""
    p = cache_path(key)
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def save_cache(key: str, data) -> None:
    """Persist JSON data to cache."""
    p = cache_path(key)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# HTTP with retry + caching
# ---------------------------------------------------------------------------
def fetch_json(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    cache_key: str | None = None,
    max_retries: int = 4,
    timeout: int = 30,
    verify_ssl: bool = True,
) -> dict | list | None:
    """
    GET a URL and return parsed JSON.
    - Uses cache_key (defaults to url+params) to avoid re-fetching.
    - Retries with exponential backoff on transient errors.
    - Returns None on terminal failure (logs a warning).
    """
    logger = get_logger("utils.fetch_json")
    key = cache_key or (url + json.dumps(params or {}, sort_keys=True))

    cached = load_cache(key)
    if cached is not None:
        logger.debug("Cache hit: %s", key[:80])
        return cached

    for attempt in range(max_retries):
        try:
            resp = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout,
                verify=verify_ssl,
            )
            resp.raise_for_status()
            data = resp.json()
            save_cache(key, data)
            return data
        except requests.exceptions.SSLError:
            if verify_ssl:
                logger.warning("SSL error on %s — retrying without SSL verification", url)
                verify_ssl = False
                continue
        except requests.exceptions.HTTPError as e:
            if resp.status_code in (429, 503):
                wait = 2 ** attempt
                logger.warning("Rate-limited (%s). Waiting %ds before retry %d/%d",
                               e, wait, attempt + 1, max_retries)
                time.sleep(wait)
            else:
                logger.error("HTTP %s for %s: %s", resp.status_code, url, e)
                return None
        except requests.exceptions.RequestException as e:
            wait = 2 ** attempt
            logger.warning("Request error (%s) — retry %d/%d in %ds", e, attempt + 1, max_retries, wait)
            time.sleep(wait)

    logger.error("All retries exhausted for %s", url)
    return None
