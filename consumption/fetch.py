"""
Consumption module — data fetching.

Source: Argentina Open Data API (apis.datos.gob.ar/series/api)

Series:
    Wages (nominal, private sector):
        149.1_SOR_PRIADO_OCTU_0_25  — Índice de salarios, sector privado (base Oct 2016=100)
    Credit:
        91.1_PEFPGR_0_0_60          — Consumer + personal loans total (ARS)
        174.1_PTAMOS_O_0_0_29       — Total private sector loans (ARS)
    Savings proxy:
        334.2_SIST_FINANIJO__54     — Fixed-term deposits, private sector (system-wide)

Output columns (consumption.csv):
    date,
    nominal_wage_yoy_pct, consumer_credit_yoy_pct, total_credit_yoy_pct, deposits_yoy_pct,
    cpi_yoy_pct (merged in),
    real_wage_yoy_pct, real_consumer_credit_yoy_pct, real_total_credit_yoy_pct, real_deposits_yoy_pct

Note: real_* columns = nominal − cpi_yoy_pct. Added via compute_real_values() in main.py.
      For industrial output, use data/gdp/emae.csv (industria_pct) — standalone EMI is stale.
"""

from datetime import date, timedelta

import pandas as pd

from utils import CONSUMPTION_DIR, fetch_json, get_logger

log = get_logger("consumption.fetch")

SERIES_BASE  = "https://apis.datos.gob.ar/series/api/series/"
WAGE_ID      = "149.1_SOR_PRIADO_OCTU_0_25"
CREDIT_ID    = "91.1_PEFPGR_0_0_60"
TOTAL_CR_ID  = "174.1_PTAMOS_O_0_0_29"
DEPOSITS_ID  = "334.2_SIST_FINANIJO__54"


def _fetch_series(ids: list[str], limit: int, start_date: str) -> pd.DataFrame | None:
    params = {"ids": ",".join(ids), "format": "json", "limit": limit,
              "sort": "asc", "start_date": start_date}
    cache_key = f"consumption_{'_'.join(i[:15] for i in ids)}_{limit}_{start_date}"
    data = fetch_json(SERIES_BASE, params=params, cache_key=cache_key)
    if data is None or "data" not in data:
        return None
    meta = [m for m in data.get("meta", []) if "field" in m]
    columns = ["date"] + [m["field"]["id"] for m in meta]
    df = pd.DataFrame(data["data"], columns=columns)
    df["date"] = pd.to_datetime(df["date"])
    for col in columns[1:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("date").reset_index(drop=True)


def fetch_consumption(months: int = 24) -> pd.DataFrame | None:
    """
    Monthly consumption driver indicators.
    Columns: date, nominal_wage_yoy_pct, consumer_credit_yoy_pct,
             total_credit_yoy_pct, deposits_yoy_pct
    """
    start = (date.today() - timedelta(days=(months + 14) * 31)).strftime("%Y-%m-%d")
    limit = months + 20

    batch1 = _fetch_series([WAGE_ID], limit=limit, start_date=start)
    batch2 = _fetch_series([CREDIT_ID, TOTAL_CR_ID, DEPOSITS_ID], limit=limit, start_date=start)

    if batch1 is None or batch1.empty:
        log.warning("fetch_consumption: wages batch failed.")
        return None

    result = batch1[["date"]].copy()

    if WAGE_ID in batch1.columns:
        result["nominal_wage_yoy_pct"] = batch1[WAGE_ID].pct_change(12) * 100
        result["nominal_wage_mom_pct"]  = batch1[WAGE_ID].pct_change(1)  * 100
    else:
        log.warning("fetch_consumption: wage series not found.")
        result["nominal_wage_yoy_pct"] = None
        result["nominal_wage_mom_pct"] = None

    if batch2 is not None and not batch2.empty:
        if CREDIT_ID in batch2.columns:
            batch2["consumer_credit_yoy_pct"] = batch2[CREDIT_ID].pct_change(12) * 100
        if TOTAL_CR_ID in batch2.columns:
            batch2["total_credit_yoy_pct"] = batch2[TOTAL_CR_ID].pct_change(12) * 100
        if DEPOSITS_ID in batch2.columns:
            batch2["deposits_yoy_pct"] = batch2[DEPOSITS_ID].pct_change(12) * 100
        fin_cols = [c for c in ["consumer_credit_yoy_pct", "total_credit_yoy_pct", "deposits_yoy_pct"]
                    if c in batch2.columns]
        if fin_cols:
            result = result.merge(
                batch2[["date"] + fin_cols].dropna(subset=fin_cols, how="all"),
                on="date", how="left"
            )
    else:
        log.warning("fetch_consumption: credit/deposits batch failed.")

    yoy_cols = [c for c in result.columns if c != "date"]
    result = result.dropna(subset=yoy_cols, how="all").tail(months).reset_index(drop=True)

    if result.empty:
        log.warning("fetch_consumption: empty after YoY computation.")
        return None

    out = CONSUMPTION_DIR / "consumption.csv"
    result.to_csv(out, index=False)
    log.info("Consumption drivers saved → %s  (%d rows, latest: %s)",
             out.name, len(result), result["date"].max().strftime("%Y-%m"))
    return result


def compute_real_values(consumption_df: pd.DataFrame, cpi_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge CPI YoY into consumption_df and add real (inflation-adjusted) columns.

    Real value = nominal YoY % − CPI YoY %
    (approximation valid when both are expressed as annual % changes)

    Adds columns: real_wage_yoy_pct, real_consumer_credit_yoy_pct,
                  real_total_credit_yoy_pct, real_deposits_yoy_pct
    Also adds: cpi_yoy_pct (for reference)
    Overwrites consumption.csv with the enriched version.
    """
    cpi_cols = [c for c in ["date", "cpi_yoy_pct", "cpi_mom_pct"] if c in cpi_df.columns]
    cpi = cpi_df[cpi_cols].copy()
    cpi["date"] = pd.to_datetime(cpi["date"]).dt.to_period("M").dt.to_timestamp()
    cpi = cpi.dropna(subset=["cpi_yoy_pct"])

    df = consumption_df.copy()
    df["_date_m"] = pd.to_datetime(df["date"]).dt.to_period("M").dt.to_timestamp()
    df = df.merge(cpi.rename(columns={"date": "_date_m"}), on="_date_m", how="left")
    df.drop(columns=["_date_m"], inplace=True)

    NOMINAL_REAL = {
        "nominal_wage_yoy_pct":       "real_wage_yoy_pct",
        "consumer_credit_yoy_pct":    "real_consumer_credit_yoy_pct",
        "total_credit_yoy_pct":       "real_total_credit_yoy_pct",
        "deposits_yoy_pct":           "real_deposits_yoy_pct",
    }
    for nom, real in NOMINAL_REAL.items():
        if nom in df.columns and "cpi_yoy_pct" in df.columns:
            # Fisher equation: real = ((1 + nominal) / (1 + inflation)) - 1
            # Critical at Argentina's inflation levels — simple subtraction is badly wrong
            # e.g. nominal=430%, CPI=84% → simple gives 346%, Fisher gives 188%
            df[real] = (((1 + df[nom] / 100) / (1 + df["cpi_yoy_pct"] / 100)) - 1) * 100

    # Real wage MoM: Fisher using nominal wage MoM and CPI MoM
    if "nominal_wage_mom_pct" in df.columns and "cpi_mom_pct" in df.columns:
        df["real_wage_mom_pct"] = (
            ((1 + df["nominal_wage_mom_pct"] / 100) / (1 + df["cpi_mom_pct"] / 100)) - 1
        ) * 100

    out = CONSUMPTION_DIR / "consumption.csv"
    df.to_csv(out, index=False)
    log.info("Consumption (real-adjusted) saved → %s", out.name)
    return df
