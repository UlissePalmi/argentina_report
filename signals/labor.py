"""
Layer 3 — Signal: Labor Market

Reads:
  data/productivity/employment.csv
  data/productivity/productivity.csv
Outputs data/signals/signals_labor.json.
"""

import json

import pandas as pd

from utils import PRODUCTIVITY_DIR, SIGNALS_DIR, get_logger

log = get_logger("signals.labor")

OUT_FILE = SIGNALS_DIR / "signals_labor.json"


def compute() -> dict:
    emp_df  = _read_csv("employment.csv")
    prod_df = _read_csv("productivity.csv")

    if emp_df is None and prod_df is None:
        log.warning("Employment and productivity CSVs not found")
        return _empty()

    metrics = {}
    flags   = []
    as_of   = None

    # ------------------------------------------------------------------
    # Employment (SIPA)
    # ------------------------------------------------------------------
    sipa_yoy         = None
    sipa_trend_3m    = None
    consec_pos_emp   = 0

    if emp_df is not None and "emp_total_yoy_pct" in emp_df.columns:
        ev = emp_df.dropna(subset=["emp_total_yoy_pct"])
        if not ev.empty:
            latest_emp = ev.iloc[-1]
            as_of      = str(latest_emp["date"])[:10]
            sipa_yoy   = _safe_float(latest_emp["emp_total_yoy_pct"])
            sipa_trend_3m = _avg(ev["emp_total_yoy_pct"].tail(3).tolist())
            consec_pos_emp = _count_consecutive_positive(ev["emp_total_yoy_pct"].tolist())

        # Sector breakdown
        industry_yoy     = _safe_float(ev.iloc[-1].get("emp_industry_yoy_pct")) if not ev.empty else None
        construction_yoy = _safe_float(ev.iloc[-1].get("emp_construction_yoy_pct")) if not ev.empty else None
        services_yoy     = _safe_float(ev.iloc[-1].get("emp_services_yoy_pct")) if not ev.empty else None
    else:
        industry_yoy = construction_yoy = services_yoy = None

    metrics.update({
        "sipa_yoy_latest": sipa_yoy,
        "sipa_trend_3m": sipa_trend_3m,
        "sipa_consecutive_positive": consec_pos_emp,
        "emp_industry_yoy": industry_yoy,
        "emp_construction_yoy": construction_yoy,
        "emp_services_yoy": services_yoy,
    })

    # Employment flags
    if sipa_yoy is not None:
        if sipa_yoy > 3:
            flags.append(f"POSITIVE: Formal employment +{sipa_yoy:.1f}% YoY — productive sector expanding")
        elif sipa_yoy > 0:
            flags.append(f"NOTE: Formal employment +{sipa_yoy:.1f}% YoY — modest growth")
        elif sipa_yoy > -2:
            flags.append(f"WARNING: Formal employment {sipa_yoy:.1f}% YoY — stagnating")
        else:
            flags.append(f"CRITICAL: Formal employment {sipa_yoy:.1f}% YoY — job destruction")

    if consec_pos_emp >= 6:
        flags.append(
            f"POSITIVE: {consec_pos_emp} consecutive periods of positive formal employment — "
            f"sustained labor market expansion"
        )

    # ------------------------------------------------------------------
    # Productivity
    # ------------------------------------------------------------------
    prod_industry_yoy  = None
    prod_services_yoy  = None
    real_wage_prod     = None
    ulc_industry_yoy   = None
    productivity_trend = "unknown"

    if prod_df is not None:
        pv = prod_df.dropna(subset=[c for c in ["productivity_industry_yoy_pct"] if c in prod_df.columns], how="all")
        if not pv.empty:
            latest_prod = pv.iloc[-1]
            if as_of is None:
                as_of = str(latest_prod["date"])[:10]
            prod_industry_yoy = _safe_float(latest_prod.get("productivity_industry_yoy_pct"))
            prod_services_yoy = _safe_float(latest_prod.get("productivity_services_yoy_pct"))
            real_wage_prod    = _safe_float(latest_prod.get("real_wage_yoy_pct"))
            ulc_industry_yoy  = _safe_float(latest_prod.get("ulc_industry_yoy_pct"))
            productivity_trend = _prod_trend(pv)

    metrics.update({
        "productivity_industry_yoy": prod_industry_yoy,
        "productivity_services_yoy": prod_services_yoy,
        "real_wage_yoy_from_prod": real_wage_prod,
        "ulc_industry_yoy": ulc_industry_yoy,
        "productivity_trend": productivity_trend,
    })

    # Productivity flags
    if prod_industry_yoy is not None:
        if prod_industry_yoy > 5:
            flags.append(
                f"POSITIVE: Industrial productivity +{prod_industry_yoy:.1f}% YoY — "
                f"output per worker rising (wage growth can be sustained)"
            )
        elif prod_industry_yoy < -5:
            flags.append(
                f"WARNING: Industrial productivity -{abs(prod_industry_yoy):.1f}% YoY — "
                f"output per worker falling (wage growth without productivity base)"
            )

    # ULC: rising ULC = wages growing faster than productivity = competitiveness pressure
    if ulc_industry_yoy is not None:
        if ulc_industry_yoy > 10:
            flags.append(
                f"WARNING: Unit labor costs +{ulc_industry_yoy:.1f}% YoY — "
                f"wages outpacing productivity, competitiveness risk"
            )
        elif ulc_industry_yoy < 0:
            flags.append(
                f"POSITIVE: Unit labor costs {ulc_industry_yoy:.1f}% YoY — "
                f"productivity gains outpacing wage growth, competitiveness improving"
            )

    # Master variable connection
    connection = _connection(sipa_yoy, prod_industry_yoy)

    result = {
        "domain": "labor",
        "as_of_date": as_of,
        "data_quality": "good" if sipa_yoy is not None else "partial",
        "metrics": metrics,
        "flags": flags,
        "trend": _overall_trend(sipa_yoy, prod_industry_yoy),
        "connection_to_master_variable": connection,
        "summary": _make_summary(sipa_yoy, prod_industry_yoy, ulc_industry_yoy),
    }

    _save(result)
    return result


def _read_csv(filename: str) -> pd.DataFrame | None:
    path = PRODUCTIVITY_DIR / filename
    if not path.exists():
        log.warning("%s not found", filename)
        return None
    try:
        df = pd.read_csv(path, parse_dates=["date"])
        return df.sort_values("date").reset_index(drop=True)
    except Exception as e:
        log.warning("Could not read %s: %s", filename, e)
        return None


def _avg(vals: list) -> float | None:
    clean = [v for v in vals if v is not None]
    return round(sum(clean) / len(clean), 2) if clean else None


def _count_consecutive_positive(series: list) -> int:
    count = 0
    for v in reversed(series):
        try:
            if float(v) > 0:
                count += 1
            else:
                break
        except (TypeError, ValueError):
            break
    return count


def _prod_trend(df: pd.DataFrame) -> str:
    col = "productivity_industry_yoy_pct"
    if col not in df.columns:
        return "unknown"
    vals = df[col].dropna().tail(4).tolist()
    if len(vals) < 2:
        return "unknown"
    if vals[-1] > vals[0] + 3:
        return "improving"
    if vals[-1] < vals[0] - 3:
        return "deteriorating"
    return "stable"


def _overall_trend(sipa, prod) -> str:
    positives = sum(1 for v in [sipa, prod] if v is not None and v > 0)
    if positives == 2:
        return "improving"
    if positives == 0:
        return "deteriorating"
    return "mixed"


def _connection(sipa, prod) -> str:
    if (sipa or 0) > 2 and (prod or 0) > 0:
        return "positive"
    if (sipa or 0) < 0:
        return "negative"
    return "neutral"


def _safe_float(v) -> float | None:
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


def _make_summary(sipa, prod, ulc) -> str:
    parts = []
    if sipa is not None:
        parts.append(f"Formal employment {sipa:+.1f}% YoY")
    if prod is not None:
        parts.append(f"industrial productivity {prod:+.1f}% YoY")
    if ulc is not None:
        direction = "rising" if ulc > 0 else "falling"
        parts.append(f"unit labor costs {direction} ({ulc:+.1f}%)")
    return "; ".join(parts) + "." if parts else "Labor data unavailable."


def _empty() -> dict:
    return {
        "domain": "labor",
        "as_of_date": None,
        "data_quality": "poor",
        "metrics": {"sipa_yoy_latest": None, "productivity_trend": "unknown"},
        "flags": ["CRITICAL: Labor and productivity data unavailable"],
        "trend": "unknown",
        "connection_to_master_variable": "neutral",
        "summary": "Labor data unavailable.",
    }


def _save(data: dict) -> None:
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info("Saved: %s", OUT_FILE)
