"""
Layer 3 — Signal: Production (Industrial + Energy)

Reads data/production/production_monthly.csv.
Outputs data/signals/signals_production.json.
"""

import json

import pandas as pd

from utils import PRODUCTION_DIR, SIGNALS_DIR, get_logger

log = get_logger("signals.production")

OUT_FILE = SIGNALS_DIR / "signals_production.json"


def compute() -> dict:
    path = PRODUCTION_DIR / "production_monthly.csv"
    if not path.exists():
        log.warning("production_monthly.csv not found — production signal unavailable")
        return _empty()

    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    key_cols = ["ipi_yoy_pct", "oil_yoy_pct", "gas_yoy_pct"]
    avail    = [c for c in key_cols if c in df.columns]
    if not avail:
        return _empty()

    df_v = df.dropna(subset=avail, how="all")
    if df_v.empty:
        return _empty()

    latest = df_v.iloc[-1]
    as_of  = str(latest["date"])[:10]

    def _get_latest_nonnan(col):
        """Return latest non-NaN value for a column (handles lagged series)."""
        if col not in df_v.columns:
            return None
        vals = df_v[col].dropna()
        return _safe_float(vals.iloc[-1]) if not vals.empty else None

    def _get(col):
        return _safe_float(latest.get(col)) if col in df_v.columns else None

    ipi_yoy           = _get_latest_nonnan("ipi_yoy_pct")
    ipi_mom           = _get_latest_nonnan("ipi_mom_pct")
    oil_yoy           = _get_latest_nonnan("oil_yoy_pct")
    oil_mom           = _get_latest_nonnan("oil_mom_pct")
    gas_yoy           = _get_latest_nonnan("gas_yoy_pct")
    gas_mom           = _get_latest_nonnan("gas_mom_pct")
    isac_cement_yoy   = _get_latest_nonnan("isac_cement_yoy_pct")

    # Sub-sector breakdown
    ipi_food_yoy  = _get_latest_nonnan("ipi_food_yoy_pct")
    ipi_steel_yoy = _get_latest_nonnan("ipi_steel_yoy_pct")
    ipi_auto_yoy  = _get_latest_nonnan("ipi_auto_yoy_pct")

    # 3-month trend for IPI and oil
    ipi_trend_3m = _avg_col(df_v, "ipi_yoy_pct", 3)
    oil_trend_3m = _avg_col(df_v, "oil_yoy_pct", 3)

    # Consecutive months of positive oil production growth
    oil_consec = _count_consecutive_positive(df_v["oil_yoy_pct"].dropna().tolist()
                                              if "oil_yoy_pct" in df_v.columns else [])

    # Vaca Muerta proxy: sustained oil + gas growth
    vaca_muerta_signal = _assess_vaca_muerta(oil_yoy, gas_yoy, oil_trend_3m)

    flags = _build_flags(ipi_yoy, oil_yoy, gas_yoy, isac_cement_yoy,
                         ipi_trend_3m, oil_trend_3m, vaca_muerta_signal)

    trend = _overall_trend(ipi_yoy, oil_yoy)

    result = {
        "domain": "production",
        "as_of_date": as_of,
        "data_quality": "good" if ipi_yoy is not None or oil_yoy is not None else "poor",
        "metrics": {
            "ipi_yoy_latest": ipi_yoy,
            "ipi_mom_latest": ipi_mom,
            "ipi_food_yoy": ipi_food_yoy,
            "ipi_steel_yoy": ipi_steel_yoy,
            "ipi_auto_yoy": ipi_auto_yoy,
            "ipi_trend_3m": ipi_trend_3m,
            "oil_yoy_latest": oil_yoy,
            "oil_mom_latest": oil_mom,
            "oil_trend_3m": oil_trend_3m,
            "oil_consecutive_positive_months": oil_consec,
            "gas_yoy_latest": gas_yoy,
            "gas_mom_latest": gas_mom,
            "isac_cement_yoy": isac_cement_yoy,
            "vaca_muerta_signal": vaca_muerta_signal,
            "productivity_trend": trend,  # referenced by signals_master
        },
        "flags": flags,
        "trend": trend,
        "connection_to_master_variable": _connection(ipi_yoy, oil_yoy),
        "summary": _make_summary(ipi_yoy, oil_yoy, gas_yoy, vaca_muerta_signal),
    }

    _save(result)
    return result


def _avg_col(df: pd.DataFrame, col: str, n: int) -> float | None:
    if col not in df.columns:
        return None
    vals = df[col].dropna().tail(n).tolist()
    return round(sum(vals) / len(vals), 2) if vals else None


def _count_consecutive_positive(series: list) -> int:
    count = 0
    for v in reversed(series):
        if v > 0:
            count += 1
        else:
            break
    return count


def _assess_vaca_muerta(oil, gas, oil_trend) -> str:
    if oil is None:
        return "unknown"
    if (oil or 0) > 10 and (gas or 0) > 5 and (oil_trend or 0) > 5:
        return "strong"
    if (oil or 0) > 5:
        return "growing"
    if (oil or 0) > 0:
        return "marginal"
    return "stalling"


def _connection(ipi, oil) -> str:
    if (ipi or 0) > 5 and (oil or 0) > 10:
        return "positive"
    if (ipi or 0) > 0:
        return "neutral"
    return "negative"


def _overall_trend(ipi, oil) -> str:
    positives = sum(1 for v in [ipi, oil] if v is not None and v > 0)
    if positives == 2:
        return "improving"
    if positives == 0:
        return "deteriorating"
    return "mixed"


def _build_flags(ipi, oil, gas, cement, ipi_trend, oil_trend, vaca_muerta) -> list:
    flags = []

    if ipi is not None:
        if ipi > 5:
            flags.append(f"POSITIVE: Industrial production +{ipi:.1f}% YoY — manufacturing recovering")
        elif ipi > 0:
            flags.append(f"NOTE: Industrial production +{ipi:.1f}% YoY — modest recovery")
        elif ipi > -5:
            flags.append(f"WARNING: Industrial production -{abs(ipi):.1f}% YoY — manufacturing weak")
        else:
            flags.append(f"CRITICAL: Industrial production -{abs(ipi):.1f}% YoY — manufacturing contraction")

    if oil is not None:
        if oil > 10:
            flags.append(f"POSITIVE: Oil production +{oil:.1f}% YoY — Vaca Muerta ramp-up continuing")
        elif oil > 0:
            flags.append(f"NOTE: Oil production +{oil:.1f}% YoY — positive but modest")
        else:
            flags.append(f"WARNING: Oil production {oil:.1f}% YoY — energy sector stalling")

    if gas is not None and gas > 10:
        flags.append(f"POSITIVE: Gas production +{gas:.1f}% YoY — energy self-sufficiency progressing")

    if vaca_muerta == "strong":
        flags.append(
            "POSITIVE: Vaca Muerta signal strong — oil + gas both growing, 3m trend confirms acceleration"
        )
    elif vaca_muerta == "stalling":
        flags.append(
            "WARNING: Vaca Muerta signal stalling — oil growth near zero, dollar generation at risk"
        )

    if ipi_trend is not None and ipi is not None:
        if ipi_trend > ipi + 3:
            flags.append(
                f"POSITIVE: IPI momentum building — 3m trend ({ipi_trend:.1f}%) above latest print"
            )
        elif ipi_trend < ipi - 5:
            flags.append(
                f"WARNING: IPI momentum fading — 3m trend ({ipi_trend:.1f}%) below recent reading"
            )

    if cement is not None:
        if cement > 10:
            flags.append(f"POSITIVE: Construction activity (cement +{cement:.1f}% YoY) confirms investment pickup")
        elif cement < -10:
            flags.append(f"WARNING: Construction activity weak (cement {cement:.1f}% YoY)")

    return flags


def _safe_float(v) -> float | None:
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


def _make_summary(ipi, oil, gas, vaca_muerta) -> str:
    parts = []
    if ipi is not None:
        direction = "grew" if ipi > 0 else "contracted"
        parts.append(f"Industrial production {direction} {abs(ipi):.1f}% YoY")
    if oil is not None:
        parts.append(f"oil {oil:+.1f}% YoY")
    if gas is not None:
        parts.append(f"gas {gas:+.1f}% YoY")
    if vaca_muerta != "unknown":
        parts.append(f"Vaca Muerta: {vaca_muerta}")
    return "; ".join(parts) + "." if parts else "Production data unavailable."


def _empty() -> dict:
    return {
        "domain": "production",
        "as_of_date": None,
        "data_quality": "poor",
        "metrics": {"productivity_trend": "unknown"},
        "flags": ["CRITICAL: Production data unavailable"],
        "trend": "unknown",
        "connection_to_master_variable": "neutral",
        "summary": "Production data unavailable.",
    }


def _save(data: dict) -> None:
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info("Saved: %s", OUT_FILE)
