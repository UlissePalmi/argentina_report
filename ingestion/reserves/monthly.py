"""BCRA gross international reserves — monthly time series."""

import pandas as pd

from utils import RESERVES_DIR, get_logger
from ..client import DatosClient, _start, to_monthly_last

log = get_logger("fetch.reserves")
_d  = DatosClient()

RESERVES_DAILY   = "92.2_RESERVAS_IRES_0_0_32_40"
RESERVES_MONTHLY = "92.1_RID_0_0_32"


def fetch_reserves(months: int = 24) -> pd.DataFrame | None:
    """Fetch BCRA gross international reserves (monthly time series).

    Tries the daily datos.gob.ar series first (collapsed to month-end), falls
    back to the monthly series. Columns: date, reserves_usd_bn.
    """
    start = _start(months, buffer=1)
    df = None

    raw = _d.fetch([RESERVES_DAILY], limit=months * 31, start_date=start)
    if raw is not None and RESERVES_DAILY in raw.columns:
        raw = raw.rename(columns={RESERVES_DAILY: "reserves_usd_m"})
        df  = to_monthly_last(raw, "reserves_usd_m")
        log.info("BCRA reserves: datos.gob.ar daily -> monthly")

    if df is None:
        raw2 = _d.fetch([RESERVES_MONTHLY], limit=months + 6, start_date=start)
        if raw2 is not None and RESERVES_MONTHLY in raw2.columns:
            df = raw2.rename(columns={RESERVES_MONTHLY: "reserves_usd_m"})[["date", "reserves_usd_m"]]

    if df is None:
        log.warning("BCRA reserves: all sources failed.")
        return None

    df["reserves_usd_bn"] = df["reserves_usd_m"] / 1_000
    df = df[["date", "reserves_usd_bn"]].dropna().tail(months).reset_index(drop=True)

    df.to_csv(RESERVES_DIR / "bcra_reserves.csv", index=False)
    log.info("BCRA reserves saved -> bcra_reserves.csv  (%d rows)", len(df))
    return df
