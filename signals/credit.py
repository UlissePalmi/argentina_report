"""
Layer 3 — Signal: Credit

Reads consumption.csv (real credit columns from compute_real_values()).
Outputs data/signals/signals_credit.json.
"""

import json

import pandas as pd

from utils import CONSUMPTION_DIR, SIGNALS_DIR, get_logger

log = get_logger("signals.credit")

OUT_FILE = SIGNALS_DIR / "signals_credit.json"

# Consumer credit = personal loans + credit cards
# Business credit = overdrafts + commercial paper
CONSUMER_COLS = ["real_personal_loans_pct", "real_credit_cards_pct"]
BUSINESS_COLS = ["real_overdrafts_pct", "real_commercial_paper_pct"]
ASSET_COLS    = ["real_mortgages_pct", "real_auto_loans_pct"]
MOM_COLS      = ["real_personal_loans_mom_pct", "real_credit_cards_mom_pct",
                 "real_mortgages_mom_pct", "real_auto_loans_mom_pct",
                 "real_overdrafts_mom_pct", "real_commercial_paper_mom_pct"]


def compute() -> dict:
    path = CONSUMPTION_DIR / "consumption.csv"
    if not path.exists():
        log.warning("consumption.csv not found — credit signal unavailable")
        return _empty()

    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # Find latest row with at least some credit data
    credit_check_cols = [c for c in CONSUMER_COLS + BUSINESS_COLS if c in df.columns]
    if not credit_check_cols:
        return _empty()

    df_c = df.dropna(subset=credit_check_cols, how="all")
    if df_c.empty:
        return _empty()

    latest = df_c.iloc[-1]
    as_of  = str(latest["date"])[:10]

    def _get(col):
        return _safe_float(latest.get(col)) if col in df_c.columns else None

    personal_loans  = _get("real_personal_loans_pct")
    credit_cards    = _get("real_credit_cards_pct")
    mortgages       = _get("real_mortgages_pct")
    auto_loans      = _get("real_auto_loans_pct")
    overdrafts      = _get("real_overdrafts_pct")
    commercial      = _get("real_commercial_paper_pct")
    real_wage_yoy   = _get("real_wage_yoy_pct")
    consumer_total  = _get("real_consumer_credit_yoy_pct")
    deposits_yoy    = _get("real_deposits_yoy_pct")
    nominal_dep     = _get("deposits_yoy_pct")
    cpi_yoy         = _get("cpi_yoy_pct")

    # Average consumer credit growth if total not available
    if consumer_total is None:
        vals = [v for v in [personal_loans, credit_cards] if v is not None]
        consumer_total = sum(vals) / len(vals) if vals else None

    # Credit-to-wage spread (key sustainability indicator)
    credit_wage_spread = None
    if consumer_total is not None and real_wage_yoy is not None:
        credit_wage_spread = round(consumer_total - real_wage_yoy, 2)

    # Trend: last 3 months of consumer credit
    if "real_personal_loans_pct" in df_c.columns:
        trend_vals = df_c["real_personal_loans_pct"].dropna().tail(3).tolist()
        credit_trend_3m = round(sum(trend_vals) / len(trend_vals), 2) if trend_vals else None
    else:
        credit_trend_3m = None

    # Deposits (savings gauge)
    deposits_real_growing = None
    if deposits_yoy is not None and cpi_yoy is not None:
        deposits_real_growing = deposits_yoy > cpi_yoy

    flags = []

    # Consumer credit vs wages
    if credit_wage_spread is not None:
        if credit_wage_spread > 30:
            flags.append(
                f"CRITICAL: Consumer credit ({consumer_total:.1f}% YoY) growing "
                f"{credit_wage_spread:.1f}pp faster than real wages — households borrowing to consume"
            )
        elif credit_wage_spread > 15:
            flags.append(
                f"WARNING: Consumer credit outpacing real wages by {credit_wage_spread:.1f}pp — "
                f"moderate leverage build-up, monitor"
            )
        elif credit_wage_spread < 0:
            flags.append(
                f"POSITIVE: Consumer credit growing slower than wages — credit discipline maintained"
            )

    if mortgages is not None and mortgages > 20:
        flags.append(
            f"POSITIVE: Real mortgage credit +{mortgages:.1f}% YoY — "
            f"housing credit normalizing (from near-zero base)"
        )

    if deposits_real_growing is False:
        flags.append(
            "WARNING: Real deposits declining — households drawing down savings or dollarizing"
        )
    elif deposits_real_growing is True:
        flags.append(
            "POSITIVE: Real deposits growing — household saving behavior intact"
        )

    # Assess sustainability
    sustainability = _assess_sustainability(credit_wage_spread, real_wage_yoy)

    summary = _make_summary(consumer_total, real_wage_yoy, credit_wage_spread, mortgages)

    result = {
        "domain": "credit",
        "as_of_date": as_of,
        "data_quality": "good" if consumer_total is not None else "partial",
        "metrics": {
            "real_personal_loans_yoy": personal_loans,
            "real_credit_cards_yoy": credit_cards,
            "real_mortgages_yoy": mortgages,
            "real_auto_loans_yoy": auto_loans,
            "real_overdrafts_yoy": overdrafts,
            "real_commercial_paper_yoy": commercial,
            "consumer_credit_yoy": consumer_total,
            "real_wage_yoy_latest": real_wage_yoy,
            "credit_wage_spread_3m": credit_wage_spread,
            "consumer_credit_trend_3m": credit_trend_3m,
            "deposits_yoy_nominal": nominal_dep,
            "deposits_real_growing": deposits_real_growing,
            "sustainability": sustainability,
        },
        "flags": flags,
        "trend": _trend(df_c),
        "connection_to_master_variable": "negative" if (credit_wage_spread or 0) > 20 else "neutral",
        "summary": summary,
    }

    _save(result)
    return result


def _assess_sustainability(spread, real_wage_yoy) -> str:
    if spread is None:
        return "unknown"
    if spread < 0:
        return "sustainable"
    if spread < 15 and (real_wage_yoy or 0) > 0:
        return "moderate_risk"
    if spread > 30 or (real_wage_yoy or 0) < -5:
        return "high_risk"
    return "watch"


def _trend(df: pd.DataFrame) -> str:
    col = "real_personal_loans_pct"
    if col not in df.columns:
        return "unknown"
    vals = df[col].dropna().tail(6).tolist()
    if len(vals) < 3:
        return "insufficient_data"
    mid = len(vals) // 2
    if sum(vals[mid:]) / (len(vals) - mid) > sum(vals[:mid]) / mid + 5:
        return "accelerating"
    if sum(vals[mid:]) / (len(vals) - mid) < sum(vals[:mid]) / mid - 5:
        return "decelerating"
    return "stable"


def _safe_float(v) -> float | None:
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


def _make_summary(consumer, wage, spread, mortgages) -> str:
    parts = []
    if consumer is not None:
        parts.append(f"Consumer credit +{consumer:.1f}% YoY (real)")
    if wage is not None:
        parts.append(f"real wages {wage:+.1f}%")
    if spread is not None:
        if spread > 15:
            parts.append(f"credit-wage spread {spread:+.1f}pp — households borrowing to consume")
        else:
            parts.append(f"credit-wage spread {spread:+.1f}pp — within sustainable range")
    if mortgages is not None and mortgages > 10:
        parts.append(f"mortgages +{mortgages:.1f}% YoY (housing credit recovery)")
    return "; ".join(parts) + "." if parts else "Credit data unavailable."


def _empty() -> dict:
    return {
        "domain": "credit",
        "as_of_date": None,
        "data_quality": "poor",
        "metrics": {},
        "flags": ["CRITICAL: Credit data unavailable"],
        "trend": "unknown",
        "connection_to_master_variable": "neutral",
        "summary": "Credit data unavailable.",
    }


def _save(data: dict) -> None:
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info("Saved: %s", OUT_FILE)
