"""
Productivity module — data fetching.

Sources: datos.gob.ar (INDEC SIPA employment + UCII capacity utilization)
Reuses:  EMAE sectoral data (gdp/fetch.py) as output proxy.

Employment series (quarterly, sector private):
    155.1_ISTRIARIA_C_0_0_9    — Industry
    155.1_CTRUCCIION_C_0_0_12  — Construction
    155.1_SICIOSIOS_C_0_0_9    — Services
    151.1_TL_ESTADAD_2012_M_20 — Total formal employment (monthly)

Capacity utilization (UCII, monthly, % of installed capacity):
    31.3_UIMB_2004_M_33  — Basic metals
    29.3_UPT_2006_M_23   — Textiles
    29.3_UV_2006_M_25    — Automotive vehicles
    Note: no single headline UCII series found on datos.gob.ar;
          these sector UCIIs are used as a proxy basket.

Output files:
    data/productivity/employment.csv    — Sector employment quarterly YoY
    data/productivity/ucii.csv          — Capacity utilization monthly
    data/productivity/productivity.csv  — Computed productivity + ULC metrics
"""

from datetime import date, timedelta

import pandas as pd

from utils import PRODUCTIVITY_DIR, fetch_json, get_logger

log = get_logger("productivity.fetch")

SERIES_BASE = "https://apis.datos.gob.ar/series/api/series/"

# Employment
EMP_TOTAL_ID   = "151.1_TL_ESTADAD_2012_M_20"
EMP_INDUSTRY_ID = "155.1_ISTRIARIA_C_0_0_9"
EMP_CONSTR_ID   = "155.1_CTRUCCIION_C_0_0_12"
EMP_SERVICES_ID = "155.1_SICIOSIOS_C_0_0_9"

# Capacity utilization (sector proxies)
UCII_METALS_ID = "31.3_UIMB_2004_M_33"
UCII_TEXT_ID   = "29.3_UPT_2006_M_23"
UCII_AUTO_ID   = "29.3_UV_2006_M_25"


def _fetch_series(ids: list[str], limit: int, start_date: str,
                  frequency: str | None = None) -> pd.DataFrame | None:
    params = {"ids": ",".join(ids), "format": "json", "limit": limit,
              "sort": "asc", "start_date": start_date}
    if frequency:
        params["collapse"] = frequency
    cache_key = f"productivity_{'_'.join(i[:12] for i in ids)}_{limit}_{start_date}"
    data = fetch_json(SERIES_BASE, params=params, cache_key=cache_key)
    if data is None or "data" not in data:
        return None
    meta = [m for m in data.get("meta", []) if "field" in m]
    columns = ["date"] + [m["field"]["id"] for m in meta]
    df = pd.DataFrame(data["data"], columns=columns)
    df["date"] = pd.to_datetime(df["date"])
    for col in columns[1:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("date").reset_index(drop=True)


def fetch_employment(quarters: int = 12) -> pd.DataFrame | None:
    """
    Sector employment (SIPA, quarterly) + total formal employment (monthly).
    Quarterly data collapsed from source frequency.
    """
    start = (date.today() - timedelta(days=(quarters + 6) * 95)).strftime("%Y-%m-%d")
    limit = quarters + 8

    # Monthly total
    batch_m = _fetch_series([EMP_TOTAL_ID], limit=limit * 3, start_date=start)
    # Quarterly sector breakdown
    batch_q = _fetch_series(
        [EMP_INDUSTRY_ID, EMP_CONSTR_ID, EMP_SERVICES_ID],
        limit=limit, start_date=start
    )

    result = None

    if batch_m is not None and not batch_m.empty and EMP_TOTAL_ID in batch_m.columns:
        result = batch_m[["date"]].copy()
        result["emp_total_yoy_pct"] = batch_m[EMP_TOTAL_ID].pct_change(12) * 100
        result["emp_total_mom_pct"] = batch_m[EMP_TOTAL_ID].pct_change(1)  * 100

    if batch_q is not None and not batch_q.empty:
        for series_id, col in [
            (EMP_INDUSTRY_ID, "emp_industry_yoy_pct"),
            (EMP_CONSTR_ID,   "emp_construction_yoy_pct"),
            (EMP_SERVICES_ID, "emp_services_yoy_pct"),
        ]:
            if series_id in batch_q.columns:
                batch_q[col] = batch_q[series_id].pct_change(4) * 100  # quarterly YoY

        q_cols = [c for c in ["emp_industry_yoy_pct", "emp_construction_yoy_pct",
                               "emp_services_yoy_pct"] if c in batch_q.columns]
        if q_cols:
            q_sub = batch_q[["date"] + q_cols].dropna(subset=q_cols, how="all")
            if result is not None:
                result = result.merge(q_sub, on="date", how="left")
            else:
                result = q_sub
    else:
        log.warning("fetch_employment: sector employment batch failed.")

    if result is None or result.empty:
        log.warning("fetch_employment: no data.")
        return None

    yoy_cols = [c for c in result.columns if c != "date"]
    result = result.dropna(subset=yoy_cols, how="all").tail(quarters * 3).reset_index(drop=True)

    out = PRODUCTIVITY_DIR / "employment.csv"
    result.to_csv(out, index=False)
    log.info("Employment saved -> %s  (%d rows, latest: %s)",
             out.name, len(result), result["date"].max().strftime("%Y-%m"))
    return result


def fetch_ucii(months: int = 24) -> pd.DataFrame | None:
    """
    Capacity utilization for key manufacturing sectors (monthly, % of installed capacity).
    No single headline UCII on datos.gob.ar — returns sector basket.
    """
    start = (date.today() - timedelta(days=(months + 14) * 31)).strftime("%Y-%m-%d")
    limit = months + 20

    batch = _fetch_series([UCII_METALS_ID, UCII_TEXT_ID, UCII_AUTO_ID],
                          limit=limit, start_date=start)
    if batch is None or batch.empty:
        log.warning("fetch_ucii: UCII batch failed.")
        return None

    rename = {
        UCII_METALS_ID: "ucii_metals_pct",
        UCII_TEXT_ID:   "ucii_textiles_pct",
        UCII_AUTO_ID:   "ucii_auto_pct",
    }
    batch = batch.rename(columns={k: v for k, v in rename.items() if k in batch.columns})
    ucii_cols = [v for v in rename.values() if v in batch.columns]
    if ucii_cols:
        batch["ucii_avg_pct"] = batch[ucii_cols].mean(axis=1)

    batch = batch.dropna(subset=ucii_cols, how="all").tail(months).reset_index(drop=True)

    out = PRODUCTIVITY_DIR / "ucii.csv"
    batch.to_csv(out, index=False)
    log.info("UCII saved -> %s  (%d rows)", out.name, len(batch))
    return batch


def compute_productivity(emae_df: pd.DataFrame,
                         employment_df: pd.DataFrame,
                         consumption_df: pd.DataFrame | None = None) -> pd.DataFrame | None:
    """
    Compute sector productivity and unit labor costs.

    Productivity YoY = EMAE sector YoY - employment sector YoY
    ULC YoY = real wage YoY - productivity YoY

    Sectors with both EMAE and employment data:
        industry    — industria_pct (EMAE) vs emp_industry_yoy_pct
        construction — construccion_pct (EMAE) vs emp_construction_yoy_pct
        services    — servicios_pct or comercio_pct (EMAE) vs emp_services_yoy_pct

    Returns wide DataFrame with one row per date.
    """
    SECTOR_MAP = {
        "industry":     ("industria_pct",    "emp_industry_yoy_pct"),
        "construction": ("construccion_pct",  "emp_construction_yoy_pct"),
        "services":     ("comercio_pct",      "emp_services_yoy_pct"),
    }

    # Align dates to month-start
    emae = emae_df.copy()
    emae["date"] = pd.to_datetime(emae["date"]).dt.to_period("M").dt.to_timestamp()

    emp = employment_df.copy()
    emp["date"] = pd.to_datetime(emp["date"]).dt.to_period("M").dt.to_timestamp()

    merged = emae[["date"]].copy()
    merged = merged.merge(emp, on="date", how="outer").sort_values("date")

    # Add EMAE columns
    for emae_col in [v[0] for v in SECTOR_MAP.values()]:
        if emae_col in emae.columns:
            merged = merged.merge(emae[["date", emae_col]], on="date", how="left")

    result_rows = []
    for sector, (emae_col, emp_col) in SECTOR_MAP.items():
        if emae_col not in merged.columns or emp_col not in merged.columns:
            continue
        sub = merged[["date", emae_col, emp_col]].dropna()
        sub = sub.copy()
        sub[f"productivity_{sector}_yoy_pct"] = sub[emae_col] - sub[emp_col]
        result_rows.append(sub[["date", f"productivity_{sector}_yoy_pct"]])

    if not result_rows:
        log.warning("compute_productivity: no sectors computed.")
        return None

    prod_df = result_rows[0]
    for df in result_rows[1:]:
        prod_df = prod_df.merge(df, on="date", how="outer")

    prod_df = prod_df.sort_values("date")

    # Add ULC if real wage available
    if consumption_df is not None and "real_wage_yoy_pct" in consumption_df.columns:
        wages = consumption_df[["date", "real_wage_yoy_pct"]].copy()
        wages["date"] = pd.to_datetime(wages["date"]).dt.to_period("M").dt.to_timestamp()
        prod_df = prod_df.merge(wages, on="date", how="left")
        for sector in SECTOR_MAP:
            prod_col = f"productivity_{sector}_yoy_pct"
            if prod_col in prod_df.columns and "real_wage_yoy_pct" in prod_df.columns:
                prod_df[f"ulc_{sector}_yoy_pct"] = (
                    prod_df["real_wage_yoy_pct"] - prod_df[prod_col]
                )

    out = PRODUCTIVITY_DIR / "productivity.csv"
    prod_df.to_csv(out, index=False)
    log.info("Productivity saved -> %s  (%d rows)", out.name, len(prod_df))
    return prod_df
