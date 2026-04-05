"""
Production module — data fetching.

Sources: datos.gob.ar (INDEC + Secretaria de Energia + Ministerio de Agricultura)

Series:
    IPI manufacturing headline:
        309.1_PRODUCCIONNAL_0_M_30  — Produccion industrial, original (monthly)
    IPI subsectors (monthly):
        453.2_ALIMENTOS_DAS_0_0_17_18  — Food & beverages
        453.2_INDUSTRIA_ICA_0_0_21_100 — Steel / siderurgica
        453.2_AUTOPARTESTES_0_0_10_100 — Autoparts
        453.2_CEMENTONTO_0_0_7_59      — Cement (also used as ISAC proxy)
    ISAC construction proxy:
        33.4_ISAC_CEMENAND_0_0_21_24   — Cement inputs, seasonally adjusted
        Note: no monthly headline ISAC available on datos.gob.ar;
              cement is the primary composite input (~35% weight).
    Energy (Secretaria de Energia via datos.gob.ar):
        363.3_PRODUCCIONUDO__28        — Crude oil production (monthly)
        364.3_PRODUCCIoNRAL__25        — Natural gas production (monthly)
    Agriculture (Ministerio de Agricultura via datos.gob.ar):
        AGRO_A_Soja_0003               — Soy production (annual, tonnes)
        AGRO_A_Maiz_0003               — Corn production (annual, tonnes)
        AGRO_A_Trigo_0003              — Wheat production (annual, tonnes)
        Note: harvest data is annual; no monthly production series available.

Output files:
    data/production/production_monthly.csv  — IPI, energy, construction proxy
    data/production/production_agro.csv     — Annual agricultural harvest
"""

from datetime import date, timedelta

import pandas as pd

from utils import PRODUCTION_DIR, fetch_json, get_logger

log = get_logger("production.fetch")

SERIES_BASE = "https://apis.datos.gob.ar/series/api/series/"

# Monthly series
IPI_ID       = "309.1_PRODUCCIONNAL_0_M_30"
IPI_FOOD_ID  = "453.2_ALIMENTOS_DAS_0_0_17_18"
IPI_STEEL_ID = "453.2_INDUSTRIA_ICA_0_0_21_100"
IPI_AUTO_ID  = "453.2_AUTOPARTESTES_0_0_10_100"
IPI_CEMENT_ID= "453.2_CEMENTONTO_0_0_7_59"
ISAC_CEM_ID  = "33.4_ISAC_CEMENAND_0_0_21_24"
OIL_ID       = "363.3_PRODUCCIONUDO__28"
GAS_ID       = "364.3_PRODUCCIoNRAL__25"

# Annual agriculture
AGRO_SOY_ID   = "AGRO_A_Soja_0003"
AGRO_CORN_ID  = "AGRO_A_Maiz_0003"
AGRO_WHEAT_ID = "AGRO_A_Trigo_0003"


def _fetch_series(ids: list[str], limit: int, start_date: str,
                  frequency: str = "month") -> pd.DataFrame | None:
    params = {"ids": ",".join(ids), "format": "json", "limit": limit,
              "sort": "asc", "start_date": start_date, "collapse": frequency}
    cache_key = f"production_{'_'.join(i[:12] for i in ids)}_{limit}_{start_date}"
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


def fetch_production(months: int = 24) -> pd.DataFrame | None:
    """
    Monthly production indicators.

    Columns:
        date,
        ipi_yoy_pct, ipi_mom_pct,
        ipi_food_yoy_pct, ipi_steel_yoy_pct, ipi_auto_yoy_pct,
        oil_yoy_pct, oil_mom_pct,
        gas_yoy_pct, gas_mom_pct,
        isac_cement_yoy_pct, isac_cement_mom_pct

    Commodity production (oil + gas): dollar-generating, export-oriented.
    Domestic production (IPI + ISAC): peso economy, consumption-linked.
    """
    start = (date.today() - timedelta(days=(months + 14) * 31)).strftime("%Y-%m-%d")
    limit = months + 20

    batch_ipi = _fetch_series(
        [IPI_ID, IPI_FOOD_ID, IPI_STEEL_ID, IPI_AUTO_ID],
        limit=limit, start_date=start
    )
    batch_energy = _fetch_series(
        [OIL_ID, GAS_ID, ISAC_CEM_ID],
        limit=limit, start_date=start
    )

    if batch_ipi is None or batch_ipi.empty:
        log.warning("fetch_production: IPI batch failed.")
        return None

    result = batch_ipi[["date"]].copy()

    # IPI headline
    if IPI_ID in batch_ipi.columns:
        result["ipi_yoy_pct"] = batch_ipi[IPI_ID].pct_change(12) * 100
        result["ipi_mom_pct"] = batch_ipi[IPI_ID].pct_change(1)  * 100
    # IPI subsectors
    for series_id, col in [(IPI_FOOD_ID,  "ipi_food_yoy_pct"),
                            (IPI_STEEL_ID, "ipi_steel_yoy_pct"),
                            (IPI_AUTO_ID,  "ipi_auto_yoy_pct")]:
        if series_id in batch_ipi.columns:
            result[col] = batch_ipi[series_id].pct_change(12) * 100

    if batch_energy is not None and not batch_energy.empty:
        if OIL_ID in batch_energy.columns:
            result = result.merge(
                pd.DataFrame({
                    "date":         batch_energy["date"],
                    "oil_yoy_pct":  batch_energy[OIL_ID].pct_change(12) * 100,
                    "oil_mom_pct":  batch_energy[OIL_ID].pct_change(1)  * 100,
                }),
                on="date", how="left"
            )
        if GAS_ID in batch_energy.columns:
            result = result.merge(
                pd.DataFrame({
                    "date":         batch_energy["date"],
                    "gas_yoy_pct":  batch_energy[GAS_ID].pct_change(12) * 100,
                    "gas_mom_pct":  batch_energy[GAS_ID].pct_change(1)  * 100,
                }),
                on="date", how="left"
            )
        if ISAC_CEM_ID in batch_energy.columns:
            result = result.merge(
                pd.DataFrame({
                    "date":               batch_energy["date"],
                    "isac_cement_yoy_pct": batch_energy[ISAC_CEM_ID].pct_change(12) * 100,
                    "isac_cement_mom_pct": batch_energy[ISAC_CEM_ID].pct_change(1)  * 100,
                }),
                on="date", how="left"
            )
    else:
        log.warning("fetch_production: energy/ISAC batch failed.")

    yoy_cols = [c for c in result.columns if c != "date"]
    result = result.dropna(subset=yoy_cols, how="all").tail(months).reset_index(drop=True)

    if result.empty:
        log.warning("fetch_production: empty after YoY computation.")
        return None

    out = PRODUCTION_DIR / "production_monthly.csv"
    result.to_csv(out, index=False)
    log.info("Production (monthly) saved -> %s  (%d rows, latest: %s)",
             out.name, len(result), result["date"].max().strftime("%Y-%m"))
    return result


def fetch_agriculture(years: int = 8) -> pd.DataFrame | None:
    """
    Annual agricultural harvest volumes (tonnes) for soy, corn, wheat.
    Note: harvest data is inherently annual — no monthly breakdown available.
    """
    start = str(date.today().year - years - 1)
    batch = _fetch_series(
        [AGRO_SOY_ID, AGRO_CORN_ID, AGRO_WHEAT_ID],
        limit=years + 4, start_date=start, frequency="year"
    )
    if batch is None or batch.empty:
        # Try without wheat — it may not exist
        batch = _fetch_series(
            [AGRO_SOY_ID, AGRO_CORN_ID],
            limit=years + 4, start_date=start, frequency="year"
        )
    if batch is None or batch.empty:
        log.warning("fetch_agriculture: failed.")
        return None

    rename = {AGRO_SOY_ID: "soy_tonnes", AGRO_CORN_ID: "corn_tonnes"}
    if AGRO_WHEAT_ID in batch.columns:
        rename[AGRO_WHEAT_ID] = "wheat_tonnes"
    batch = batch.rename(columns=rename)

    # YoY for each crop
    for col in ["soy_tonnes", "corn_tonnes", "wheat_tonnes"]:
        if col in batch.columns:
            batch[col.replace("_tonnes", "_yoy_pct")] = batch[col].pct_change(1) * 100

    out = PRODUCTION_DIR / "production_agro.csv"
    batch.to_csv(out, index=False)
    log.info("Agriculture saved -> %s  (%d rows)", out.name, len(batch))
    return batch
