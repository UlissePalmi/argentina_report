"""
Fetch IMF Balance of Payments data for Argentina.

API  : dataservices.imf.org/REST/SDMX_JSON.svc
Dataset used: BOP (Balance of Payments)

Key indicators (IMF BOP methodology):
    BCA  – Current Account Balance (credits - debits)
    BG   – Goods balance
    BS   – Services balance
    BI   – Primary income balance
    BCA_BP6 – Current account (BPM6 basis, some datasets)

Frequency: Q (quarterly)
Country code: AR (Argentina)
"""

from datetime import date

import pandas as pd

from utils import OUTPUT_DIR, fetch_json, get_logger

log = get_logger("fetch_imf")

BASE = "https://dataservices.imf.org/REST/SDMX_JSON.svc"
HEADERS = {"Accept": "application/json"}


# ---------------------------------------------------------------------------
# Helper: parse SDMX-JSON compact data
# ---------------------------------------------------------------------------
def _parse_sdmx(data: dict, value_label: str = "value") -> pd.DataFrame | None:
    """
    Parse a SDMX-JSON CompactData response into a tidy DataFrame.
    Returns columns: [date, value_label]
    """
    try:
        dataset = data["CompactData"]["DataSet"]
        series = dataset.get("Series", {})

        # Some endpoints return a list, others a single dict
        if isinstance(series, dict):
            series = [series]

        rows = []
        for s in series:
            obs_list = s.get("Obs", [])
            if isinstance(obs_list, dict):
                obs_list = [obs_list]
            for obs in obs_list:
                rows.append({
                    "date": obs.get("@TIME_PERIOD", obs.get("@TIME_PERIOD")),
                    "value": obs.get("@OBS_VALUE"),
                })

        if not rows:
            return None

        df = pd.DataFrame(rows)
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df.rename(columns={"value": value_label}, inplace=True)
        df = df.dropna(subset=[value_label]).reset_index(drop=True)
        return df

    except (KeyError, TypeError) as e:
        log.error("SDMX parse error: %s", e)
        return None


# ---------------------------------------------------------------------------
# Helper: quarterly current account from datos.gob.ar (INDEC/BCRA)
# ---------------------------------------------------------------------------
def _fetch_ca_indec_quarterly(quarters: int) -> pd.DataFrame | None:
    """
    Fetch quarterly current account balance from datos.gob.ar.
    Series 160.2_TL_CUENNTE_0_T_22 — Total cuenta corriente, USD millions, quarterly.
    Data available through Q3 2025.
    """
    from datetime import date as _date, timedelta
    series_id = "160.2_TL_CUENNTE_0_T_22"
    start = (_date.today() - timedelta(days=(quarters + 4) * 95)).strftime("%Y-%m-%d")
    params = {
        "ids": series_id,
        "format": "json",
        "limit": quarters + 6,
        "sort": "asc",
        "start_date": start,
    }
    data = fetch_json("https://apis.datos.gob.ar/series/api/series/",
                      params=params,
                      cache_key=f"datos_{series_id}_{quarters}_{start}")
    if data is None or "data" not in data:
        return None

    meta = [m for m in data.get("meta", []) if "field" in m]
    if not meta:
        return None

    df = pd.DataFrame(data["data"], columns=["date", "current_account_usd_m"])
    df["date"] = pd.to_datetime(df["date"])


    # Label by end-of-quarter (Bloomberg convention)
    eoq = df["date"] + pd.offsets.QuarterEnd(0)
    df["date"] = eoq.dt.to_period("Q").astype(str)
    df["current_account_usd_m"] = pd.to_numeric(df["current_account_usd_m"], errors="coerce")
    df["current_account_usd_bn"] = df["current_account_usd_m"] / 1_000
    df = df[["date", "current_account_usd_bn"]].dropna().tail(quarters).reset_index(drop=True)
    return df if not df.empty else None


# ---------------------------------------------------------------------------
# Public: current account balance (quarterly)
# ---------------------------------------------------------------------------
def fetch_current_account(quarters: int = 10) -> pd.DataFrame | None:
    """
    Return quarterly current account balance in USD billions.
    Columns: date, current_account_usd_bn

    Primary  : datos.gob.ar INDEC/BCRA quarterly BOP series (to Q3 2025)
               Series 160.2_TL_CUENNTE_0_T_22
    Fallback : IMF BOP SDMX API (may be blocked by firewall)
    """
    # --- Primary: datos.gob.ar quarterly current account ---
    df = _fetch_ca_indec_quarterly(quarters)
    if df is not None and not df.empty:
        out = OUTPUT_DIR / "imf_current_account.csv"
        df.to_csv(out, index=False)
        log.info("Current account (INDEC quarterly) saved → %s  (%d rows)", out.name, len(df))
        return df

    # --- Fallback: IMF SDMX ---
    log.warning("IMF CA: datos.gob.ar failed — trying IMF SDMX")
    start_year = date.today().year - 4
    url = f"{BASE}/CompactData/BOP/Q.AR.BCA"
    params = {"startPeriod": str(start_year), "endPeriod": str(date.today().year)}

    # Quick connectivity check before retrying against a known-slow host
    import socket
    _imf_reachable = False
    try:
        socket.setdefaulttimeout(4)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("dataservices.imf.org", 443))
        _imf_reachable = True
    except OSError:
        log.warning("IMF host unreachable (network/firewall) — skipping to fallback immediately")
    finally:
        socket.setdefaulttimeout(None)

    df = None
    if _imf_reachable:
        data = fetch_json(url, params=params, headers=HEADERS,
                          cache_key=f"imf_bop_bca_AR_{start_year}",
                          max_retries=2, timeout=15)
        if data:
            df = _parse_sdmx(data, "current_account_usd_bn")

        if df is None:
            log.warning("IMF BOP BCA: trying IFS dataset as fallback")
            url2 = f"{BASE}/CompactData/IFS/Q.AR.BCAXF_BP6_USD"
            data2 = fetch_json(url2, params=params, headers=HEADERS,
                               cache_key=f"imf_ifs_bca_AR_{start_year}",
                               max_retries=2, timeout=15)
            if data2:
                df = _parse_sdmx(data2, "current_account_usd_bn")

    if df is None:
        log.warning("IMF current account: all sources failed.")
        return None

    # Convert to billions (IMF reports in millions)
    df["current_account_usd_bn"] = df["current_account_usd_bn"] / 1_000
    df = df.tail(quarters).reset_index(drop=True)

    out = OUTPUT_DIR / "imf_current_account.csv"
    df.to_csv(out, index=False)
    log.info("IMF current account saved → %s  (%d rows)", out.name, len(df))
    return df


# ---------------------------------------------------------------------------
# Public: list available BOP indicators (diagnostic helper)
# ---------------------------------------------------------------------------
def list_bop_indicators() -> list[str]:
    """Return available BOP series codes for Argentina (for exploration)."""
    url = f"{BASE}/CodeList/CL_INDICATOR_BOP"
    data = fetch_json(url, headers=HEADERS, cache_key="imf_bop_codelist")
    if data is None:
        return []
    try:
        codes = data["Structure"]["CodeLists"]["CodeList"]["Code"]
        return [c["@value"] for c in codes]
    except (KeyError, TypeError):
        return []


if __name__ == "__main__":
    print(fetch_current_account())
