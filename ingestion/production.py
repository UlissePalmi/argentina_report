"""Production: IPI manufacturing, energy (oil/gas), ISAC proxy, agriculture."""

from datetime import date

import pandas as pd

from utils import PRODUCTION_DIR, get_logger
from .client import DatosClient, _start

log = get_logger("fetch.production")
_d  = DatosClient()

IPI_ID        = "11.3_VMASD_2004_M_23"   # EMAE industria index (2004=100); 309.1 removed from datos.gob.ar
IPI_FOOD_ID   = "453.2_ALIMENTOS_DAS_0_0_17_18"
IPI_STEEL_ID  = "453.2_INDUSTRIA_ICA_0_0_21_100"
IPI_AUTO_ID   = "453.2_AUTOPARTESTES_0_0_10_100"
ISAC_CEM_ID   = "33.4_ISAC_CEMENAND_0_0_21_24"
OIL_ID        = "363.3_PRODUCCIONUDO__28"
GAS_ID        = "364.3_PRODUCCIoNRAL__25"
AGRO_SOY_ID   = "AGRO_A_Soja_0003"
AGRO_CORN_ID  = "AGRO_A_Maiz_0003"
AGRO_WHEAT_ID = "AGRO_A_Trigo_0003"


def _yoy_mom(src: pd.DataFrame, sid: str, yoy_col: str, mom_col: str,
             result: pd.DataFrame) -> pd.DataFrame:
    """Merge YoY + MoM for a single series into result."""
    if sid not in src.columns:
        return result
    return result.merge(
        pd.DataFrame({"date": src["date"],
                      yoy_col: src[sid].pct_change(12) * 100,
                      mom_col: src[sid].pct_change(1)  * 100}),
        on="date", how="left")


def fetch_production(months: int = 24) -> pd.DataFrame | None:
    """
    Columns: date, ipi_yoy_pct, ipi_mom_pct, ipi_food_yoy_pct, ipi_steel_yoy_pct,
             ipi_auto_yoy_pct, oil_yoy_pct, oil_mom_pct, gas_yoy_pct, gas_mom_pct,
             isac_cement_yoy_pct, isac_cement_mom_pct
    """
    start, limit = _start(months), months + 20
    b_ipi    = _d.fetch([IPI_ID, IPI_FOOD_ID, IPI_STEEL_ID, IPI_AUTO_ID],
                        limit=limit, start_date=start, frequency="month")
    b_energy = _d.fetch([OIL_ID, GAS_ID, ISAC_CEM_ID],
                        limit=limit, start_date=start, frequency="month")

    if b_ipi is None or b_ipi.empty:
        log.warning("fetch_production: IPI batch failed.")
        return None

    result = b_ipi[["date"]].copy()
    result = _yoy_mom(b_ipi, IPI_ID,       "ipi_yoy_pct",  "ipi_mom_pct",  result)
    for sid, col in [(IPI_FOOD_ID, "ipi_food_yoy_pct"),
                     (IPI_STEEL_ID, "ipi_steel_yoy_pct"),
                     (IPI_AUTO_ID,  "ipi_auto_yoy_pct")]:
        if sid in b_ipi.columns:
            result = result.merge(
                pd.DataFrame({"date": b_ipi["date"], col: b_ipi[sid].pct_change(12) * 100}),
                on="date", how="left")

    if b_energy is not None and not b_energy.empty:
        result = _yoy_mom(b_energy, OIL_ID,      "oil_yoy_pct",          "oil_mom_pct",          result)
        result = _yoy_mom(b_energy, GAS_ID,       "gas_yoy_pct",          "gas_mom_pct",          result)
        result = _yoy_mom(b_energy, ISAC_CEM_ID,  "isac_cement_yoy_pct",  "isac_cement_mom_pct",  result)
    else:
        log.warning("fetch_production: energy/ISAC batch failed.")

    result = result.dropna(subset=[c for c in result.columns if c != "date"], how="all")
    result = result.tail(months).reset_index(drop=True)
    if result.empty:
        return None

    result.to_csv(PRODUCTION_DIR / "production_monthly.csv", index=False)
    log.info("Production (monthly) saved -> production_monthly.csv  (%d rows, latest: %s)",
             len(result), result["date"].max().strftime("%Y-%m"))
    return result


def fetch_agriculture(years: int = 8) -> pd.DataFrame | None:
    """Annual harvest volumes (tonnes) for soy, corn, wheat. No monthly breakdown available."""
    start = str(date.today().year - years - 1)
    batch = _d.fetch([AGRO_SOY_ID, AGRO_CORN_ID, AGRO_WHEAT_ID],
                     limit=years + 4, start_date=start, frequency="year")
    if batch is None or batch.empty:
        batch = _d.fetch([AGRO_SOY_ID, AGRO_CORN_ID],
                         limit=years + 4, start_date=start, frequency="year")
    if batch is None or batch.empty:
        log.warning("fetch_agriculture: failed.")
        return None

    rename = {AGRO_SOY_ID: "soy_tonnes", AGRO_CORN_ID: "corn_tonnes"}
    if AGRO_WHEAT_ID in batch.columns:
        rename[AGRO_WHEAT_ID] = "wheat_tonnes"
    batch = batch.rename(columns=rename)
    for col in ["soy_tonnes", "corn_tonnes", "wheat_tonnes"]:
        if col in batch.columns:
            batch[col.replace("_tonnes", "_yoy_pct")] = batch[col].pct_change(1) * 100

    batch.to_csv(PRODUCTION_DIR / "production_agro.csv", index=False)
    log.info("Agriculture saved -> production_agro.csv  (%d rows)", len(batch))
    return batch
