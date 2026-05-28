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
from signals import fx as sig_fx
from signals import fiscal as sig_fiscal
from signals import production as sig_production
from signals import labor as sig_labor
from signals import master as sig_master

from ingestion.fetch_all          import fetch_all
from report.weekly_diff           import snapshot as diff_snapshot

def _generate_finance_research() -> None:
    """Regenerate Finance Research JS + JSON data files and render react-pdf reports (best-effort)."""
    import importlib.util
    import subprocess
    from pathlib import Path as _Path

    # Step 1: regenerate JS/JSON data files from signals
    try:
        _gen_path = _Path(__file__).parent / "Finance Research" / "generate_data.py"
        spec = importlib.util.spec_from_file_location("generate_data", _gen_path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.generate()
    except Exception as e:
        log.warning("Finance Research data generation failed (non-critical): %s", e)
        return

    # Step 2: render react-pdf reports via Node.js
    try:
        pdf_dir = _Path(__file__).parent / "Finance Research" / "pdf"
        result  = subprocess.run(
            ["node", "generate.js"],
            cwd=pdf_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.stdout:
            for line in result.stdout.strip().splitlines():
                log.info("  [FR-pdf] %s", line)
        if result.returncode != 0:
            log.warning("Finance Research PDF render non-zero exit: %s", result.stderr[:300])
    except FileNotFoundError:
        log.warning("node not found — Finance Research PDFs skipped (install Node.js to enable).")
    except Exception as e:
        log.warning("Finance Research PDF render failed (non-critical): %s", e)
from sections.consumption.report    import build_productivity_report
from sections.financing.report      import build_financing_report
from sections.debt_reserves.report  import build_debt_reserves_report
from sections.reserves.report       import build_reserves_report
from report.build                import build_report
from svar.run                    import run_svar
from utils                       import get_logger

log = get_logger("main")


def run_pipeline(no_pdf: bool = False) -> dict:
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
        sig_fx.compute()
        sig_fiscal.compute()
        sig_production.compute()
        sig_labor.compute()
        sig_master.compute()
        log.info("Signals computed successfully → data/signals/")
        try:
            diff_snapshot()
            log.info("Weekly diff snapshot written.")
        except Exception as snap_err:
            log.warning("Diff snapshot failed (non-critical): %s", snap_err)
        _generate_finance_research()
        log.info("Finance Research JS data files regenerated.")
    except Exception as e:
        log.warning("Signal computation failed (non-critical): %s", e)

    # ------------------------------------------------------------------
    # SVAR model — Layer 3.5
    # ------------------------------------------------------------------
    log.info("Running SVAR inflation dynamics model...")
    run_svar()

    productivity_report_path = None
    debt_reserves_report_path = None
    financing_report_path = None
    reserves_report_path = None
    report_path = {"pdf": None, "md": None}

    if no_pdf:
        log.info("--no-pdf: skipping all report generation.")
    else:
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
        # Build reserves report
        # ------------------------------------------------------------------
        log.info("Building reserves report...")
        reserves_report_path = build_reserves_report(
            reserves_df = data["reserves_df"],
            fx_df       = data["fx_df"],
            trade_df    = data["trade_df"],
            ca_df       = data["ca_df"],
            m2_df       = data.get("m2_df"),
        )

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
            fx_data={
                "fx_parallel_df": data["fx_parallel_df"],
                "reer_df":        data["reer_df"],
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
    log.info("Reserves report:     %s", reserves_report_path)

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
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF/report generation (data fetch + signals + SVAR only)")
    parser.add_argument("--data-only", action="store_true", help="Fetch and save CSVs only — skip signals, SVAR, and reports")
    args = parser.parse_args()

    if args.refresh:
        from utils import CACHE_DIR
        shutil.rmtree(CACHE_DIR, ignore_errors=True)
        CACHE_DIR.mkdir(exist_ok=True)
        print("Cache cleared.")

    if args.data_only:
        data, warnings = fetch_all()
        for w in warnings:
            log.warning("  * %s", w)
        sys.exit(0)

    try:
        paths = run_pipeline(no_pdf=args.no_pdf)
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
