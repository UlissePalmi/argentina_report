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

from signals import wages as sig_wages
from signals import credit as sig_credit
from signals import investment as sig_investment
from signals import inflation as sig_inflation
from signals import external as sig_external
from signals import fiscal as sig_fiscal
from signals import production as sig_production
from signals import labor as sig_labor
from signals import master as sig_master

from external.debt  import fetch_govt_ext_debt
from external.fetch import (
    fetch_reserves, fetch_exchange_rate,
    fetch_current_account, fetch_trade_balance,
    fetch_external_debt, fetch_current_account_pct_gdp,
    fetch_fiscal,
    fetch_gdp_growth, fetch_gdp_components, fetch_emae,
    fetch_gdp_nominal, fetch_fbcf_breakdown,
    fetch_cpi,
    fetch_consumption, compute_real_values,
    fetch_production, fetch_agriculture,
    fetch_employment, fetch_ucii, compute_productivity,
)
from sections.consumption.report import build_productivity_report
from sections.financing.report   import build_financing_report
from report.build        import build_report
from utils               import get_logger

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

    log.info("[1/4f] Fetching fiscal balance...")
    fiscal_df = fetch_fiscal(years=6)
    if fiscal_df is None:
        warnings.append("Fiscal balance: FAILED (non-critical -- scorecard will show n/a)")

    log.info("[1/4g] Fetching government external debt breakdown...")
    debt_df = fetch_govt_ext_debt(quarters=10)
    if debt_df is None:
        warnings.append("Govt ext debt breakdown: FAILED (non-critical)")

    # ------------------------------------------------------------------
    # GDP
    # ------------------------------------------------------------------
    log.info("[2/4a] Fetching GDP growth (quarterly)...")
    gdp_df = fetch_gdp_growth(quarters=10)
    if gdp_df is None:
        warnings.append("GDP growth: FAILED")

    log.info("[2/4b] Fetching GDP expenditure components (C+I+G+X-M)...")
    components_df = fetch_gdp_components(quarters=8)

    log.info("[2/4c] Fetching GDP nominal expenditure shares (current prices)...")
    nominal_df = fetch_gdp_nominal(quarters=8)

    log.info("[2/4d] Fetching FBCF investment sub-component breakdown...")
    fbcf_df = fetch_fbcf_breakdown(quarters=12)

    log.info("[2/4e] Fetching EMAE monthly activity (headline + sectors)...")
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
    # Production
    # ------------------------------------------------------------------
    log.info("[5/6]  Fetching production data (IPI, energy, ISAC)...")
    production_df = fetch_production(months=24)
    if production_df is None:
        warnings.append("Production: FAILED -- check datos.gob.ar IPI/energy series")

    log.info("[5/6b] Fetching agriculture (annual harvest)...")
    agro_df = fetch_agriculture(years=8)
    if agro_df is None:
        warnings.append("Agriculture: FAILED -- check AGRO_A_* series")

    # ------------------------------------------------------------------
    # Productivity
    # ------------------------------------------------------------------
    log.info("[6/6a] Fetching SIPA employment by sector...")
    employment_df = fetch_employment(quarters=12)
    if employment_df is None:
        warnings.append("Employment: FAILED -- check SIPA series")

    log.info("[6/6b] Fetching capacity utilization (UCII)...")
    ucii_df = fetch_ucii(months=24)
    if ucii_df is None:
        warnings.append("UCII: FAILED -- check capacity utilization series")

    log.info("[6/6c] Computing productivity and ULC...")
    productivity_df = None
    if emae_df is not None and employment_df is not None:
        productivity_df = compute_productivity(emae_df, employment_df, consumption_df)
    else:
        warnings.append("Productivity: SKIPPED -- requires EMAE + employment data")

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
    # Build productivity deep-dive report
    # ------------------------------------------------------------------
    log.info("Building productivity deep-dive report...")
    productivity_report_path = build_productivity_report(
        consumption_df=consumption_df,
        cpi_df=cpi_df,
        components_df=components_df,
        nominal_df=nominal_df,
        fbcf_df=fbcf_df,
        emae_df=emae_df,
        production_df=production_df,
        agro_df=agro_df,
        productivity_df=productivity_df,
        ucii_df=ucii_df,
        employment_df=employment_df,
    )

    # ------------------------------------------------------------------
    # Build financing report
    # ------------------------------------------------------------------
    log.info("Building financing report...")
    financing_report_path = build_financing_report(consumption_df=consumption_df)

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
        fiscal_data={
            "fiscal_df": fiscal_df,
        },
        debt_data={
            "debt_df": debt_df,
        },
        gdp_data={
            "gdp_df":        gdp_df,
            "components_df": components_df,
            "nominal_df":    nominal_df,
            "fbcf_df":       fbcf_df,
            "emae_df":       emae_df,
        },
        labor_data={
            "consumption_df": consumption_df,
            "employment_df":  employment_df,
        },
        production_data={
            "production_df": production_df,
            "agro_df":       agro_df,
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
    log.info("Productivity report: %s", productivity_report_path)
    log.info("Financing report:    %s", financing_report_path)

    all_dfs = {
        "reserves": reserves_df, "fx": fx_df, "ca": ca_df, "trade": trade_df,
        "ext_debt": ext_debt_df, "fiscal": fiscal_df, "gdp": gdp_df,
        "components": components_df, "emae": emae_df, "cpi": cpi_df,
        "consumption": consumption_df,
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
    report_path["productivity_report"] = productivity_report_path
    report_path["financing_report"]    = financing_report_path
    return report_path


if __name__ == "__main__":
    try:
        paths = run_pipeline()
        print(f"\nPDF:                {paths['pdf']}")
        print(f"Markdown:           {paths['md']}")
        print(f"Productivity report:{paths.get('productivity_report', 'n/a')}")
        print(f"Financing report:   {paths.get('financing_report', 'n/a')}")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
    except Exception as e:
        log.exception("Pipeline crashed: %s", e)
        sys.exit(2)
