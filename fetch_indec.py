"""
Fetch INDEC (Instituto Nacional de Estadística y Censos) data for Argentina.

Primary source : Argentina Open Data Series API  (apis.datos.gob.ar/series/api)
                 This is the official government API that serves INDEC series.
Fallback       : World Bank annual trade data

Verified series IDs (confirmed working April 2026):
    IPC nivel general (index, monthly)     : 148.3_INIVELNAL_DICI_M_26
    IPC tasa variación mensual             : 145.3_INGNACUAL_DICI_M_38
    Exportaciones total general (USD M, M) : 75.3_IETG_0_M_31
    Importaciones total general (USD M, M) : 76.3_ITG_0_M_17
"""

from datetime import date, timedelta

import pandas as pd

from utils import OUTPUT_DIR, fetch_json, get_logger

log = get_logger("fetch_indec")

SERIES_BASE = "https://apis.datos.gob.ar/series/api/series/"

# Confirmed working series IDs
IPC_INDEX_ID = "148.3_INIVELNAL_DICI_M_26"
IPC_MOM_ID = "145.3_INGNACUAL_DICI_M_38"
EXPORTS_ID = "75.3_IETG_0_M_31"
IMPORTS_ID = "76.3_ITG_0_M_17"


# ---------------------------------------------------------------------------
# Helper: fetch one or more datos.gob.ar series
# ---------------------------------------------------------------------------
def _fetch_series(series_ids: list[str], limit: int = 50,
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
# Public: CPI — monthly index + MoM + YoY
# ---------------------------------------------------------------------------
def fetch_cpi(months: int = 24) -> pd.DataFrame | None:
    """
    Return monthly CPI and inflation rates.
    Columns: date, cpi_index, cpi_mom_pct, cpi_yoy_pct
    """
    # Fetch extra history so we can compute YoY for the earliest months
    start = (date.today() - timedelta(days=(months + 14) * 31)).strftime("%Y-%m-%d")

    # Fetch index + monthly rate together
    df = _fetch_series([IPC_INDEX_ID, IPC_MOM_ID], limit=months + 20, start_date=start)

    if df is None or df.empty:
        log.warning("INDEC CPI: datos.gob.ar fetch failed.")
        return None

    df = df.rename(columns={
        IPC_INDEX_ID: "cpi_index",
        IPC_MOM_ID: "cpi_mom_raw",
    })

    # cpi_mom_raw is returned as a fraction (0.058 = 5.8%) — convert to %
    df["cpi_mom_pct"] = df["cpi_mom_raw"] * 100
    df.drop(columns=["cpi_mom_raw"], inplace=True)

    # YoY from index
    df["cpi_yoy_pct"] = df["cpi_index"].pct_change(12) * 100

    df = df.tail(months).reset_index(drop=True)
    df = df.dropna(subset=["cpi_mom_pct"])

    out = OUTPUT_DIR / "indec_cpi.csv"
    df.to_csv(out, index=False)
    log.info("INDEC CPI saved → %s  (%d rows)", out.name, len(df))
    return df


# ---------------------------------------------------------------------------
# Public: trade balance — exports and imports (monthly)
# ---------------------------------------------------------------------------
def fetch_trade_balance(months: int = 24) -> pd.DataFrame | None:
    """
    Return monthly exports (FOB) and imports (CIF) in USD billions.
    Columns: date, exports_usd_bn, imports_usd_bn, trade_balance_usd_bn
    """
    start = (date.today() - timedelta(days=months * 31 + 60)).strftime("%Y-%m-%d")

    df = _fetch_series([EXPORTS_ID, IMPORTS_ID], limit=months + 6, start_date=start)

    if df is None or df.empty:
        log.warning("INDEC trade: datos.gob.ar fetch failed — trying World Bank fallback")
        return _fetch_trade_worldbank_fallback(months)

    df = df.rename(columns={
        EXPORTS_ID: "exports_usd_m",
        IMPORTS_ID: "imports_usd_m",
    })

    # Series are in USD millions → convert to billions
    df["exports_usd_bn"] = df["exports_usd_m"] / 1_000
    df["imports_usd_bn"] = df["imports_usd_m"] / 1_000
    df["trade_balance_usd_bn"] = df["exports_usd_bn"] - df["imports_usd_bn"]
    df.drop(columns=["exports_usd_m", "imports_usd_m"], inplace=True)

    df = df.dropna(subset=["exports_usd_bn"]).tail(months).reset_index(drop=True)

    out = OUTPUT_DIR / "indec_trade.csv"
    df.to_csv(out, index=False)
    log.info("Trade balance saved → %s  (%d rows)", out.name, len(df))
    return df


def _fetch_trade_worldbank_fallback(months: int) -> pd.DataFrame | None:
    """Last-resort: World Bank annual merchandise trade data for Argentina."""
    from fetch_worldbank import _fetch_indicator  # local import to avoid circularity

    exp_df = _fetch_indicator("TX.VAL.MRCH.CD.WT", mrv=8)
    imp_df = _fetch_indicator("TM.VAL.MRCH.CD.WT", mrv=8)

    if exp_df is None or imp_df is None:
        log.error("Trade balance: World Bank fallback also failed.")
        return None

    df = exp_df.rename(columns={"value": "exports_usd_bn"}).merge(
        imp_df.rename(columns={"value": "imports_usd_bn"}), on="date", how="inner"
    )
    df["exports_usd_bn"] /= 1e9
    df["imports_usd_bn"] /= 1e9
    df["trade_balance_usd_bn"] = df["exports_usd_bn"] - df["imports_usd_bn"]
    df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y")
    df = df.sort_values("date").reset_index(drop=True)

    out = OUTPUT_DIR / "indec_trade_wb_fallback.csv"
    df.to_csv(out, index=False)
    log.warning("Trade balance from WB fallback → %s  (annual data)", out.name)
    return df


if __name__ == "__main__":
    print(fetch_cpi())
    print(fetch_trade_balance())
