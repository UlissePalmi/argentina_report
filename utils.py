"""Shared utilities: caching, retry logic, logging setup."""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent
CACHE_DIR = ROOT / "cache"

DATA_DIR         = ROOT / "data"
GDP_DIR          = DATA_DIR / "gdp"
EXTERNAL_DIR     = DATA_DIR / "external"
INFLATION_DIR    = DATA_DIR / "inflation"
CONSUMPTION_DIR  = DATA_DIR / "consumption"
PRODUCTION_DIR   = DATA_DIR / "production"
PRODUCTIVITY_DIR = DATA_DIR / "productivity"
SIGNALS_DIR      = DATA_DIR / "signals"
CHARTS_DIR       = DATA_DIR / "charts"
REPORTS_DIR      = DATA_DIR / "reports"

CACHE_DIR.mkdir(exist_ok=True)
for _d in (GDP_DIR, EXTERNAL_DIR, INFLATION_DIR, CONSUMPTION_DIR,
           PRODUCTION_DIR, PRODUCTIVITY_DIR, SIGNALS_DIR, CHARTS_DIR, REPORTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

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
# Quarter helpers
# ---------------------------------------------------------------------------
def add_quarter_cols(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    """Add year_quarter, quarter_start, quarter_end as the first three columns."""
    dates   = pd.to_datetime(df[date_col])
    quarter = dates.dt.quarter
    year    = dates.dt.year

    df["year_quarter"]  = year.astype(str) + "Q" + quarter.astype(str)
    df["quarter_start"] = pd.to_datetime({"year": year, "month": (quarter - 1) * 3 + 1, "day": 1})
    df["quarter_end"]   = (df["quarter_start"] + pd.offsets.QuarterEnd(1)).dt.normalize()

    other = [c for c in df.columns if c not in ("year_quarter", "quarter_start", "quarter_end")]
    return df[["year_quarter", "quarter_start", "quarter_end"] + other]


# ---------------------------------------------------------------------------
# Cache helpers: save and load .json
# ---------------------------------------------------------------------------
_CACHE_DATE_KEY = "_cache_date"
_CACHE_DATA_KEY = "_cache_data"


def cache_path(key: str) -> Path:
    """Return the cache file path for a given cache key."""
    safe_key = key.replace("/", "_").replace(":", "_").replace("?", "_").replace("&", "_")
    return CACHE_DIR / f"{safe_key}.json"


def load_cache(key: str):
    """
    Return cached JSON data if it exists and was saved today.

    Cache files are date-stamped. If the date doesn't match today the entry is
    treated as a miss so the caller re-fetches fresh data. Old-format files
    (no date wrapper) are deleted on first read and trigger a re-fetch.
    """
    p = cache_path(key)
    if not p.exists():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            wrapper = json.load(f)
        # Checks if wrapper has a date key and checks if it fetched today
        if isinstance(wrapper, dict) and _CACHE_DATE_KEY in wrapper:
            today = datetime.now().strftime("%Y-%m-%d")
            if wrapper[_CACHE_DATE_KEY] == today:
                return wrapper[_CACHE_DATA_KEY] 
        return None
    except Exception:
        return None


def save_cache(key: str, data) -> None:
    """Persist JSON data to cache, stamped with today's date."""
    p = cache_path(key)
    wrapper = {
        _CACHE_DATE_KEY: datetime.now().strftime("%Y-%m-%d"),
        _CACHE_DATA_KEY: data,
    }
    with open(p, "w", encoding="utf-8") as f:
        json.dump(wrapper, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# HTTP GET request: with retry + caching
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

    # Checks if the .json is already cached
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
