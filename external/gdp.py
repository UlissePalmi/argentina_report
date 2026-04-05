"""GDP: quarterly growth, expenditure components, EMAE monthly activity."""

import pandas as pd

from utils import GDP_DIR, get_logger
from external.client import DatosClient, WorldBankClient, _start

log = get_logger("fetch.gdp")
_d  = DatosClient()
_wb = WorldBankClient()

GDP_ID         = "9.2_PP2_2004_T_16"
GDP_COMPONENTS = {"C": "4.2_MGCP_2004_T_25", "G": "4.2_DGCP_2004_T_30",
                  "I": "4.2_DGIT_2004_T_25", "X": "4.2_DGE_2004_T_26",
                  "OGT": "4.2_OGT_2004_T_19", "GDP": "9.2_PP2_2004_T_16"}
EMAE_HEADLINE  = "143.3_ICE_SERVIA_2004_A_25"
EMAE_SECTORS   = {"agricultura": "11.3_ISOM_2004_M_39", "mineria":      "11.3_ISD_2004_M_26",
                  "industria":   "11.3_VMASD_2004_M_23", "comercio":    "11.3_AGCS_2004_M_41",
                  "construccion":"11.3_VMATC_2004_M_12", "financiero":  "11.3_IM_2004_M_25",
                  "transporte":  "11.3_EMC_2004_M_25"}

# Nominal (current-price) GDP expenditure components — millions of current pesos
GDP_NOM_COMPONENTS = {
    "C_nom":   "4.4_DGCP_2004_T_27",   # private consumption
    "G_nom":   "4.4_DGCP_2004_T_30",   # government consumption
    "X_nom":   "4.4_DGE_2004_T_26",    # exports
    "M_nom":   "4.4_OGI_2004_T_25",    # imports
    "GDP_nom": "4.4_OGP_2004_T_17",    # GDP at market prices
}
# FBCF sub-components at current prices (nominal) — summed to get I_nom
FBCF_NOM_SUBCOMP = {
    "fbcf_constr_nom":    "4.4_DGIC_2004_T_32",
    "fbcf_maq_nac_nom":   "4.4_DGIEDPN_2004_T_54",
    "fbcf_maq_imp_nom":   "4.4_DGIEDPI_2004_T_55",
    "fbcf_transport_nom": "4.4_DGIEDPMTT_2004_T_53",
}
# FBCF sub-components at constant 2004 prices (for YoY growth and structural analysis)
FBCF_REAL_SUBCOMP = {
    "fbcf_constr":    "4.2_DGIC_2004_T_32",
    "fbcf_maq_nac":   "4.2_DGIEDPN_2004_T_54",
    "fbcf_maq_imp":   "4.2_DGIEDPI_2004_T_55",
    "fbcf_transport": "4.2_DGIEDPMTT_2004_T_53",
}


def _to_quarter_period(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise date to quarter period strings (in-place) and add 'quarter' column."""
    period = (df["date"] + pd.offsets.QuarterEnd(0)).dt.to_period("Q")
    df["date"]    = period.astype(str)
    df["quarter"] = "Q" + period.dt.quarter.astype(str) + " " + period.dt.year.astype(str)
    return df


def fetch_gdp_growth(quarters: int = 10) -> pd.DataFrame | None:
    """Columns: date (period str), gdp_growth_pct. Primary: INDEC quarterly. Fallback: WB annual."""
    start = _start(quarters * 3, buffer=18)
    raw = _d.fetch([GDP_ID], limit=quarters + 10, start_date=start)
    if raw is not None and GDP_ID in raw.columns:
        raw["gdp_growth_pct"] = raw[GDP_ID].pct_change(4) * 100
        raw = raw.dropna(subset=["gdp_growth_pct"]).tail(quarters).reset_index(drop=True)
        raw["date"] = (raw["date"] + pd.offsets.QuarterEnd(0)).dt.to_period("Q").astype(str)
        df = raw[["date", "gdp_growth_pct"]]
        df.to_csv(GDP_DIR / "wb_gdp_growth.csv", index=False)
        log.info("GDP growth (INDEC quarterly) saved -> wb_gdp_growth.csv  (%d rows)", len(df))
        return df

    log.warning("GDP growth: quarterly unavailable -- trying World Bank annual")
    df = _wb.fetch("NY.GDP.MKTP.KD.ZG", mrv=12)
    if df is None:
        log.warning("GDP growth: all sources failed.")
        return None
    df = df.rename(columns={"value": "gdp_growth_pct"}).tail(quarters).reset_index(drop=True)
    df.to_csv(GDP_DIR / "wb_gdp_growth.csv", index=False)
    log.info("GDP growth (WB annual fallback) saved -> wb_gdp_growth.csv  (%d rows)", len(df))
    return df


def fetch_gdp_components(quarters: int = 8) -> pd.DataFrame | None:
    """
    Constant-2004-price (real) expenditure components.
    Columns: date, quarter, C_pct, G_pct, I_pct, X_pct, M_pct, GDP_pct,
             C_share_real, G_share_real, I_share_real, X_share_real, M_share_real, NX_share_real
    """
    from utils import fetch_json
    start = _start(quarters * 3, buffer=18)
    ids   = list(GDP_COMPONENTS.values())
    raw   = fetch_json(DatosClient.URL,
                       params={"ids": ",".join(ids), "format": "json",
                               "limit": quarters + 10, "sort": "asc", "start_date": start},
                       cache_key=f"datos_gdp_components_{quarters}_{start}")
    if raw is None or "data" not in raw:
        log.warning("GDP components: fetch failed.")
        return None

    id_to_key = {v: k for k, v in GDP_COMPONENTS.items()}
    col_ids   = [m["field"]["id"] for m in raw.get("meta", []) if "field" in m]
    cols      = ["date"] + [id_to_key.get(c, c) for c in col_ids]
    df        = pd.DataFrame(raw["data"], columns=cols)
    df["date"] = pd.to_datetime(df["date"])
    for c in cols[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["M"]  = df["OGT"] - df["GDP"]
    df["NX"] = df["X"] - df["M"]

    result = df[["date"]].copy()
    for comp in ["C", "G", "I", "X", "M", "GDP"]:
        result[f"{comp}_pct"] = df[comp].pct_change(4) * 100

    # Real (constant-price) shares — note: Fisher chain-linking means sum may not be 100%
    for comp in ["C", "G", "I", "X", "M"]:
        result[f"{comp}_share_real"] = df[comp] / df["GDP"] * 100
    result["NX_share_real"] = df["NX"] / df["GDP"] * 100

    result = result.dropna(subset=["C_pct", "G_pct", "I_pct", "GDP_pct"]).tail(quarters).reset_index(drop=True)
    result = _to_quarter_period(result)
    result = result[["date", "quarter",
                     "C_pct", "G_pct", "I_pct", "X_pct", "M_pct", "GDP_pct",
                     "C_share_real", "G_share_real", "I_share_real",
                     "X_share_real", "M_share_real", "NX_share_real"]]
    result.to_csv(GDP_DIR / "gdp_components.csv", index=False)
    log.info("GDP components saved -> gdp_components.csv  (%d rows)", len(result))
    return result


def fetch_gdp_nominal(quarters: int = 8) -> pd.DataFrame | None:
    """
    GDP expenditure composition at current prices (nominal pesos).
    I is the sum of 4 FBCF sub-components (construction, domestic machinery,
    imported machinery, transport) — excludes minor items like software/IP (~1% of GDP).
    Columns: date, quarter, C_share_nom, G_share_nom, I_share_nom, NX_share_nom,
             X_share_nom, M_share_nom
    """
    start = _start(quarters * 3, buffer=18)
    limit = quarters + 12

    b_main = _d.fetch(list(GDP_NOM_COMPONENTS.values()), limit=limit, start_date=start)
    if b_main is None or b_main.empty:
        log.warning("fetch_gdp_nominal: main components batch failed.")
        return None

    b_fbcf = _d.fetch(list(FBCF_NOM_SUBCOMP.values()), limit=limit, start_date=start)

    key_main = {v: k for k, v in GDP_NOM_COMPONENTS.items()}
    b_main = b_main.rename(columns=key_main)
    result = b_main[["date"] + [k for k in GDP_NOM_COMPONENTS if k in b_main.columns]].copy()
    for col in GDP_NOM_COMPONENTS:
        if col in result.columns:
            result[col] = pd.to_numeric(result[col], errors="coerce")

    # Sum FBCF sub-components to get I_nom
    if b_fbcf is not None and not b_fbcf.empty:
        key_fbcf = {v: k for k, v in FBCF_NOM_SUBCOMP.items()}
        b_fbcf = b_fbcf.rename(columns=key_fbcf)
        fbcf_cols = [k for k in FBCF_NOM_SUBCOMP if k in b_fbcf.columns]
        result = result.merge(b_fbcf[["date"] + fbcf_cols], on="date", how="left")
        result["I_nom"] = result[fbcf_cols].sum(axis=1, min_count=len(fbcf_cols) // 2)

    if "GDP_nom" not in result.columns:
        log.warning("fetch_gdp_nominal: GDP_nom missing.")
        return None

    gdp = result["GDP_nom"]
    for comp in ["C_nom", "G_nom", "I_nom", "X_nom", "M_nom"]:
        if comp in result.columns:
            result[f"{comp.replace('_nom', '_share_nom')}"] = result[comp] / gdp * 100
    if "X_nom" in result.columns and "M_nom" in result.columns:
        result["NX_share_nom"] = (result["X_nom"] - result["M_nom"]) / gdp * 100

    share_cols = [c for c in ["C_share_nom", "G_share_nom", "I_share_nom",
                               "X_share_nom", "M_share_nom", "NX_share_nom"]
                  if c in result.columns]
    result = result.dropna(subset=["C_share_nom", "G_share_nom"]).tail(quarters).reset_index(drop=True)
    result = _to_quarter_period(result)
    result = result[["date", "quarter"] + share_cols]
    result.to_csv(GDP_DIR / "gdp_nominal.csv", index=False)
    log.info("GDP nominal shares saved -> gdp_nominal.csv  (%d rows)", len(result))
    return result


def fetch_fbcf_breakdown(quarters: int = 12) -> pd.DataFrame | None:
    """
    FBCF sub-components at constant 2004 prices.
    Provides share within total FBCF and YoY growth for each sub-component.
    Dollar classification:
      - Construction, domestic machinery → dollar-neutral
      - Imported machinery, transport    → dollar-draining
    Columns: date, quarter, fbcf_constr_share/yoy, fbcf_maq_nac_share/yoy,
             fbcf_maq_imp_share/yoy, fbcf_transport_share/yoy
    """
    start = _start(quarters * 3, buffer=18)
    limit = quarters + 16  # extra for pct_change(4)

    batch = _d.fetch(list(FBCF_REAL_SUBCOMP.values()), limit=limit, start_date=start)
    if batch is None or batch.empty:
        log.warning("fetch_fbcf_breakdown: failed.")
        return None

    key_map = {v: k for k, v in FBCF_REAL_SUBCOMP.items()}
    batch = batch.rename(columns=key_map)

    result = batch[["date"]].copy()
    cols_avail = [k for k in FBCF_REAL_SUBCOMP if k in batch.columns]
    for col in cols_avail:
        result[col] = pd.to_numeric(batch[col], errors="coerce")
        result[f"{col}_yoy"] = batch[col].pct_change(4) * 100

    total_fbcf = result[cols_avail].sum(axis=1, min_count=1)
    for col in cols_avail:
        result[f"{col}_share"] = result[col] / total_fbcf * 100

    result = result.dropna(subset=cols_avail, how="all").tail(quarters).reset_index(drop=True)
    result = _to_quarter_period(result)

    keep = ["date", "quarter"]
    for col in cols_avail:
        keep += [f"{col}_share", f"{col}_yoy"]
    result = result[[c for c in keep if c in result.columns]]
    result.to_csv(GDP_DIR / "gdp_fbcf.csv", index=False)
    log.info("FBCF breakdown saved -> gdp_fbcf.csv  (%d rows)", len(result))
    return result


def fetch_emae(months: int = 24) -> pd.DataFrame | None:
    """Columns: date, emae_yoy_pct, agricultura_pct, … transporte_pct"""
    start = _start(months)
    h = _d.fetch([EMAE_HEADLINE], limit=months + 20, start_date=start)
    if h is None or h.empty:
        log.warning("EMAE headline: fetch failed.")
        return None

    result = h[["date"]].copy()
    result["emae_yoy_pct"] = h[EMAE_HEADLINE] * 100

    s = _d.fetch(list(EMAE_SECTORS.values()), limit=months + 20, start_date=start)
    if s is not None and not s.empty:
        for label, sid in EMAE_SECTORS.items():
            if sid in s.columns:
                s[f"{label}_pct"] = s[sid].pct_change(12) * 100
        avail  = [f"{k}_pct" for k in EMAE_SECTORS if f"{k}_pct" in s.columns]
        result = result.merge(s[["date"] + avail].dropna(subset=avail, how="all"),
                              on="date", how="left")
    else:
        log.warning("EMAE sectors: fetch failed -- headline only.")

    result = result.dropna(subset=["emae_yoy_pct"]).tail(months).reset_index(drop=True)
    result.to_csv(GDP_DIR / "emae.csv", index=False)
    log.info("EMAE saved -> emae.csv  (%d rows, latest: %s)",
             len(result), result["date"].max().strftime("%Y-%m"))
    return result
