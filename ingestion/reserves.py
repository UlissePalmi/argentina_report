"""
External sector: reserves, FX, current account, trade balance, external debt.
Sources: datos.gob.ar (primary), BCRA REST, IMF SDMX, World Bank (fallbacks).
"""

import socket

import pandas as pd

from utils import RESERVES_DIR, fetch_json, get_logger
from .client import DatosClient, WorldBankClient, _start

log   = get_logger("fetch.reserves")
_d    = DatosClient()
_wb   = WorldBankClient()

# Series IDs
RESERVES_DAILY   = "92.2_RESERVAS_IRES_0_0_32_40"
RESERVES_MONTHLY = "92.1_RID_0_0_32"
FX_IDS           = ["175.1_DR_REFE500_0_0_25", "174.1_T_CAMBIOR_0_0_6", "43.3_TC_0_0_6"]
EXPORTS_ID       = "75.3_IETG_0_M_31"
IMPORTS_ID       = "76.3_ITG_0_M_17"
CA_QUARTERLY_ID  = "160.2_TL_CUENNTE_0_T_22"
IMF_BASE         = "https://dataservices.imf.org/REST/SDMX_JSON.svc"
M2_SERIES_ID     = "90.1_AMTMA_0_0_39"   # M2 privado, monthly, millions ARS (Sep 2013–)

# BCRA balance sheet reserve components — dataset 300 (ARS thousands, monthly).
# Sourced from the BCRA's Apertura de Activos del Balance.
# Conversion to USD: divide by concurrent ARS/USD FX rate.
# All four active series sum precisely to the total (verified Oct 2025).
_BREAKDOWN_SERIES = {
    "gold_net":     "300.1_AP_ACT_RESNES_0_M_42",  # Net gold (after fineness provisions)
    "divisas":      "300.1_AP_ACT_RESSAS_0_M_29",  # Foreign currency (spot deposits, SDRs, IMF position)
    "colocaciones": "300.1_AP_ACT_RESSAS_0_M_54",  # Realizable placements (bonds, term deposits)
    "swaps":        "300.1_AP_ACT_RESIOR_0_M_51",  # Passive swaps with exterior (China RMB, BIS repos)
    "derivatives":  "300.1_AP_ACT_RESTER_0_M_59",  # Derivative instruments (typically negative)
}

# Human-readable metadata for each component.
_BREAKDOWN_META = {
    "gold_net": {
        "label":     "Monetary gold (net)",
        "is_liquid": False,
        "note":      "Physical gold at market value, net of fineness-purity provision; "
                     "deployable only via repo or sale",
    },
    "divisas": {
        "label":     "Foreign currency deposits",
        "is_liquid": True,
        "note":      "Spot deposits at BIS, US Fed, IMF (incl. SDR holdings and IMF reserve tranche); "
                     "most liquid tier of reserves",
    },
    "colocaciones": {
        "label":     "Investable foreign currency placements",
        "is_liquid": True,
        "note":      "US Treasuries, foreign sovereign bonds, and term deposits at foreign banks; "
                     "liquid but with settlement lag",
    },
    "swaps": {
        "label":     "Passive currency swaps (net)",
        "is_liquid": False,
        "note":      "Bilateral currency swap lines drawn from third parties (e.g. China RMB swap); "
                     "counted in gross reserves but deducted for net/liquid calculations",
    },
    "derivatives": {
        "label":     "Derivative instruments",
        "is_liquid": False,
        "note":      "Net mark-to-market of FX forwards and other derivatives; typically a small negative",
    },
}

# Static fallback: real BCRA balance sheet data for Oct 2025 (latest available via API).
# Source: BCRA Apertura de Activos, dataset 300, datos.gob.ar — values converted at
# ARS/USD 1,437 (Oct 2025 official rate). Refresh when API series lag exceeds 3 months.
_BREAKDOWN_STATIC = {
    "as_of":  "2025-10-31",
    "source": "BCRA Balance Sheet / Apertura de Activos (dataset 300, datos.gob.ar, Oct 2025)",
    "components": [
        {
            "category":  "divisas",
            "label":     "Foreign currency deposits",
            "usd_bn":    22.42,
            "is_liquid": True,
            "note":      "Spot deposits at BIS, Fed, IMF (incl. SDR and IMF reserve tranche)",
        },
        {
            "category":  "colocaciones",
            "label":     "Investable foreign currency placements",
            "usd_bn":    9.32,
            "is_liquid": True,
            "note":      "US Treasuries, foreign sovereign bonds, term deposits",
        },
        {
            "category":  "gold_net",
            "label":     "Monetary gold (net)",
            "usd_bn":    7.97,
            "is_liquid": False,
            "note":      "Physical gold at market value, net of fineness provision",
        },
        {
            "category":  "derivatives",
            "label":     "Derivative instruments",
            "usd_bn":    -0.17,
            "is_liquid": False,
            "note":      "Net mark-to-market FX forwards and other derivatives",
        },
    ],
}


def _to_monthly_last(raw: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Collapse a daily series to last-of-month."""
    raw["month"] = raw["date"].dt.to_period("M")
    df = raw.groupby("month", as_index=False).last()
    df["date"] = df["month"].dt.to_timestamp()
    return df[["date", value_col]].copy()


def _parse_sdmx(data: dict, value_label: str) -> pd.DataFrame | None:
    """Parse an IMF SDMX-JSON CompactData response into a date/value DataFrame."""
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


def fetch_gross_reserves(months: int = 24) -> pd.DataFrame | None:
    """Fetch BCRA gross international reserves.

    Tries the daily datos.gob.ar series first (collapsed to month-end), falls
    back to the monthly series. Columns: date, reserves_usd_bn.
    """
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
        log.warning("BCRA reserves: all sources failed.")
        return None

    df["reserves_usd_bn"] = df["reserves_usd_m"] / 1_000
    df = df[["date", "reserves_usd_bn"]].dropna().tail(months).reset_index(drop=True)

    df.to_csv(RESERVES_DIR / "bcra_reserves.csv", index=False)
    log.info("BCRA reserves saved -> bcra_reserves.csv  (%d rows)", len(df))
    return df


def estimate_net_reserves(df: pd.DataFrame) -> pd.DataFrame:
    """Add a net_reserves_usd_bn column by subtracting known short-term liabilities.

    Deducts the drawn China RMB swap line (~USD 18.5B as of 2024) and other
    short-term items. Update CHINA_SWAP_BN if BCRA discloses changes.
    BCRA API is fully deprecated so no direct net figure is available from the API.
    """
    CHINA_SWAP_BN = 18.5
    OTHER_LIAB_BN =  1.5   # repos, minor short-term items
    df = df.copy()
    df["net_reserves_usd_bn"] = (
        df["reserves_usd_bn"] - CHINA_SWAP_BN - OTHER_LIAB_BN
    ).round(2)
    log.info("Net reserves: estimated (gross - %.1fB China swap - %.1fB other)",
             CHINA_SWAP_BN, OTHER_LIAB_BN)
    return df


def fetch_reserves(months: int = 24) -> pd.DataFrame | None:
    """Fetch gross reserves and append the net reserves estimate.

    Convenience wrapper combining fetch_gross_reserves and estimate_net_reserves.
    Columns: date, reserves_usd_bn, net_reserves_usd_bn.
    """
    df = fetch_gross_reserves(months)
    if df is None:
        return None
    return estimate_net_reserves(df)


def fetch_reserves_breakdown(months: int = 24) -> pd.DataFrame | None:
    """Fetch a monthly time-series breakdown of BCRA gross international reserves.

    Source: BCRA Apertura de Activos (dataset 300, datos.gob.ar). Series are
    denominated in ARS thousands and converted to USD billions using the concurrent
    official FX rate. The four active components sum precisely to the reported total.

    Components:
      - gold_net      : monetary gold at market value, net of fineness provision
      - divisas       : spot deposits (BIS, Fed, IMF) incl. SDRs and IMF reserve tranche
      - colocaciones  : investable placements (US Treasuries, foreign bonds, term deposits)
      - swaps         : passive currency swaps drawn from third parties (if active)
      - derivatives   : net FX derivative mark-to-market (usually small/negative)

    Returns a long-format DataFrame (date, category, label, usd_bn, is_liquid, note).
    Saves bcra_reserves_breakdown.csv (wide) and bcra_reserves_breakdown_long.csv (long).
    Falls back to a static Oct-2025 snapshot when the API series are not yet updated.
    """
    start = _start(months, buffer=2)
    all_sids = list(_BREAKDOWN_SERIES.values()) + [FX_IDS[0]]
    raw = _d.fetch(all_sids, limit=months + 6, start_date=start)

    fx_sid = FX_IDS[0]
    use_api = (
        raw is not None
        and fx_sid in raw.columns
        and any(sid in raw.columns for sid in _BREAKDOWN_SERIES.values())
    )

    if use_api:
        fx = raw[["date", fx_sid]].dropna().set_index("date").rename(columns={fx_sid: "fx"})
        rows = []
        for cat, sid in _BREAKDOWN_SERIES.items():
            if sid not in raw.columns:
                continue
            series = raw[["date", sid]].dropna().set_index("date")
            merged = series.join(fx, how="inner")
            if merged.empty:
                continue
            meta = _BREAKDOWN_META[cat]
            for date_idx, row in merged.iterrows():
                ars_k  = row[sid]
                rate   = row["fx"]
                usd_bn = round((ars_k * 1_000) / rate / 1e9, 3) if rate > 0 else None
                if usd_bn is not None:
                    rows.append({
                        "date":      date_idx,
                        "category":  cat,
                        "label":     meta["label"],
                        "usd_bn":    usd_bn,
                        "is_liquid": meta["is_liquid"],
                        "note":      meta["note"],
                    })

        if rows:
            long_df = pd.DataFrame(rows).sort_values(["date", "category"]).reset_index(drop=True)
            latest  = long_df["date"].max().strftime("%Y-%m")
            liquid  = long_df.loc[long_df["date"] == long_df["date"].max()].query("is_liquid")["usd_bn"].sum()
            gross   = long_df.loc[long_df["date"] == long_df["date"].max()]["usd_bn"].sum()
            log.info(
                "Reserves breakdown: %d months fetched from datos.gob.ar (latest %s). "
                "Gross=$%.1fB  Liquid=$%.1fB",
                long_df["date"].nunique(), latest, gross, liquid,
            )
            _save_breakdown(long_df)
            return long_df
        log.warning("Reserves breakdown: API series returned no usable rows.")

    # Static fallback — real Oct-2025 BCRA balance sheet values
    log.info("Reserves breakdown: API unavailable — using static fallback (%s)", _BREAKDOWN_STATIC["as_of"])
    rows = [
        {
            "date":      pd.Timestamp(_BREAKDOWN_STATIC["as_of"]),
            "category":  c["category"],
            "label":     c["label"],
            "usd_bn":    c["usd_bn"],
            "is_liquid": c["is_liquid"],
            "note":      c["note"],
        }
        for c in _BREAKDOWN_STATIC["components"]
    ]
    long_df = pd.DataFrame(rows)
    _save_breakdown(long_df)
    return long_df


def _save_breakdown(long_df: pd.DataFrame) -> None:
    """Save long and wide CSV files for the reserves breakdown."""
    long_df.to_csv(RESERVES_DIR / "bcra_reserves_breakdown_long.csv", index=False)

    wide = long_df.pivot_table(index="date", columns="category", values="usd_bn", aggfunc="sum")
    wide.columns.name = None
    # Add summary columns
    liquid_cats = set(
        long_df.loc[long_df["is_liquid"], "category"].unique()
    )
    wide["total_gross_usd_bn"] = wide.sum(axis=1)
    wide["liquid_usd_bn"]      = wide[[c for c in wide.columns if c in liquid_cats]].sum(axis=1)
    wide = wide.reset_index()
    wide.to_csv(RESERVES_DIR / "bcra_reserves_breakdown.csv", index=False)
    log.info(
        "Reserves breakdown saved -> bcra_reserves_breakdown.csv (%d months)",
        len(wide),
    )


def fetch_exchange_rate(months: int = 24) -> pd.DataFrame | None:
    """Fetch the official ARS/USD exchange rate (month-end).

    Tries three datos.gob.ar series in order of preference. Columns: date, usd_ars.
    """
    start = _start(months, buffer=1)
    for fxid in FX_IDS:
        raw = _d.fetch([fxid], limit=months * 31, start_date=start)
        if raw is not None and fxid in raw.columns:
            df = _to_monthly_last(raw.rename(columns={fxid: "usd_ars"}), "usd_ars").tail(months).reset_index(drop=True)
            df.to_csv(RESERVES_DIR / "bcra_fx.csv", index=False)
            log.info("BCRA FX saved -> bcra_fx.csv  (%d rows)", len(df))
            return df
    log.warning("BCRA FX rate: all sources failed.")
    return None


def fetch_money_supply(months: int = 24) -> pd.DataFrame | None:
    """
    Fetch M2 private sector money supply (nominal ARS) and compute YoY growth.
    Columns: date, m2_ars_bn, m2_yoy_pct
    Source: BCRA via datos.gob.ar (series 90.1_AMTMA_0_0_39, Sep 2013–present).
    Requires 13+ months to compute first YoY — fetch with buffer.
    """
    # Need 12 extra months beyond requested window to compute YoY from the start
    start = _start(months + 13, buffer=1)
    raw = _d.fetch([M2_SERIES_ID], limit=months + 20, start_date=start)
    if raw is None or M2_SERIES_ID not in raw.columns:
        log.warning("BCRA M2: datos.gob.ar fetch failed.")
        return None

    df = raw[["date", M2_SERIES_ID]].rename(columns={M2_SERIES_ID: "m2_ars_m"}).dropna()
    df = df.sort_values("date").reset_index(drop=True)
    df["m2_ars_bn"]  = df["m2_ars_m"] / 1_000
    df["m2_yoy_pct"] = df["m2_ars_m"].pct_change(12) * 100
    df = df[["date", "m2_ars_bn", "m2_yoy_pct"]].dropna(subset=["m2_yoy_pct"])
    df = df.tail(months).reset_index(drop=True)

    df.to_csv(RESERVES_DIR / "bcra_m2.csv", index=False)
    log.info("BCRA M2 saved -> bcra_m2.csv  (%d rows, latest: %s)",
             len(df), df["date"].iloc[-1].strftime("%Y-%m") if not df.empty else "n/a")
    return df


def fetch_current_account(quarters: int = 10) -> pd.DataFrame | None:
    """Fetch Argentina's quarterly current account balance.

    Primary source is INDEC via datos.gob.ar; falls back to IMF SDMX (BOP/IFS).
    Columns: date (quarter string), quarter_start, quarter_end, current_account_usd_bn.
    """
    start = _start(quarters * 3, buffer=12)

    # Primary: datos.gob.ar INDEC quarterly
    raw = fetch_json(DatosClient.URL,
                     params={"ids": CA_QUARTERLY_ID, "format": "json",
                             "limit": quarters + 6, "sort": "asc", "start_date": start},
                     cache_key=f"datos_{CA_QUARTERLY_ID}_{quarters}_{start}")
    if raw and "data" in raw and [m for m in raw.get("meta", []) if "field" in m]:
        df = pd.DataFrame(raw["data"], columns=["date", "current_account_usd_m"])
        df["date"] = pd.to_datetime(df["date"])
        period = (df["date"] + pd.offsets.QuarterEnd(0)).dt.to_period("Q")
        df["date"]          = period.astype(str)
        df["quarter_start"] = period.dt.start_time.dt.normalize()
        df["quarter_end"]   = period.dt.end_time.dt.normalize()
        df["current_account_usd_bn"] = pd.to_numeric(df["current_account_usd_m"], errors="coerce") / 1_000
        df = df[["date", "quarter_start", "quarter_end", "current_account_usd_bn"]].dropna(subset=["current_account_usd_bn"]).tail(quarters).reset_index(drop=True)
        # date is already the period string (year_quarter); quarter_start/end are first after it
        if not df.empty:
            df.to_csv(RESERVES_DIR / "imf_current_account.csv", index=False)
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
                    df.to_csv(RESERVES_DIR / "imf_current_account.csv", index=False)
                    log.info("IMF CA saved -> imf_current_account.csv  (%d rows)", len(df))
                    return df

    log.warning("Current account: all sources failed.")
    return None


def fetch_trade_balance(months: int = 24) -> pd.DataFrame | None:
    """Fetch monthly merchandise exports, imports, and trade balance.

    Primary source is INDEC via datos.gob.ar; falls back to annual World Bank data.
    Columns: date, exports_usd_bn, imports_usd_bn, trade_balance_usd_bn.
    """
    start = _start(months, buffer=2)
    raw = _d.fetch([EXPORTS_ID, IMPORTS_ID], limit=months + 6, start_date=start)
    if raw is not None and EXPORTS_ID in raw.columns and IMPORTS_ID in raw.columns:
        df = raw[["date"]].copy()
        df["exports_usd_bn"]      = raw[EXPORTS_ID] / 1_000
        df["imports_usd_bn"]      = raw[IMPORTS_ID] / 1_000
        df["trade_balance_usd_bn"] = df["exports_usd_bn"] - df["imports_usd_bn"]
        df = df.dropna(subset=["exports_usd_bn"]).tail(months).reset_index(drop=True)
        df.to_csv(RESERVES_DIR / "indec_trade.csv", index=False)
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
    df.to_csv(RESERVES_DIR / "indec_trade_wb_fallback.csv", index=False)
    log.warning("Trade balance from WB fallback -> indec_trade_wb_fallback.csv  (annual data)")
    return df.sort_values("date").reset_index(drop=True)


def fetch_external_debt(years: int = 8) -> pd.DataFrame | None:
    """Fetch total external debt as a percentage of GNI from the World Bank.

    Columns: date, ext_debt_pct_gni.
    """
    df = _wb.fetch("DT.DOD.DECT.GN.ZS", mrv=years + 2)
    if df is None:
        log.warning("WB external debt: failed.")
        return None
    df = df.rename(columns={"value": "ext_debt_pct_gni"}).tail(years).reset_index(drop=True)
    df.to_csv(RESERVES_DIR / "wb_ext_debt.csv", index=False)
    log.info("WB ext debt saved -> wb_ext_debt.csv  (%d rows)", len(df))
    return df


def fetch_current_account_pct_gdp(years: int = 8) -> pd.DataFrame | None:
    """Fetch the current account balance as a percentage of GDP from the World Bank.

    Used as a fallback when the quarterly INDEC series is unavailable.
    Columns: date, current_account_pct_gdp.
    """
    df = _wb.fetch("BN.CAB.XOKA.GD.ZS", mrv=years + 2)
    if df is None:
        log.warning("WB CA balance: failed.")
        return None
    df = df.rename(columns={"value": "current_account_pct_gdp"}).tail(years).reset_index(drop=True)
    df.to_csv(RESERVES_DIR / "wb_current_account_pct_gdp.csv", index=False)
    log.info("WB CA pct-GDP saved -> wb_current_account_pct_gdp.csv  (%d rows)", len(df))
    return df
