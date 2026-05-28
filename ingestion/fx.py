"""
FX regime — parallel dollars (brecha) and the real exchange rate.

Independent of the net-reserves computation. Two outputs:
  data/external/fx_parallel.csv  — spot oficial/blue/MEP/CCL + gaps, appended weekly
  data/external/reer.csv         — real exchange-rate index (bilateral proxy)

Parallel quotes are a SPOT source (no history endpoint), so the time series is
built up one row per run, the same way the BCRA balance-sheet parser accumulates.
"""

from datetime import date

import pandas as pd

from utils import EXTERNAL_DIR, INFLATION_DIR, RESERVES_DIR, fetch_json, get_logger

log = get_logger("fetch.fx")

# Fragile external source — isolated here on purpose. Free public API, spot only.
# criptoya returns oficial/blue/mep/ccl; mep & ccl are nested by bond (we use AL30 24hs).
DOLAR_API_URL = "https://criptoya.com/api/dolar"
_HEADERS = {"User-Agent": "Mozilla/5.0"}
# World Bank US CPI (annual index, 2010=100) for the REER foreign-price term.
US_CPI_URL = "https://api.worldbank.org/v2/country/US/indicator/FP.CPI.TOTL"

PARALLEL_CSV = EXTERNAL_DIR / "fx_parallel.csv"
REER_CSV     = EXTERNAL_DIR / "reer.csv"


def _criptoya_quotes(d: dict) -> dict[str, float]:
    """Extract oficial/blue/mep/ccl spot prices from the criptoya response."""
    q: dict[str, float] = {}
    oficial = (d.get("oficial") or {}).get("price") or (d.get("oficial") or {}).get("ask")
    if oficial:
        q["oficial"] = float(oficial)
    blue = (d.get("blue") or {}).get("price") or (d.get("blue") or {}).get("ask")
    if blue:
        q["blue"] = float(blue)
    for key, col in (("mep", "mep"), ("ccl", "ccl")):
        price = (((d.get(key) or {}).get("al30") or {}).get("24hs") or {}).get("price")
        if price:
            q[col] = float(price)
    return q


# ---------------------------------------------------------------------------
# Parallel dollars + brecha
# ---------------------------------------------------------------------------

def fetch_parallel_fx() -> pd.DataFrame | None:
    """Fetch spot parallel dollar quotes, compute the gap to official, and append
    today's row to fx_parallel.csv. Returns the full accumulated DataFrame.

    Columns: date, oficial, blue, mep, ccl, brecha_ccl_pct, brecha_mep_pct.
    History accumulates from the first run (dolarapi has no historical endpoint).
    """
    raw = fetch_json(DOLAR_API_URL, headers=_HEADERS, cache_key="criptoya_dolar")
    if not isinstance(raw, dict):
        log.warning("FX parallel: dollar API returned no usable data")
        return _read_parallel_csv()  # fall back to whatever history we already have

    quotes = _criptoya_quotes(raw)
    if "oficial" not in quotes:
        log.warning("FX parallel: official quote missing from response")
        return _read_parallel_csv()

    oficial = quotes["oficial"]
    row = {"date": date.today().strftime("%Y-%m-%d"), **quotes}
    if quotes.get("ccl"):
        row["brecha_ccl_pct"] = round((quotes["ccl"] / oficial - 1) * 100, 2)
    if quotes.get("mep"):
        row["brecha_mep_pct"] = round((quotes["mep"] / oficial - 1) * 100, 2)

    df = _append_row(row)
    log.info("FX parallel: %s  oficial=%.0f ccl=%s brecha_ccl=%s%%",
             row["date"], oficial, quotes.get("ccl"), row.get("brecha_ccl_pct"))
    return df


def _append_row(row: dict) -> pd.DataFrame:
    """Append a dated row to fx_parallel.csv, skipping if today is already present."""
    existing = _read_parallel_csv()
    if existing is not None and row["date"] in existing["date"].astype(str).values:
        log.info("FX parallel: %s already recorded, skipping append", row["date"])
        return existing
    new = pd.DataFrame([row])
    df = pd.concat([existing, new], ignore_index=True) if existing is not None else new
    df = df.sort_values("date").reset_index(drop=True)
    df.to_csv(PARALLEL_CSV, index=False)
    return df


def _read_parallel_csv() -> pd.DataFrame | None:
    if not PARALLEL_CSV.exists():
        return None
    try:
        return pd.read_csv(PARALLEL_CSV)
    except Exception as e:
        log.warning("FX parallel: could not read %s: %s", PARALLEL_CSV.name, e)
        return None


# ---------------------------------------------------------------------------
# Real exchange rate (bilateral proxy)
# ---------------------------------------------------------------------------

def fetch_reer(months: int = 36) -> pd.DataFrame | None:
    """Compute a bilateral real exchange-rate index vs USD.

    BCRA's multilateral ITCRM is not on datos.gob.ar, so this is a documented
    PROXY: RER = official_fx * (US_CPI / AR_CPI), indexed to 100 at series start.
    Convention: HIGHER = more depreciated/competitive; LOWER = real appreciation
    (peso expensive / overvaluation risk).

    Writes data/external/reer.csv (date, reer_index, reer_percentile). Returns it.
    """
    cpi = _read_csv(INFLATION_DIR / "indec_cpi.csv")
    fx  = _read_csv(RESERVES_DIR / "bcra_fx.csv")
    if cpi is None or fx is None or "cpi_index" not in cpi.columns or "usd_ars" not in fx.columns:
        log.warning("REER: missing AR CPI or FX input")
        return None

    df = pd.merge(fx[["date", "usd_ars"]], cpi[["date", "cpi_index"]], on="date", how="inner")
    df = df.dropna().sort_values("date").reset_index(drop=True)
    if df.empty:
        log.warning("REER: no overlapping FX/CPI dates")
        return None

    us = _fetch_us_cpi_monthly(df["date"])
    if us is not None:
        df = df.merge(us, on="date", how="left")
        df["us_cpi"] = df["us_cpi"].ffill().bfill()
        proxy_note = "bilateral (US CPI from World Bank, interpolated)"
    else:
        df["us_cpi"] = 100.0  # US inflation omitted — domestic-real proxy
        proxy_note = "domestic-real (US inflation omitted)"

    df["rer"] = df["usd_ars"] * (df["us_cpi"] / df["cpi_index"])
    base = df["rer"].iloc[0]
    df["reer_index"] = (df["rer"] / base * 100).round(2)
    df["reer_percentile"] = (df["reer_index"].rank(pct=True) * 100).round(1)

    out = df[["date", "reer_index", "reer_percentile"]].tail(months).reset_index(drop=True)
    out.to_csv(REER_CSV, index=False)
    log.info("REER (%s): latest index %.1f, percentile %.0f -> reer.csv (%d rows)",
             proxy_note, out["reer_index"].iloc[-1], out["reer_percentile"].iloc[-1], len(out))
    return out


def _fetch_us_cpi_monthly(dates: pd.Series) -> pd.DataFrame | None:
    """Fetch World Bank annual US CPI and expand to month-start rows covering `dates`."""
    raw = fetch_json(US_CPI_URL, params={"format": "json", "mrv": 15, "per_page": 15},
                     cache_key="wb_us_cpi_FP.CPI.TOTL")
    if not isinstance(raw, list) or len(raw) < 2 or not raw[1]:
        log.warning("REER: World Bank US CPI unavailable — using domestic-real proxy")
        return None
    annual = {int(r["date"]): float(r["value"]) for r in raw[1] if r.get("value") is not None}
    if not annual:
        return None
    d = pd.to_datetime(dates)
    return pd.DataFrame({
        "date": dates.values,
        "us_cpi": [annual.get(y) for y in d.dt.year],
    })


def _read_csv(path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except Exception as e:
        log.warning("FX: could not read %s: %s", path, e)
        return None
