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

import argparse
import shutil
import sys
from pathlib import Path

from signals import wages as sig_wages
from signals import credit as sig_credit
from signals import investment as sig_investment
from signals import inflation as sig_inflation
from signals import external as sig_external
from signals import fiscal as sig_fiscal
from signals import production as sig_production
from signals import labor as sig_labor
from signals import master as sig_master

from ingestion.fetch_all          import fetch_all
from sections.consumption.report    import build_productivity_report
from sections.financing.report      import build_financing_report
from sections.debt_reserves.report  import build_debt_reserves_report
from report.build                import build_report
from svar.run                    import run_svar
from utils                       import get_logger

log = get_logger("main")


def run_pipeline() -> dict:
    log.info("=" * 60)
    log.info("Argentina Macro Report Pipeline -- starting")
    log.info("=" * 60)

    # ------------------------------------------------------------------
    # Layer 2: Fetch all data
    # ------------------------------------------------------------------
    data, warnings = fetch_all()

    # ------------------------------------------------------------------
    # Layer 3: Compute signals (reads CSVs → outputs data/signals/*.json)
    # ------------------------------------------------------------------
    log.info("Computing domain signals...")
    try:
        sig_wages.compute()
        sig_credit.compute()
        sig_investment.compute()
        sig_inflation.compute()
        sig_external.compute()
        sig_fiscal.compute()
        sig_production.compute()
        sig_labor.compute()
        sig_master.compute()
        log.info("Signals computed successfully → data/signals/")
    except Exception as e:
        log.warning("Signal computation failed (non-critical): %s", e)

    # ------------------------------------------------------------------
    # SVAR model — Layer 3.5
    # ------------------------------------------------------------------
    log.info("Running SVAR inflation dynamics model...")
    run_svar()

    # ------------------------------------------------------------------
    # Build productivity deep-dive report
    # ------------------------------------------------------------------
    log.info("Building productivity deep-dive report...")
    productivity_report_path = build_productivity_report(
        consumption_df=data["consumption_df"],
        cpi_df=data["cpi_df"],
        components_df=data["components_df"],
        nominal_df=data["nominal_df"],
        fbcf_df=data["fbcf_df"],
        emae_df=data["emae_df"],
        production_df=data["production_df"],
        agro_df=data["agro_df"],
        productivity_df=data["productivity_df"],
        ucii_df=data["ucii_df"],
        employment_df=data["employment_df"],
    )

    # ------------------------------------------------------------------
    # Build debt & reserves report
    # ------------------------------------------------------------------
    log.info("Building debt & reserves report...")
    debt_reserves_report_path = build_debt_reserves_report(
        reserves_df=            data["reserves_df"],
        fx_df=                  data["fx_df"],
        ext_debt_sector_df=     data["ext_debt_sector_df"],
        ext_debt_sector_iip_df= data["ext_debt_sector_iip_df"],
        govt_ext_debt_df=       data["govt_external_debt_df"],
        trade_df=               data["trade_df"],
        ca_df=                  data["ca_df"],
    )

    # ------------------------------------------------------------------
    # Build financing report
    # ------------------------------------------------------------------
    log.info("Building financing report...")
    financing_report_path = build_financing_report(consumption_df=data["consumption_df"])

    # ------------------------------------------------------------------
    # Build main report
    # ------------------------------------------------------------------
    log.info("Building report (PDF + Markdown)...")
    report_path = build_report(
        external_data={
            "trade_df":    data["trade_df"],
            "reserves_df": data["reserves_df"],
            "ca_df":       data["ca_df"],
            "fx_df":       data["fx_df"],
        },
        inflation_data={
            "cpi_df": data["cpi_df"],
        },
        fiscal_data={
            "fiscal_df": data["fiscal_df"],
        },
        debt_data={
            "debt_df": data["govt_external_debt_df"],
        },
        gdp_data={
            "gdp_df":        data["gdp_df"],
            "components_df": data["components_df"],
            "nominal_df":    data["nominal_df"],
            "fbcf_df":       data["fbcf_df"],
            "emae_df":       data["emae_df"],
        },
        labor_data={
            "consumption_df": data["consumption_df"],
            "employment_df":  data["employment_df"],
        },
        production_data={
            "production_df": data["production_df"],
            "agro_df":       data["agro_df"],
        },
        consumption_data={
            "consumption_df": data["consumption_df"],
        },
    )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    log.info("=" * 60)
    log.info("Pipeline complete.")
    log.info("PDF:              %s", report_path["pdf"])
    log.info("Markdown:         %s", report_path["md"])
    log.info("Productivity report: %s", productivity_report_path)
    log.info("Financing report:    %s", financing_report_path)
    log.info("Debt & reserves:     %s", debt_reserves_report_path)

    check_keys = ["reserves_df", "fx_df", "ca_df", "trade_df", "ext_debt_df",
                  "fiscal_df", "gdp_df", "components_df", "emae_df", "cpi_df", "consumption_df"]
    succeeded = [k for k in check_keys if data.get(k) is not None]
    failed    = [k for k in check_keys if data.get(k) is None]
    log.info("Datasets fetched successfully: %s", ", ".join(succeeded) or "none")
    if failed:
        log.warning("Datasets that FAILED: %s", ", ".join(failed))
    if warnings:
        log.info("-" * 40)
        for w in warnings:
            log.warning("  * %s", w)
    log.info("=" * 60)
    report_path["productivity_report"]   = productivity_report_path
    report_path["financing_report"]      = financing_report_path
    report_path["debt_reserves_report"]  = debt_reserves_report_path
    return report_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Clear cache before running to force re-fetch")
    args = parser.parse_args()

    if args.refresh:
        from utils import CACHE_DIR
        shutil.rmtree(CACHE_DIR, ignore_errors=True)
        CACHE_DIR.mkdir(exist_ok=True)
        print("Cache cleared.")

    try:
        paths = run_pipeline()
        print(f"\nPDF:                {paths['pdf']}")
        print(f"Markdown:           {paths['md']}")
        print(f"Productivity report: {paths.get('productivity_report', 'n/a')}")
        print(f"Financing report:    {paths.get('financing_report', 'n/a')}")
        print(f"Debt & reserves:     {paths.get('debt_reserves_report', 'n/a')}")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
    except Exception as e:
        log.exception("Pipeline crashed: %s", e)
        sys.exit(2)
