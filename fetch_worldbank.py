"""
Fetch World Bank data for Argentina.

API  : api.worldbank.org/v2/country/{iso}/indicator/{indicator}
Format: JSON (v2)

Indicators used:
    NY.GDP.MKTP.KD.ZG  – GDP growth (annual %, constant prices)
    DT.DOD.DECT.GN.ZS  – External debt stocks (% of GNI)
    BN.CAB.XOKA.GD.ZS  – Current account balance (% of GDP) [annual fallback]
    NE.EXP.GNFS.ZS     – Exports of goods and services (% of GDP)
"""

from datetime import date

import pandas as pd

from utils import OUTPUT_DIR, fetch_json, get_logger

log = get_logger("fetch_worldbank")

BASE = "https://api.worldbank.org/v2/country/AR/indicator"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _fetch_indicator(
    indicator: str,
    mrv: int = 30,
    frequency: str | None = None,
) -> pd.DataFrame | None:
    """
    Fetch a World Bank indicator for Argentina.
    Returns DataFrame with columns: [date, value]
    mrv = most recent values to fetch.
    """
    params: dict = {"format": "json", "mrv": mrv, "per_page": mrv}
    if frequency:
        params["frequency"] = frequency

    url = f"{BASE}/{indicator}"
    data = fetch_json(url, params=params,
                      cache_key=f"wb_{indicator}_mrv{mrv}_{frequency or 'A'}")
    if data is None:
        return None

    # WB returns [metadata_dict, data_list]
    if not isinstance(data, list) or len(data) < 2:
        log.warning("WB %s: unexpected response structure", indicator)
        return None

    records = data[1]
    if not records:
        log.warning("WB %s: no data returned", indicator)
        return None

    rows = []
    for r in records:
        if r.get("value") is None:
            continue
        rows.append({"date": r["date"], "value": float(r["value"])})

    if not rows:
        return None

    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Public: real GDP growth YoY (quarterly)
# ---------------------------------------------------------------------------
def fetch_gdp_growth(quarters: int = 10) -> pd.DataFrame | None:
    """
    Return quarterly YoY real GDP growth (%).
    Columns: date, gdp_growth_pct

    Primary   : datos.gob.ar INDEC quarterly GDP level (base 2004) → compute YoY
                Series 9.2_PP2_2004_T_16, goes to Q3 2025
    Fallback  : World Bank annual NY.GDP.MKTP.KD.ZG (1-year publication lag)
    """
    # --- Primary: datos.gob.ar quarterly GDP level → compute YoY ---
    df = _fetch_gdp_indec_quarterly(quarters)
    if df is not None and not df.empty:
        out = OUTPUT_DIR / "wb_gdp_growth.csv"
        df.to_csv(out, index=False)
        log.info("GDP growth (INDEC quarterly) saved → %s  (%d rows)", out.name, len(df))
        return df

    # --- Fallback: World Bank annual ---
    log.warning("WB GDP growth: quarterly unavailable — trying annual")
    df = _fetch_indicator("NY.GDP.MKTP.KD.ZG", mrv=12)
    if df is None or df.empty:
        log.warning("WB GDP growth: all sources failed.")
        return None

    df.rename(columns={"value": "gdp_growth_pct"}, inplace=True)
    df = df.tail(quarters).reset_index(drop=True)

    out = OUTPUT_DIR / "wb_gdp_growth.csv"
    df.to_csv(out, index=False)
    log.info("WB GDP growth (annual fallback) saved → %s  (%d rows)", out.name, len(df))
    return df


def fetch_gdp_components(quarters: int = 8) -> pd.DataFrame | None:
    """
    Return quarterly YoY growth for each GDP expenditure component (C+I+G+X-M).
    Columns: date, quarter, C_pct, G_pct, I_pct, X_pct, M_pct, GDP_pct

    Sources (datos.gob.ar, base 2004 pesos, quarterly):
        C  = 4.2_MGCP_2004_T_25   Consumo privado
        G  = 4.2_DGCP_2004_T_30   Consumo público
        I  = 4.2_DGIT_2004_T_25   Inversión bruta interna fija
        X  = 4.2_DGE_2004_T_26    Exportaciones
        M  = OGT - PIB             (Oferta global total minus PIB = Importaciones)
        OGT= 4.2_OGT_2004_T_19
        GDP= 9.2_PP2_2004_T_16
    """
    from datetime import date as _date, timedelta
    SERIES = {
        "C":   "4.2_MGCP_2004_T_25",
        "G":   "4.2_DGCP_2004_T_30",
        "I":   "4.2_DGIT_2004_T_25",
        "X":   "4.2_DGE_2004_T_26",
        "OGT": "4.2_OGT_2004_T_19",
        "GDP": "9.2_PP2_2004_T_16",
    }
    ids = ",".join(SERIES.values())
    start = (_date.today() - timedelta(days=(quarters + 6) * 95)).strftime("%Y-%m-%d")

    params = {"ids": ids, "format": "json", "limit": quarters + 10,
              "sort": "asc", "start_date": start}
    data = fetch_json("https://apis.datos.gob.ar/series/api/series/",
                      params=params,
                      cache_key=f"datos_gdp_components_{quarters}_{start}")
    if data is None or "data" not in data:
        log.warning("GDP components: datos.gob.ar fetch failed.")
        return None

    meta = [m for m in data.get("meta", []) if "field" in m]
    col_ids = [m["field"]["id"] for m in meta]
    id_to_key = {v: k for k, v in SERIES.items()}
    columns = ["date"] + [id_to_key.get(c, c) for c in col_ids]

    df = pd.DataFrame(data["data"], columns=columns)
    df["date"] = pd.to_datetime(df["date"])
    for col in columns[1:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Derive imports level: M = OGT - GDP
    df["M"] = df["OGT"] - df["GDP"]

    # Compute YoY (pct_change vs same quarter prior year)
    result = df[["date"]].copy()
    for comp in ["C", "G", "I", "X", "M", "GDP"]:
        result[f"{comp}_pct"] = df[comp].pct_change(4) * 100

    result = result.dropna().tail(quarters).reset_index(drop=True)

    # Quarter label
    eoq = result["date"] + pd.offsets.QuarterEnd(0)
    period = eoq.dt.to_period("Q")
    result["date"] = period.astype(str)
    result["quarter"] = "Q" + period.dt.quarter.astype(str) + " " + period.dt.year.astype(str)
    result = result[["date", "quarter", "C_pct", "G_pct", "I_pct", "X_pct", "M_pct", "GDP_pct"]]

    out = OUTPUT_DIR / "gdp_components.csv"
    result.to_csv(out, index=False)
    log.info("GDP components saved → %s  (%d rows)", out.name, len(result))
    return result


def _fetch_gdp_indec_quarterly(quarters: int) -> pd.DataFrame | None:
    """
    Fetch quarterly real GDP level from datos.gob.ar and compute YoY % change.
    Series: 9.2_PP2_2004_T_16 (PIB a precios constantes 2004, trimestral)
    """
    from datetime import date, timedelta
    series_id = "9.2_PP2_2004_T_16"
    start = (date.today() - timedelta(days=(quarters + 6) * 95)).strftime("%Y-%m-%d")
    params = {
        "ids": series_id,
        "format": "json",
        "limit": quarters + 10,
        "sort": "asc",
        "start_date": start,
    }
    cache_key = f"datos_{series_id}_{quarters}_{start}"
    data = fetch_json("https://apis.datos.gob.ar/series/api/series/",
                      params=params, cache_key=cache_key)
    if data is None or "data" not in data:
        return None

    meta = data.get("meta", [])
    field_meta = [m for m in meta if "field" in m]
    columns = ["date"] + [m["field"]["id"] for m in field_meta]
    if len(columns) < 2:
        return None

    df = pd.DataFrame(data["data"], columns=columns)
    df["date"] = pd.to_datetime(df["date"])
    df[series_id] = pd.to_numeric(df[series_id], errors="coerce")

    # YoY: compare to same quarter one year prior (4 rows back)
    df["gdp_growth_pct"] = df[series_id].pct_change(4) * 100
    df = df.dropna(subset=["gdp_growth_pct"]).tail(quarters).reset_index(drop=True)

    # Label by end-of-quarter (Bloomberg convention: Sep 30 for Q3, not Jul 1)
    eoq = df["date"] + pd.offsets.QuarterEnd(0)
    df["date"] = eoq.dt.to_period("Q").astype(str)
    df = df[["date", "gdp_growth_pct"]]
    return df if not df.empty else None


# ---------------------------------------------------------------------------
# Public: external debt / GNI ratio (annual)
# ---------------------------------------------------------------------------
def fetch_external_debt(years: int = 8) -> pd.DataFrame | None:
    """
    Return external debt stocks as % of GNI (annual).
    Columns: date, ext_debt_pct_gni
    """
    df = _fetch_indicator("DT.DOD.DECT.GN.ZS", mrv=years + 2)
    if df is None or df.empty:
        log.warning("WB external debt: failed.")
        return None

    df.rename(columns={"value": "ext_debt_pct_gni"}, inplace=True)
    df = df.tail(years).reset_index(drop=True)

    out = OUTPUT_DIR / "wb_ext_debt.csv"
    df.to_csv(out, index=False)
    log.info("WB ext debt saved → %s  (%d rows)", out.name, len(df))
    return df


# ---------------------------------------------------------------------------
# Public: current account balance % GDP (annual fallback)
# ---------------------------------------------------------------------------
def fetch_current_account_pct_gdp(years: int = 8) -> pd.DataFrame | None:
    """Annual current account balance as % of GDP (World Bank fallback)."""
    df = _fetch_indicator("BN.CAB.XOKA.GD.ZS", mrv=years + 2)
    if df is None or df.empty:
        log.warning("WB CA balance: failed.")
        return None

    df.rename(columns={"value": "current_account_pct_gdp"}, inplace=True)
    df = df.tail(years).reset_index(drop=True)

    out = OUTPUT_DIR / "wb_current_account_pct_gdp.csv"
    df.to_csv(out, index=False)
    log.info("WB CA pct-GDP saved → %s  (%d rows)", out.name, len(df))
    return df


if __name__ == "__main__":
    print(fetch_gdp_growth())
    print(fetch_external_debt())
