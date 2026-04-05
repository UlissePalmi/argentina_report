"""
Inflation module — data fetching.

Source: Argentina Open Data API (apis.datos.gob.ar/series/api)

Series:
    IPC nivel general (index, monthly)  : 148.3_INIVELNAL_DICI_M_26
    IPC tasa variación mensual          : 145.3_INGNACUAL_DICI_M_38
"""

from datetime import date, timedelta

import pandas as pd

from utils import INFLATION_DIR, fetch_json, get_logger

log = get_logger("inflation.fetch")

SERIES_BASE = "https://apis.datos.gob.ar/series/api/series/"
IPC_INDEX_ID = "148.3_INIVELNAL_DICI_M_26"
IPC_MOM_ID   = "145.3_INGNACUAL_DICI_M_38"


def _fetch_datos(ids: list[str], limit: int, start_date: str | None = None) -> pd.DataFrame | None:
    params: dict = {"ids": ",".join(ids), "format": "json", "limit": limit, "sort": "asc"}
    if start_date:
        params["start_date"] = start_date
    cache_key = f"datos_{'_'.join(s[:20] for s in ids)}_{limit}_{start_date or ''}"
    data = fetch_json(SERIES_BASE, params=params, cache_key=cache_key)
    if data is None or "data" not in data:
        return None
    meta = data.get("meta", [])
    columns = ["date"] + [m["field"]["id"] for m in meta if "field" in m]
    df = pd.DataFrame(data["data"], columns=columns)
    df["date"] = pd.to_datetime(df["date"])
    for col in columns[1:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("date").reset_index(drop=True)


def fetch_cpi(months: int = 24) -> pd.DataFrame | None:
    """
    Monthly CPI index, MoM %, and YoY %.
    Columns: date, cpi_index, cpi_mom_pct, cpi_yoy_pct
    """
    start = (date.today() - timedelta(days=(months + 14) * 31)).strftime("%Y-%m-%d")
    df = _fetch_datos([IPC_INDEX_ID, IPC_MOM_ID], limit=months + 20, start_date=start)

    if df is None or df.empty:
        log.warning("INDEC CPI: fetch failed.")
        return None

    df = df.rename(columns={IPC_INDEX_ID: "cpi_index", IPC_MOM_ID: "cpi_mom_raw"})
    df["cpi_mom_pct"] = df["cpi_mom_raw"] * 100
    df.drop(columns=["cpi_mom_raw"], inplace=True)
    df["cpi_yoy_pct"] = df["cpi_index"].pct_change(12) * 100
    df = df.tail(months).reset_index(drop=True)
    df = df.dropna(subset=["cpi_mom_pct"])

    out = INFLATION_DIR / "indec_cpi.csv"
    df.to_csv(out, index=False)
    log.info("INDEC CPI saved → %s  (%d rows)", out.name, len(df))
    return df
