"""
External sector: government external debt stock and debt service.

Primary sources (datos.gob.ar — INDEC IIP quarterly):
  144.4_PVOSGOLES_0_T_32  — Total government external liabilities (USD m, quarterly)
  144.4_PVOSGOLES_0_T_50  — Portfolio / bonds component (USD m, quarterly)
  144.4_PVOSGOION_0_T_39  — Loans & other investment component (USD m, quarterly)

Secondary (World Bank, annual):
  DT.TDS.DECT.EX.ZS       — Debt service as % of exports
  DT.DOD.DECT.GN.ZS       — External debt as % of GNI

Output: data/external/govt_ext_debt.csv
  Columns: date, total_liab_usd_bn, bonds_usd_bn, loans_usd_bn,
           bonds_pct, loans_pct,
           debt_service_pct_exports, ext_debt_pct_gni
"""

import pandas as pd

from utils import EXTERNAL_DIR, get_logger
from .client import DatosClient, WorldBankClient

log = get_logger("fetch.debt")
_d  = DatosClient()
_wb = WorldBankClient()

# INDEC IIP — government external liabilities by instrument (quarterly, USD millions)
IIP_TOTAL_ID  = "144.4_PVOSGOLES_0_T_32"   # total liabilities
IIP_BONDS_ID  = "144.4_PVOSGOLES_0_T_50"   # portfolio investment (sovereign bonds)
IIP_LOANS_ID  = "144.4_PVOSGOION_0_T_39"   # other investment (IMF, multilaterals, bilateral)

# World Bank annual
WB_DS_EXPORTS = "DT.TDS.DECT.EX.ZS"        # debt service % exports
WB_DEBT_GNI   = "DT.DOD.DECT.GN.ZS"        # external debt % GNI


def fetch_govt_ext_debt(quarters: int = 10) -> pd.DataFrame | None:
    """
    Fetch government external debt stock breakdown and debt service ratios.

    Returns DataFrame with columns:
      date, total_liab_usd_bn, bonds_usd_bn, loans_usd_bn,
      bonds_pct, loans_pct,
      debt_service_pct_exports, ext_debt_pct_gni
    """
    # ------------------------------------------------------------------
    # Step 1: INDEC IIP quarterly — government liabilities by instrument
    # ------------------------------------------------------------------
    from .client import _start
    raw = _d.fetch(
        [IIP_TOTAL_ID, IIP_BONDS_ID, IIP_LOANS_ID],
        limit=quarters + 4,
        start_date=_start(quarters * 3, buffer=6),
    )

    if raw is not None and IIP_TOTAL_ID in raw.columns:
        df = raw[["date"]].copy()
        df["total_liab_usd_bn"] = raw[IIP_TOTAL_ID] / 1_000
        if IIP_BONDS_ID in raw.columns:
            df["bonds_usd_bn"] = raw[IIP_BONDS_ID] / 1_000
        if IIP_LOANS_ID in raw.columns:
            df["loans_usd_bn"] = raw[IIP_LOANS_ID] / 1_000

        # Compute shares
        if "bonds_usd_bn" in df.columns and "loans_usd_bn" in df.columns:
            total = df["total_liab_usd_bn"]
            df["bonds_pct"] = (df["bonds_usd_bn"] / total * 100).round(1)
            df["loans_pct"] = (df["loans_usd_bn"] / total * 100).round(1)

        df = df.dropna(subset=["total_liab_usd_bn"]).tail(quarters).reset_index(drop=True)

        if not df.empty:
            log.info("Govt ext debt: INDEC IIP (%d rows, latest: %s)",
                     len(df), str(df["date"].iloc[-1])[:7])
    else:
        log.warning("Govt ext debt: INDEC IIP unavailable")
        df = pd.DataFrame()

    # ------------------------------------------------------------------
    # Step 2: World Bank annual service ratios — merge onto quarterly
    # ------------------------------------------------------------------
    for wb_id, col in [(WB_DS_EXPORTS, "debt_service_pct_exports"),
                       (WB_DEBT_GNI,   "ext_debt_pct_gni")]:
        raw_wb = _wb.fetch(wb_id, mrv=8)
        if raw_wb is not None and not raw_wb.empty:
            wb = raw_wb.rename(columns={"value": col}).copy()
            wb["date"] = pd.to_datetime(wb["date"].astype(str), format="%Y")
            if not df.empty:
                # Merge on year: map each quarterly row to its year's WB value
                df["_year"] = pd.to_datetime(df["date"]).dt.year
                wb["_year"] = wb["date"].dt.year
                df = df.merge(wb[["_year", col]], on="_year", how="left").drop(columns="_year")
            else:
                # Fallback: return WB-only frame (annual)
                df = wb[["date", col]].tail(8).reset_index(drop=True)
        else:
            log.warning("WB %s unavailable", wb_id)
            if not df.empty:
                df[col] = None

    if df.empty:
        log.warning("Govt ext debt: all sources failed.")
        return None

    df.to_csv(EXTERNAL_DIR / "govt_ext_debt.csv", index=False)
    log.info("Govt ext debt saved -> govt_ext_debt.csv (%d rows)", len(df))
    return df
