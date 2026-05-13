"""
Shared API clients — datos.gob.ar, World Bank, PDF.
Not called from main.py; imported by the topic fetch modules.
"""

import hashlib
import io
import re
from datetime import date, timedelta

import pandas as pd

from utils import fetch_json, get_logger, load_cache, save_cache


def _start(months: int, buffer: int = 14) -> str:
    """ISO date string roughly (months + buffer) months before today."""
    return (date.today() - timedelta(days=(months + buffer) * 31)).strftime("%Y-%m-%d")


class DatosClient:
    """datos.gob.ar time-series API."""
    URL = "https://apis.datos.gob.ar/series/api/series/"

    def fetch(self, ids: list[str], limit: int,
              start_date: str | None = None,
              frequency: str | None = None) -> pd.DataFrame | None:
        params: dict = {"ids": ",".join(ids), "format": "json", "limit": limit, "sort": "asc"}
        if start_date: params["start_date"] = start_date
        if frequency:  params["collapse"]   = frequency
        ids_part = "_".join(s[:20] for s in ids)
        raw_key  = f"datos_{ids_part}_{limit}_{start_date or ''}_{frequency or ''}"
        key = raw_key if len(raw_key) < 180 else f"datos_{hashlib.md5(raw_key.encode()).hexdigest()}"
        raw = fetch_json(self.URL, params=params, cache_key=key)
        if raw is None or "data" not in raw:
            return None
        cols = ["date"] + [m["field"]["id"] for m in raw.get("meta", []) if "field" in m]
        df = pd.DataFrame(raw["data"], columns=cols)
        df["date"] = pd.to_datetime(df["date"])
        for c in cols[1:]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df.sort_values("date").reset_index(drop=True)


class WorldBankClient:
    """World Bank indicator API (annual)."""
    URL = "https://api.worldbank.org/v2/country/AR/indicator"

    def fetch(self, indicator: str, mrv: int) -> pd.DataFrame | None:
        raw = fetch_json(f"{self.URL}/{indicator}",
                         params={"format": "json", "mrv": mrv, "per_page": mrv},
                         cache_key=f"wb_{indicator}_mrv{mrv}_A")
        if not isinstance(raw, list) or len(raw) < 2 or not raw[1]:
            return None
        rows = [{"date": r["date"], "value": float(r["value"])}
                for r in raw[1] if r.get("value") is not None]
        return pd.DataFrame(rows).sort_values("date").reset_index(drop=True) if rows else None


def to_monthly_last(raw: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Collapse a daily series to last-of-month."""
    raw = raw.copy()
    raw["month"] = raw["date"].dt.to_period("M")
    df = raw.groupby("month", as_index=False).last()
    df["date"] = df["month"].dt.to_timestamp()
    return df[["date", value_col]].copy()


# BCRAClient removed -- api.bcra.gob.ar/estadisticas deprecated all versions (v1/v2/v3).
# Reserves and credit data now sourced exclusively from datos.gob.ar.


class PdfClient:
    """Download, cache, and extract content from remote PDFs."""

    DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0"}

    def __init__(self, timeout: int = 60, headers: dict | None = None):
        self.timeout = timeout
        self.headers = headers or self.DEFAULT_HEADERS
        self.log = get_logger("pdf_client")

    def fetch_bytes(self, url: str, cache_key: str | None = None) -> bytes | None:
        """Download PDF bytes, optionally caching as hex so re-runs skip the download."""
        if cache_key:
            cached = load_cache(cache_key)
            if cached:
                try:
                    return bytes.fromhex(cached)
                except Exception:
                    pass

        try:
            import requests
            resp = requests.get(url, timeout=self.timeout, headers=self.headers)
            resp.raise_for_status()
            if cache_key:
                save_cache(cache_key, resp.content.hex())
            return resp.content
        except Exception as e:
            self.log.warning("PDF download failed (%s): %s", url, e)
            return None

    def extract_text(self, pdf_bytes: bytes, pages: list[int] | None = None) -> str | None:
        """Extract full text from PDF bytes. Pass page indices to restrict to specific pages."""
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                page_list = [pdf.pages[i] for i in pages] if pages else pdf.pages
                return "\n".join(p.extract_text() or "" for p in page_list)
        except Exception as e:
            self.log.warning("PDF text extraction failed: %s", e)
            return None

    def extract_tables(self, pdf_bytes: bytes, page: int = 0) -> list:
        """Extract all tables from a single page (0-indexed)."""
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                return pdf.pages[page].extract_tables() or []
        except Exception as e:
            self.log.warning("PDF table extraction failed (page %d): %s", page, e)
            return []

    def find(self, text: str, pattern: str, flags: int = 0,
             warn: str | None = None) -> re.Match | None:
        """Search text for pattern; log a warning and return None if not found."""
        m = re.search(pattern, text, flags)
        if m is None and warn:
            self.log.warning(warn)
        return m

    def fetch_text(self, url: str, cache_key: str | None = None,
                   pages: list[int] | None = None) -> str | None:
        """Convenience: download + extract text in one call."""
        pdf_bytes = self.fetch_bytes(url, cache_key)
        if pdf_bytes is None:
            return None
        return self.extract_text(pdf_bytes, pages)
