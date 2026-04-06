"""
Re-export hub — all public fetch functions in one place.
main.py imports from here; topic modules live in external/<topic>.py.
"""

from external.reserves    import (fetch_reserves, fetch_exchange_rate,
                                   fetch_current_account, fetch_trade_balance,
                                   fetch_external_debt, fetch_current_account_pct_gdp)
from external.fiscal      import fetch_fiscal
from external.gdp         import (fetch_gdp_growth, fetch_gdp_components, fetch_emae,
                                   fetch_gdp_nominal, fetch_fbcf_breakdown)
from external.inflation   import fetch_cpi
from external.consumption import fetch_consumption, compute_real_values
from external.production  import fetch_production, fetch_agriculture
from external.productivity import fetch_employment, fetch_ucii, compute_productivity

__all__ = [
    "fetch_reserves", "fetch_exchange_rate", "fetch_current_account",
    "fetch_trade_balance", "fetch_external_debt", "fetch_current_account_pct_gdp",
    "fetch_fiscal",
    "fetch_gdp_growth", "fetch_gdp_components", "fetch_emae",
    "fetch_gdp_nominal", "fetch_fbcf_breakdown",
    "fetch_cpi",
    "fetch_consumption", "compute_real_values",
    "fetch_production", "fetch_agriculture",
    "fetch_employment", "fetch_ucii", "compute_productivity",
]
