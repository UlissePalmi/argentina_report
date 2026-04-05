"""
GDP module — data fetching.

Sources: Argentina Open Data API (apis.datos.gob.ar/series/api)

Functions:
    fetch_gdp_growth(quarters)    — quarterly YoY real GDP growth (%)
    fetch_gdp_components(quarters)— quarterly YoY C, G, I, X, M, GDP growth
    fetch_emae(months)            — monthly EMAE headline + sectoral YoY

Series:
    GDP level (quarterly, base 2004): 9.2_PP2_2004_T_16
    C:   4.2_MGCP_2004_T_25
    G:   4.2_DGCP_2004_T_30
    I:   4.2_DGIT_2004_T_25
    X:   4.2_DGE_2004_T_26
    OGT: 4.2_OGT_2004_T_19
    EMAE headline YoY: 143.3_ICE_SERVIA_2004_A_25
    EMAE sectors (base 2004=100, monthly):
        agricultura  11.3_ISOM_2004_M_39
        mineria      11.3_ISD_2004_M_26
        industria    11.3_VMASD_2004_M_23
        comercio     11.3_AGCS_2004_M_41
        construccion 11.3_VMATC_2004_M_12
        financiero   11.3_IM_2004_M_25
        transporte   11.3_EMC_2004_M_25
"""

from datetime import date, timedelta

import pandas as pd

from utils import GDP_DIR, fetch_json, get_logger

log = get_logger("gdp.fetch")

SERIES_BASE = "https://apis.datos.gob.ar/series/api/series/"
WB_BASE = "https://api.worldbank.org/v2/country/AR/indicator"

# GDP level series
GDP_SERIES_ID = "9.2_PP2_2004_T_16"

# GDP components
GDP_COMPONENTS = {
    "C":   "4.2_MGCP_2004_T_25",
    "G":   "4.2_DGCP_2004_T_30",
    "I":   "4.2_DGIT_2004_T_25",
    "X":   "4.2_DGE_2004_T_26",
    "OGT": "4.2_OGT_2004_T_19",
    "GDP": "9.2_PP2_2004_T_16",
}

# EMAE
HEADLINE_ID = "143.3_ICE_SERVIA_2004_A_25"
SECTOR_IDS = {
    "agricultura":   "11.3_ISOM_2004_M_39",
    "mineria":       "11.3_ISD_2004_M_26",
    "industria":     "11.3_VMASD_2004_M_23",
    "comercio":      "11.3_AGCS_2004_M_41",
    "construccion":  "11.3_VMATC_2004_M_12",
    "financiero":    "11.3_IM_2004_M_25",
    "transporte":    "11.3_EMC_2004_M_25",
}


def _fetch_datos(ids: list[str], limit: int, start_date: str) -> pd.DataFrame | None:
    params = {
        "ids": ",".join(ids),
        "format": "json",
        "limit": limit,
        "sort": "asc",
        "start_date": start_date,
    }
    cache_key = f"datos_{'_'.join(i[:15] for i in ids)}_{limit}_{start_date}"
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


def _fetch_wb_indicator(indicator: str, mrv: int = 12) -> pd.DataFrame | None:
    params = {"format": "json", "mrv": mrv, "per_page": mrv}
    data = fetch_json(f"{WB_BASE}/{indicator}", params=params,
                      cache_key=f"wb_{indicator}_mrv{mrv}_A")
    if not isinstance(data, list) or len(data) < 2 or not data[1]:
        return None
    rows = [{"date": r["date"], "value": float(r["value"])}
            for r in data[1] if r.get("value") is not None]
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True) if rows else None


# ---------------------------------------------------------------------------
# Public: GDP growth (quarterly YoY %)
# ---------------------------------------------------------------------------
def fetch_gdp_growth(quarters: int = 10) -> pd.DataFrame | None:
    """
    Quarterly YoY real GDP growth (%).
    Columns: date (period str e.g. '2025Q4'), gdp_growth_pct
    Primary: INDEC quarterly PIB via datos.gob.ar
    Fallback: World Bank annual
    """
    start = (date.today() - timedelta(days=(quarters + 6) * 95)).strftime("%Y-%m-%d")
    df_raw = _fetch_datos([GDP_SERIES_ID], limit=quarters + 10, start_date=start)

    if df_raw is not None and not df_raw.empty and GDP_SERIES_ID in df_raw.columns:
        df_raw["gdp_growth_pct"] = df_raw[GDP_SERIES_ID].pct_change(4) * 100
        df_raw = df_raw.dropna(subset=["gdp_growth_pct"]).tail(quarters).reset_index(drop=True)
        eoq = df_raw["date"] + pd.offsets.QuarterEnd(0)
        df_raw["date"] = eoq.dt.to_period("Q").astype(str)
        df = df_raw[["date", "gdp_growth_pct"]]
        out = GDP_DIR / "wb_gdp_growth.csv"
        df.to_csv(out, index=False)
        log.info("GDP growth (INDEC quarterly) saved → %s  (%d rows)", out.name, len(df))
        return df

    log.warning("GDP growth: quarterly unavailable — trying World Bank annual")
    wb = _fetch_wb_indicator("NY.GDP.MKTP.KD.ZG", mrv=12)
    if wb is None or wb.empty:
        log.warning("GDP growth: all sources failed.")
        return None
    wb.rename(columns={"value": "gdp_growth_pct"}, inplace=True)
    wb = wb.tail(quarters).reset_index(drop=True)
    out = GDP_DIR / "wb_gdp_growth.csv"
    wb.to_csv(out, index=False)
    log.info("GDP growth (WB annual fallback) saved → %s  (%d rows)", out.name, len(wb))
    return wb


# ---------------------------------------------------------------------------
# Public: GDP expenditure components (quarterly YoY %)
# ---------------------------------------------------------------------------
def fetch_gdp_components(quarters: int = 8) -> pd.DataFrame | None:
    """
    Quarterly YoY growth for C, G, I, X, M, GDP.
    Columns: date, quarter, C_pct, G_pct, I_pct, X_pct, M_pct, GDP_pct
    """
    start = (date.today() - timedelta(days=(quarters + 6) * 95)).strftime("%Y-%m-%d")
    ids = list(GDP_COMPONENTS.values())
    params = {"ids": ",".join(ids), "format": "json",
              "limit": quarters + 10, "sort": "asc", "start_date": start}
    data = fetch_json(SERIES_BASE, params=params,
                      cache_key=f"datos_gdp_components_{quarters}_{start}")
    if data is None or "data" not in data:
        log.warning("GDP components: fetch failed.")
        return None

    meta = [m for m in data.get("meta", []) if "field" in m]
    col_ids = [m["field"]["id"] for m in meta]
    id_to_key = {v: k for k, v in GDP_COMPONENTS.items()}
    columns = ["date"] + [id_to_key.get(c, c) for c in col_ids]

    df = pd.DataFrame(data["data"], columns=columns)
    df["date"] = pd.to_datetime(df["date"])
    for col in columns[1:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["M"] = df["OGT"] - df["GDP"]
    result = df[["date"]].copy()
    for comp in ["C", "G", "I", "X", "M", "GDP"]:
        result[f"{comp}_pct"] = df[comp].pct_change(4) * 100

    result = result.dropna().tail(quarters).reset_index(drop=True)
    eoq = result["date"] + pd.offsets.QuarterEnd(0)
    period = eoq.dt.to_period("Q")
    result["date"] = period.astype(str)
    result["quarter"] = "Q" + period.dt.quarter.astype(str) + " " + period.dt.year.astype(str)
    result = result[["date", "quarter", "C_pct", "G_pct", "I_pct", "X_pct", "M_pct", "GDP_pct"]]

    out = GDP_DIR / "gdp_components.csv"
    result.to_csv(out, index=False)
    log.info("GDP components saved → %s  (%d rows)", out.name, len(result))
    return result


# ---------------------------------------------------------------------------
# Public: EMAE monthly activity
# ---------------------------------------------------------------------------
def fetch_emae(months: int = 24) -> pd.DataFrame | None:
    """
    Monthly EMAE headline YoY + sectoral YoY growth rates.
    Columns: date, emae_yoy_pct, agricultura_pct, mineria_pct, industria_pct,
             comercio_pct, construccion_pct, financiero_pct, transporte_pct
    """
    start = (date.today() - timedelta(days=(months + 14) * 31)).strftime("%Y-%m-%d")

    h_df = _fetch_datos([HEADLINE_ID], limit=months + 20, start_date=start)
    if h_df is None or h_df.empty:
        log.warning("EMAE headline: fetch failed.")
        return None

    h_df["emae_yoy_pct"] = h_df[HEADLINE_ID] * 100
    h_df = h_df[["date", "emae_yoy_pct"]]

    sector_ids = list(SECTOR_IDS.values())
    s_df = _fetch_datos(sector_ids, limit=months + 20, start_date=start)

    result = h_df.copy()
    if s_df is not None and not s_df.empty:
        for label, sid in SECTOR_IDS.items():
            if sid in s_df.columns:
                s_df[f"{label}_pct"] = s_df[sid].pct_change(12) * 100
        pct_cols = [f"{k}_pct" for k in SECTOR_IDS]
        available = [c for c in pct_cols if c in s_df.columns]
        result = result.merge(
            s_df[["date"] + available].dropna(subset=available, how="all"),
            on="date", how="left"
        )
    else:
        log.warning("EMAE sectors: fetch failed — headline only.")

    result = result.dropna(subset=["emae_yoy_pct"]).tail(months).reset_index(drop=True)
    out = GDP_DIR / "emae.csv"
    result.to_csv(out, index=False)
    log.info("EMAE saved → %s  (%d rows, latest: %s)",
             out.name, len(result), result["date"].max().strftime("%Y-%m"))
    return result
