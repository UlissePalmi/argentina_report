"""
SVAR data preparation — Layer 3.5.

Loads and aligns five monthly series for the Argentine inflation SVAR:
  1. cpi_mom_pct        — CPI month-on-month % change (inflation)
  2. fx_mom_pct         — USD/ARS MoM % change (exchange rate shock)
  3. emae_yoy_pct       — EMAE YoY % change (activity)
  4. real_total_credit_yoy_pct — Real total credit YoY % change
  5. real_wage_yoy_pct  — Real wage YoY % change

Strategy: try to build a 120-month panel by re-fetching at extended window
(same sources, longer history). Falls back to the 24-month CSVs if fetch fails.
Minimum 48 observations required for any meaningful VAR estimation.

Binding constraint: real wages and real credit series start Dec 2017, so the
inner-joined panel covers roughly Dec 2017-present (~97 obs).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from utils import get_logger

log = get_logger("svar.data_prep")

SVAR_DIR = Path(__file__).parent.parent / "data" / "svar"

# Variable ordering: most exogenous → most endogenous (Cholesky identification)
VAR_COLS = [
    "m2_yoy_pct",
    "fx_mom_pct",
    "emae_yoy_pct",
    "real_total_credit_yoy_pct",
    "real_wage_yoy_pct",
    "cpi_mom_pct",
]

MIN_OBS = 48    # hard minimum for estimation
TARGET_MONTHS = 120  # aim for 10 years — binding constraint is M2 series start (Sep 2013)


def _load_extended() -> pd.DataFrame | None:
    """
    Try to assemble a 72-month panel by calling existing fetch functions
    at an extended window. Returns None if any fetch fails critically.
    """
    try:
        from ingestion.inflation   import fetch_cpi
        from ingestion.reserves    import fetch_exchange_rate, fetch_money_supply
        from ingestion.consumption import fetch_consumption, compute_real_values
        from ingestion.gdp         import fetch_emae

        log.info("SVAR data_prep: fetching extended %d-month history...", TARGET_MONTHS)

        cpi_df  = fetch_cpi(months=TARGET_MONTHS)
        fx_df   = fetch_exchange_rate(months=TARGET_MONTHS)
        cons_df = fetch_consumption(months=TARGET_MONTHS)
        emae_df = fetch_emae(months=TARGET_MONTHS)
        m2_df   = fetch_money_supply(months=TARGET_MONTHS)

        if cpi_df is None or fx_df is None or cons_df is None or emae_df is None:
            log.warning("SVAR data_prep: one or more extended fetches failed.")
            return None

        cons_df = compute_real_values(cons_df, cpi_df)

        return _assemble(cpi_df, fx_df, cons_df, emae_df, m2_df)

    except Exception as exc:
        log.warning("SVAR data_prep: extended fetch failed (%s).", exc)
        return None


def _load_from_csv() -> pd.DataFrame | None:
    """
    Fallback: load from the 24-month CSVs already written by the main pipeline.
    """
    base = Path(__file__).parent.parent / "data"
    try:
        cpi_df  = pd.read_csv(base / "inflation/indec_cpi.csv",    parse_dates=["date"])
        fx_df   = pd.read_csv(base / "external/bcra_fx.csv",       parse_dates=["date"])
        cons_df = pd.read_csv(base / "consumption/consumption.csv", parse_dates=["date"])
        emae_df = pd.read_csv(base / "gdp/emae.csv",               parse_dates=["date"])
        m2_path = base / "external/bcra_m2.csv"
        m2_df   = pd.read_csv(m2_path, parse_dates=["date"]) if m2_path.exists() else None
        return _assemble(cpi_df, fx_df, cons_df, emae_df, m2_df)
    except Exception as exc:
        log.error("SVAR data_prep: CSV fallback also failed (%s).", exc)
        return None


def _assemble(cpi_df: pd.DataFrame, fx_df: pd.DataFrame,
              cons_df: pd.DataFrame, emae_df: pd.DataFrame,
              m2_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Merge DataFrames onto a common monthly date index."""
    # CPI mom
    cpi = cpi_df[["date", "cpi_mom_pct"]].dropna().set_index("date")

    # FX → MoM % change
    fx = fx_df[["date", "usd_ars"]].dropna().set_index("date").sort_index()
    fx["fx_mom_pct"] = fx["usd_ars"].pct_change() * 100
    fx = fx[["fx_mom_pct"]].dropna()

    # EMAE
    emae = emae_df[["date", "emae_yoy_pct"]].dropna().set_index("date")

    # Consumption (wages + credit)
    credit_col = "real_total_credit_yoy_pct"
    wage_col   = "real_wage_yoy_pct"
    cons_cols  = [c for c in [credit_col, wage_col] if c in cons_df.columns]
    cons = cons_df[["date"] + cons_cols].dropna(subset=cons_cols, how="any").set_index("date")

    panel = (cpi
             .join(fx,   how="inner")
             .join(emae, how="inner")
             .join(cons, how="inner")
             .sort_index())

    # M2 — join if available; rows without M2 are dropped (inner join)
    if m2_df is not None and "m2_yoy_pct" in m2_df.columns:
        m2 = m2_df[["date", "m2_yoy_pct"]].dropna().set_index("date")
        panel = panel.join(m2, how="inner")
        log.info("SVAR data_prep: M2 joined (%d rows after inner join)", len(panel))
    else:
        log.warning("SVAR data_prep: M2 not available — m2_yoy_pct will be absent from panel.")

    # Ensure all target columns exist
    for col in VAR_COLS:
        if col not in panel.columns:
            log.warning("SVAR data_prep: column '%s' missing from panel.", col)

    return panel[[c for c in VAR_COLS if c in panel.columns]]


def _run_adf(series: pd.Series) -> dict:
    """ADF test with automatic lag selection (AIC). Returns dict with key stats."""
    from statsmodels.tsa.stattools import adfuller
    clean = series.dropna()
    if len(clean) < 10:
        return {"statistic": None, "p_value": None, "stationary": None}
    result = adfuller(clean, autolag="AIC")
    return {
        "statistic": round(float(result[0]), 4),
        "p_value":   round(float(result[1]), 4),
        "lags_used": int(result[2]),
        "stationary": bool(result[1] < 0.10),   # 10% threshold
    }


def prepare_data() -> pd.DataFrame | None:
    """
    Main entry point. Returns aligned panel DataFrame with VAR_COLS columns,
    or None if insufficient data.
    """
    SVAR_DIR.mkdir(parents=True, exist_ok=True)

    panel = _load_extended()
    if panel is None or len(panel) < MIN_OBS:
        if panel is not None:
            log.warning("SVAR data_prep: extended fetch gave only %d rows (<%d). Trying CSV fallback.", len(panel), MIN_OBS)
        panel = _load_from_csv()

    if panel is None or panel.empty:
        log.error("SVAR data_prep: no data available. Skipping SVAR.")
        return None

    n = len(panel)
    if n < MIN_OBS:
        log.warning(
            "SVAR data_prep: only %d observations after alignment (minimum %d recommended). "
            "Results will have very wide confidence bands.", n, MIN_OBS
        )

    log.info("SVAR data_prep: panel ready — %d observations, %s to %s",
             n, panel.index.min().strftime("%Y-%m"), panel.index.max().strftime("%Y-%m"))

    # ADF stationarity tests
    log.info("SVAR data_prep: ADF stationarity tests (H0: unit root, reject if p < 0.10)")
    adf_results = {}
    for col in panel.columns:
        r = _run_adf(panel[col])
        adf_results[col] = r
        flag = "STATIONARY" if r.get("stationary") else "NON-STATIONARY / insufficient"
        log.info("  %-35s  stat=%s  p=%s  [%s]",
                 col,
                 f"{r['statistic']:.3f}" if r["statistic"] is not None else "n/a",
                 f"{r['p_value']:.3f}"   if r["p_value"]   is not None else "n/a",
                 flag)

    panel.to_csv(SVAR_DIR / "svar_input.csv")
    log.info("SVAR data_prep: saved -> data/svar/svar_input.csv  (%d rows x %d cols)",
             len(panel), len(panel.columns))

    return panel
