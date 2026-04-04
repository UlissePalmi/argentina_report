"""
Argentina Macro Report — main pipeline runner.

Run with:
    python main.py

The pipeline will:
  1. Pull data from BCRA, IMF, World Bank, and INDEC/datos.gob.ar
  2. Cache raw responses in /cache
  3. Write cleaned CSVs to /output
  4. Generate charts (PNG) and a markdown report in /output
"""

import sys
from pathlib import Path

from build_report import build_report
from fetch_bcra import fetch_exchange_rate, fetch_reserves
from fetch_imf import fetch_current_account
from fetch_indec import fetch_cpi, fetch_trade_balance
from fetch_worldbank import fetch_current_account_pct_gdp, fetch_external_debt, fetch_gdp_components, fetch_gdp_growth
from utils import OUTPUT_DIR, get_logger

log = get_logger("main")


def run_pipeline() -> Path:
    log.info("=" * 60)
    log.info("Argentina Macro Report Pipeline — starting")
    log.info("=" * 60)

    results: dict = {}
    warnings: list[str] = []

    # ------------------------------------------------------------------
    # 1. BCRA: reserves (primary source — most reliable)
    # ------------------------------------------------------------------
    log.info("[1/7] Fetching BCRA reserves...")
    results["reserves"] = fetch_reserves(months=24)
    if results["reserves"] is None:
        warnings.append("BCRA reserves: FAILED — check api.bcra.gob.ar")

    log.info("[2/7] Fetching BCRA exchange rate...")
    results["fx"] = fetch_exchange_rate(months=24)
    if results["fx"] is None:
        warnings.append("BCRA FX rate: FAILED")

    # ------------------------------------------------------------------
    # 2. IMF: current account balance (quarterly)
    # ------------------------------------------------------------------
    log.info("[3/7] Fetching IMF current account balance...")
    results["current_account"] = fetch_current_account(quarters=10)
    if results["current_account"] is None:
        warnings.append("IMF current account: FAILED — trying World Bank fallback")
        results["current_account"] = fetch_current_account_pct_gdp(years=8)
        if results["current_account"] is not None:
            log.info("  → World Bank CA %GDP fallback succeeded")

    # ------------------------------------------------------------------
    # 3. World Bank: GDP growth and debt
    # ------------------------------------------------------------------
    log.info("[4/7] Fetching World Bank GDP growth...")
    results["gdp"] = fetch_gdp_growth(quarters=10)

    log.info("[4b]  Fetching GDP expenditure components (C+I+G+X-M)...")
    results["gdp_components"] = fetch_gdp_components(quarters=8)
    if results["gdp"] is None:
        warnings.append("World Bank GDP growth: FAILED")

    log.info("[5/7] Fetching World Bank external debt...")
    results["ext_debt"] = fetch_external_debt(years=8)
    if results["ext_debt"] is None:
        warnings.append("World Bank external debt: FAILED (non-critical)")

    # ------------------------------------------------------------------
    # 4. INDEC: CPI and trade balance
    # ------------------------------------------------------------------
    log.info("[6/7] Fetching INDEC CPI...")
    results["cpi"] = fetch_cpi(months=24)
    if results["cpi"] is None:
        warnings.append("INDEC CPI: FAILED — datos.gob.ar may be down")

    log.info("[7/7] Fetching INDEC trade balance...")
    results["trade"] = fetch_trade_balance(months=24)
    if results["trade"] is None:
        warnings.append("INDEC trade balance: FAILED — all sources exhausted")

    # ------------------------------------------------------------------
    # 5. Build report
    # ------------------------------------------------------------------
    log.info("Building report (PDF + Markdown)...")
    report_path = build_report(
        trade_df=results.get("trade"),
        reserves_df=results.get("reserves"),
        cpi_df=results.get("cpi"),
        gdp_df=results.get("gdp"),
        ca_df=results.get("current_account"),
        gdp_components_df=results.get("gdp_components"),
    )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    log.info("=" * 60)
    log.info("Pipeline complete.")
    log.info("PDF:      %s", report_path["pdf"])
    log.info("Markdown: %s", report_path["md"])

    succeeded = [k for k, v in results.items() if v is not None]
    failed = [k for k, v in results.items() if v is None]

    log.info("Datasets fetched successfully: %s", ", ".join(succeeded) or "none")
    if failed:
        log.warning("Datasets that FAILED: %s", ", ".join(failed))

    if warnings:
        log.info("-" * 40)
        log.info("WARNINGS:")
        for w in warnings:
            log.warning("  • %s", w)

    log.info("=" * 60)
    return report_path


if __name__ == "__main__":
    try:
        paths = run_pipeline()
        print(f"\nPDF:      {paths['pdf']}")
        print(f"Markdown: {paths['md']}")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
    except Exception as e:
        log.exception("Pipeline crashed: %s", e)
        sys.exit(2)
