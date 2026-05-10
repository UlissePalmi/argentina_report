"""Inflation: INDEC CPI index, MoM %, and YoY %."""

from utils import INFLATION_DIR, get_logger
from .client import DatosClient, _start

log = get_logger("fetch.inflation")
_d  = DatosClient()

IPC_INDEX_ID = "148.3_INIVELNAL_DICI_M_26"
IPC_MOM_ID   = "145.3_INGNACUAL_DICI_M_38"


def fetch_cpi(months: int = 24):
    """Columns: date, cpi_index, cpi_mom_pct, cpi_yoy_pct"""
    df = _d.fetch([IPC_INDEX_ID, IPC_MOM_ID], limit=months + 20, start_date=_start(months))
    if df is None or df.empty:
        log.warning("INDEC CPI: fetch failed.")
        return None
    df = df.rename(columns={IPC_INDEX_ID: "cpi_index", IPC_MOM_ID: "cpi_mom_raw"})
    df["cpi_mom_pct"] = df["cpi_mom_raw"] * 100
    df["cpi_yoy_pct"] = df["cpi_index"].pct_change(12) * 100
    df = df.drop(columns=["cpi_mom_raw"]).dropna(subset=["cpi_mom_pct"]).tail(months).reset_index(drop=True)
    df.to_csv(INFLATION_DIR / "indec_cpi.csv", index=False)
    log.info("INDEC CPI saved -> indec_cpi.csv  (%d rows)", len(df))
    return df
