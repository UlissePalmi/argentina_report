"""
Layer 3 — Signal: Investment (FBCF)

Reads data/gdp/gdp_fbcf.csv.
Outputs data/signals/signals_investment.json.

Dollar classification:
  dollar-neutral:  construction, domestic machinery
  dollar-draining: imported machinery, transport equipment
"""

import json

import pandas as pd

from utils import GDP_DIR, SIGNALS_DIR, get_logger

log = get_logger("signals.investment")

OUT_FILE = SIGNALS_DIR / "signals_investment.json"

DOLLAR_DRAINING  = ["fbcf_maq_imp_yoy", "fbcf_transport_yoy"]
DOLLAR_NEUTRAL   = ["fbcf_constr_yoy", "fbcf_maq_nac_yoy"]
SHARE_COLS       = ["fbcf_constr_share", "fbcf_maq_nac_share", "fbcf_maq_imp_share", "fbcf_transport_share"]

LABELS = {
    "fbcf_constr_yoy":     ("Construction",       "dollar-neutral"),
    "fbcf_maq_nac_yoy":    ("Domestic machinery", "dollar-neutral"),
    "fbcf_maq_imp_yoy":    ("Imported machinery", "dollar-draining"),
    "fbcf_transport_yoy":  ("Transport equip.",   "dollar-draining"),
}


def compute() -> dict:
    path = GDP_DIR / "gdp_fbcf.csv"
    if not path.exists():
        log.warning("gdp_fbcf.csv not found — investment signal unavailable")
        return _empty()

    df = pd.read_csv(path)
    df = df.sort_values("date").reset_index(drop=True)

    all_yoy = DOLLAR_DRAINING + DOLLAR_NEUTRAL
    avail = [c for c in all_yoy if c in df.columns]
    if not avail:
        return _empty()

    df_v = df.dropna(subset=avail, how="all")
    if df_v.empty:
        return _empty()

    latest  = df_v.iloc[-1]
    as_of   = str(latest["date"])[:10]
    quarter = str(latest.get("quarter", as_of))

    def _get(col):
        return _safe_float(latest.get(col)) if col in df_v.columns else None

    constr_yoy    = _get("fbcf_constr_yoy")
    maq_nac_yoy   = _get("fbcf_maq_nac_yoy")
    maq_imp_yoy   = _get("fbcf_maq_imp_yoy")
    transport_yoy = _get("fbcf_transport_yoy")

    constr_share    = _get("fbcf_constr_share")
    maq_nac_share   = _get("fbcf_maq_nac_share")
    maq_imp_share   = _get("fbcf_maq_imp_share")
    transport_share = _get("fbcf_transport_share")

    # Dollar-draining share of total FBCF
    dd_share = None
    if maq_imp_share is not None and transport_share is not None:
        dd_share = round(maq_imp_share + transport_share, 1)

    # Proxy for total FBCF YoY: weighted average of sub-components using shares
    fbcf_yoy_proxy = _weighted_yoy(
        [constr_yoy, maq_nac_yoy, maq_imp_yoy, transport_yoy],
        [constr_share, maq_nac_share, maq_imp_share, transport_share]
    )

    # 3-quarter trend for each component
    constr_trend = _component_trend(df_v, "fbcf_constr_yoy")
    maq_imp_trend = _component_trend(df_v, "fbcf_maq_imp_yoy")

    # Consecutive quarters of FBCF growth (use proxy)
    if "fbcf_constr_yoy" in df_v.columns:
        series = df_v["fbcf_constr_yoy"].dropna().tolist()
        consec_pos = _count_consecutive_positive(series)
    else:
        consec_pos = 0

    flags = _build_flags(constr_yoy, maq_nac_yoy, maq_imp_yoy, transport_yoy,
                         fbcf_yoy_proxy, dd_share)

    trend = _overall_trend(fbcf_yoy_proxy, df_v)

    result = {
        "domain": "investment",
        "as_of_date": as_of,
        "latest_quarter": quarter,
        "data_quality": "good" if fbcf_yoy_proxy is not None else "partial",
        "metrics": {
            "fbcf_yoy_proxy": fbcf_yoy_proxy,
            "fbcf_constr_yoy": constr_yoy,
            "fbcf_maq_nac_yoy": maq_nac_yoy,
            "fbcf_maq_imp_yoy": maq_imp_yoy,
            "fbcf_transport_yoy": transport_yoy,
            "fbcf_constr_share": constr_share,
            "fbcf_maq_nac_share": maq_nac_share,
            "fbcf_maq_imp_share": maq_imp_share,
            "fbcf_transport_share": transport_share,
            "dollar_draining_share_pct": dd_share,
            "fbcf_constr_trend_3q": constr_trend,
            "fbcf_maq_imp_trend_3q": maq_imp_trend,
            "consecutive_positive_quarters": consec_pos,
        },
        "flags": flags,
        "trend": trend,
        "connection_to_master_variable": _connection(fbcf_yoy_proxy),
        "summary": _make_summary(fbcf_yoy_proxy, constr_yoy, maq_imp_yoy, trend),
    }

    _save(result)
    return result


def _weighted_yoy(yoys: list, shares: list) -> float | None:
    pairs = [(y, s) for y, s in zip(yoys, shares)
             if y is not None and s is not None and s > 0]
    if not pairs:
        return None
    total_share = sum(s for _, s in pairs)
    weighted    = sum(y * s for y, s in pairs)
    return round(weighted / total_share, 2)


def _component_trend(df: pd.DataFrame, col: str) -> str:
    if col not in df.columns:
        return "unknown"
    vals = df[col].dropna().tail(3).tolist()
    if len(vals) < 2:
        return "unknown"
    if vals[-1] > vals[0] + 5:
        return "improving"
    if vals[-1] < vals[0] - 5:
        return "deteriorating"
    return "stable"


def _count_consecutive_positive(series: list) -> int:
    count = 0
    for v in reversed(series):
        if v > 0:
            count += 1
        else:
            break
    return count


def _overall_trend(proxy, df: pd.DataFrame) -> str:
    if "fbcf_constr_yoy" not in df.columns:
        return "unknown"
    vals = df["fbcf_constr_yoy"].dropna().tail(4).tolist()
    if not vals:
        return "unknown"
    pos = sum(1 for v in vals if v > 0)
    if pos >= 3:
        return "improving"
    elif pos == 0:
        return "deteriorating"
    return "mixed"


def _connection(proxy) -> str:
    if proxy is None:
        return "neutral"
    if proxy > 5:
        return "positive"
    if proxy > 0:
        return "neutral"
    return "negative"


def _build_flags(constr, maq_nac, maq_imp, transport, proxy, dd_share) -> list:
    flags = []
    if proxy is not None:
        if proxy > 15:
            flags.append(f"POSITIVE: Total FBCF proxy +{proxy:.1f}% YoY — strong investment cycle")
        elif proxy > 5:
            flags.append(f"POSITIVE: FBCF growing +{proxy:.1f}% YoY — moderate investment recovery")
        elif proxy is not None and proxy < 0:
            flags.append(f"WARNING: FBCF contracting {proxy:.1f}% YoY — investment falling")

    if maq_imp is not None and maq_imp > 20:
        flags.append(
            f"WARNING: Imported machinery surging +{maq_imp:.1f}% YoY — "
            f"positive for capacity but dollar-draining (reserve pressure)"
        )
    elif maq_imp is not None and maq_imp < -10:
        flags.append(
            f"NOTE: Imported machinery -{ abs(maq_imp):.1f}% YoY — "
            f"short-term reserve relief but signals weak capital formation"
        )

    if maq_nac is not None and maq_nac > 10:
        flags.append(
            f"POSITIVE: Domestic machinery +{maq_nac:.1f}% YoY — dollar-neutral capacity building"
        )

    if constr is not None and constr > 10:
        flags.append(
            f"POSITIVE: Construction +{constr:.1f}% YoY — domestic activity and employment driver"
        )
    elif constr is not None and constr < -10:
        flags.append(
            f"WARNING: Construction -{abs(constr):.1f}% YoY — employment drag, domestic demand weakness"
        )

    if dd_share is not None and dd_share > 40:
        flags.append(
            f"WARNING: Dollar-draining components = {dd_share:.1f}% of FBCF — "
            f"investment recovery structurally reserve-intensive"
        )

    return flags


def _safe_float(v) -> float | None:
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


def _make_summary(proxy, constr, maq_imp, trend) -> str:
    parts = []
    if proxy is not None:
        direction = "grew" if proxy > 0 else "contracted"
        parts.append(f"Total FBCF {direction} {abs(proxy):.1f}% YoY (weighted estimate)")
    if constr is not None:
        parts.append(f"construction {constr:+.1f}%")
    if maq_imp is not None:
        parts.append(f"imported machinery {maq_imp:+.1f}%")
    parts.append(f"trend: {trend}")
    return "; ".join(parts) + "." if parts else "FBCF data unavailable."


def _empty() -> dict:
    return {
        "domain": "investment",
        "as_of_date": None,
        "data_quality": "poor",
        "metrics": {},
        "flags": ["CRITICAL: FBCF data unavailable"],
        "trend": "unknown",
        "connection_to_master_variable": "neutral",
        "summary": "FBCF investment data unavailable.",
    }


def _save(data: dict) -> None:
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info("Saved: %s", OUT_FILE)
