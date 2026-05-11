"""Closing synthesis section — reconnect, three things to watch, bull/bear cases."""

import json

from fpdf import XPos

from utils import SIGNALS_DIR
from .pdf_base import ArgentinaPDF, _safe
from .executive_summary import SIGNAL_COLORS, _fmt_pct


def _load_master_signal() -> dict | None:
    path = SIGNALS_DIR / "signals_master.json"
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def build_closing_synthesis(pdf: ArgentinaPDF) -> str:
    """Render the closing synthesis page. Returns markdown equivalent."""
    master = _load_master_signal()
    if not master:
        pdf.section_title("Closing Synthesis")
        pdf.body_text("Signal data unavailable -- run main.py first.")
        return "## Closing Synthesis\n\nSignal data unavailable.\n"

    verdict      = master.get("verdict", "structural_improvement_underway_unconfirmed")
    mv           = master.get("master_variable", {})
    drivers      = master.get("drivers", {})
    enablers     = master.get("enablers", {})
    accelerators = master.get("accelerators", {})
    flags        = master.get("flags", [])
    as_of        = master.get("as_of_date", "")

    real_wage    = mv.get("value")
    consec       = mv.get("consecutive_positive_months", 0)
    fbcf_yoy     = drivers.get("investment_fbcf_yoy")
    invest_trend = drivers.get("investment_trend", "unknown")
    emp_yoy      = drivers.get("formal_employment_yoy")
    cred_disc    = drivers.get("credit_discipline", "unknown")
    cpi_mom      = enablers.get("inflation_mom_latest")
    disinfl      = enablers.get("disinflation_confirmed", False)
    net_res      = enablers.get("net_reserves_bn")
    reserves     = net_res if net_res is not None else enablers.get("gross_reserves_bn")
    res_trend    = enablers.get("reserves_trend", "unknown")
    ca           = enablers.get("current_account_bn")
    oil_yoy      = accelerators.get("oil_yoy")
    vaca_muerta  = accelerators.get("vaca_muerta_signal", "unknown")

    p1          = _reconnect(real_wage, consec, cpi_mom, disinfl, reserves, res_trend,
                             ca, fbcf_yoy, invest_trend, emp_yoy, cred_disc, oil_yoy,
                             vaca_muerta, verdict)
    watch_items = _watch_items(master)
    bull        = _bull_case(real_wage, fbcf_yoy, invest_trend, cpi_mom, disinfl,
                             reserves, res_trend, ca, oil_yoy, vaca_muerta)
    bear        = _bear_case(real_wage, fbcf_yoy, cpi_mom, flags, cred_disc,
                             res_trend, emp_yoy)

    pdf.section_title("Closing Synthesis")

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(20, 80, 160)
    pdf.cell(0, 6, "The central question revisited", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.body_text(p1)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(20, 80, 160)
    pdf.cell(0, 6, "Three things to watch in the next two quarters",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1)
    for i, (metric, why, upgrade, downgrade) in enumerate(watch_items, 1):
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(40, 40, 40)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin, 5, _safe(f"{i}. {metric}"))
        pdf.set_font("Helvetica", "", 8.5)
        for label, color, text in [
            ("Why: ",       (60, 60, 60),   why),
            ("Upgrade: ",   (30, 120, 60),  upgrade),
            ("Downgrade: ", (160, 40, 40),  downgrade),
        ]:
            pdf.set_text_color(*color)
            pdf.set_x(pdf.l_margin + 4)
            pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin - 4, 5, _safe(label + text))
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    # Bull / Bear side by side
    pdf.ln(2)
    avail_w = pdf.w - pdf.l_margin - pdf.r_margin
    col_w   = avail_w / 2 - 2
    y_start = pdf.get_y()
    y_after_bull = y_start

    for title, text, bg, fg in [
        ("BULL CASE", bull, (39, 174, 96),  (255, 255, 255)),
        ("BEAR CASE", bear, (192, 57, 43),  (255, 255, 255)),
    ]:
        x = pdf.l_margin if title == "BULL CASE" else pdf.l_margin + col_w + 4
        pdf.set_xy(x, y_start)
        pdf.set_fill_color(*bg)
        pdf.set_text_color(*fg)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(col_w, 6, title, fill=True, align="C",
                 new_x=XPos.LMARGIN, new_y=XPos.LMARGIN)
        pdf.set_xy(x, pdf.get_y() + 6)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(40, 40, 40)
        if title == "BULL CASE":
            pdf.set_fill_color(245, 250, 245)
        else:
            pdf.set_fill_color(255, 245, 245)
        pdf.multi_cell(col_w, 4.5, _safe(text), fill=True)
        if title == "BULL CASE":
            y_after_bull = pdf.get_y()

    pdf.set_y(max(pdf.get_y(), y_after_bull) + 4)
    pdf.set_text_color(0, 0, 0)

    if as_of:
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(130, 130, 130)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin, 4.5,
                       _safe(f"Analysis as of {as_of}. Verdict: {verdict.replace('_', ' ').upper()}."))
        pdf.set_text_color(0, 0, 0)

    return _closing_md(p1, watch_items, bull, bear, verdict, as_of)


# ---------------------------------------------------------------------------
# Content generators
# ---------------------------------------------------------------------------

def _reconnect(real_wage, consec, cpi_mom, disinfl, reserves, res_trend,
               ca, fbcf_yoy, invest_trend, emp_yoy, cred_disc,
               oil_yoy, vaca_muerta, verdict) -> str:
    parts = []

    if cpi_mom is not None:
        if cpi_mom < 3:
            parts.append(f"Inflation has fallen to {cpi_mom:.1f}%/month -- the primary enabler "
                         f"is largely in place, removing the monthly erosion that was suppressing real wages.")
        else:
            parts.append(f"Inflation at {cpi_mom:.1f}%/month is still the binding constraint on wage recovery.")

    if reserves is not None and ca is not None:
        if (ca or 0) > 0 and res_trend == "improving":
            parts.append(f"The external position is supportive: a current account surplus of "
                         f"${ca:.1f}B/quarter and gross reserves of ${reserves:.0f}B are accumulating -- "
                         f"the devaluation risk that historically wiped out wage gains is not present.")
        else:
            parts.append(f"External fragility remains a constraint: reserves at ${reserves:.0f}B "
                         f"and a current account in {'surplus' if (ca or 0) > 0 else 'deficit'} "
                         f"define the ceiling on how aggressively the BCRA can support wages.")

    if fbcf_yoy is not None:
        if fbcf_yoy < 0 and invest_trend == "improving":
            parts.append(f"Fixed investment is still contracting ({fbcf_yoy:+.1f}% YoY) but the trend "
                         f"is improving -- the capital base required for productivity-backed wage growth "
                         f"is forming, not yet arrived.")
        elif fbcf_yoy > 0:
            parts.append(f"Fixed investment grew {fbcf_yoy:+.1f}% YoY, adding to the productive "
                         f"capacity that will support sustainable wages in 2-4 quarters.")

    if cred_disc in ("elevated", "warning"):
        parts.append(f"The consumption data points to a structural risk: households are borrowing "
                     f"to consume (credit discipline: {cred_disc}) -- a pattern that indicates the "
                     f"recovery has not yet reached wages and that credit is bridging the gap.")

    if vaca_muerta in ("strong", "growing") and oil_yoy is not None:
        parts.append(f"The structural case rests on Vaca Muerta: oil production at {oil_yoy:+.1f}% YoY "
                     f"signals that Argentina may finally have a permanent dollar solution, removing "
                     f"the external constraint that has ended every prior recovery cycle.")

    if real_wage is not None and real_wage < 0:
        parts.append(f"The master variable -- real wages -- remains negative at {real_wage:+.1f}% YoY. "
                     f"All the conditions are forming. The proof is still ahead of us.")
    elif real_wage is not None and consec >= 9:
        parts.append(f"The master variable has turned: real wages positive for {consec} consecutive months, "
                     f"backed by the productivity and stability conditions now in place.")
    elif real_wage is not None and real_wage > 0:
        parts.append(f"The master variable has turned positive ({real_wage:+.1f}% YoY) but {consec} "
                     f"consecutive positive month(s) is not yet the 9-month threshold for confirmed recovery.")

    return " ".join(parts)


def _watch_items(master: dict) -> list:
    mv        = master.get("master_variable", {})
    drivers   = master.get("drivers", {})
    enablers  = master.get("enablers", {})
    flags     = master.get("flags", [])

    real_wage    = mv.get("value") or 0
    fbcf_yoy     = drivers.get("investment_fbcf_yoy") or 0
    invest_trend = drivers.get("investment_trend", "")
    cpi_mom      = enablers.get("inflation_mom_latest") or 0
    disinfl      = enablers.get("disinflation_confirmed", False)
    cred_disc    = drivers.get("credit_discipline", "")

    items = []

    if real_wage <= 0 or mv.get("consecutive_positive_months", 0) < 9:
        items.append((
            "Real wages -- first 3 consecutive positive months",
            "This is the master variable. All other signals exist to predict when this turns.",
            "Upgrade to RECOVERY CONFIRMED once positive for 3 consecutive months backed by "
            "productivity (IPI growing, credit-wage spread below 20pp).",
            "Downgrade if wages remain negative through Q2 2026 -- signals the credit cycle "
            "peaked before wages recovered, risking a consumption cliff.",
        ))

    if fbcf_yoy < 0 and invest_trend == "improving":
        items.append((
            "Fixed investment (FBCF) -- first positive quarter",
            "Investment trend is improving despite negative YoY. This is the leading indicator "
            "of future productive capacity. No investment growth = no sustainable wage growth.",
            "Upgrade signal when FBCF turns positive for 2 consecutive quarters, particularly "
            "if led by domestic machinery (dollar-neutral) over imported equipment.",
            "Downgrade if investment turns sharply negative again -- signals business confidence "
            "collapse, removing the productivity foundation entirely.",
        ))

    if cpi_mom > 2 and not disinfl:
        items.append((
            "Monthly CPI -- structural disinflation confirmed (below 2.5% for 3 months)",
            f"CPI at {cpi_mom:.1f}%/month is close but not yet confirmed structural. "
            "Disinflation is the prerequisite for any real wage recovery.",
            "Upgrade signal if CPI holds below 2.5% for 3 consecutive months.",
            "Downgrade if CPI re-accelerates above 4%.",
        ))

    fx_warning = any("real appreciation" in f.lower() or "FX depreciated" in f for f in flags)
    if fx_warning and len(items) < 3:
        items.append((
            "Trade surplus -- holding above $1B/month despite import normalization",
            "Real FX appreciation is making imports cheaper and exports less competitive.",
            "Upgrade if monthly trade surplus holds above $1.5B.",
            "Downgrade if monthly surplus falls below $0.5B consistently.",
        ))

    if cred_disc in ("elevated", "warning") and len(items) < 3:
        items.append((
            "Consumer credit growth -- decelerating toward wage growth",
            "A credit-wage spread means households are borrowing to sustain consumption.",
            "Upgrade signal if real consumer credit decelerates below 25% YoY as wages recover.",
            "Downgrade if credit growth peaks and defaults rise before wages recover.",
        ))

    return items[:3]


def _bull_case(real_wage, fbcf_yoy, invest_trend, cpi_mom, disinfl,
               reserves, res_trend, ca, oil_yoy, vaca_muerta) -> str:
    parts = []
    if cpi_mom is not None and cpi_mom < 3:
        parts.append(f"Inflation has fallen to {cpi_mom:.1f}%/month after peaking at 25% -- "
                     f"the monetary stabilization is real and durable.")
    if reserves is not None and res_trend == "improving":
        parts.append(f"Gross reserves at ${reserves:.0f}B and growing remove the devaluation "
                     f"shock that ended every prior recovery.")
    if fbcf_yoy is not None and invest_trend == "improving":
        parts.append(f"Investment is bottoming -- FBCF trend is improving despite "
                     f"the negative YoY print, signaling business confidence is rebuilding.")
    if oil_yoy is not None and vaca_muerta in ("strong", "growing"):
        parts.append(f"Vaca Muerta oil at {oil_yoy:+.1f}% YoY provides a structural "
                     f"dollar inflow that prior cycles never had.")
    parts.append("If these hold, real wages turn positive in Q1-Q2 2026, investment "
                 "follows in H2 2026, and the verdict upgrades to RECOVERY CONFIRMED.")
    return " ".join(parts)


def _bear_case(real_wage, fbcf_yoy, cpi_mom, flags, cred_disc, res_trend, emp_yoy) -> str:
    parts = []
    fx_flag = next((f for f in flags if "real appreciation" in f.lower()), None)
    if fx_flag:
        parts.append("Real FX appreciation is the primary risk: if inflation stays elevated "
                     "while the crawl slows further, imports become cheap and exports uncompetitive "
                     "-- the 2024 trade surplus compresses and reserves stop accumulating.")
    if cred_disc in ("elevated", "warning"):
        parts.append("The credit-wage spread is unsustainable: households are borrowing "
                     "to consume ahead of wage recovery. If wages don't turn positive within "
                     "2-3 quarters, debt servicing pressure triggers a consumption cliff.")
    if (emp_yoy or 0) < 0:
        parts.append("Formal employment is contracting -- if this continues, the wage bill "
                     "shrinks even if individual wages recover, limiting aggregate demand.")
    parts.append("In this scenario, a combination of FX adjustment and credit cycle turn "
                 "triggers a consumption shock before the productive investment cycle matures.")
    return " ".join(parts)


def _closing_md(p1, watch_items, bull, bear, verdict, as_of) -> str:
    lines = ["## Closing Synthesis", "", "### The central question revisited", p1, ""]
    lines.append("### Three things to watch in the next two quarters")
    lines.append("")
    for i, (metric, why, upgrade, downgrade) in enumerate(watch_items, 1):
        lines += [
            f"**{i}. {metric}**",
            f"- Why: {why}",
            f"- Upgrade: {upgrade}",
            f"- Downgrade: {downgrade}",
            "",
        ]
    lines += ["### Bull case", bull, "", "### Bear case", bear, ""]
    if as_of:
        lines.append(f"*Analysis as of {as_of}. Verdict: {verdict.replace('_', ' ').upper()}.*")
    return "\n".join(lines)
