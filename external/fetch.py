"""
External module — data fetching.

Covers: international reserves, FX rate, current account, trade balance,
        external debt, CA % GDP (World Bank fallback).

Sources: datos.gob.ar (primary), IMF SDMX (CA fallback), World Bank (debt + CA fallback)
"""

import socket
from datetime import date, timedelta

import pandas as pd

from utils import EXTERNAL_DIR, fetch_json, get_logger

log = get_logger("external.fetch")

SERIES_BASE = "https://apis.datos.gob.ar/series/api/series/"
BCRA_BASE   = "https://api.bcra.gob.ar/estadisticas/v2.0"
BCRA_HEADERS = {"accept": "application/json"}
IMF_BASE    = "https://dataservices.imf.org/REST/SDMX_JSON.svc"
WB_BASE     = "https://api.worldbank.org/v2/country/AR/indicator"

# Series IDs
RESERVES_DAILY   = "92.2_RESERVAS_IRES_0_0_32_40"
RESERVES_MONTHLY = "92.1_RID_0_0_32"
FX_IDS           = ["175.1_DR_REFE500_0_0_25", "174.1_T_CAMBIOR_0_0_6", "43.3_TC_0_0_6"]
EXPORTS_ID       = "75.3_IETG_0_M_31"
IMPORTS_ID       = "76.3_ITG_0_M_17"
CA_QUARTERLY_ID  = "160.2_TL_CUENNTE_0_T_22"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _fetch_datos(ids: list[str], limit: int, start_date: str | None = None) -> pd.DataFrame | None:
    params: dict = {"ids": ",".join(ids), "format": "json", "limit": limit, "sort": "asc"}
    if start_date:
        params["start_date"] = start_date
    cache_key = f"datos_{'_'.join(s[:20] for s in ids)}_{limit}_{start_date or ''}"
    data = fetch_json(SERIES_BASE, params=params, cache_key=cache_key)
    if data is None or "data" not in data:
        return None
    meta = data.get("meta", [])
    columns = ["date"] + [m["field"]["id"] for m in meta if "field" in m]
    df = pd.DataFrame(data["data"], columns=columns)
    df["date"] = pd.to_datetime(df["date"])
    for col in columns[1:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("date").reset_index(drop=True)


def _fetch_bcra_variable(var_id: int, desde: str, hasta: str) -> pd.DataFrame | None:
    from datetime import datetime as _dt
    start = _dt.strptime(desde, "%Y-%m-%d")
    end   = _dt.strptime(hasta, "%Y-%m-%d")
    all_rows = []
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + timedelta(days=364), end)
        d1, d2 = cursor.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")
        url = f"{BCRA_BASE}/datosvariable/{var_id}/{d1}/{d2}"
        data = fetch_json(url, headers=BCRA_HEADERS, verify_ssl=False,
                          cache_key=f"bcra_var{var_id}_{d1}_{d2}",
                          max_retries=2, timeout=15)
        if data:
            all_rows.extend(data.get("results", []))
        cursor = chunk_end + timedelta(days=1)
    if not all_rows:
        return None
    df = pd.DataFrame(all_rows).rename(columns={"fecha": "date", "valor": "value"})
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.drop_duplicates("date").sort_values("date").reset_index(drop=True)


def _wb_indicator(indicator: str, mrv: int) -> pd.DataFrame | None:
    params = {"format": "json", "mrv": mrv, "per_page": mrv}
    data = fetch_json(f"{WB_BASE}/{indicator}", params=params,
                      cache_key=f"wb_{indicator}_mrv{mrv}_A")
    if not isinstance(data, list) or len(data) < 2 or not data[1]:
        return None
    rows = [{"date": r["date"], "value": float(r["value"])}
            for r in data[1] if r.get("value") is not None]
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True) if rows else None


def _parse_sdmx(data: dict, value_label: str = "value") -> pd.DataFrame | None:
    try:
        series = data["CompactData"]["DataSet"].get("Series", {})
        if isinstance(series, dict):
            series = [series]
        rows = []
        for s in series:
            obs_list = s.get("Obs", [])
            if isinstance(obs_list, dict):
                obs_list = [obs_list]
            for obs in obs_list:
                rows.append({"date": obs.get("@TIME_PERIOD"), "value": obs.get("@OBS_VALUE")})
        if not rows:
            return None
        df = pd.DataFrame(rows)
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        return df.rename(columns={"value": value_label}).dropna(subset=[value_label]).reset_index(drop=True)
    except (KeyError, TypeError) as e:
        log.error("SDMX parse error: %s", e)
        return None


# ---------------------------------------------------------------------------
# Public: gross international reserves (monthly, USD billions)
# ---------------------------------------------------------------------------
def fetch_reserves(months: int = 24) -> pd.DataFrame | None:
    """Columns: date, reserves_usd_bn"""
    start = (date.today() - timedelta(days=months * 31 + 30)).strftime("%Y-%m-%d")
    df = None

    raw = _fetch_datos([RESERVES_DAILY], limit=months * 31, start_date=start)
    if raw is not None and not raw.empty and RESERVES_DAILY in raw.columns:
        raw["month"] = raw["date"].dt.to_period("M")
        df_m = raw.groupby("month", as_index=False).last()
        df_m["date"] = df_m["month"].dt.to_timestamp()
        df_m.rename(columns={RESERVES_DAILY: "reserves_usd_m"}, inplace=True)
        df = df_m[["date", "reserves_usd_m"]].copy()
        log.info("BCRA reserves: datos.gob.ar daily series (collapsed to monthly)")

    if df is None:
        raw2 = _fetch_datos([RESERVES_MONTHLY], limit=months + 6, start_date=start)
        if raw2 is not None and not raw2.empty and RESERVES_MONTHLY in raw2.columns:
            raw2.rename(columns={RESERVES_MONTHLY: "reserves_usd_m"}, inplace=True)
            df = raw2[["date", "reserves_usd_m"]].copy()

    if df is None:
        log.warning("BCRA reserves: datos.gob.ar failed — trying BCRA REST API")
        hasta = date.today().strftime("%Y-%m-%d")
        raw3 = _fetch_bcra_variable(1, start, hasta)
        if raw3 is not None:
            raw3["month"] = raw3["date"].dt.to_period("M")
            df_m = raw3.groupby("month", as_index=False).last()
            df_m["date"] = df_m["month"].dt.to_timestamp()
            df_m.rename(columns={"value": "reserves_usd_m"}, inplace=True)
            df = df_m[["date", "reserves_usd_m"]].copy()

    if df is None:
        log.warning("BCRA reserves: all sources failed.")
        return None

    df["reserves_usd_bn"] = df["reserves_usd_m"] / 1_000
    df = df[["date", "reserves_usd_bn"]].dropna().tail(months).reset_index(drop=True)
    out = EXTERNAL_DIR / "bcra_reserves.csv"
    df.to_csv(out, index=False)
    log.info("BCRA reserves saved → %s  (%d rows)", out.name, len(df))
    return df


# ---------------------------------------------------------------------------
# Public: official FX rate (monthly last obs, ARS/USD)
# ---------------------------------------------------------------------------
def fetch_exchange_rate(months: int = 24) -> pd.DataFrame | None:
    """Columns: date, usd_ars"""
    start = (date.today() - timedelta(days=months * 31 + 30)).strftime("%Y-%m-%d")
    for fxid in FX_IDS:
        raw = _fetch_datos([fxid], limit=months * 31, start_date=start)
        if raw is not None and not raw.empty and fxid in raw.columns:
            raw["month"] = raw["date"].dt.to_period("M")
            df_m = raw.groupby("month", as_index=False).last()
            df_m["date"] = df_m["month"].dt.to_timestamp()
            df_m.rename(columns={fxid: "usd_ars"}, inplace=True)
            df = df_m[["date", "usd_ars"]].tail(months).reset_index(drop=True)
            out = EXTERNAL_DIR / "bcra_fx.csv"
            df.to_csv(out, index=False)
            log.info("BCRA FX saved → %s  (%d rows)", out.name, len(df))
            return df
    log.warning("BCRA FX rate: all sources failed.")
    return None


# ---------------------------------------------------------------------------
# Public: current account balance (quarterly, USD billions)
# ---------------------------------------------------------------------------
def fetch_current_account(quarters: int = 10) -> pd.DataFrame | None:
    """Columns: date (period str), current_account_usd_bn"""
    start = (date.today() - timedelta(days=(quarters + 4) * 95)).strftime("%Y-%m-%d")
    params = {"ids": CA_QUARTERLY_ID, "format": "json",
              "limit": quarters + 6, "sort": "asc", "start_date": start}
    data = fetch_json(SERIES_BASE, params=params,
                      cache_key=f"datos_{CA_QUARTERLY_ID}_{quarters}_{start}")

    if data is not None and "data" in data:
        meta = [m for m in data.get("meta", []) if "field" in m]
        if meta:
            df = pd.DataFrame(data["data"], columns=["date", "current_account_usd_m"])
            df["date"] = pd.to_datetime(df["date"])
            eoq = df["date"] + pd.offsets.QuarterEnd(0)
            df["date"] = eoq.dt.to_period("Q").astype(str)
            df["current_account_usd_m"] = pd.to_numeric(df["current_account_usd_m"], errors="coerce")
            df["current_account_usd_bn"] = df["current_account_usd_m"] / 1_000
            df = df[["date", "current_account_usd_bn"]].dropna().tail(quarters).reset_index(drop=True)
            if not df.empty:
                out = EXTERNAL_DIR / "imf_current_account.csv"
                df.to_csv(out, index=False)
                log.info("Current account (INDEC quarterly) saved → %s  (%d rows)", out.name, len(df))
                return df

    # IMF SDMX fallback
    log.warning("CA: datos.gob.ar failed — trying IMF SDMX")
    _reachable = False
    try:
        socket.setdefaulttimeout(4)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("dataservices.imf.org", 443))
        _reachable = True
    except OSError:
        log.warning("IMF host unreachable — skipping")
    finally:
        socket.setdefaulttimeout(None)

    if _reachable:
        start_year = date.today().year - 4
        for url, ck in [
            (f"{IMF_BASE}/CompactData/BOP/Q.AR.BCA", f"imf_bop_bca_AR_{start_year}"),
            (f"{IMF_BASE}/CompactData/IFS/Q.AR.BCAXF_BP6_USD", f"imf_ifs_bca_AR_{start_year}"),
        ]:
            raw = fetch_json(url, params={"startPeriod": str(start_year),
                                          "endPeriod": str(date.today().year)},
                             headers={"Accept": "application/json"},
                             cache_key=ck, max_retries=2, timeout=15)
            if raw:
                df = _parse_sdmx(raw, "current_account_usd_bn")
                if df is not None and not df.empty:
                    df["current_account_usd_bn"] /= 1_000
                    df = df.tail(quarters).reset_index(drop=True)
                    out = EXTERNAL_DIR / "imf_current_account.csv"
                    df.to_csv(out, index=False)
                    log.info("IMF CA saved → %s  (%d rows)", out.name, len(df))
                    return df

    log.warning("Current account: all sources failed.")
    return None


# ---------------------------------------------------------------------------
# Public: trade balance (monthly, USD billions)
# ---------------------------------------------------------------------------
def fetch_trade_balance(months: int = 24) -> pd.DataFrame | None:
    """Columns: date, exports_usd_bn, imports_usd_bn, trade_balance_usd_bn"""
    start = (date.today() - timedelta(days=months * 31 + 60)).strftime("%Y-%m-%d")
    params: dict = {"ids": f"{EXPORTS_ID},{IMPORTS_ID}", "format": "json",
                    "limit": months + 6, "sort": "asc"}
    if start:
        params["start_date"] = start
    cache_key = f"datos_{EXPORTS_ID[:20]}_{IMPORTS_ID[:20]}_{months + 6}_{start}"
    data = fetch_json(SERIES_BASE, params=params, cache_key=cache_key)

    if data is not None and "data" in data:
        meta = data.get("meta", [])
        columns = ["date"] + [m["field"]["id"] for m in meta if "field" in m]
        df = pd.DataFrame(data["data"], columns=columns)
        df["date"] = pd.to_datetime(df["date"])
        for col in columns[1:]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        if EXPORTS_ID in df.columns and IMPORTS_ID in df.columns:
            df["exports_usd_bn"] = df[EXPORTS_ID] / 1_000
            df["imports_usd_bn"] = df[IMPORTS_ID] / 1_000
            df["trade_balance_usd_bn"] = df["exports_usd_bn"] - df["imports_usd_bn"]
            df = df[["date", "exports_usd_bn", "imports_usd_bn", "trade_balance_usd_bn"]]
            df = df.dropna(subset=["exports_usd_bn"]).tail(months).reset_index(drop=True)
            out = EXTERNAL_DIR / "indec_trade.csv"
            df.to_csv(out, index=False)
            log.info("Trade balance saved → %s  (%d rows)", out.name, len(df))
            return df

    log.warning("INDEC trade: datos.gob.ar failed — trying World Bank fallback")
    return _fetch_trade_wb_fallback(months)


def _fetch_trade_wb_fallback(months: int) -> pd.DataFrame | None:
    exp = _wb_indicator("TX.VAL.MRCH.CD.WT", mrv=8)
    imp = _wb_indicator("TM.VAL.MRCH.CD.WT", mrv=8)
    if exp is None or imp is None:
        log.error("Trade balance: World Bank fallback also failed.")
        return None
    df = exp.rename(columns={"value": "exports_usd_bn"}).merge(
        imp.rename(columns={"value": "imports_usd_bn"}), on="date", how="inner")
    df["exports_usd_bn"] /= 1e9
    df["imports_usd_bn"] /= 1e9
    df["trade_balance_usd_bn"] = df["exports_usd_bn"] - df["imports_usd_bn"]
    df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y")
    df = df.sort_values("date").reset_index(drop=True)
    out = EXTERNAL_DIR / "indec_trade_wb_fallback.csv"
    df.to_csv(out, index=False)
    log.warning("Trade balance from WB fallback → %s  (annual data)", out.name)
    return df


# ---------------------------------------------------------------------------
# Public: external debt (annual, % of GNI)
# ---------------------------------------------------------------------------
def fetch_external_debt(years: int = 8) -> pd.DataFrame | None:
    """Columns: date, ext_debt_pct_gni"""
    df = _wb_indicator("DT.DOD.DECT.GN.ZS", mrv=years + 2)
    if df is None or df.empty:
        log.warning("WB external debt: failed.")
        return None
    df.rename(columns={"value": "ext_debt_pct_gni"}, inplace=True)
    df = df.tail(years).reset_index(drop=True)
    out = EXTERNAL_DIR / "wb_ext_debt.csv"
    df.to_csv(out, index=False)
    log.info("WB ext debt saved → %s  (%d rows)", out.name, len(df))
    return df


# ---------------------------------------------------------------------------
# Public: current account % GDP (annual WB fallback)
# ---------------------------------------------------------------------------
def fetch_current_account_pct_gdp(years: int = 8) -> pd.DataFrame | None:
    """Columns: date, current_account_pct_gdp"""
    df = _wb_indicator("BN.CAB.XOKA.GD.ZS", mrv=years + 2)
    if df is None or df.empty:
        log.warning("WB CA balance: failed.")
        return None
    df.rename(columns={"value": "current_account_pct_gdp"}, inplace=True)
    df = df.tail(years).reset_index(drop=True)
    out = EXTERNAL_DIR / "wb_current_account_pct_gdp.csv"
    df.to_csv(out, index=False)
    log.info("WB CA pct-GDP saved → %s  (%d rows)", out.name, len(df))
    return df
