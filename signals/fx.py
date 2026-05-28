"""
Layer 3 — Signal: FX Regime

Reads:
  data/external/fx_parallel.csv   (oficial/blue/mep/ccl + brecha, spot-accumulated)
  data/external/reer.csv          (real exchange-rate index + percentile)
Outputs data/signals/signals_fx.json.

Independent of net reserves. Tracks the parallel-dollar gap (regime credibility)
and the real exchange rate (competitiveness / overvaluation risk).
"""

import json

import pandas as pd

from utils import EXTERNAL_DIR, SIGNALS_DIR, get_logger

log = get_logger("signals.fx")

OUT_FILE = SIGNALS_DIR / "signals_fx.json"


def compute() -> dict:
    parallel = _read_csv("fx_parallel.csv")
    reer     = _read_csv("reer.csv")

    metrics: dict = {}
    flags: list[str] = []
    as_of = None

    # ------------------------------------------------------------------
    # Brecha (parallel-dollar gap = regime credibility)
    # ------------------------------------------------------------------
    brecha_ccl = brecha_mep = official = None
    brecha_trend = None

    if parallel is not None and not parallel.empty:
        last = parallel.iloc[-1]
        as_of = str(last.get("date"))[:10]
        official   = _f(last.get("oficial"))
        brecha_ccl = _f(last.get("brecha_ccl_pct"))
        brecha_mep = _f(last.get("brecha_mep_pct"))
        if "brecha_ccl_pct" in parallel.columns:
            series = parallel["brecha_ccl_pct"].dropna()
            if len(series) >= 3:
                brecha_trend = "deteriorating" if series.iloc[-1] > series.iloc[-3] else "improving"

    metrics["official_fx_latest"] = official
    metrics["brecha_ccl_pct"]     = brecha_ccl
    metrics["brecha_mep_pct"]     = brecha_mep
    metrics["brecha_trend"]       = brecha_trend

    if brecha_ccl is not None:
        if brecha_ccl < 10:
            flags.append(f"POSITIVE: CCL brecha {brecha_ccl:.1f}% — FX gap contained, regime credible")
        elif brecha_ccl < 25:
            flags.append(f"NOTE: CCL brecha {brecha_ccl:.1f}% — moderate gap, monitor")
        else:
            flags.append(f"WARNING: CCL brecha {brecha_ccl:.1f}% — wide gap signals devaluation pressure")
        if brecha_trend == "deteriorating":
            flags.append("WARNING: Brecha widening — market front-running FX pressure")

    # ------------------------------------------------------------------
    # REER (competitiveness / overvaluation)
    # ------------------------------------------------------------------
    reer_index = reer_pct = None
    if reer is not None and not reer.empty:
        last = reer.iloc[-1]
        reer_index = _f(last.get("reer_index"))
        reer_pct   = _f(last.get("reer_percentile"))
        if as_of is None:
            as_of = str(last.get("date"))[:10]

    metrics["reer_index"]      = reer_index
    metrics["reer_percentile"] = reer_pct

    if reer_pct is not None:
        if reer_pct < 20:
            flags.append(f"WARNING: REER at {reer_pct:.0f}th percentile — peso real-expensive, "
                         f"overvaluation/competitiveness risk")
        elif reer_pct > 80:
            flags.append(f"POSITIVE: REER at {reer_pct:.0f}th percentile — peso real-cheap, competitive")
        else:
            flags.append(f"NOTE: REER at {reer_pct:.0f}th percentile of recent history")

    # ------------------------------------------------------------------
    # Trend + master-variable connection
    # ------------------------------------------------------------------
    trend = _overall_trend(brecha_trend, reer_pct)
    connection = _connection(brecha_ccl, reer_pct)

    result = {
        "domain": "fx",
        "as_of_date": as_of,
        "data_quality": _quality(parallel, reer),
        "metrics": metrics,
        "flags": flags,
        "trend": trend,
        "connection_to_master_variable": connection,
        "summary": _make_summary(official, brecha_ccl, reer_index, reer_pct),
    }

    _save(result)
    return result


def _overall_trend(brecha_trend, reer_pct) -> str:
    if brecha_trend == "deteriorating" or (reer_pct is not None and reer_pct < 20):
        return "deteriorating"
    if brecha_trend == "improving":
        return "improving"
    return "stable"


def _connection(brecha_ccl, reer_pct) -> str:
    # A wide gap or an overvalued peso = devaluation/inflation risk = negative for
    # sustainable real wages. A contained gap with a competitive peso = positive.
    if (brecha_ccl or 0) > 25 or (reer_pct is not None and reer_pct < 20):
        return "negative"
    if (brecha_ccl is not None and brecha_ccl < 10) and (reer_pct is None or reer_pct >= 20):
        return "positive"
    return "neutral"


def _make_summary(official, brecha_ccl, reer_index, reer_pct) -> str:
    parts = []
    if official is not None:
        parts.append(f"Official ARS {official:,.0f}/USD")
    if brecha_ccl is not None:
        parts.append(f"CCL brecha {brecha_ccl:.1f}%")
    if reer_index is not None and reer_pct is not None:
        parts.append(f"REER {reer_index:.0f} ({reer_pct:.0f}th pct)")
    return ("; ".join(parts) + ".") if parts else "FX data unavailable."


def _quality(parallel, reer) -> str:
    if parallel is not None and reer is not None:
        return "good"
    if parallel is not None or reer is not None:
        return "partial"
    return "poor"


def _f(v):
    try:
        if v is None or pd.isna(v):
            return None
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


def _read_csv(filename: str) -> pd.DataFrame | None:
    path = EXTERNAL_DIR / filename
    if not path.exists():
        log.warning("%s not found", filename)
        return None
    try:
        return pd.read_csv(path).sort_values("date").reset_index(drop=True)
    except Exception as e:
        log.warning("Could not read %s: %s", filename, e)
        return None


def _save(data: dict) -> None:
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info("Saved: %s", OUT_FILE)
