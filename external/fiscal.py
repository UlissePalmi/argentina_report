"""
External sector: fiscal balance (public sector surplus/deficit).

Primary: datos.gob.ar — IMIG monthly series (Secretaria de Hacienda).
  Fetches both primary result and financial result (after interest) simultaneously.
  Normalises to % GDP using World Bank annual nominal GDP (ARS), interpolated monthly.

Fallback: World Bank GC.BAL.CASH.GD.ZS (annual, % GDP).

Output: data/external/fiscal_balance.csv
  Columns: date,
           fiscal_primary_ars_bn,   fiscal_financial_ars_bn,
           fiscal_primary_pct_gdp,  fiscal_financial_pct_gdp
"""

import pandas as pd

from utils import EXTERNAL_DIR, get_logger
from external.client import DatosClient, WorldBankClient, _start

log = get_logger("fetch.fiscal")
_d  = DatosClient()
_wb = WorldBankClient()

# ---- datos.gob.ar series (monthly, ARS millions, fetched together) ----
# Primary result  = revenues - primary spending (excludes interest)
# Financial result = primary result - interest payments
# Source: IMIG — Informe Mensual de Ingresos y Gastos, Secretaria de Hacienda
PRIMARY_ID   = "452.3_RESULTADO_RIO_0_M_18_54"   # IMIG resultado primario (excl. interest)
FINANCIAL_ID = "452.3_RESULTADO_ERO_0_M_20_25"   # IMIG resultado financiero (incl. interest) -- same dataset

# World Bank: annual nominal GDP in current ARS (for % GDP normalization)
WB_GDP_ARS   = "NY.GDP.MKTP.CN"

# World Bank fallback fiscal indicators (% GDP, annual)
WB_FISCAL_INDICATORS = ["GC.BAL.CASH.GD.ZS", "GC.NLD.TOTL.GD.ZS"]


def fetch_fiscal(years: int = 6) -> pd.DataFrame | None:
    """
    Fetch public-sector fiscal balance (monthly).

    Returns DataFrame with columns:
      date,
      fiscal_primary_ars_bn,   fiscal_financial_ars_bn,
      fiscal_primary_pct_gdp,  fiscal_financial_pct_gdp

    Falls back to World Bank annual % GDP if datos.gob.ar unavailable.
    """
    months = years * 12
    start  = _start(months, buffer=3)

    # ------------------------------------------------------------------
    # Step 1: Fetch both IMIG series in a single API call
    # ------------------------------------------------------------------
    raw = _d.fetch([PRIMARY_ID, FINANCIAL_ID], limit=months + 6, start_date=start)

    primary_ok   = raw is not None and PRIMARY_ID   in raw.columns
    financial_ok = raw is not None and FINANCIAL_ID in raw.columns

    if primary_ok or financial_ok:
        df = raw[["date"]].copy()

        if primary_ok:
            df["fiscal_primary_ars_bn"] = (
                pd.to_numeric(raw[PRIMARY_ID], errors="coerce") / 1_000
            )
        if financial_ok:
            df["fiscal_financial_ars_bn"] = (
                pd.to_numeric(raw[FINANCIAL_ID], errors="coerce") / 1_000
            )

        # Drop rows where both value columns are NaN, keep tail
        val_cols = [c for c in ["fiscal_primary_ars_bn", "fiscal_financial_ars_bn"]
                    if c in df.columns]
        df = df.dropna(subset=val_cols, how="all").tail(months).reset_index(drop=True)

        if not df.empty:
            log.info(
                "Fiscal: datos.gob.ar (%d rows; primary=%s financial=%s)",
                len(df), primary_ok, financial_ok,
            )
            df = _add_pct_gdp(df)
            df.to_csv(EXTERNAL_DIR / "fiscal_balance.csv", index=False)
            log.info("Fiscal saved -> fiscal_balance.csv")
            return df

    log.warning("Fiscal: datos.gob.ar failed -- trying World Bank")

    # ------------------------------------------------------------------
    # Step 2: World Bank annual % GDP fallback
    # ------------------------------------------------------------------
    for wb_id in WB_FISCAL_INDICATORS:
        raw_wb = _wb.fetch(wb_id, mrv=years + 3)
        if raw_wb is not None and not raw_wb.empty:
            df = raw_wb.rename(columns={"value": "fiscal_primary_pct_gdp"}).copy()
            df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y")
            df = df.dropna(subset=["fiscal_primary_pct_gdp"]).tail(years)
            if not df.empty:
                log.info("Fiscal: World Bank %s (%d rows, annual)", wb_id, len(df))
                df.to_csv(EXTERNAL_DIR / "fiscal_balance.csv", index=False)
                log.info("Fiscal saved -> fiscal_balance.csv (annual WB fallback)")
                return df

    log.warning("Fiscal: all sources failed.")
    return None


def _add_pct_gdp(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise ARS bn columns to % of GDP using World Bank annual nominal GDP (ARS).

    Strategy:
      - Fetch WB NY.GDP.MKTP.CN (annual ARS, current prices)
      - Interpolate to monthly using linear growth between years
      - fiscal_*_pct_gdp = (monthly ARS bn / (annual GDP ARS bn / 12)) * 100

    If WB fetch fails, returns df unchanged (% GDP columns absent).
    """
    try:
        raw_gdp = _wb.fetch(WB_GDP_ARS, mrv=10)
        if raw_gdp is None or raw_gdp.empty:
            log.warning("Fiscal % GDP: WB nominal GDP unavailable")
            return df

        # Build annual series: date = year-start, value in ARS bn
        gdp_ann = raw_gdp.copy()
        gdp_ann["date"] = pd.to_datetime(gdp_ann["date"].astype(str), format="%Y")
        gdp_ann["gdp_ann_ars_bn"] = pd.to_numeric(gdp_ann["value"], errors="coerce") / 1e9
        gdp_ann = gdp_ann[["date", "gdp_ann_ars_bn"]].dropna().sort_values("date")

        if gdp_ann.empty:
            return df

        # Interpolate to monthly: resample annual → monthly via linear fill.
        # resample("MS") only spans between the known annual points (e.g. Jan 2015 → Jan 2024).
        # Months after the last annual point need a separate forward extension.
        gdp_monthly = (
            gdp_ann.set_index("date")
            .resample("MS")
            .interpolate(method="linear")
            .reset_index()
        )

        # Extend from the month AFTER the last known annual point to cover the
        # current data range (WB typically lags 1 year so 2025/2026 months are missing).
        last_gdp  = float(gdp_ann["gdp_ann_ars_bn"].iloc[-1])
        last_date = gdp_monthly["date"].iloc[-1]          # last month produced by resample
        future_dates = pd.date_range(
            start=last_date + pd.DateOffset(months=1),   # one month after resample end
            periods=30, freq="MS",                        # cover 2.5 years forward
        )
        future_gdp = pd.DataFrame({
            "date":           future_dates,
            "gdp_ann_ars_bn": last_gdp,                  # flat at last known level (conservative)
        })
        gdp_monthly = pd.concat([gdp_monthly, future_gdp], ignore_index=True)
        gdp_monthly = gdp_monthly.sort_values("date").drop_duplicates("date")

        # Merge onto fiscal df
        df["date"] = pd.to_datetime(df["date"])
        merged = df.merge(gdp_monthly, on="date", how="left")

        # monthly GDP denominator = annual GDP / 12
        merged["_monthly_gdp"] = merged["gdp_ann_ars_bn"] / 12

        for ars_col, pct_col in [
            ("fiscal_primary_ars_bn",   "fiscal_primary_pct_gdp"),
            ("fiscal_financial_ars_bn", "fiscal_financial_pct_gdp"),
        ]:
            if ars_col in merged.columns and merged["_monthly_gdp"].notna().any():
                merged[pct_col] = (merged[ars_col] / merged["_monthly_gdp"] * 100).round(2)

        merged = merged.drop(columns=["gdp_ann_ars_bn", "_monthly_gdp"], errors="ignore")
        log.info("Fiscal % GDP computed using WB nominal GDP (ARS)")
        return merged

    except Exception as e:
        log.warning("Could not compute fiscal %% GDP: %s", e)
        return df
