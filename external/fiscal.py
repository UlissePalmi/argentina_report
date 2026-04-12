"""
External sector: fiscal balance (public sector surplus/deficit).

Primary: datos.gob.ar — IMIG monthly series (Secretaria de Hacienda).
  Fetches both primary result and financial result (after interest) simultaneously.
  Normalises to % GDP using INDEC quarterly nominal GDP (datos.gob.ar, annualized rates).
  For months beyond last available quarter, extends using CPI index.

Fallback: World Bank NY.GDP.MKTP.CN (annual) if INDEC quarterly unavailable.
Fiscal fallback: World Bank GC.BAL.CASH.GD.ZS (annual, % GDP).

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

# INDEC quarterly nominal GDP — annualized rates, millions of ARS current prices
# Source: Secretaría de Programación Macroeconómica / INDEC, via datos.gob.ar
INDEC_GDP_QUARTERLY = "166.2_PPIB_0_0_3"

# World Bank: annual nominal GDP in current ARS (fallback if INDEC quarterly unavailable)
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
    Normalise ARS bn columns to % of GDP.

    Primary: INDEC quarterly nominal GDP (datos.gob.ar 166.2_PPIB_0_0_3).
      Values are annualized quarterly rates in millions of ARS (current prices).
      Each month in a quarter gets that quarter's annualized GDP as its denominator.
      Months beyond the last published quarter are CPI-scaled forward.

    Fallback: World Bank NY.GDP.MKTP.CN (annual, interpolated to monthly + CPI extension).

    Formula: fiscal_*_pct_gdp = (monthly_ars_bn / (annualized_gdp_bn / 12)) * 100
    """
    gdp_monthly = _build_gdp_monthly(df)
    if gdp_monthly is None:
        return df

    df["date"] = pd.to_datetime(df["date"])
    merged = df.merge(gdp_monthly, on="date", how="left")
    merged["_monthly_gdp"] = merged["gdp_ann_ars_bn"] / 12

    for ars_col, pct_col in [
        ("fiscal_primary_ars_bn",   "fiscal_primary_pct_gdp"),
        ("fiscal_financial_ars_bn", "fiscal_financial_pct_gdp"),
    ]:
        if ars_col in merged.columns and merged["_monthly_gdp"].notna().any():
            merged[pct_col] = (merged[ars_col] / merged["_monthly_gdp"] * 100).round(2)

    return merged.drop(columns=["gdp_ann_ars_bn", "_monthly_gdp"], errors="ignore")


def _build_gdp_monthly(df: pd.DataFrame) -> pd.DataFrame | None:
    """
    Build a monthly series of annualized nominal GDP in ARS bn.

    Tries INDEC quarterly first, falls back to WB annual.
    For months beyond the last data point, extends using CPI.
    Returns DataFrame with columns: date, gdp_ann_ars_bn.
    """
    # ------------------------------------------------------------------
    # Option 1: INDEC quarterly (datos.gob.ar) — annualized rates
    # ------------------------------------------------------------------
    try:
        raw_q = _d.fetch([INDEC_GDP_QUARTERLY], limit=40, start_date="2018-01-01")
        if raw_q is not None and INDEC_GDP_QUARTERLY in raw_q.columns:
            gdp_q = raw_q[["date", INDEC_GDP_QUARTERLY]].copy()
            gdp_q["date"] = pd.to_datetime(gdp_q["date"])
            # values are millions ARS annualized → convert to ARS bn
            gdp_q["gdp_ann_ars_bn"] = pd.to_numeric(gdp_q[INDEC_GDP_QUARTERLY], errors="coerce") / 1_000
            gdp_q = gdp_q[["date", "gdp_ann_ars_bn"]].dropna().sort_values("date")

            if not gdp_q.empty:
                # Each quarterly point is the annualized rate for that quarter's 3 months.
                # Expand: for each quarter start date Q, assign the value to Q, Q+1m, Q+2m.
                rows = []
                for _, row in gdp_q.iterrows():
                    for m in range(3):
                        rows.append({
                            "date":          row["date"] + pd.DateOffset(months=m),
                            "gdp_ann_ars_bn": row["gdp_ann_ars_bn"],
                        })
                gdp_monthly = pd.DataFrame(rows).sort_values("date").drop_duplicates("date")

                # Extend beyond last quarter using CPI
                last_date = gdp_monthly["date"].iloc[-1]
                last_gdp  = float(gdp_monthly["gdp_ann_ars_bn"].iloc[-1])
                gdp_monthly = _cpi_extend(gdp_monthly, last_date, last_gdp, ref_date=last_date)

                log.info("Fiscal %% GDP: INDEC quarterly GDP (last Q: %s)", str(gdp_q["date"].iloc[-1])[:7])
                return gdp_monthly
    except Exception as e:
        log.warning("INDEC quarterly GDP failed: %s", e)

    # ------------------------------------------------------------------
    # Option 2: World Bank annual (interpolated to monthly + CPI extension)
    # ------------------------------------------------------------------
    try:
        raw_wb = _wb.fetch(WB_GDP_ARS, mrv=10)
        if raw_wb is None or raw_wb.empty:
            log.warning("Fiscal %% GDP: both INDEC quarterly and WB unavailable")
            return None

        gdp_ann = raw_wb.copy()
        gdp_ann["date"] = pd.to_datetime(gdp_ann["date"].astype(str), format="%Y")
        gdp_ann["gdp_ann_ars_bn"] = pd.to_numeric(gdp_ann["value"], errors="coerce") / 1e9
        gdp_ann = gdp_ann[["date", "gdp_ann_ars_bn"]].dropna().sort_values("date")
        if gdp_ann.empty:
            return None

        gdp_monthly = (
            gdp_ann.set_index("date")
            .resample("MS")
            .interpolate(method="linear")
            .reset_index()
        )

        last_wb_year = int(gdp_ann["date"].iloc[-1].year)
        last_date    = gdp_monthly["date"].iloc[-1]
        last_gdp     = float(gdp_ann["gdp_ann_ars_bn"].iloc[-1])

        # CPI scaling only for months after the last WB year
        first_cpi_date = pd.Timestamp(year=last_wb_year + 1, month=1, day=1)
        ref_date       = pd.Timestamp(year=last_wb_year,     month=12, day=1)
        gdp_monthly    = _cpi_extend(gdp_monthly, last_date, last_gdp,
                                     ref_date=ref_date, first_scaled=first_cpi_date)

        log.info("Fiscal %% GDP: WB annual GDP (last year: %s)", last_wb_year)
        return gdp_monthly

    except Exception as e:
        log.warning("Could not build GDP monthly series: %s", e)
        return None


def _cpi_extend(gdp_monthly: pd.DataFrame, last_date: pd.Timestamp,
                last_gdp: float, ref_date: pd.Timestamp,
                first_scaled: pd.Timestamp | None = None) -> pd.DataFrame:
    """
    Append CPI-scaled monthly GDP rows from last_date+1m through ~2.5 years forward.

    ref_date:     the month whose CPI level = scale 1.0 (the reference point)
    first_scaled: first month that gets CPI scaling; months before this use scale=1.0
                  (default: all future months are CPI-scaled from ref_date)
    """
    future_dates = pd.date_range(
        start=last_date + pd.DateOffset(months=1),
        periods=30, freq="MS",
    )
    if first_scaled is None:
        first_scaled = future_dates[0]

    # Load CPI index
    cpi_map: dict = {}
    try:
        from utils import EXTERNAL_DIR as _ED
        cpi_path = _ED.parent / "inflation" / "indec_cpi.csv"
        if cpi_path.exists():
            cpi_df = pd.read_csv(cpi_path, parse_dates=["date"])
            cpi_df = cpi_df[["date", "cpi_index"]].dropna().sort_values("date")
            # Reference CPI: last available month on or before ref_date
            ref_rows = cpi_df[cpi_df["date"] <= ref_date]
            if ref_rows.empty:
                ref_rows = cpi_df   # fall back to earliest
            ref_cpi = float(ref_rows["cpi_index"].iloc[-1])
            for _, row in cpi_df[cpi_df["date"] >= first_scaled].iterrows():
                cpi_map[row["date"]] = float(row["cpi_index"]) / ref_cpi
    except Exception:
        pass

    future_rows = []
    running_scale = 1.0
    for d in sorted(future_dates):
        if d >= first_scaled and d in cpi_map:
            running_scale = cpi_map[d]
        elif d < first_scaled:
            running_scale = 1.0
        future_rows.append({"date": d, "gdp_ann_ars_bn": last_gdp * running_scale})

    result = pd.concat([gdp_monthly, pd.DataFrame(future_rows)], ignore_index=True)
    return result.sort_values("date").drop_duplicates("date")
