"""
Shared API clients — datos.gob.ar, World Bank, BCRA.
Not called from main.py; imported by the topic fetch modules.
"""

import hashlib
from datetime import date, timedelta

import pandas as pd

from utils import fetch_json


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
