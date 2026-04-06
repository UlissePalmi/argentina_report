"""
Layer 3 — Signal: Wages

Reads consumption.csv (which has real wage columns from compute_real_values()).
Outputs data/signals/signals_wages.json.
"""

import json
from datetime import datetime

import pandas as pd

from utils import CONSUMPTION_DIR, SIGNALS_DIR, get_logger

log = get_logger("signals.wages")

OUT_FILE = SIGNALS_DIR / "signals_wages.json"


def compute() -> dict:
    path = CONSUMPTION_DIR / "consumption.csv"
    if not path.exists():
        log.warning("consumption.csv not found — wages signal unavailable")
        return _empty()

    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # Drop rows with no wage data at all
    wage_cols = ["real_wage_yoy_pct", "nominal_wage_yoy_pct", "real_wage_mom_pct"]
    avail_cols = [c for c in wage_cols if c in df.columns]
    if not avail_cols:
        return _empty()

    df_w = df.dropna(subset=["real_wage_yoy_pct"], how="all")
    if df_w.empty:
        return _empty()

    latest = df_w.iloc[-1]
    as_of = str(latest["date"])[:10]

    real_yoy     = _safe_float(latest.get("real_wage_yoy_pct"))
    nominal_yoy  = _safe_float(latest.get("nominal_wage_yoy_pct"))
    cpi_yoy      = _safe_float(latest.get("cpi_yoy_pct"))
    real_mom     = _safe_float(latest.get("real_wage_mom_pct"))

    # 3-month rolling average of real YoY
    recent = df_w["real_wage_yoy_pct"].dropna().tail(3).tolist()
    trend_3m = sum(recent) / len(recent) if recent else None

    # 6-month series for trend direction
    last6 = df_w["real_wage_yoy_pct"].dropna().tail(6).tolist()
    trend_dir = _trend_direction(last6)

    # Quarters positive (consecutive months > 0)
    series = df_w["real_wage_yoy_pct"].dropna().tolist()
    consecutive_positive = _count_consecutive_positive(series)

    flags = []
    if real_yoy is not None:
        if real_yoy > 5:
            flags.append("POSITIVE: Real wages growing above 5% YoY — genuine purchasing power recovery")
        elif real_yoy > 0:
            flags.append("POSITIVE: Real wages in positive territory — recovery underway but modest")
        elif real_yoy > -5:
            flags.append("WARNING: Real wages slightly negative — households losing purchasing power")
        else:
            flags.append("CRITICAL: Real wages deeply negative — severe purchasing power erosion")

    if trend_3m is not None and real_yoy is not None:
        if trend_3m > real_yoy:
            flags.append("POSITIVE: Trend improving — 3m average above latest print (momentum building)")
        elif trend_3m < real_yoy - 3:
            flags.append("WARNING: Momentum fading — 3m average below recent readings")

    if consecutive_positive >= 9:
        flags.append(f"POSITIVE: Real wages positive for {consecutive_positive} consecutive months — sustained recovery")
    elif consecutive_positive >= 3:
        flags.append(f"NOTE: Real wages positive for {consecutive_positive} consecutive months")

    connection = "positive" if (real_yoy or 0) > 0 else "negative"
    summary = _make_summary(real_yoy, nominal_yoy, cpi_yoy, trend_dir)

    result = {
        "domain": "wages",
        "as_of_date": as_of,
        "data_quality": "good" if real_yoy is not None else "poor",
        "metrics": {
            "real_wage_yoy_latest": real_yoy,
            "nominal_wage_yoy_latest": nominal_yoy,
            "cpi_yoy_latest": cpi_yoy,
            "real_wage_mom_latest": real_mom,
            "real_wage_trend_3m": round(trend_3m, 2) if trend_3m is not None else None,
            "consecutive_positive_months": consecutive_positive,
            "last_6_months_real_yoy": [round(v, 2) for v in last6],
        },
        "flags": flags,
        "trend": trend_dir,
        "connection_to_master_variable": connection,
        "summary": summary,
    }

    _save(result)
    return result


def _safe_float(v) -> float | None:
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


def _trend_direction(series: list) -> str:
    if len(series) < 2:
        return "insufficient_data"
    first_half = series[:len(series) // 2]
    second_half = series[len(series) // 2:]
    avg_first = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)
    diff = avg_second - avg_first
    if diff > 2:
        return "improving"
    elif diff < -2:
        return "deteriorating"
    else:
        return "stable"


def _count_consecutive_positive(series: list) -> int:
    count = 0
    for v in reversed(series):
        if v > 0:
            count += 1
        else:
            break
    return count


def _make_summary(real_yoy, nominal_yoy, cpi_yoy, trend) -> str:
    if real_yoy is None:
        return "Real wage data unavailable."
    direction = "grew" if real_yoy > 0 else "contracted"
    base = f"Real wages {direction} {abs(real_yoy):.1f}% YoY"
    if nominal_yoy and cpi_yoy:
        base += f" (nominal {nominal_yoy:.1f}% minus CPI {cpi_yoy:.1f}%)"
    base += f"; trend is {trend}."
    return base


def _empty() -> dict:
    return {
        "domain": "wages",
        "as_of_date": None,
        "data_quality": "poor",
        "metrics": {},
        "flags": ["CRITICAL: Wage data unavailable"],
        "trend": "unknown",
        "connection_to_master_variable": "neutral",
        "summary": "Wage data unavailable.",
    }


def _save(data: dict) -> None:
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info("Saved: %s", OUT_FILE)
