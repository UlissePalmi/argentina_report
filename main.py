"""
Argentina Macro Report — main pipeline runner.

Run with:
    python main.py

The pipeline will:
  1. Pull data from BCRA, IMF, World Bank, and INDEC/datos.gob.ar
  2. Cache raw responses in /cache
  3. Write cleaned CSVs to /data/{module}/
  4. Generate charts (PNG) in /data/charts/
  5. Write PDF and markdown report to /data/reports/
"""

import sys
from pathlib import Path

from external.fetch    import (fetch_reserves, fetch_exchange_rate,
                                fetch_current_account, fetch_trade_balance,
                                fetch_external_debt, fetch_current_account_pct_gdp)
from gdp.fetch         import fetch_gdp_growth, fetch_gdp_components, fetch_emae
from inflation.fetch   import fetch_cpi
from consumption.fetch  import fetch_consumption, compute_real_values
from consumption.report import build_consumption_report
from report.build       import build_report
from utils              import get_logger

log = get_logger("main")


def run_pipeline() -> dict:
    log.info("=" * 60)
    log.info("Argentina Macro Report Pipeline -- starting")
    log.info("=" * 60)

    warnings: list[str] = []

    # ------------------------------------------------------------------
    # External (dollar situation)
    # ------------------------------------------------------------------
    log.info("[1/4a] Fetching BCRA reserves...")
    reserves_df = fetch_reserves(months=24)
    if reserves_df is None:
        warnings.append("BCRA reserves: FAILED -- check api.bcra.gob.ar")

    log.info("[1/4b] Fetching BCRA exchange rate...")
    fx_df = fetch_exchange_rate(months=24)
    if fx_df is None:
        warnings.append("BCRA FX rate: FAILED")

    log.info("[1/4c] Fetching current account balance...")
    ca_df = fetch_current_account(quarters=10)
    if ca_df is None:
        warnings.append("Current account: FAILED -- trying World Bank fallback")
        ca_df = fetch_current_account_pct_gdp(years=8)
        if ca_df is not None:
            log.info("  -> World Bank CA %%GDP fallback succeeded")

    log.info("[1/4d] Fetching trade balance...")
    trade_df = fetch_trade_balance(months=24)
    if trade_df is None:
        warnings.append("INDEC trade balance: FAILED -- all sources exhausted")

    log.info("[1/4e] Fetching external debt...")
    ext_debt_df = fetch_external_debt(years=8)
    if ext_debt_df is None:
        warnings.append("World Bank external debt: FAILED (non-critical)")

    # ------------------------------------------------------------------
    # GDP
    # ------------------------------------------------------------------
    log.info("[2/4a] Fetching GDP growth (quarterly)...")
    gdp_df = fetch_gdp_growth(quarters=10)
    if gdp_df is None:
        warnings.append("GDP growth: FAILED")

    log.info("[2/4b] Fetching GDP expenditure components (C+I+G+X-M)...")
    components_df = fetch_gdp_components(quarters=8)

    log.info("[2/4c] Fetching EMAE monthly activity (headline + sectors)...")
    emae_df = fetch_emae(months=24)

    # ------------------------------------------------------------------
    # Inflation
    # ------------------------------------------------------------------
    log.info("[3/4]  Fetching INDEC CPI...")
    cpi_df = fetch_cpi(months=24)
    if cpi_df is None:
        warnings.append("INDEC CPI: FAILED -- datos.gob.ar may be down")

    # ------------------------------------------------------------------
    # Consumption drivers
    # ------------------------------------------------------------------
    log.info("[4/4]  Fetching consumption drivers (wages, credit, deposits)...")
    consumption_df = fetch_consumption(months=24)
    if consumption_df is None:
        warnings.append("Consumption drivers: FAILED -- check datos.gob.ar wage/credit series")
    elif cpi_df is not None:
        consumption_df = compute_real_values(consumption_df, cpi_df)

    # ------------------------------------------------------------------
    # Build consumption deep-dive report
    # ------------------------------------------------------------------
    log.info("Building consumption deep-dive report...")
    consumption_report_path = build_consumption_report(
        consumption_df=consumption_df,
        cpi_df=cpi_df,
        components_df=components_df,
        emae_df=emae_df,
    )

    # ------------------------------------------------------------------
    # Build main report
    # ------------------------------------------------------------------
    log.info("Building report (PDF + Markdown)...")
    report_path = build_report(
        external_data={
            "trade_df":    trade_df,
            "reserves_df": reserves_df,
            "ca_df":       ca_df,
            "fx_df":       fx_df,
        },
        inflation_data={
            "cpi_df": cpi_df,
        },
        gdp_data={
            "gdp_df":        gdp_df,
            "components_df": components_df,
            "emae_df":       emae_df,
        },
        consumption_data={
            "consumption_df": consumption_df,
        },
    )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    log.info("=" * 60)
    log.info("Pipeline complete.")
    log.info("PDF:      %s", report_path["pdf"])
    log.info("Markdown: %s", report_path["md"])
    log.info("Consumption report: %s", consumption_report_path)

    all_dfs = {
        "reserves": reserves_df, "fx": fx_df, "ca": ca_df, "trade": trade_df,
        "ext_debt": ext_debt_df, "gdp": gdp_df, "components": components_df,
        "emae": emae_df, "cpi": cpi_df, "consumption": consumption_df,
    }
    succeeded = [k for k, v in all_dfs.items() if v is not None]
    failed    = [k for k, v in all_dfs.items() if v is None]
    log.info("Datasets fetched successfully: %s", ", ".join(succeeded) or "none")
    if failed:
        log.warning("Datasets that FAILED: %s", ", ".join(failed))
    if warnings:
        log.info("-" * 40)
        for w in warnings:
            log.warning("  * %s", w)
    log.info("=" * 60)
    report_path["consumption_report"] = consumption_report_path
    return report_path


if __name__ == "__main__":
    try:
        paths = run_pipeline()
        print(f"\nPDF:               {paths['pdf']}")
        print(f"Markdown:          {paths['md']}")
        print(f"Consumption report:{paths.get('consumption_report', 'n/a')}")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
    except Exception as e:
        log.exception("Pipeline crashed: %s", e)
        sys.exit(2)
