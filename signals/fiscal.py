"""
Layer 3 — Signal: Fiscal Balance

Reads:  data/external/fiscal_balance.csv
Output: data/signals/signals_fiscal.json

Metrics computed:
  - fiscal_primary_latest_ars_bn   : latest monthly primary result (ARS bn)
  - fiscal_primary_pct_gdp         : latest period as % of GDP
  - fiscal_balance_label           : "primary" or "overall"
  - fiscal_trend_3m                : improving / deteriorating / stable
  - fiscal_consecutive_surplus_months : streak of positive months
  - fiscal_ytd_ars_bn              : calendar year-to-date cumulative
  - fiscal_12m_rolling_ars_bn      : rolling 12-month sum
  - fiscal_as_of                   : date of most recent data point
"""

import json
from datetime import datetime

import pandas as pd

from utils import EXTERNAL_DIR, SIGNALS_DIR, get_logger

log     = get_logger("signals.fiscal")
OUT_FILE = SIGNALS_DIR / "signals_fiscal.json"


def compute() -> dict:
    fiscal_df = _read_csv("fiscal_balance.csv")

    if fiscal_df is None or fiscal_df.empty:
        result = _empty()
        _save(result)
        return result

    # ------------------------------------------------------------------
    # Identify value column and label
    # ------------------------------------------------------------------
    ars_col = next(
        (c for c in ["fiscal_primary_ars_bn", "fiscal_financial_ars_bn", "fiscal_result_ars_bn"]
         if c in fiscal_df.columns),
        None,
    )
    pct_col = next(
        (c for c in ["fiscal_primary_pct_gdp", "fiscal_financial_pct_gdp", "fiscal_balance_pct_gdp"]
         if c in fiscal_df.columns),
        None,
    )

    if ars_col is None and pct_col is None:
        log.warning("fiscal_balance.csv has no recognised value column: %s", fiscal_df.columns.tolist())
        result = _empty()
        _save(result)
        return result

    fiscal_label = "primary" if (ars_col and "primary" in ars_col) or (pct_col and "primary" in pct_col) else "overall"

    # Work with whichever column we have for the ARS series
    val_col = ars_col or pct_col
    df = fiscal_df[["date", val_col]].dropna(subset=[val_col]).copy()
    df = df.sort_values("date").reset_index(drop=True)

    if df.empty:
        result = _empty()
        _save(result)
        return result

    metrics = {}
    flags   = []

    # ------------------------------------------------------------------
    # Latest value
    # ------------------------------------------------------------------
    latest_val   = float(df[val_col].iloc[-1])
    latest_date  = str(df["date"].iloc[-1])[:10]
    as_of        = latest_date

    if ars_col:
        metrics["fiscal_primary_latest_ars_bn"] = round(latest_val, 2)
    metrics["fiscal_balance_label"] = fiscal_label
    metrics["fiscal_as_of"]         = as_of

    # % GDP (if available from the CSV)
    pct_latest = None
    if pct_col and pct_col in fiscal_df.columns:
        pct_series = fiscal_df[["date", pct_col]].dropna(subset=[pct_col]).sort_values("date")
        if not pct_series.empty:
            pct_latest = round(float(pct_series[pct_col].iloc[-1]), 2)
    metrics["fiscal_primary_pct_gdp"] = pct_latest

    # ------------------------------------------------------------------
    # 3-month trend (compare last 3 avg vs prior 3 avg)
    # ------------------------------------------------------------------
    fiscal_trend_3m = "stable"
    if len(df) >= 6:
        recent3 = df[val_col].tail(3).mean()
        prior3  = df[val_col].iloc[-6:-3].mean()
        diff    = recent3 - prior3
        if abs(diff) < 0.05 * abs(prior3) if prior3 != 0 else abs(diff) < 0.5:
            fiscal_trend_3m = "stable"
        elif diff > 0:
            fiscal_trend_3m = "improving"   # moving toward surplus / larger surplus
        else:
            fiscal_trend_3m = "deteriorating"
    elif len(df) >= 2:
        fiscal_trend_3m = "improving" if float(df[val_col].iloc[-1]) > float(df[val_col].iloc[-2]) else "deteriorating"
    metrics["fiscal_trend_3m"] = fiscal_trend_3m

    # ------------------------------------------------------------------
    # Consecutive surplus months (streak of positive values)
    # ------------------------------------------------------------------
    streak = 0
    for v in reversed(df[val_col].tolist()):
        if v > 0:
            streak += 1
        else:
            break
    metrics["fiscal_consecutive_surplus_months"] = streak

    # ------------------------------------------------------------------
    # YTD cumulative (current calendar year)
    # ------------------------------------------------------------------
    ytd_ars_bn = None
    if ars_col:
        current_year = pd.to_datetime(latest_date).year
        ytd_df = df[pd.to_datetime(df["date"]).dt.year == current_year]
        if not ytd_df.empty:
            ytd_ars_bn = round(float(ytd_df[val_col].sum()), 2)
    metrics["fiscal_ytd_ars_bn"] = ytd_ars_bn

    # ------------------------------------------------------------------
    # 12-month rolling sum
    # ------------------------------------------------------------------
    rolling_12m = None
    if ars_col and len(df) >= 12:
        rolling_12m = round(float(df[val_col].tail(12).sum()), 2)
    metrics["fiscal_12m_rolling_ars_bn"] = rolling_12m

    # ------------------------------------------------------------------
    # Flags
    # ------------------------------------------------------------------
    if pct_latest is not None:
        if pct_latest > 1.5:
            flags.append(
                f"POSITIVE: Fiscal {fiscal_label} surplus {pct_latest:+.1f}% GDP -- "
                f"removes crisis risk and is above the 1.5% green threshold"
            )
        elif pct_latest >= 0:
            flags.append(
                f"NOTE: Fiscal {fiscal_label} balance {pct_latest:+.1f}% GDP -- "
                f"balanced but thin margin; below 1.5% green threshold"
            )
        else:
            flags.append(
                f"WARNING: Fiscal {fiscal_label} deficit {pct_latest:+.1f}% GDP -- "
                f"fiscal pressure present; monitor for sustainability"
            )
    elif ars_col:
        direction = "surplus" if latest_val > 0 else "deficit"
        flags.append(
            f"{'POSITIVE' if latest_val > 0 else 'WARNING'}: "
            f"Fiscal {fiscal_label} {direction} ARS {abs(latest_val):.1f}bn in {latest_date[:7]} "
            f"(% GDP normalisation not yet available)"
        )

    if streak >= 6:
        flags.append(
            f"POSITIVE: {streak} consecutive months of fiscal {fiscal_label} surplus -- "
            f"structural not cyclical"
        )
    elif streak >= 3:
        flags.append(
            f"NOTE: {streak} consecutive months of fiscal {fiscal_label} surplus -- "
            f"consolidation underway but too early to call structural"
        )
    elif streak == 0 and ars_col:
        flags.append("WARNING: Latest month shows a fiscal deficit -- surplus streak broken")

    if fiscal_trend_3m == "deteriorating":
        flags.append("WARNING: 3-month fiscal trend is deteriorating -- watch for reversal")
    elif fiscal_trend_3m == "improving":
        flags.append("POSITIVE: 3-month fiscal trend is improving -- consolidation momentum")

    # ------------------------------------------------------------------
    # Assemble result
    # ------------------------------------------------------------------
    is_surplus    = (pct_latest or latest_val or 0) > 0
    connection    = "positive" if is_surplus else "negative"

    summary = _make_summary(latest_val if ars_col else None, pct_latest,
                            fiscal_label, streak, fiscal_trend_3m, as_of)

    result = {
        "domain":   "fiscal",
        "as_of_date": as_of,
        "data_quality": "good" if (ars_col and len(df) >= 6) else "partial",
        "metrics":  metrics,
        "flags":    flags,
        "trend":    fiscal_trend_3m,
        "connection_to_master_variable": connection,
        "summary":  summary,
    }

    _save(result)
    return result


def _make_summary(ars_bn, pct_gdp, label, streak, trend, as_of) -> str:
    parts = []
    if pct_gdp is not None:
        direction = "surplus" if pct_gdp >= 0 else "deficit"
        parts.append(f"Fiscal {label} {direction} of {abs(pct_gdp):.1f}% GDP as of {as_of[:7]}")
    elif ars_bn is not None:
        direction = "surplus" if ars_bn >= 0 else "deficit"
        parts.append(f"Fiscal {label} {direction} of ARS {abs(ars_bn):.1f}bn in {as_of[:7]}")

    if streak >= 3:
        parts.append(f"{streak} consecutive months in surplus")
    elif streak == 0:
        parts.append("latest month in deficit")

    if trend == "improving":
        parts.append("3-month trend improving")
    elif trend == "deteriorating":
        parts.append("3-month trend deteriorating")

    return "; ".join(parts) + "." if parts else "Fiscal data available but metrics could not be computed."


def _empty() -> dict:
    return {
        "domain":   "fiscal",
        "as_of_date": None,
        "data_quality": "poor",
        "metrics":  {},
        "flags":    ["WARNING: Fiscal balance data unavailable -- scorecard shows n/a"],
        "trend":    "unknown",
        "connection_to_master_variable": "neutral",
        "summary":  "Fiscal balance data unavailable.",
    }


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


def _save(data: dict) -> None:
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info("Saved: %s", OUT_FILE)
