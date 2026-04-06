"""
External sector: reserves, FX, current account, trade balance, external debt.
Sources: datos.gob.ar (primary), BCRA REST, IMF SDMX, World Bank (fallbacks).
"""

import socket
from datetime import date

import pandas as pd

from utils import EXTERNAL_DIR, fetch_json, get_logger
from external.client import DatosClient, WorldBankClient, BCRAClient, _start

log  = get_logger("fetch.reserves")
_d   = DatosClient()
_wb  = WorldBankClient()
_bcra = BCRAClient()

# Series IDs
RESERVES_DAILY   = "92.2_RESERVAS_IRES_0_0_32_40"
RESERVES_MONTHLY = "92.1_RID_0_0_32"
FX_IDS           = ["175.1_DR_REFE500_0_0_25", "174.1_T_CAMBIOR_0_0_6", "43.3_TC_0_0_6"]
EXPORTS_ID       = "75.3_IETG_0_M_31"
IMPORTS_ID       = "76.3_ITG_0_M_17"
CA_QUARTERLY_ID  = "160.2_TL_CUENNTE_0_T_22"
IMF_BASE         = "https://dataservices.imf.org/REST/SDMX_JSON.svc"


def _to_monthly_last(raw: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Collapse a daily series to last-of-month."""
    raw["month"] = raw["date"].dt.to_period("M")
    df = raw.groupby("month", as_index=False).last()
    df["date"] = df["month"].dt.to_timestamp()
    return df[["date", value_col]].copy()


def _parse_sdmx(data: dict, value_label: str) -> pd.DataFrame | None:
    try:
        series = data["CompactData"]["DataSet"].get("Series", {})
        if isinstance(series, dict):
            series = [series]
        rows = []
        for s in series:
            obs = s.get("Obs", [])
            if isinstance(obs, dict):
                obs = [obs]
            for o in obs:
                rows.append({"date": o.get("@TIME_PERIOD"), "value": o.get("@OBS_VALUE")})
        if not rows:
            return None
        df = pd.DataFrame(rows)
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        return df.rename(columns={"value": value_label}).dropna(subset=[value_label]).reset_index(drop=True)
    except (KeyError, TypeError) as e:
        log.error("SDMX parse error: %s", e)
        return None


def fetch_reserves(months: int = 24) -> pd.DataFrame | None:
    """Columns: date, reserves_usd_bn"""
    start = _start(months, buffer=1)
    df = None

    raw = _d.fetch([RESERVES_DAILY], limit=months * 31, start_date=start)
    if raw is not None and RESERVES_DAILY in raw.columns:
        raw = raw.rename(columns={RESERVES_DAILY: "reserves_usd_m"})
        df  = _to_monthly_last(raw, "reserves_usd_m")
        log.info("BCRA reserves: datos.gob.ar daily -> monthly")

    if df is None:
        raw2 = _d.fetch([RESERVES_MONTHLY], limit=months + 6, start_date=start)
        if raw2 is not None and RESERVES_MONTHLY in raw2.columns:
            df = raw2.rename(columns={RESERVES_MONTHLY: "reserves_usd_m"})[["date", "reserves_usd_m"]]

    if df is None:
        log.warning("BCRA reserves: datos.gob.ar failed -- trying BCRA REST API")
        raw3 = _bcra.fetch_variable(1, start, date.today().strftime("%Y-%m-%d"))
        if raw3 is not None:
            df = _to_monthly_last(raw3.rename(columns={"value": "reserves_usd_m"}), "reserves_usd_m")

    if df is None:
        log.warning("BCRA reserves: all sources failed.")
        return None

    df["reserves_usd_bn"] = df["reserves_usd_m"] / 1_000
    df = df[["date", "reserves_usd_bn"]].dropna().tail(months).reset_index(drop=True)

    # ------------------------------------------------------------------
    # Net reserves estimate
    # Method: gross minus China swap line drawn + other short-term liabilities
    # Argentina's RMB swap with PBoC: ~CNY 130B = ~USD 18.5B (drawn as of 2024)
    # This is a known approximation; update CHINA_SWAP_BN if BCRA discloses changes.
    # Try BCRA variable 15 first for a direct API figure.
    # ------------------------------------------------------------------
    net_col = _fetch_bcra_net_reserves(months)
    if net_col is not None and len(net_col) > 0:
        # Merge BCRA net series into df on nearest month
        net_col["_ym"] = net_col["date"].dt.to_period("M")
        df["_ym"]      = df["date"].dt.to_period("M")
        merged = df.merge(net_col[["_ym", "net_reserves_usd_bn"]], on="_ym", how="left")
        df["net_reserves_usd_bn"] = merged["net_reserves_usd_bn"].values
        df = df.drop(columns=["_ym"])
        log.info("Net reserves: BCRA API source")
    else:
        CHINA_SWAP_BN = 18.5   # USD bn drawn; see methodology note above
        OTHER_LIAB_BN =  1.5   # Other short-term (repos, minor items)
        df["net_reserves_usd_bn"] = (
            df["reserves_usd_bn"] - CHINA_SWAP_BN - OTHER_LIAB_BN
        ).round(2)
        log.info("Net reserves: estimated (gross - %.1fB China swap - %.1fB other)",
                 CHINA_SWAP_BN, OTHER_LIAB_BN)

    df.to_csv(EXTERNAL_DIR / "bcra_reserves.csv", index=False)
    log.info("BCRA reserves saved -> bcra_reserves.csv  (%d rows)", len(df))
    return df


def _fetch_bcra_net_reserves(months: int) -> pd.DataFrame | None:
    """
    Try BCRA v2.0 variables for net reserves components.
    Returns DataFrame with columns [date, net_reserves_usd_bn] if successful,
    None if no plausible data found.

    BCRA variable 15: "Reservas Internacionales Netas de Pasivos del Sector Público"
    (in USD millions if it exists on v2.0; validation: must be in [-10, 35] range)
    """
    start = _start(months, buffer=2)
    for var_id in [15, 16]:
        try:
            raw = _bcra.fetch_variable(var_id, start, date.today().strftime("%Y-%m-%d"))
            if raw is None or raw.empty:
                continue
            sample_val = raw["value"].dropna()
            if sample_val.empty:
                continue
            # Validate: net reserves in USD millions should be in [-20000, 40000]
            # (i.e., $-20B to $40B — outside this range it's a different variable)
            med = float(sample_val.median())
            if not (-20_000 < med < 40_000):
                log.debug("BCRA var %d median %.0f out of reserves range, skipping", var_id, med)
                continue
            df = _to_monthly_last(raw.rename(columns={"value": "net_usd_m"}), "net_usd_m")
            df["net_reserves_usd_bn"] = df["net_usd_m"] / 1_000
            log.info("BCRA net reserves from variable %d", var_id)
            return df[["date", "net_reserves_usd_bn"]]
        except Exception as e:
            log.debug("BCRA var %d failed: %s", var_id, e)
    return None


def fetch_exchange_rate(months: int = 24) -> pd.DataFrame | None:
    """Columns: date, usd_ars"""
    start = _start(months, buffer=1)
    for fxid in FX_IDS:
        raw = _d.fetch([fxid], limit=months * 31, start_date=start)
        if raw is not None and fxid in raw.columns:
            df = _to_monthly_last(raw.rename(columns={fxid: "usd_ars"}), "usd_ars").tail(months).reset_index(drop=True)
            df.to_csv(EXTERNAL_DIR / "bcra_fx.csv", index=False)
            log.info("BCRA FX saved -> bcra_fx.csv  (%d rows)", len(df))
            return df
    log.warning("BCRA FX rate: all sources failed.")
    return None


def fetch_current_account(quarters: int = 10) -> pd.DataFrame | None:
    """Columns: date (period str), current_account_usd_bn"""
    start = _start(quarters * 3, buffer=12)

    # Primary: datos.gob.ar INDEC quarterly
    raw = fetch_json(DatosClient.URL,
                     params={"ids": CA_QUARTERLY_ID, "format": "json",
                             "limit": quarters + 6, "sort": "asc", "start_date": start},
                     cache_key=f"datos_{CA_QUARTERLY_ID}_{quarters}_{start}")
    if raw and "data" in raw and [m for m in raw.get("meta", []) if "field" in m]:
        df = pd.DataFrame(raw["data"], columns=["date", "current_account_usd_m"])
        df["date"] = pd.to_datetime(df["date"])
        df["date"] = (df["date"] + pd.offsets.QuarterEnd(0)).dt.to_period("Q").astype(str)
        df["current_account_usd_bn"] = pd.to_numeric(df["current_account_usd_m"], errors="coerce") / 1_000
        df = df[["date", "current_account_usd_bn"]].dropna().tail(quarters).reset_index(drop=True)
        if not df.empty:
            df.to_csv(EXTERNAL_DIR / "imf_current_account.csv", index=False)
            log.info("Current account (INDEC quarterly) saved -> imf_current_account.csv  (%d rows)", len(df))
            return df

    # Fallback: IMF SDMX
    log.warning("CA: datos.gob.ar failed -- trying IMF SDMX")
    try:
        socket.setdefaulttimeout(4)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("dataservices.imf.org", 443))
        reachable = True
    except OSError:
        reachable = False
        log.warning("IMF host unreachable -- skipping")
    finally:
        socket.setdefaulttimeout(None)

    if reachable:
        yr = date.today().year - 4
        for url, ck in [
            (f"{IMF_BASE}/CompactData/BOP/Q.AR.BCA",           f"imf_bop_bca_AR_{yr}"),
            (f"{IMF_BASE}/CompactData/IFS/Q.AR.BCAXF_BP6_USD", f"imf_ifs_bca_AR_{yr}"),
        ]:
            data = fetch_json(url, params={"startPeriod": str(yr), "endPeriod": str(date.today().year)},
                              headers={"Accept": "application/json"}, cache_key=ck,
                              max_retries=2, timeout=15)
            if data:
                df = _parse_sdmx(data, "current_account_usd_bn")
                if df is not None and not df.empty:
                    df["current_account_usd_bn"] /= 1_000
                    df = df.tail(quarters).reset_index(drop=True)
                    df.to_csv(EXTERNAL_DIR / "imf_current_account.csv", index=False)
                    log.info("IMF CA saved -> imf_current_account.csv  (%d rows)", len(df))
                    return df

    log.warning("Current account: all sources failed.")
    return None


def fetch_trade_balance(months: int = 24) -> pd.DataFrame | None:
    """Columns: date, exports_usd_bn, imports_usd_bn, trade_balance_usd_bn"""
    start = _start(months, buffer=2)
    raw = _d.fetch([EXPORTS_ID, IMPORTS_ID], limit=months + 6, start_date=start)
    if raw is not None and EXPORTS_ID in raw.columns and IMPORTS_ID in raw.columns:
        df = raw[["date"]].copy()
        df["exports_usd_bn"]      = raw[EXPORTS_ID] / 1_000
        df["imports_usd_bn"]      = raw[IMPORTS_ID] / 1_000
        df["trade_balance_usd_bn"] = df["exports_usd_bn"] - df["imports_usd_bn"]
        df = df.dropna(subset=["exports_usd_bn"]).tail(months).reset_index(drop=True)
        df.to_csv(EXTERNAL_DIR / "indec_trade.csv", index=False)
        log.info("Trade balance saved -> indec_trade.csv  (%d rows)", len(df))
        return df

    log.warning("INDEC trade: datos.gob.ar failed -- trying World Bank fallback")
    exp = _wb.fetch("TX.VAL.MRCH.CD.WT", mrv=8)
    imp = _wb.fetch("TM.VAL.MRCH.CD.WT", mrv=8)
    if exp is None or imp is None:
        log.error("Trade balance: World Bank fallback also failed.")
        return None
    df = exp.rename(columns={"value": "exports_usd_bn"}).merge(
         imp.rename(columns={"value": "imports_usd_bn"}), on="date")
    df[["exports_usd_bn", "imports_usd_bn"]] /= 1e9
    df["trade_balance_usd_bn"] = df["exports_usd_bn"] - df["imports_usd_bn"]
    df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y")
    df.to_csv(EXTERNAL_DIR / "indec_trade_wb_fallback.csv", index=False)
    log.warning("Trade balance from WB fallback -> indec_trade_wb_fallback.csv  (annual data)")
    return df.sort_values("date").reset_index(drop=True)


def fetch_external_debt(years: int = 8) -> pd.DataFrame | None:
    """Columns: date, ext_debt_pct_gni"""
    df = _wb.fetch("DT.DOD.DECT.GN.ZS", mrv=years + 2)
    if df is None:
        log.warning("WB external debt: failed.")
        return None
    df = df.rename(columns={"value": "ext_debt_pct_gni"}).tail(years).reset_index(drop=True)
    df.to_csv(EXTERNAL_DIR / "wb_ext_debt.csv", index=False)
    log.info("WB ext debt saved -> wb_ext_debt.csv  (%d rows)", len(df))
    return df


def fetch_current_account_pct_gdp(years: int = 8) -> pd.DataFrame | None:
    """Columns: date, current_account_pct_gdp"""
    df = _wb.fetch("BN.CAB.XOKA.GD.ZS", mrv=years + 2)
    if df is None:
        log.warning("WB CA balance: failed.")
        return None
    df = df.rename(columns={"value": "current_account_pct_gdp"}).tail(years).reset_index(drop=True)
    df.to_csv(EXTERNAL_DIR / "wb_current_account_pct_gdp.csv", index=False)
    log.info("WB CA pct-GDP saved -> wb_current_account_pct_gdp.csv  (%d rows)", len(df))
    return df
