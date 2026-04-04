"""
Fetch Argentine central bank (BCRA) data.

Primary source  : Argentina Open Data API (apis.datos.gob.ar/series/api)
                  — BCRA v2 REST API was deprecated; datos.gob.ar is the reliable path
Fallback        : BCRA API (api.bcra.gob.ar) if a newer version is discovered
                  — chunks requests at ≤365 days to respect API limits

Verified series IDs on datos.gob.ar (confirmed April 2026):
    92.2_RESERVAS_IRES_0_0_32_40  – Reservas internacionales del BCRA (USD millions, daily→monthly)
    92.1_RID_0_0_32               – Reservas internacionales del BCRA (monthly)
"""

from datetime import date, timedelta

import pandas as pd

from utils import OUTPUT_DIR, fetch_json, get_logger

log = get_logger("fetch_bcra")

SERIES_BASE = "https://apis.datos.gob.ar/series/api/series/"
BCRA_BASE = "https://api.bcra.gob.ar/estadisticas/v2.0"
BCRA_HEADERS = {"accept": "application/json"}

RESERVES_SERIES_PRIMARY = "92.2_RESERVAS_IRES_0_0_32_40"   # daily, very recent
RESERVES_SERIES_MONTHLY = "92.1_RID_0_0_32"                 # monthly, slightly older
FX_SERIES_ID = "175.1_DR_REFE500_0_0_25"                     # Dólar Referencia Comunicación A3500 (daily)


# ---------------------------------------------------------------------------
# Helper: fetch from datos.gob.ar series API
# ---------------------------------------------------------------------------
def _fetch_datos_series(series_ids: list[str], limit: int = 50,
                        start_date: str | None = None) -> pd.DataFrame | None:
    params: dict = {
        "ids": ",".join(series_ids),
        "format": "json",
        "limit": limit,
        "sort": "asc",
    }
    if start_date:
        params["start_date"] = start_date

    cache_key = f"datos_{'_'.join(s[:20] for s in series_ids)}_{limit}_{start_date or ''}"
    data = fetch_json(SERIES_BASE, params=params, cache_key=cache_key)

    if data is None or "data" not in data:
        return None

    meta = data.get("meta", [])
    # meta[0] = time-index info; meta[1:] = one entry per series with field.id
    columns = ["date"] + [m["field"]["id"] for m in meta if "field" in m]
    df = pd.DataFrame(data["data"], columns=columns)
    df["date"] = pd.to_datetime(df["date"])
    for col in columns[1:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("date").reset_index(drop=True)


# ---------------------------------------------------------------------------
# BCRA API fallback: chunk requests at ≤365 days
# ---------------------------------------------------------------------------
def _fetch_bcra_variable(var_id: int, desde: str, hasta: str) -> pd.DataFrame | None:
    """
    Attempt BCRA REST API (v2, may be deprecated).
    Chunks requests to ≤365 days per call.
    """
    from datetime import datetime

    start = datetime.strptime(desde, "%Y-%m-%d")
    end = datetime.strptime(hasta, "%Y-%m-%d")
    chunk_days = 365
    all_rows = []

    cursor = start
    while cursor < end:
        chunk_end = min(cursor + timedelta(days=chunk_days - 1), end)
        d1 = cursor.strftime("%Y-%m-%d")
        d2 = chunk_end.strftime("%Y-%m-%d")
        url = f"{BCRA_BASE}/datosvariable/{var_id}/{d1}/{d2}"
        data = fetch_json(url, headers=BCRA_HEADERS, verify_ssl=False,
                          cache_key=f"bcra_var{var_id}_{d1}_{d2}",
                          max_retries=2, timeout=15)
        if data is not None:
            rows = data.get("results", [])
            all_rows.extend(rows)
        else:
            log.debug("BCRA var %d: chunk %s – %s failed", var_id, d1, d2)
        cursor = chunk_end + timedelta(days=1)

    if not all_rows:
        return None

    df = pd.DataFrame(all_rows)
    df.rename(columns={"fecha": "date", "valor": "value"}, inplace=True)
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.drop_duplicates("date").sort_values("date").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Public: reserves (gross, monthly last obs)
# ---------------------------------------------------------------------------
def fetch_reserves(months: int = 24) -> pd.DataFrame | None:
    """
    Return monthly gross international reserves in USD billions.
    Columns: date, reserves_usd_bn
    """
    start = (date.today() - timedelta(days=months * 31 + 30)).strftime("%Y-%m-%d")
    df = None

    # --- Primary: datos.gob.ar (daily series, collapse to monthly) ---
    raw = _fetch_datos_series([RESERVES_SERIES_PRIMARY], limit=months * 31,
                               start_date=start)
    if raw is not None and not raw.empty and RESERVES_SERIES_PRIMARY in raw.columns:
        raw["month"] = raw["date"].dt.to_period("M")
        df_m = raw.groupby("month", as_index=False).last()
        df_m["date"] = df_m["month"].dt.to_timestamp()
        df_m.rename(columns={RESERVES_SERIES_PRIMARY: "reserves_usd_m"}, inplace=True)
        df = df_m[["date", "reserves_usd_m"]].copy()
        log.info("BCRA reserves: using datos.gob.ar daily series (collapsed to monthly)")

    # --- Secondary: monthly series ---
    if df is None:
        raw2 = _fetch_datos_series([RESERVES_SERIES_MONTHLY], limit=months + 6,
                                    start_date=start)
        if raw2 is not None and not raw2.empty and RESERVES_SERIES_MONTHLY in raw2.columns:
            raw2.rename(columns={RESERVES_SERIES_MONTHLY: "reserves_usd_m"}, inplace=True)
            df = raw2[["date", "reserves_usd_m"]].copy()
            log.info("BCRA reserves: using datos.gob.ar monthly series")

    # --- Tertiary: BCRA API (deprecated but worth a try) ---
    if df is None:
        log.warning("BCRA reserves: datos.gob.ar failed — trying BCRA REST API (may be deprecated)")
        hasta = date.today().strftime("%Y-%m-%d")
        raw3 = _fetch_bcra_variable(1, start, hasta)
        if raw3 is not None:
            raw3["month"] = raw3["date"].dt.to_period("M")
            df_m = raw3.groupby("month", as_index=False).last()
            df_m["date"] = df_m["month"].dt.to_timestamp()
            df_m.rename(columns={"value": "reserves_usd_m"}, inplace=True)
            df = df_m[["date", "reserves_usd_m"]].copy()
            log.info("BCRA reserves: using BCRA REST API")

    if df is None:
        log.warning("BCRA reserves: all sources failed.")
        return None

    # Convert USD millions → billions, keep last N months
    df["reserves_usd_bn"] = df["reserves_usd_m"] / 1_000
    df = df[["date", "reserves_usd_bn"]].dropna().tail(months).reset_index(drop=True)

    out = OUTPUT_DIR / "bcra_reserves.csv"
    df.to_csv(out, index=False)
    log.info("BCRA reserves saved → %s  (%d rows)", out.name, len(df))
    return df


# ---------------------------------------------------------------------------
# Public: exchange rate
# ---------------------------------------------------------------------------
def fetch_exchange_rate(months: int = 24) -> pd.DataFrame | None:
    """
    Return monthly official ARS/USD exchange rate (last obs per month).
    Columns: date, usd_ars
    """
    start = (date.today() - timedelta(days=months * 31 + 30)).strftime("%Y-%m-%d")

    # Try a known FX series on datos.gob.ar
    fx_ids_to_try = [
        "175.1_DR_REFE500_0_0_25",   # Dólar Referencia Comunicación A3500 (daily→monthly)
        "174.1_T_CAMBIOR_0_0_6",
        "43.3_TC_0_0_6",
    ]
    df = None
    for fxid in fx_ids_to_try:
        raw = _fetch_datos_series([fxid], limit=months * 31, start_date=start)
        if raw is not None and not raw.empty and fxid in raw.columns:
            raw["month"] = raw["date"].dt.to_period("M")
            df_m = raw.groupby("month", as_index=False).last()
            df_m["date"] = df_m["month"].dt.to_timestamp()
            df_m.rename(columns={fxid: "usd_ars"}, inplace=True)
            df = df_m[["date", "usd_ars"]].copy()
            log.info("BCRA FX: using series %s", fxid)
            break

    if df is None:
        log.warning("BCRA FX rate: all sources failed.")
        return None

    df = df.tail(months).reset_index(drop=True)
    out = OUTPUT_DIR / "bcra_fx.csv"
    df.to_csv(out, index=False)
    log.info("BCRA FX saved → %s  (%d rows)", out.name, len(df))
    return df


if __name__ == "__main__":
    print(fetch_reserves())
    print(fetch_exchange_rate())
