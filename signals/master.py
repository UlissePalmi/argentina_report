"""
Layer 3 — Signal: Master Synthesis

Reads all domain signal JSON files from data/signals/.
Outputs data/signals/signals_master.json.

This is the file the SKILL_master reads to write the report executive summary.
"""

import json
from pathlib import Path

from utils import SIGNALS_DIR, get_logger

log = get_logger("signals.master")

OUT_FILE = SIGNALS_DIR / "signals_master.json"

DOMAIN_FILES = {
    "wages":      "signals_wages.json",
    "credit":     "signals_credit.json",
    "investment": "signals_investment.json",
    "inflation":  "signals_inflation.json",
    "external":   "signals_external.json",
    "production": "signals_production.json",
    "labor":      "signals_labor.json",
}

# Verdict thresholds (from Blueprint)
VERDICT_SCALE = [
    "crisis_risk",
    "fragile_recovery",
    "structural_improvement_underway_unconfirmed",
    "recovery_confirmed_watch_sustainability",
    "sustainable_growth",
]


def compute() -> dict:
    # Load all domain signals
    all_signals = {}
    missing = []
    for domain, fname in DOMAIN_FILES.items():
        path = SIGNALS_DIR / fname
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    all_signals[domain] = json.load(f)
            except Exception as e:
                log.warning("Could not load %s: %s", fname, e)
                missing.append(domain)
        else:
            log.warning("%s not found — run compute() for domain first", fname)
            missing.append(domain)

    if not all_signals:
        log.error("No domain signals found — run domain signal scripts first")
        return _empty()

    # --- Extract key metrics (with safe fallbacks) ---
    def _m(domain, *keys):
        """Safely extract nested metric."""
        s = all_signals.get(domain, {})
        metrics = s.get("metrics", {})
        for k in keys:
            if isinstance(metrics, dict):
                metrics = metrics.get(k)
            else:
                return None
        return metrics

    # MASTER VARIABLE
    real_wage_yoy    = _m("wages", "real_wage_yoy_latest")
    real_wage_trend  = _m("wages", "real_wage_trend_3m")
    consec_wage_pos  = _m("wages", "consecutive_positive_months") or 0

    # DRIVERS
    fbcf_yoy         = _m("investment", "fbcf_yoy_proxy")
    formal_emp_yoy   = _m("labor", "sipa_yoy_latest")
    prod_trend       = _m("production", "productivity_trend") or _m("labor", "productivity_trend") or "unknown"
    credit_wage_spread = _m("credit", "credit_wage_spread_3m")

    # ENABLERS
    cpi_mom_latest   = _m("inflation", "cpi_mom_latest")
    inflation_trend  = all_signals.get("inflation", {}).get("trend", "unknown")
    gross_reserves   = _m("external", "gross_reserves_bn")
    net_reserves     = _m("external", "net_reserves_bn")   # gross minus swap liabilities
    reserves_trend   = _m("external", "reserves_trend_6m")
    ca_latest        = _m("external", "current_account_latest_bn")
    fiscal_pct_gdp   = _m("external", "fiscal_balance_pct_gdp")

    # ACCELERATORS (Vaca Muerta)
    oil_yoy          = _m("production", "oil_yoy_latest")
    gas_yoy          = _m("production", "gas_yoy_latest")
    vaca_muerta      = _m("production", "vaca_muerta_signal") or "unknown"

    # For verdict, prefer net reserves; fall back to gross if net unavailable
    reserves_for_verdict = net_reserves if net_reserves is not None else gross_reserves

    # --- Compute verdict ---
    verdict = _compute_verdict(
        real_wage_yoy=real_wage_yoy,
        consec_wage_pos=consec_wage_pos,
        fbcf_yoy=fbcf_yoy,
        net_reserves=reserves_for_verdict,
        ca_latest=ca_latest,
        inflation_trend=inflation_trend,
        credit_wage_spread=credit_wage_spread,
        using_net=(net_reserves is not None),
    )

    # --- Collect all flags ---
    all_flags = []
    for domain, sig in all_signals.items():
        for flag in sig.get("flags", []):
            all_flags.append(f"[{domain.upper()}] {flag}")

    # --- Scorecard ---
    scorecard = _build_scorecard(
        real_wage_yoy, fbcf_yoy, cpi_mom_latest,
        gross_reserves, net_reserves,
        ca_latest, formal_emp_yoy, oil_yoy, fiscal_pct_gdp,
    )

    # --- Summary ---
    summary = _make_summary(verdict, real_wage_yoy, fbcf_yoy, cpi_mom_latest,
                            gross_reserves, net_reserves)

    result = {
        "domain": "master",
        "verdict": verdict,
        "as_of_date": _latest_date(all_signals),
        "data_quality": "good" if len(missing) == 0 else "partial",
        "missing_domains": missing,

        "master_variable": {
            "value": real_wage_yoy,
            "trend_3m": real_wage_trend,
            "consecutive_positive_months": consec_wage_pos,
            "status": "positive" if (real_wage_yoy or 0) > 0 else "negative",
            "backed_by_productivity": _is_productivity_backed(
                real_wage_yoy, credit_wage_spread, prod_trend
            ),
        },

        "drivers": {
            "investment_fbcf_yoy": fbcf_yoy,
            "investment_trend": all_signals.get("investment", {}).get("trend", "unknown"),
            "formal_employment_yoy": formal_emp_yoy,
            "productivity_trend": prod_trend,
            "credit_discipline": _credit_discipline(credit_wage_spread),
        },

        "enablers": {
            "inflation_mom_latest": cpi_mom_latest,
            "inflation_trend": inflation_trend,
            "disinflation_confirmed": _m("inflation", "disinflation_confirmed"),
            "gross_reserves_bn": gross_reserves,
            "net_reserves_bn": net_reserves,
            "reserves_trend": reserves_trend,
            "current_account_bn": ca_latest,
            "fiscal_balance_pct_gdp": fiscal_pct_gdp,
        },

        "accelerators": {
            "oil_yoy": oil_yoy,
            "gas_yoy": gas_yoy,
            "vaca_muerta_signal": vaca_muerta,
        },

        "scorecard": scorecard,
        "flags": all_flags,
        "summary": summary,
    }

    _save(result)
    return result


def _compute_verdict(real_wage_yoy, consec_wage_pos, fbcf_yoy, net_reserves,
                     ca_latest, inflation_trend, credit_wage_spread,
                     using_net: bool = False) -> str:
    """
    Returns one of the five verdict levels from the Blueprint.

    net_reserves: if using_net=True, thresholds are for true net reserves
      (blueprint: green >$5B, yellow $0-5B, red <$0).
      If using_net=False (gross), apply legacy gross thresholds.
    """
    w  = real_wage_yoy or 0
    f  = fbcf_yoy or 0
    r  = net_reserves or 0
    ca = ca_latest or 0

    # Crisis thresholds differ: net reserves can be negative by design
    if using_net:
        crisis_reserves = r < -5   # net < -$5B = externally constrained
        danger_reserves = r < 0
    else:
        crisis_reserves = r < 20   # gross < $20B = thin
        danger_reserves = r < 25

    # CRISIS RISK
    if w < -5 and f < 0 and crisis_reserves:
        return "crisis_risk"
    if ca < -5 and danger_reserves:
        return "crisis_risk"

    # FRAGILE RECOVERY: wages positive but credit-driven + investment weak
    if w > 0 and (credit_wage_spread or 0) > 25 and f < 5:
        return "fragile_recovery"

    # RECOVERY CONFIRMED: wages positive 3+ quarters backed by productivity
    if w > 0 and consec_wage_pos >= 9 and f > 0:
        return "recovery_confirmed_watch_sustainability"

    # SUSTAINABLE GROWTH: all levels positive and self-reinforcing
    sus_reserves = (r > 5) if using_net else (r > 30)
    if w > 5 and consec_wage_pos >= 12 and f > 10 and sus_reserves:
        return "sustainable_growth"

    return "structural_improvement_underway_unconfirmed"


def _is_productivity_backed(real_wage_yoy, credit_spread, prod_trend) -> bool | None:
    if real_wage_yoy is None:
        return None
    if real_wage_yoy <= 0:
        return False
    # Wage growth backed by productivity if: spread low AND productivity improving
    credit_ok = (credit_spread or 0) < 15
    prod_ok   = prod_trend in ("improving", "stable")
    return credit_ok and prod_ok


def _credit_discipline(spread) -> str:
    if spread is None:
        return "unknown"
    if spread < 0:
        return "disciplined"
    if spread < 15:
        return "moderate"
    if spread < 30:
        return "elevated"
    return "warning"


def _build_scorecard(wage, fbcf, cpi_mom, gross_res, net_res,
                     ca, emp, oil, fiscal) -> dict:
    def _traffic(value, green_fn, yellow_fn) -> str:
        if value is None:
            return "grey"
        if green_fn(value):
            return "green"
        if yellow_fn(value):
            return "yellow"
        return "red"

    # Net reserves row: use net if available, else gross with adjusted thresholds
    if net_res is not None:
        res_label    = "Net Reserves (est., $B)"
        res_value    = net_res
        res_signal   = _traffic(net_res, lambda v: v > 5, lambda v: v >= 0)
        res_green    = "> $5B"
        res_yellow   = "$0-5B"
        res_red      = "< $0B (negative)"
    else:
        res_label    = "Gross Reserves ($B)"
        res_value    = gross_res
        res_signal   = _traffic(gross_res, lambda v: v > 30, lambda v: v > 20)
        res_green    = "> $30B"
        res_yellow   = "$20-30B"
        res_red      = "< $20B"

    return {
        "Master Variable (real wages YoY)": {
            "value": wage,
            "signal": _traffic(wage, lambda v: v > 3, lambda v: v >= 0),
            "green": "> 3%", "yellow": "0-3%", "red": "< 0%",
        },
        "Investment (FBCF YoY proxy)": {
            "value": fbcf,
            "signal": _traffic(fbcf, lambda v: v > 10, lambda v: v >= 0),
            "green": "> 10%", "yellow": "0-10%", "red": "< 0%",
        },
        "Inflation (monthly CPI)": {
            "value": cpi_mom,
            "signal": _traffic(cpi_mom, lambda v: v < 2, lambda v: v < 4),
            "green": "< 2%", "yellow": "2-4%", "red": "> 4%",
        },
        res_label: {
            "value": res_value,
            "signal": res_signal,
            "green": res_green, "yellow": res_yellow, "red": res_red,
        },
        "Current Account (quarterly $B)": {
            "value": ca,
            "signal": _traffic(ca, lambda v: v > 1, lambda v: v > -1),
            "green": "> $1B surplus", "yellow": "-$1B to $1B", "red": "< -$1B deficit",
        },
        "Formal Employment (YoY)": {
            "value": emp,
            "signal": _traffic(emp, lambda v: v > 3, lambda v: v >= 0),
            "green": "> 3%", "yellow": "0-3%", "red": "< 0%",
        },
        "Oil Production (YoY)": {
            "value": oil,
            "signal": _traffic(oil, lambda v: v > 10, lambda v: v >= 0),
            "green": "> 10%", "yellow": "0-10%", "red": "< 0%",
        },
        "Fiscal Balance (% GDP)": {
            "value": fiscal,
            "signal": _traffic(fiscal, lambda v: v > 1.5, lambda v: v >= 0),
            "green": "> 1.5% surplus", "yellow": "0-1.5%", "red": "< 0% deficit",
        },
    }


def _latest_date(signals: dict) -> str | None:
    dates = []
    for s in signals.values():
        d = s.get("as_of_date")
        if d:
            dates.append(d)
    return max(dates) if dates else None


def _make_summary(verdict, wage, fbcf, cpi, gross, net) -> str:
    reserves = net if net is not None else gross
    verdict_labels = {
        "crisis_risk": "CRISIS RISK",
        "fragile_recovery": "FRAGILE RECOVERY",
        "structural_improvement_underway_unconfirmed":
            "STRUCTURAL IMPROVEMENT UNDERWAY -- UNCONFIRMED",
        "recovery_confirmed_watch_sustainability":
            "RECOVERY CONFIRMED -- WATCH SUSTAINABILITY",
        "sustainable_growth": "SUSTAINABLE GROWTH",
    }
    label = verdict_labels.get(verdict, verdict.upper())
    parts = [f"Verdict: {label}"]
    if wage is not None:
        parts.append(f"real wages {wage:+.1f}% YoY")
    if fbcf is not None:
        parts.append(f"FBCF {fbcf:+.1f}% YoY")
    if cpi is not None:
        parts.append(f"CPI {cpi:.1f}%/month")
    if reserves is not None:
        label = "net reserves (est.)" if net is not None else "gross reserves"
        parts.append(f"{label} ${reserves:.1f}B")
    return "; ".join(parts) + "."


def _empty() -> dict:
    return {
        "domain": "master",
        "verdict": "structural_improvement_underway_unconfirmed",
        "as_of_date": None,
        "data_quality": "poor",
        "missing_domains": list(DOMAIN_FILES.keys()),
        "master_variable": {},
        "drivers": {},
        "enablers": {},
        "accelerators": {},
        "scorecard": {},
        "flags": ["CRITICAL: No domain signals available — run pipeline first"],
        "summary": "Insufficient data for master verdict.",
    }


def _save(data: dict) -> None:
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info("Saved: %s", OUT_FILE)
