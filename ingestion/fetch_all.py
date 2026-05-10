"""Layer-2 orchestrator: fetches all data sources and returns DataFrames + warnings."""

from .reserves    import (fetch_reserves, fetch_exchange_rate,
                           fetch_current_account, fetch_trade_balance,
                           fetch_external_debt, fetch_current_account_pct_gdp)
from .fiscal      import fetch_fiscal
from .debt        import fetch_govt_ext_debt
from .gdp         import (fetch_gdp_growth, fetch_gdp_components, fetch_emae,
                           fetch_gdp_nominal, fetch_fbcf_breakdown)
from .inflation   import fetch_cpi
from .consumption import fetch_consumption, compute_real_values
from .production  import fetch_production, fetch_agriculture
from .productivity import fetch_employment, fetch_ucii, compute_productivity
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
    # External (dollar situation)
    # ------------------------------------------------------------------
    log.info("[1/6a] Fetching BCRA reserves...")
    reserves_df = fetch_reserves(months=24)
    if reserves_df is None:
        warnings.append("BCRA reserves: FAILED -- check api.bcra.gob.ar")

    log.info("[1/6b] Fetching BCRA exchange rate...")
    fx_df = fetch_exchange_rate(months=24)
    if fx_df is None:
        warnings.append("BCRA FX rate: FAILED")

    log.info("[1/6c] Fetching current account balance...")
    ca_df = fetch_current_account(quarters=10)
    if ca_df is None:
        warnings.append("Current account: FAILED -- trying World Bank fallback")
        ca_df = fetch_current_account_pct_gdp(years=8)
        if ca_df is not None:
            log.info("  -> World Bank CA %%GDP fallback succeeded")

    log.info("[1/6d] Fetching trade balance...")
    trade_df = fetch_trade_balance(months=24)
    if trade_df is None:
        warnings.append("INDEC trade balance: FAILED -- all sources exhausted")

    log.info("[1/6e] Fetching external debt...")
    ext_debt_df = fetch_external_debt(years=8)
    if ext_debt_df is None:
        warnings.append("World Bank external debt: FAILED (non-critical)")

    log.info("[1/6f] Fetching fiscal balance...")
    fiscal_df = fetch_fiscal(years=6)
    if fiscal_df is None:
        warnings.append("Fiscal balance: FAILED (non-critical -- scorecard will show n/a)")

    log.info("[1/6g] Fetching government external debt breakdown...")
    debt_df = fetch_govt_ext_debt(quarters=10)
    if debt_df is None:
        warnings.append("Govt ext debt breakdown: FAILED (non-critical)")

    # ------------------------------------------------------------------
    # GDP
    # ------------------------------------------------------------------
    log.info("[2/6a] Fetching GDP growth (quarterly)...")
    gdp_df = fetch_gdp_growth(quarters=10)
    if gdp_df is None:
        warnings.append("GDP growth: FAILED")

    log.info("[2/6b] Fetching GDP expenditure components (C+I+G+X-M)...")
    components_df = fetch_gdp_components(quarters=8)

    log.info("[2/6c] Fetching GDP nominal expenditure shares (current prices)...")
    nominal_df = fetch_gdp_nominal(quarters=8)

    log.info("[2/6d] Fetching FBCF investment sub-component breakdown...")
    fbcf_df = fetch_fbcf_breakdown(quarters=12)

    log.info("[2/6e] Fetching EMAE monthly activity (headline + sectors)...")
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
    log.info("[5/6a] Fetching production data (IPI, energy, ISAC)...")
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

    data = {
        "reserves_df":    reserves_df,
        "fx_df":          fx_df,
        "ca_df":          ca_df,
        "trade_df":       trade_df,
        "ext_debt_df":    ext_debt_df,
        "fiscal_df":      fiscal_df,
        "debt_df":        debt_df,
        "gdp_df":         gdp_df,
        "components_df":  components_df,
        "nominal_df":     nominal_df,
        "fbcf_df":        fbcf_df,
        "emae_df":        emae_df,
        "cpi_df":         cpi_df,
        "consumption_df": consumption_df,
        "production_df":  production_df,
        "agro_df":        agro_df,
        "employment_df":  employment_df,
        "ucii_df":        ucii_df,
        "productivity_df": productivity_df,
    }
    return data, warnings
