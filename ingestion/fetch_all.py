"""Layer-2 orchestrator: fetches all data sources and returns DataFrames + warnings."""

from .reserves    import (fetch_reserves, fetch_exchange_rate,
                           fetch_current_account, fetch_trade_balance,
                           fetch_external_debt, fetch_current_account_pct_gdp)
from .fiscal      import fetch_fiscal
from .debt        import (fetch_govt_ext_debt, fetch_domestic_debt_flows,
                           fetch_ext_debt_by_sector, fetch_ext_debt_by_sector_iip)
from .gdp         import (fetch_gdp_growth, fetch_gdp_components, fetch_emae,
                           fetch_gdp_nominal, fetch_fbcf_breakdown)
from .inflation   import fetch_cpi
from .consumption import fetch_consumption, compute_real_values
from .production  import fetch_production, fetch_agriculture
from .productivity import fetch_employment, fetch_ucii, compute_productivity
from .debt_pdf     import fetch_all_ede_pdfs
from utils import get_logger

log = get_logger("pipeline.fetch")


def fetch_all() -> tuple[dict, list[str]]:
    """
    Run all Layer-2 fetch calls.
    Returns (data, warnings) where data is a dict of DataFrames (None on failure)
    and warnings is a list of human-readable failure messages.
    """
    warnings: list[str] = []

    # ------------------------------------------------------------------
    # External position (reserves, FX, trade, current account)
    # ------------------------------------------------------------------
    log.info("[1a/6] Fetching BCRA reserves...")
    reserves_df = fetch_reserves(months=24)
    if reserves_df is None:
        warnings.append("BCRA reserves: FAILED -- check api.bcra.gob.ar")

    log.info("[1b/6] Fetching BCRA exchange rate...")
    fx_df = fetch_exchange_rate(months=24)
    if fx_df is None:
        warnings.append("BCRA FX rate: FAILED")

    log.info("[1c/6] Fetching current account balance...")
    ca_df = fetch_current_account(quarters=40)
    if ca_df is None:
        warnings.append("Current account: FAILED -- trying World Bank fallback")
        ca_df = fetch_current_account_pct_gdp(years=8)
        if ca_df is not None:
            log.info("  -> World Bank CA %%GDP fallback succeeded")

    log.info("[1d/6] Fetching trade balance...")
    trade_df = fetch_trade_balance(months=24)
    if trade_df is None:
        warnings.append("INDEC trade balance: FAILED -- all sources exhausted")

    # ------------------------------------------------------------------
    # Fiscal
    # ------------------------------------------------------------------
    log.info("[1e/6] Fetching fiscal balance...")
    fiscal_df = fetch_fiscal(years=6)
    if fiscal_df is None:
        warnings.append("Fiscal balance: FAILED (non-critical -- scorecard will show n/a)")

    # ------------------------------------------------------------------
    # Debt (external stock + domestic flows)
    # ------------------------------------------------------------------
    log.info("[1f/6] Fetching World Bank total external debt ratios...")
    ext_debt_df = fetch_external_debt(years=8)
    if ext_debt_df is None:
        warnings.append("World Bank external debt: FAILED (non-critical)")

    log.info("[1g/6] Fetching government external debt breakdown (bonds vs loans)...")
    debt_df = fetch_govt_ext_debt(quarters=40)
    if debt_df is None:
        warnings.append("Govt ext debt breakdown: FAILED (non-critical)")

    log.info("[1h/6] Fetching government domestic debt flows (amortization + interest)...")
    domestic_debt_df = fetch_domestic_debt_flows(months=120)
    if domestic_debt_df is None:
        warnings.append("Domestic debt flows: FAILED (non-critical)")

    log.info("[1i/6] Fetching external debt by sector -- nominal value (INDEC EDE)...")
    ext_debt_sector_df = fetch_ext_debt_by_sector(quarters=40)
    if ext_debt_sector_df is None:
        warnings.append("Ext debt by sector (EDE nominal): FAILED (non-critical)")

    log.info("[1j/6] Fetching external debt by sector -- market value (INDEC IIP)...")
    ext_debt_sector_iip_df = fetch_ext_debt_by_sector_iip(quarters=40)
    if ext_debt_sector_iip_df is None:
        warnings.append("Ext debt by sector (IIP market value): FAILED (non-critical)")

    log.info("[1k/6] Downloading & parsing all INDEC EDE PDFs (Cuadros III.3–III.8)...")
    ede_pdf_data = fetch_all_ede_pdfs()
    if not ede_pdf_data:
        warnings.append("INDEC EDE PDFs: FAILED (non-critical -- pdfplumber may not be installed)")

    # ------------------------------------------------------------------
    # GDP
    # ------------------------------------------------------------------
    log.info("[2a/6] Fetching GDP growth (quarterly)...")
    gdp_df = fetch_gdp_growth(quarters=40)
    if gdp_df is None:
        warnings.append("GDP growth: FAILED")

    log.info("[2b/6] Fetching GDP expenditure components (C+I+G+X-M)...")
    components_df = fetch_gdp_components(quarters=40)

    log.info("[2c/6] Fetching GDP nominal expenditure shares (current prices)...")
    nominal_df = fetch_gdp_nominal(quarters=40)

    log.info("[2d/6] Fetching FBCF investment sub-component breakdown...")
    fbcf_df = fetch_fbcf_breakdown(quarters=40)

    log.info("[2e/6] Fetching EMAE monthly activity (headline + sectors)...")
    emae_df = fetch_emae(months=24)

    # ------------------------------------------------------------------
    # Inflation
    # ------------------------------------------------------------------
    log.info("[3/6]  Fetching INDEC CPI...")
    cpi_df = fetch_cpi(months=24)
    if cpi_df is None:
        warnings.append("INDEC CPI: FAILED -- datos.gob.ar may be down")

    # ------------------------------------------------------------------
    # Consumption drivers
    # ------------------------------------------------------------------
    log.info("[4/6]  Fetching consumption drivers (wages, credit, deposits)...")
    consumption_df = fetch_consumption(months=24)
    if consumption_df is None:
        warnings.append("Consumption drivers: FAILED -- check datos.gob.ar wage/credit series")
    elif cpi_df is not None:
        consumption_df = compute_real_values(consumption_df, cpi_df)

    # ------------------------------------------------------------------
    # Production
    # ------------------------------------------------------------------
    log.info("[5a/6] Fetching production data (IPI, energy, ISAC)...")
    production_df = fetch_production(months=24)
    if production_df is None:
        warnings.append("Production: FAILED -- check datos.gob.ar IPI/energy series")

    log.info("[5b/6] Fetching agriculture (annual harvest)...")
    agro_df = fetch_agriculture(years=8)
    if agro_df is None:
        warnings.append("Agriculture: FAILED -- check AGRO_A_* series")

    # ------------------------------------------------------------------
    # Productivity
    # ------------------------------------------------------------------
    log.info("[6a/6] Fetching SIPA employment by sector...")
    employment_df = fetch_employment(quarters=40)
    if employment_df is None:
        warnings.append("Employment: FAILED -- check SIPA series")

    log.info("[6b/6] Fetching capacity utilization (UCII)...")
    ucii_df = fetch_ucii(months=24)
    if ucii_df is None:
        warnings.append("UCII: FAILED -- check capacity utilization series")

    log.info("[6c/6] Computing productivity and ULC...")
    productivity_df = None
    if emae_df is not None and employment_df is not None:
        productivity_df = compute_productivity(emae_df, employment_df, consumption_df)
    else:
        warnings.append("Productivity: SKIPPED -- requires EMAE + employment data")

    data = {
        "reserves_df":           reserves_df,
        "fx_df":                 fx_df,
        "ca_df":                 ca_df,
        "trade_df":              trade_df,
        "ext_debt_df":           ext_debt_df,
        "fiscal_df":             fiscal_df,
        "govt_external_debt_df": debt_df,
        "govt_domestic_debt_df": domestic_debt_df,
        "ext_debt_sector_df":     ext_debt_sector_df,
        "ext_debt_sector_iip_df": ext_debt_sector_iip_df,
        "ede_pdf_levels":         ede_pdf_data.get("levels"),
        "ede_pdf_creditor_types": ede_pdf_data.get("creditor_types"),
        "ede_pdf_multilateral":   ede_pdf_data.get("multilateral"),
        "ede_pdf_bonds":          ede_pdf_data.get("bonds"),
        "ede_pdf_bond_series":    ede_pdf_data.get("bond_series"),
        "ede_pdf_nonresident":    ede_pdf_data.get("nonresident"),
        "gdp_df":                gdp_df,
        "components_df":         components_df,
        "nominal_df":            nominal_df,
        "fbcf_df":               fbcf_df,
        "emae_df":               emae_df,
        "cpi_df":                cpi_df,
        "consumption_df":        consumption_df,
        "production_df":         production_df,
        "agro_df":               agro_df,
        "employment_df":         employment_df,
        "ucii_df":               ucii_df,
        "productivity_df":       productivity_df,
    }
    return data, warnings
