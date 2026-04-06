"""
External sector: fiscal balance (public sector surplus/deficit).

Primary: datos.gob.ar — Secretaría de Hacienda quarterly fiscal result series.
Fallback: World Bank GC.BAL.CASH.GD.ZS (annual, % GDP).

Output: data/external/fiscal_balance.csv
  Columns: date, fiscal_primary_ars_bn, fiscal_result_ars_bn,
           fiscal_primary_pct_gdp, fiscal_balance_pct_gdp
"""

from datetime import date

import pandas as pd

from utils import EXTERNAL_DIR, get_logger
from external.client import DatosClient, WorldBankClient, _start

log = _log = get_logger("fetch.fiscal")
_d  = DatosClient()
_wb = WorldBankClient()

# ---- datos.gob.ar candidate series (quarterly, ARS millions) ----
# These are tried in order; first one with data wins.
# Primary result = ingresos - gastos primarios (excludes interest)
# Financial result = primary minus interest payments
DATOS_CANDIDATES = [
    ("11.3_RPRIMARIO_2016_T_33", "fiscal_primary_ars_bn"),   # Resultado primario SPN
    ("11.3_RFGT_2016_T_33",      "fiscal_result_ars_bn"),    # Resultado financiero total
    ("30.3_RFMP_0_0_37",         "fiscal_primary_ars_bn"),   # Alternate monthly/quarterly
    ("11.3_RFMP_0_0_37",         "fiscal_primary_ars_bn"),   # Alternate ID variant
]

# World Bank fallback — annual cash surplus/deficit (% of GDP, + = surplus)
WB_INDICATOR   = "GC.BAL.CASH.GD.ZS"
WB_INDICATOR_P = "GC.NLD.TOTL.GD.ZS"  # net lending/borrowing % GDP (alt)


def fetch_fiscal(years: int = 6) -> pd.DataFrame | None:
    """
    Fetch public-sector fiscal balance.

    Returns DataFrame with columns:
      date, fiscal_primary_pct_gdp (or fiscal_balance_pct_gdp)

    Quarterly if datos.gob.ar succeeds; annual (WB) as fallback.
    """
    # ------------------------------------------------------------------
    # Attempt 1: datos.gob.ar quarterly fiscal series (ARS millions)
    # ------------------------------------------------------------------
    quarters = years * 4
    start    = _start(quarters * 3, buffer=12)

    for series_id, col_name in DATOS_CANDIDATES:
        raw = _d.fetch([series_id], limit=quarters + 8, start_date=start)
        if raw is not None and series_id in raw.columns:
            df = raw[["date", series_id]].rename(columns={series_id: col_name}).copy()
            df[col_name] = pd.to_numeric(df[col_name], errors="coerce") / 1_000  # M → B
            df = df.dropna(subset=[col_name]).tail(quarters)
            if not df.empty:
                log.info("Fiscal: datos.gob.ar series %s  (%d rows)", series_id, len(df))
                # Normalise to % GDP using nominal GDP if possible
                df = _add_pct_gdp(df, col_name)
                df.to_csv(EXTERNAL_DIR / "fiscal_balance.csv", index=False)
                log.info("Fiscal saved -> fiscal_balance.csv")
                return df

    log.warning("Fiscal: all datos.gob.ar candidates failed -- trying World Bank")

    # ------------------------------------------------------------------
    # Attempt 2: World Bank annual % GDP
    # ------------------------------------------------------------------
    for wb_id in [WB_INDICATOR, WB_INDICATOR_P]:
        raw_wb = _wb.fetch(wb_id, mrv=years + 3)
        if raw_wb is not None and not raw_wb.empty:
            df = raw_wb.rename(columns={"value": "fiscal_balance_pct_gdp"}).copy()
            df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y")
            df = df.dropna(subset=["fiscal_balance_pct_gdp"]).tail(years)
            if not df.empty:
                log.info("Fiscal: World Bank %s  (%d rows, annual)", wb_id, len(df))
                df.to_csv(EXTERNAL_DIR / "fiscal_balance.csv", index=False)
                log.info("Fiscal saved -> fiscal_balance.csv (annual WB)")
                return df

    log.warning("Fiscal: all sources failed.")
    return None


def _add_pct_gdp(df: pd.DataFrame, ars_col: str) -> pd.DataFrame:
    """
    Attempt to attach % GDP column using the nominal GDP CSV already on disk.
    If GDP file not available, returns df unchanged (column absent).
    """
    from utils import DATA_DIR
    gdp_path = DATA_DIR / "gdp" / "gdp_nominal.csv"
    if not gdp_path.exists():
        return df
    try:
        gdp = pd.read_csv(gdp_path, parse_dates=["date"])
        # Look for a nominal GDP level column
        gdp_col = next((c for c in gdp.columns
                        if "nominal" in c.lower() or "gdp_ars" in c.lower()
                        or "current" in c.lower()), None)
        if gdp_col is None:
            return df
        gdp = gdp[["date", gdp_col]].dropna()
        # Merge on nearest quarter
        df["_qdate"] = df["date"].dt.to_period("Q").dt.to_timestamp()
        gdp["_qdate"] = gdp["date"].dt.to_period("Q").dt.to_timestamp()
        merged = df.merge(gdp[["_qdate", gdp_col]], on="_qdate", how="left")
        # Compute: fiscal ARS bn / quarterly nominal GDP ARS bn * 100
        merged["fiscal_primary_pct_gdp"] = (
            merged[ars_col] / merged[gdp_col] * 100
        ).round(2)
        return merged.drop(columns=["_qdate", gdp_col])
    except Exception as e:
        log.warning("Could not compute fiscal % GDP: %s", e)
        return df
