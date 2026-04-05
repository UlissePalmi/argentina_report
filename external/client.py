"""
Shared API clients — datos.gob.ar, World Bank, BCRA.
Not called from main.py; imported by the topic fetch modules.
"""

from datetime import date, datetime as _dt, timedelta

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
        key = f"datos_{'_'.join(s[:20] for s in ids)}_{limit}_{start_date or ''}_{frequency or ''}"
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


class BCRAClient:
    """BCRA REST API — fetches in 364-day chunks to respect the API limit."""
    URL     = "https://api.bcra.gob.ar/estadisticas/v2.0"
    HEADERS = {"accept": "application/json"}

    def fetch_variable(self, var_id: int, desde: str, hasta: str) -> pd.DataFrame | None:
        start, end, rows = _dt.strptime(desde, "%Y-%m-%d"), _dt.strptime(hasta, "%Y-%m-%d"), []
        cursor = start
        while cursor < end:
            chunk_end = min(cursor + timedelta(days=364), end)
            d1, d2 = cursor.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")
            data = fetch_json(f"{self.URL}/datosvariable/{var_id}/{d1}/{d2}",
                              headers=self.HEADERS, verify_ssl=False,
                              cache_key=f"bcra_var{var_id}_{d1}_{d2}",
                              max_retries=2, timeout=15)
            if data:
                rows.extend(data.get("results", []))
            cursor = chunk_end + timedelta(days=1)
        if not rows:
            return None
        df = pd.DataFrame(rows).rename(columns={"fecha": "date", "valor": "value"})
        df["date"]  = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        return df.drop_duplicates("date").sort_values("date").reset_index(drop=True)
