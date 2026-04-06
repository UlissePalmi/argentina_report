"""
Layer 3 — Signal: Inflation

Reads data/inflation/indec_cpi.csv.
Outputs data/signals/signals_inflation.json.
"""

import json

import pandas as pd

from utils import INFLATION_DIR, SIGNALS_DIR, get_logger

log = get_logger("signals.inflation")

OUT_FILE = SIGNALS_DIR / "signals_inflation.json"


def compute() -> dict:
    path = INFLATION_DIR / "indec_cpi.csv"
    if not path.exists():
        log.warning("indec_cpi.csv not found — inflation signal unavailable")
        return _empty()

    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df = df.dropna(subset=["cpi_mom_pct"], how="all")
    if df.empty:
        return _empty()

    latest = df.iloc[-1]
    as_of  = str(latest["date"])[:10]

    cpi_mom_latest = _safe_float(latest.get("cpi_mom_pct"))
    cpi_yoy_latest = _safe_float(latest.get("cpi_yoy_pct"))

    # 3-month and 6-month averages
    mom_series = df["cpi_mom_pct"].dropna()
    trend_3m  = _avg(mom_series.tail(3).tolist())
    trend_6m  = _avg(mom_series.tail(6).tolist())
    trend_12m = _avg(mom_series.tail(12).tolist())

    # Consecutive months below 5%
    consec_below5 = _count_consecutive_below(mom_series.tolist(), threshold=5.0)
    consec_below3 = _count_consecutive_below(mom_series.tolist(), threshold=3.0)
    consec_below2 = _count_consecutive_below(mom_series.tolist(), threshold=2.0)

    # Disinflation: is 3m average below 6m average? (structural decline)
    disinflation_confirmed = (trend_3m is not None and trend_6m is not None
                              and trend_3m < trend_6m - 0.5)

    # Real rate proxy: if we have the rate, assess; otherwise just flag CPI level
    # (Rate data not in CPI file — noted as qualitative)

    flags = _build_flags(cpi_mom_latest, trend_3m, trend_6m,
                         consec_below5, consec_below3, consec_below2,
                         disinflation_confirmed)

    trend_dir = _trend_direction(mom_series.tail(6).tolist())

    result = {
        "domain": "inflation",
        "as_of_date": as_of,
        "data_quality": "good" if cpi_mom_latest is not None else "poor",
        "metrics": {
            "cpi_mom_latest": cpi_mom_latest,
            "cpi_yoy_latest": cpi_yoy_latest,
            "cpi_mom_trend_3m": trend_3m,
            "cpi_mom_trend_6m": trend_6m,
            "cpi_mom_trend_12m": trend_12m,
            "consecutive_months_below_5pct": consec_below5,
            "consecutive_months_below_3pct": consec_below3,
            "consecutive_months_below_2pct": consec_below2,
            "disinflation_confirmed": disinflation_confirmed,
            "last_12_months_mom": [round(v, 2) for v in mom_series.tail(12).tolist()],
        },
        "flags": flags,
        "trend": trend_dir,
        "connection_to_master_variable": _connection(cpi_mom_latest, trend_dir),
        "summary": _make_summary(cpi_mom_latest, cpi_yoy_latest, trend_3m, trend_dir),
    }

    _save(result)
    return result


def _avg(vals: list) -> float | None:
    clean = [v for v in vals if v is not None]
    return round(sum(clean) / len(clean), 2) if clean else None


def _count_consecutive_below(series: list, threshold: float) -> int:
    count = 0
    for v in reversed(series):
        if v is not None and v < threshold:
            count += 1
        else:
            break
    return count


def _trend_direction(series: list) -> str:
    if len(series) < 3:
        return "insufficient_data"
    # Use last 3 vs prior 3
    recent = series[-3:]
    prior  = series[-6:-3] if len(series) >= 6 else series[:3]
    avg_r  = sum(recent) / len(recent)
    avg_p  = sum(prior)  / len(prior)
    diff   = avg_r - avg_p
    if diff < -0.5:
        return "improving"   # inflation falling = improving for wages
    elif diff > 0.5:
        return "deteriorating"
    return "stable"


def _connection(mom, trend) -> str:
    # Lower inflation = positive for purchasing power = positive for master variable
    if mom is None:
        return "neutral"
    if mom < 2 and trend == "improving":
        return "positive"
    if mom < 4:
        return "neutral"
    return "negative"


def _build_flags(mom, t3m, t6m, cb5, cb3, cb2, disinflation) -> list:
    flags = []
    if mom is None:
        flags.append("CRITICAL: CPI data unavailable")
        return flags

    if mom < 2:
        flags.append(f"POSITIVE: Monthly CPI {mom:.1f}% — approaching developed-market levels")
    elif mom < 3:
        flags.append(f"POSITIVE: Monthly CPI {mom:.1f}% — significant disinflation achieved")
    elif mom < 5:
        flags.append(f"NOTE: Monthly CPI {mom:.1f}% — still elevated but on downward path")
    else:
        flags.append(f"WARNING: Monthly CPI {mom:.1f}% — still high, wage erosion risk")

    if disinflation:
        flags.append(
            f"POSITIVE: Disinflation confirmed — 3m avg ({t3m:.1f}%) below 6m avg ({t6m:.1f}%)"
        )

    if cb2 >= 3:
        flags.append(f"POSITIVE: {cb2} consecutive months below 2% MoM — structural stabilization")
    elif cb3 >= 3:
        flags.append(f"POSITIVE: {cb3} consecutive months below 3% MoM — disinflation sustained")
    elif cb5 >= 6:
        flags.append(f"NOTE: {cb5} consecutive months below 5% MoM — inflation normalizing")

    if t3m is not None and t6m is not None:
        if t3m > t6m + 0.5:
            flags.append(
                f"WARNING: Inflation re-accelerating — 3m avg ({t3m:.1f}%) above 6m avg ({t6m:.1f}%)"
            )

    return flags


def _safe_float(v) -> float | None:
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


def _make_summary(mom, yoy, t3m, trend) -> str:
    parts = []
    if mom is not None:
        parts.append(f"Monthly CPI {mom:.1f}%")
    if yoy is not None:
        parts.append(f"YoY {yoy:.1f}%")
    if t3m is not None:
        parts.append(f"3m avg {t3m:.1f}%/month")
    parts.append(f"trend: {trend}")
    return "; ".join(parts) + "." if parts else "CPI data unavailable."


def _empty() -> dict:
    return {
        "domain": "inflation",
        "as_of_date": None,
        "data_quality": "poor",
        "metrics": {},
        "flags": ["CRITICAL: CPI data unavailable"],
        "trend": "unknown",
        "connection_to_master_variable": "neutral",
        "summary": "CPI data unavailable.",
    }


def _save(data: dict) -> None:
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info("Saved: %s", OUT_FILE)
