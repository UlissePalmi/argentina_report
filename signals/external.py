"""
Layer 3 — Signal: External (Dollar Situation)

Reads:
  data/external/bcra_reserves.csv
  data/external/imf_current_account.csv
  data/external/indec_trade.csv
  data/external/bcra_fx.csv
Outputs data/signals/signals_external.json.
"""

import json

import pandas as pd

from utils import EXTERNAL_DIR, SIGNALS_DIR, get_logger

log = get_logger("signals.external")

OUT_FILE = SIGNALS_DIR / "signals_external.json"


def compute() -> dict:
    reserves_df = _read_csv("bcra_reserves.csv")
    ca_df       = _read_csv("imf_current_account.csv")
    trade_df    = _read_csv("indec_trade.csv")
    fx_df       = _read_csv("bcra_fx.csv")

    metrics = {}
    flags   = []

    # ------------------------------------------------------------------
    # Reserves (gross — net requires external calculation)
    # ------------------------------------------------------------------
    as_of = None
    reserves_latest    = None
    reserves_trend_6m  = None
    reserves_change_6m = None

    if reserves_df is not None and "reserves_usd_bn" in reserves_df.columns:
        rv = reserves_df["reserves_usd_bn"].dropna()
        if not rv.empty:
            reserves_latest = round(float(rv.iloc[-1]), 2)
            as_of = str(reserves_df["date"].dropna().iloc[-1])[:10]
            if len(rv) >= 6:
                reserves_change_6m = round(float(rv.iloc[-1]) - float(rv.iloc[-6]), 2)
                reserves_trend_6m  = "improving" if reserves_change_6m > 0 else "deteriorating"

    metrics["gross_reserves_bn"]   = reserves_latest
    metrics["reserves_change_6m"]  = reserves_change_6m
    metrics["reserves_trend_6m"]   = reserves_trend_6m

    # Flag reserves
    if reserves_latest is not None:
        if reserves_latest > 35:
            flags.append(f"POSITIVE: Gross reserves ${reserves_latest:.1f}B — adequate buffer")
        elif reserves_latest > 25:
            flags.append(f"NOTE: Gross reserves ${reserves_latest:.1f}B — moderate; net reserves materially lower")
        else:
            flags.append(f"WARNING: Gross reserves ${reserves_latest:.1f}B — thin; watch net reserves closely")
        if reserves_change_6m is not None:
            if reserves_change_6m > 3:
                flags.append(f"POSITIVE: Reserves +${reserves_change_6m:.1f}B over 6 months — accumulation underway")
            elif reserves_change_6m < -3:
                flags.append(f"WARNING: Reserves -${abs(reserves_change_6m):.1f}B over 6 months — depletion signal")

    # ------------------------------------------------------------------
    # Current account
    # ------------------------------------------------------------------
    ca_latest      = None
    ca_as_of       = None
    ca_trend       = None
    ca_last4       = []

    if ca_df is not None and "current_account_usd_bn" in ca_df.columns:
        cv = ca_df[["date", "current_account_usd_bn"]].dropna(subset=["current_account_usd_bn"])
        if not cv.empty:
            ca_latest = round(float(cv["current_account_usd_bn"].iloc[-1]), 2)
            ca_as_of  = str(cv["date"].iloc[-1])[:10]
            ca_last4  = [round(float(v), 2) for v in cv["current_account_usd_bn"].tail(4).tolist()]
            if len(ca_last4) >= 2:
                ca_trend = "improving" if ca_last4[-1] > ca_last4[-2] else "deteriorating"
            if as_of is None:
                as_of = ca_as_of

    metrics["current_account_latest_bn"] = ca_latest
    metrics["current_account_as_of"]     = ca_as_of
    metrics["current_account_last4"]     = ca_last4
    metrics["current_account_trend"]     = ca_trend

    if ca_latest is not None:
        if ca_latest > 1:
            flags.append(f"POSITIVE: Current account surplus ${ca_latest:.1f}B in latest quarter")
        elif ca_latest > -1:
            flags.append(f"NOTE: Current account near-balanced at ${ca_latest:.1f}B — monitor")
        elif ca_latest > -3:
            flags.append(f"WARNING: Current account deficit ${abs(ca_latest):.1f}B — manageable but watch")
        else:
            flags.append(f"CRITICAL: Current account deficit ${abs(ca_latest):.1f}B — significant external pressure")

    # ------------------------------------------------------------------
    # Trade balance
    # ------------------------------------------------------------------
    trade_surplus_latest = None
    trade_trend          = None

    if trade_df is not None:
        # Try to find exports/imports or a balance column
        bal_col = next((c for c in trade_df.columns if "balance" in c.lower()), None)
        exp_col = next((c for c in trade_df.columns if "export" in c.lower()), None)
        imp_col = next((c for c in trade_df.columns if "import" in c.lower()), None)

        if bal_col:
            bv = trade_df[bal_col].dropna()
            if not bv.empty:
                trade_surplus_latest = round(float(bv.iloc[-1]), 2)
        elif exp_col and imp_col:
            sub = trade_df[[exp_col, imp_col]].dropna()
            if not sub.empty:
                trade_surplus_latest = round(
                    float(sub[exp_col].iloc[-1]) - float(sub[imp_col].iloc[-1]), 2
                )

        if trade_surplus_latest is not None:
            series = trade_df[bal_col].dropna().tail(6).tolist() if bal_col else []
            if len(series) >= 2:
                trade_trend = "improving" if series[-1] > series[-2] else "deteriorating"

    metrics["trade_surplus_latest_bn"] = trade_surplus_latest
    metrics["trade_trend"]             = trade_trend

    if trade_surplus_latest is not None:
        if trade_surplus_latest > 2:
            flags.append(f"POSITIVE: Trade surplus ${trade_surplus_latest:.2f}B — goods sector generating dollars")
        elif trade_surplus_latest > 0:
            flags.append(f"NOTE: Small trade surplus ${trade_surplus_latest:.2f}B")
        else:
            flags.append(f"WARNING: Trade deficit ${abs(trade_surplus_latest):.2f}B — external pressure")

    # ------------------------------------------------------------------
    # FX (crawling peg assessment)
    # ------------------------------------------------------------------
    fx_latest     = None
    fx_change_6m  = None
    fx_pct_change = None

    if fx_df is not None:
        fx_col = next((c for c in fx_df.columns if c != "date"), None)
        if fx_col:
            fv = fx_df[fx_col].dropna()
            if not fv.empty:
                fx_latest = round(float(fv.iloc[-1]), 2)
                if len(fv) >= 6:
                    old = float(fv.iloc[-6])
                    fx_change_6m  = round(fx_latest - old, 2)
                    fx_pct_change = round((fx_latest / old - 1) * 100, 2) if old > 0 else None

    metrics["fx_rate_latest"]  = fx_latest
    metrics["fx_change_6m_pct"] = fx_pct_change

    # Real appreciation warning: if FX depreciation < CPI over same period
    # (qualitative flag since we don't have both series aligned here)
    if fx_pct_change is not None and fx_pct_change < 10:
        flags.append(
            f"WARNING: FX depreciated only {fx_pct_change:.1f}% over 6 months — "
            f"real appreciation likely given elevated inflation; monitor trade competitiveness"
        )

    # ------------------------------------------------------------------
    # Overall assessment
    # ------------------------------------------------------------------
    overall = _overall_assessment(reserves_latest, reserves_change_6m, ca_latest, ca_trend)
    trend   = _overall_trend(reserves_trend_6m, ca_trend)

    result = {
        "domain": "external",
        "as_of_date": as_of,
        "data_quality": "good" if reserves_latest is not None else "partial",
        "metrics": metrics,
        "flags": flags,
        "trend": trend,
        "connection_to_master_variable": _connection(reserves_latest, reserves_change_6m, ca_latest),
        "summary": _make_summary(reserves_latest, ca_latest, trade_surplus_latest, trend),
    }

    _save(result)
    return result


def _overall_assessment(res, res_chg, ca, ca_trend) -> str:
    if res is None:
        return "unknown"
    if (res or 0) < 20 and (res_chg or 0) < 0 and (ca or 0) < -3:
        return "crisis_risk"
    if (ca or 0) > 0 and (res_chg or 0) > 0:
        return "improving"
    if (ca or 0) < -3:
        return "deteriorating"
    return "stable"


def _overall_trend(res_trend, ca_trend) -> str:
    signals = [s for s in [res_trend, ca_trend] if s]
    if not signals:
        return "unknown"
    improving = signals.count("improving")
    deteriorating = signals.count("deteriorating")
    if improving > deteriorating:
        return "improving"
    if deteriorating > improving:
        return "deteriorating"
    return "mixed"


def _connection(res, res_chg, ca) -> str:
    if (ca or 0) > 0 and (res_chg or 0) > 0:
        return "positive"
    if (ca or 0) < -3 or (res or 0) < 20:
        return "negative"
    return "neutral"


def _make_summary(reserves, ca, trade, trend) -> str:
    parts = []
    if reserves is not None:
        parts.append(f"Gross reserves ${reserves:.1f}B")
    if ca is not None:
        direction = "surplus" if ca > 0 else "deficit"
        parts.append(f"CA {direction} ${abs(ca):.1f}B/quarter")
    if trade is not None:
        direction = "surplus" if trade > 0 else "deficit"
        parts.append(f"trade {direction} ${abs(trade):.2f}B")
    parts.append(f"trend: {trend}")
    return "; ".join(parts) + "." if parts else "External data unavailable."


def _read_csv(filename: str) -> pd.DataFrame | None:
    path = EXTERNAL_DIR / filename
    if not path.exists():
        log.warning("%s not found", filename)
        return None
    try:
        df = pd.read_csv(path, parse_dates=["date"])
        return df.sort_values("date").reset_index(drop=True)
    except Exception as e:
        log.warning("Could not read %s: %s", filename, e)
        return None


def _empty() -> dict:
    return {
        "domain": "external",
        "as_of_date": None,
        "data_quality": "poor",
        "metrics": {},
        "flags": ["CRITICAL: External data unavailable"],
        "trend": "unknown",
        "connection_to_master_variable": "neutral",
        "summary": "External data unavailable.",
    }


def _save(data: dict) -> None:
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info("Saved: %s", OUT_FILE)
