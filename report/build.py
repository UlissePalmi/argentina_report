"""
Report assembler — combines all module sections into PDF and markdown.

This file owns:
  - ArgentinaPDF class (fpdf2 subclass)
  - _safe() latin-1 sanitiser
  - build_executive_summary_section() — reads signals_master.json, renders verdict + scorecard
  - build_report() — calls each module's section builder in order
"""

import json
from datetime import date
from pathlib import Path

import pandas as pd
from fpdf import FPDF, XPos, YPos

from utils import REPORTS_DIR, SIGNALS_DIR, get_logger
from external.section              import build_pdf_section as ext_pdf,  build_md_section as ext_md
from sections.inflation.section    import build_pdf_section as inf_pdf,  build_md_section as inf_md
from sections.fiscal.section       import build_pdf_section as fis_pdf,  build_md_section as fis_md
from sections.gdp.section          import build_pdf_section as gdp_pdf,  build_md_section as gdp_md
from sections.production.section   import build_pdf_section as pro_pdf,  build_md_section as pro_md
from sections.consumption.section  import build_pdf_section as con_pdf,  build_md_section as con_md
from sections.labor.section        import build_pdf_section as lab_pdf,  build_md_section as lab_md
from sections.debt.section         import build_pdf_section as dbt_pdf,  build_md_section as dbt_md
from svar.section                  import build_pdf_section as svar_pdf, build_md_section as svar_md

log = get_logger("report.build")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe(text: str) -> str:
    """Replace characters outside Latin-1 with safe ASCII equivalents."""
    return (text
            .replace("\u2014", "--")
            .replace("\u2013", "-")
            .replace("\u2019", "'")
            .replace("\u2018", "'")
            .replace("\u201c", '"')
            .replace("\u201d", '"')
            .replace("\u2192", "->")
            .replace("\u2022", "*")
            .encode("latin-1", errors="replace").decode("latin-1"))


# ---------------------------------------------------------------------------
# Executive summary helpers
# ---------------------------------------------------------------------------

VERDICT_DISPLAY = {
    "crisis_risk":
        ("CRISIS RISK", (192, 57, 43), (255, 255, 255)),
    "fragile_recovery":
        ("FRAGILE RECOVERY", (211, 84, 0), (255, 255, 255)),
    "structural_improvement_underway_unconfirmed":
        ("STRUCTURAL IMPROVEMENT UNDERWAY -- UNCONFIRMED", (25, 113, 194), (255, 255, 255)),
    "recovery_confirmed_watch_sustainability":
        ("RECOVERY CONFIRMED -- WATCH SUSTAINABILITY", (39, 174, 96), (255, 255, 255)),
    "sustainable_growth":
        ("SUSTAINABLE GROWTH", (27, 94, 32), (255, 255, 255)),
}

SIGNAL_COLORS = {
    "green":  (39, 174, 96),
    "yellow": (230, 126, 34),
    "red":    (192, 57, 43),
    "grey":   (160, 160, 160),
}


def _load_master_signal() -> dict | None:
    path = SIGNALS_DIR / "signals_master.json"
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def build_executive_summary_section(pdf: "ArgentinaPDF") -> str:
    """
    Render the executive summary page into the PDF.
    Returns the markdown equivalent string.
    """
    master = _load_master_signal()
    if master is None:
        pdf.section_title("1. Executive Summary")
        pdf.body_text("Signal data unavailable -- run main.py to generate signals.")
        return "## 1. Executive Summary\n\nSignal data unavailable.\n"

    verdict_key  = master.get("verdict", "structural_improvement_underway_unconfirmed")
    label, bg, fg = VERDICT_DISPLAY.get(verdict_key, VERDICT_DISPLAY["structural_improvement_underway_unconfirmed"])
    as_of        = master.get("as_of_date", "")
    scorecard    = master.get("scorecard", {})
    mv           = master.get("master_variable", {})
    enablers     = master.get("enablers", {})
    drivers      = master.get("drivers", {})
    accelerators = master.get("accelerators", {})

    # ------------------------------------------------------------------
    # Section heading
    # ------------------------------------------------------------------
    pdf.section_title("1. Executive Summary")

    # ------------------------------------------------------------------
    # Verdict banner — full-width colored box
    # ------------------------------------------------------------------
    avail_w = pdf.PAGE_W - 2 * pdf.MARGIN
    banner_h = 14

    pdf.set_fill_color(*bg)
    pdf.set_text_color(*fg)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(avail_w, banner_h, _safe(label), border=0, fill=True, align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)

    if as_of:
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(avail_w, 5, f"As of {as_of}", align="C",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)
    pdf.set_text_color(0, 0, 0)

    # ------------------------------------------------------------------
    # Traffic light scorecard table
    # ------------------------------------------------------------------
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 6, "Key Metrics Scorecard", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)

    col_widths = [avail_w * 0.42, avail_w * 0.18, avail_w * 0.12, avail_w * 0.28]
    headers    = ["Metric", "Value", "Signal", "Threshold"]

    # Table header
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_fill_color(30, 100, 200)
    pdf.set_text_color(255, 255, 255)
    for h, w in zip(headers, col_widths):
        pdf.cell(w, 6, h, border=0, fill=True, align="C")
    pdf.ln()

    # Table rows
    pdf.set_font("Helvetica", "", 8.5)
    for i, (metric_name, item) in enumerate(scorecard.items()):
        value_raw  = item.get("value")
        signal_key = item.get("signal", "grey")
        green_lbl  = item.get("green", "")
        note       = item.get("note", "")

        # Format value
        if value_raw is None:
            value_str = "n/a"
        elif isinstance(value_raw, float):
            value_str = f"{value_raw:+.1f}%" if abs(value_raw) < 1000 else f"${value_raw:.1f}B"
            # Reserves and CA are dollar values, not percentages
            if "Reserve" in metric_name or "Account" in metric_name:
                value_str = f"${value_raw:.1f}B" if value_raw is not None else "n/a"
        else:
            value_str = str(value_raw)

        # Threshold label: combine green + note
        threshold = green_lbl
        if note:
            threshold = note[:35]  # truncate to fit

        signal_rgb = SIGNAL_COLORS.get(signal_key, SIGNAL_COLORS["grey"])
        row_bg     = (248, 248, 248) if i % 2 == 0 else (255, 255, 255)

        pdf.set_fill_color(*row_bg)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(col_widths[0], 5.5, _safe(metric_name), border=0, fill=True, align="L")
        pdf.cell(col_widths[1], 5.5, _safe(value_str),   border=0, fill=True, align="C")

        # Signal cell — colored background
        pdf.set_fill_color(*signal_rgb)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(col_widths[2], 5.5, signal_key.upper(), border=0, fill=True, align="C")

        pdf.set_fill_color(*row_bg)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(col_widths[3], 5.5, _safe(threshold), border=0, fill=True, align="L")
        pdf.ln()

    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.MARGIN, pdf.get_y(), pdf.PAGE_W - pdf.MARGIN, pdf.get_y())
    pdf.ln(5)
    pdf.set_text_color(0, 0, 0)

    # ------------------------------------------------------------------
    # Four-level snapshot
    # ------------------------------------------------------------------
    _render_level_row(pdf, "MASTER VARIABLE",
                      f"Real wages {_fmt_pct(mv.get('value'))} YoY "
                      f"({mv.get('consecutive_positive_months', 0)} consecutive positive months). "
                      f"Productivity-backed: {mv.get('backed_by_productivity', 'unknown')}.",
                      "green" if (mv.get("value") or 0) > 0 else "red")

    _render_level_row(pdf, "DRIVERS",
                      f"FBCF {_fmt_pct(drivers.get('investment_fbcf_yoy'))} YoY. "
                      f"Formal employment {_fmt_pct(drivers.get('formal_employment_yoy'))} YoY. "
                      f"Credit discipline: {drivers.get('credit_discipline', 'unknown')}.",
                      "green" if (drivers.get("investment_fbcf_yoy") or 0) > 0 else "yellow")

    _net = enablers.get("net_reserves_bn")
    _gross = enablers.get("gross_reserves_bn")
    _res_str = (f"Net reserves (est.) ${_net:.1f}B" if _net is not None
                else f"Gross reserves ${_gross or 0:.1f}B")
    _fiscal = enablers.get("fiscal_balance_pct_gdp")
    _fiscal_str = f"  Fiscal {_fiscal:+.1f}% GDP." if _fiscal is not None else ""
    _render_level_row(pdf, "ENABLERS",
                      f"CPI {_fmt_pct(enablers.get('inflation_mom_latest'))} /month. "
                      f"Disinflation confirmed: {enablers.get('disinflation_confirmed', 'unknown')}. "
                      f"{_res_str} ({enablers.get('reserves_trend', 'unknown')}).{_fiscal_str}",
                      "green" if enablers.get("disinflation_confirmed") else "yellow")

    _render_level_row(pdf, "ACCELERATORS",
                      f"Oil {_fmt_pct(accelerators.get('oil_yoy'))} YoY. "
                      f"Vaca Muerta: {accelerators.get('vaca_muerta_signal', 'unknown')}.",
                      "green" if (accelerators.get("oil_yoy") or 0) > 5 else "yellow")

    pdf.ln(3)

    # ------------------------------------------------------------------
    # Markdown equivalent
    # ------------------------------------------------------------------
    md = _build_exec_summary_md(label, as_of, scorecard, mv, drivers, enablers, accelerators)
    return md


def _render_level_row(pdf: "ArgentinaPDF", level: str, text: str, signal: str):
    """Render a single four-level framework row with a colored left indicator."""
    avail_w   = pdf.PAGE_W - 2 * pdf.MARGIN
    dot_w     = 3
    label_w   = avail_w * 0.22
    text_w    = avail_w - dot_w - label_w
    row_h     = 7

    color = SIGNAL_COLORS.get(signal, SIGNAL_COLORS["grey"])
    pdf.set_fill_color(*color)
    pdf.cell(dot_w, row_h, "", border=0, fill=True)

    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(label_w, row_h, level, border=0, fill=False, align="L")

    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(60, 60, 60)
    pdf.multi_cell(text_w, row_h, _safe(text), border=0, align="L")
    pdf.ln(1)


def _fmt_pct(v) -> str:
    if v is None:
        return "n/a"
    return f"{v:+.1f}%"


def build_closing_synthesis(pdf: "ArgentinaPDF") -> str:
    """
    Generate the closing synthesis section from signals_master.json.

    Structure (per SKILL_master.md):
      Para 1 — Reconnect all sections to the master variable
      Para 2 — 3 specific data points to watch (with upgrade / downgrade conditions)
      Para 3 — Bull case
      Para 4 — Bear case

    Returns the markdown equivalent.
    """
    master = _load_master_signal()
    if not master:
        pdf.section_title("Closing Synthesis")
        pdf.body_text("Signal data unavailable -- run main.py first.")
        return "## Closing Synthesis\n\nSignal data unavailable.\n"

    verdict     = master.get("verdict", "structural_improvement_underway_unconfirmed")
    mv          = master.get("master_variable", {})
    drivers     = master.get("drivers", {})
    enablers    = master.get("enablers", {})
    accelerators = master.get("accelerators", {})
    flags       = master.get("flags", [])
    as_of       = master.get("as_of_date", "")

    # Convenience accessors
    real_wage      = mv.get("value")
    consec         = mv.get("consecutive_positive_months", 0)
    fbcf_yoy       = drivers.get("investment_fbcf_yoy")
    invest_trend   = drivers.get("investment_trend", "unknown")
    emp_yoy        = drivers.get("formal_employment_yoy")
    cred_disc      = drivers.get("credit_discipline", "unknown")
    cpi_mom        = enablers.get("inflation_mom_latest")
    disinfl        = enablers.get("disinflation_confirmed", False)
    net_reserves   = enablers.get("net_reserves_bn")
    reserves       = net_reserves if net_reserves is not None else enablers.get("gross_reserves_bn")
    res_trend      = enablers.get("reserves_trend", "unknown")
    ca             = enablers.get("current_account_bn")
    fiscal         = enablers.get("fiscal_balance_pct_gdp")
    oil_yoy        = accelerators.get("oil_yoy")
    vaca_muerta    = accelerators.get("vaca_muerta_signal", "unknown")

    # ------------------------------------------------------------------
    # Para 1 — Reconnect all sections to the master variable
    # ------------------------------------------------------------------
    p1 = _synthesis_reconnect(real_wage, consec, cpi_mom, disinfl,
                              reserves, res_trend, ca, fbcf_yoy, invest_trend,
                              emp_yoy, cred_disc, oil_yoy, vaca_muerta, verdict)

    # ------------------------------------------------------------------
    # Para 2 — 3 things to watch
    # ------------------------------------------------------------------
    watch_items = _determine_watch_items(master)

    # ------------------------------------------------------------------
    # Bull / Bear cases
    # ------------------------------------------------------------------
    bull = _bull_case(real_wage, fbcf_yoy, invest_trend, cpi_mom, disinfl,
                     reserves, res_trend, ca, oil_yoy, vaca_muerta)
    bear = _bear_case(real_wage, fbcf_yoy, cpi_mom, flags, cred_disc,
                     res_trend, emp_yoy)

    # ------------------------------------------------------------------
    # Render to PDF
    # ------------------------------------------------------------------
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
        pdf.set_text_color(60, 60, 60)
        pdf.set_x(pdf.l_margin + 4)
        pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin - 4, 5,
                       _safe(f"Why: {why}"))
        pdf.set_text_color(30, 120, 60)
        pdf.set_x(pdf.l_margin + 4)
        pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin - 4, 5,
                       _safe(f"Upgrade: {upgrade}"))
        pdf.set_text_color(160, 40, 40)
        pdf.set_x(pdf.l_margin + 4)
        pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin - 4, 5,
                       _safe(f"Downgrade: {downgrade}"))
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    # Bull / Bear — two columns side by side
    pdf.ln(2)
    avail_w = pdf.w - pdf.l_margin - pdf.r_margin
    col_w   = avail_w / 2 - 2
    y_start = pdf.get_y()

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
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_xy(x, pdf.get_y())
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(40, 40, 40)
        pdf.set_fill_color(245, 250, 245) if title == "BULL CASE" else pdf.set_fill_color(255, 245, 245)
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

    # ------------------------------------------------------------------
    # Markdown
    # ------------------------------------------------------------------
    return _closing_synthesis_md(p1, watch_items, bull, bear, verdict, as_of)


# ---------------------------------------------------------------------------
# Closing synthesis helpers
# ---------------------------------------------------------------------------

def _synthesis_reconnect(real_wage, consec, cpi_mom, disinfl,
                         reserves, res_trend, ca, fbcf_yoy, invest_trend,
                         emp_yoy, cred_disc, oil_yoy, vaca_muerta, verdict) -> str:
    """
    One synthesizing paragraph threading all domains back to the master variable.
    """
    parts = []

    # Inflation → wages link
    if cpi_mom is not None:
        if cpi_mom < 3:
            parts.append(
                f"Inflation has fallen to {cpi_mom:.1f}%/month -- the primary enabler is largely "
                f"in place, removing the monthly erosion that was suppressing real wages."
            )
        else:
            parts.append(
                f"Inflation at {cpi_mom:.1f}%/month is still the binding constraint on wage recovery."
            )

    # External → stability link
    if reserves is not None and ca is not None:
        if (ca or 0) > 0 and res_trend == "improving":
            parts.append(
                f"The external position is supportive: a current account surplus of "
                f"${ca:.1f}B/quarter and gross reserves of ${reserves:.0f}B are accumulating -- "
                f"the devaluation risk that historically wiped out wage gains is not present."
            )
        else:
            parts.append(
                f"External fragility remains a constraint: reserves at ${reserves:.0f}B "
                f"and a current account in {'surplus' if (ca or 0) > 0 else 'deficit'} "
                f"define the ceiling on how aggressively the BCRA can support wages."
            )

    # Investment → future capacity
    if fbcf_yoy is not None:
        if fbcf_yoy < 0 and invest_trend == "improving":
            parts.append(
                f"Fixed investment is still contracting ({fbcf_yoy:+.1f}% YoY) but the trend "
                f"is improving -- the capital base required for productivity-backed wage growth "
                f"is forming, not yet arrived."
            )
        elif fbcf_yoy > 0:
            parts.append(
                f"Fixed investment grew {fbcf_yoy:+.1f}% YoY, adding to the productive "
                f"capacity that will support sustainable wages in 2-4 quarters."
            )

    # Consumption → credit-led warning
    if cred_disc in ("elevated", "warning"):
        parts.append(
            f"The consumption data points to a structural risk: households are borrowing "
            f"to consume (credit discipline: {cred_disc}) -- a pattern that indicates the "
            f"recovery has not yet reached wages and that credit is bridging the gap."
        )

    # Vaca Muerta → structural dollar
    if vaca_muerta in ("strong", "growing") and oil_yoy is not None:
        parts.append(
            f"The structural case rests on Vaca Muerta: oil production at {oil_yoy:+.1f}% YoY "
            f"signals that Argentina may finally have a permanent dollar solution, removing "
            f"the external constraint that has ended every prior recovery cycle."
        )

    # Master variable verdict
    if real_wage is not None and real_wage < 0:
        parts.append(
            f"The master variable -- real wages -- remains negative at {real_wage:+.1f}% YoY. "
            f"All the conditions are forming. The proof is still ahead of us."
        )
    elif real_wage is not None and consec >= 9:
        parts.append(
            f"The master variable has turned: real wages positive for {consec} consecutive months, "
            f"backed by the productivity and stability conditions now in place."
        )
    elif real_wage is not None and real_wage > 0:
        parts.append(
            f"The master variable has turned positive ({real_wage:+.1f}% YoY) but {consec} "
            f"consecutive positive month(s) is not yet the 9-month threshold for confirmed recovery."
        )

    return " ".join(parts)


def _determine_watch_items(master: dict) -> list:
    """Return exactly 3 (metric, why, upgrade, downgrade) tuples."""
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

    # 1. Always: master variable if negative or not yet confirmed
    if real_wage <= 0 or mv.get("consecutive_positive_months", 0) < 9:
        items.append((
            "Real wages -- first 3 consecutive positive months",
            "This is the master variable. All other signals exist to predict when this turns.",
            "Upgrade to RECOVERY CONFIRMED once positive for 3 consecutive months backed by "
            "productivity (IPI growing, credit-wage spread below 20pp).",
            "Downgrade if wages remain negative through Q2 2026 -- signals the credit cycle "
            "peaked before wages recovered, risking a consumption cliff.",
        ))

    # 2. FBCF if negative but improving
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

    # 3. Inflation structural confirmation if above 2%
    if cpi_mom > 2 and not disinfl:
        items.append((
            "Monthly CPI -- structural disinflation confirmed (below 2.5% for 3 months)",
            f"CPI at {cpi_mom:.1f}%/month is close but not yet confirmed structural. "
            "Disinflation is the prerequisite for any real wage recovery.",
            "Upgrade signal if CPI holds below 2.5% for 3 consecutive months -- "
            "structural disinflation confirmed, wage recovery mathematically easier.",
            "Downgrade if CPI re-accelerates above 4% -- real wages cannot recover "
            "while inflation re-ignites, and the BCRA faces a rate/FX dilemma.",
        ))

    # 4. FX / trade (fallback if list not full yet)
    fx_warning = any("real appreciation" in f.lower() or "FX depreciated" in f for f in flags)
    if fx_warning and len(items) < 3:
        items.append((
            "Trade surplus -- holding above $1B/month despite import normalization",
            "Real FX appreciation is making imports cheaper and exports less competitive. "
            "The 2024 $19B goods surplus will compress unless the crawl pace adjusts.",
            "Upgrade if monthly trade surplus holds above $1.5B -- reserves keep accumulating "
            "and the external constraint stays removed.",
            "Downgrade if monthly surplus falls below $0.5B consistently -- reserve "
            "accumulation stalls, crawling peg becomes unsustainable, devaluation risk returns.",
        ))

    # 5. Credit-wage spread (fallback)
    if cred_disc in ("elevated", "warning") and len(items) < 3:
        items.append((
            "Consumer credit growth -- decelerating toward wage growth",
            "A 49.7pp credit-wage spread means households are borrowing to sustain consumption. "
            "Sustainable only if wages catch up before credit quality deteriorates.",
            "Upgrade signal if real consumer credit decelerates below 25% YoY "
            "as wages recover -- transition from credit-led to wage-led confirmed.",
            "Downgrade if credit growth peaks and defaults rise before wages recover -- "
            "consumption cliff materializes as households deleverage.",
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

    if oil_yoy is not None and (vaca_muerta in ("strong", "growing")):
        parts.append(f"Vaca Muerta oil at {oil_yoy:+.1f}% YoY provides a structural "
                     f"dollar inflow that prior cycles never had -- the external constraint "
                     f"may be permanently lifted.")

    parts.append("If these hold, real wages turn positive in Q1-Q2 2026, investment "
                 "follows in H2 2026, and the verdict upgrades to RECOVERY CONFIRMED "
                 "within two quarters.")

    return " ".join(parts)


def _bear_case(real_wage, fbcf_yoy, cpi_mom, flags, cred_disc, res_trend, emp_yoy) -> str:
    parts = []

    fx_flag = next((f for f in flags if "real appreciation" in f.lower()), None)
    if fx_flag:
        parts.append("Real FX appreciation is the primary risk: if inflation stays at 2.9%/month "
                     "while the crawl slows further, imports become cheap and exports uncompetitive "
                     "-- the 2024 trade surplus compresses and reserves stop accumulating.")

    if cred_disc in ("elevated", "warning"):
        parts.append("The credit-wage spread of 49.7pp is unsustainable: households are borrowing "
                     "to consume ahead of wage recovery. If wages don't turn positive within "
                     "2-3 quarters, debt servicing pressure triggers a consumption cliff.")

    if (emp_yoy or 0) < 0:
        parts.append("Formal employment is contracting -- if this continues, the wage bill "
                     "shrinks even if individual wages recover, limiting aggregate demand.")

    parts.append("In this scenario, a combination of FX adjustment and credit cycle turn "
                 "triggers a consumption shock before the productive investment cycle matures -- "
                 "the verdict downgrades to FRAGILE RECOVERY and the stabilization "
                 "cycle repeats.")

    return " ".join(parts)


def _closing_synthesis_md(p1, watch_items, bull, bear, verdict, as_of) -> str:
    lines = ["## Closing Synthesis", ""]
    lines.append("### The central question revisited")
    lines.append(p1)
    lines.append("")

    lines.append("### Three things to watch in the next two quarters")
    lines.append("")
    for i, (metric, why, upgrade, downgrade) in enumerate(watch_items, 1):
        lines.append(f"**{i}. {metric}**")
        lines.append(f"- Why: {why}")
        lines.append(f"- Upgrade: {upgrade}")
        lines.append(f"- Downgrade: {downgrade}")
        lines.append("")

    lines.append("### Bull case")
    lines.append(bull)
    lines.append("")
    lines.append("### Bear case")
    lines.append(bear)
    lines.append("")
    if as_of:
        lines.append(f"*Analysis as of {as_of}. Verdict: {verdict.replace('_', ' ').upper()}.*")

    return "\n".join(lines)


def _build_exec_summary_md(label, as_of, scorecard, mv, drivers, enablers, accelerators) -> str:
    lines = ["## 1. Executive Summary", ""]
    lines.append(f"### Verdict: {label}")
    if as_of:
        lines.append(f"*As of {as_of}*")
    lines.append("")

    # Scorecard table
    lines.append("| Metric | Value | Signal | Target |")
    lines.append("|---|---|---|---|")
    for metric, item in scorecard.items():
        v = item.get("value")
        val_str = "n/a"
        if v is not None:
            if "Reserve" in metric or "Account" in metric:
                val_str = f"${v:.1f}B"
            else:
                val_str = f"{v:+.1f}%"
        sig = item.get("signal", "grey").upper()
        tgt = item.get("green", "")
        lines.append(f"| {metric} | {val_str} | {sig} | {tgt} |")
    lines.append("")

    # Four-level snapshot
    lines.append("### Framework Assessment")
    lines.append(f"- **MASTER VARIABLE**: Real wages {_fmt_pct(mv.get('value'))} YoY "
                 f"({mv.get('consecutive_positive_months', 0)} consecutive positive months)")
    lines.append(f"- **DRIVERS**: FBCF {_fmt_pct(drivers.get('investment_fbcf_yoy'))} YoY | "
                 f"Employment {_fmt_pct(drivers.get('formal_employment_yoy'))} YoY | "
                 f"Credit discipline: {drivers.get('credit_discipline', 'unknown')}")
    _en_net   = enablers.get("net_reserves_bn")
    _en_gross = enablers.get("gross_reserves_bn")
    _en_res   = f"Net res. (est.) ${_en_net:.1f}B" if _en_net is not None else f"Gross res. ${_en_gross or 0:.1f}B"
    _en_fisc  = enablers.get("fiscal_balance_pct_gdp")
    _en_fisc_s = f" | Fiscal {_en_fisc:+.1f}% GDP" if _en_fisc is not None else ""
    lines.append(f"- **ENABLERS**: CPI {_fmt_pct(enablers.get('inflation_mom_latest'))}/month | "
                 f"Disinflation confirmed: {enablers.get('disinflation_confirmed')} | "
                 f"{_en_res}{_en_fisc_s}")
    lines.append(f"- **ACCELERATORS**: Oil {_fmt_pct(accelerators.get('oil_yoy'))} YoY | "
                 f"Vaca Muerta: {accelerators.get('vaca_muerta_signal', 'unknown')}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# PDF class
# ---------------------------------------------------------------------------
class ArgentinaPDF(FPDF):
    MARGIN = 15
    PAGE_W = 210

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(130, 130, 130)
        self.cell(0, 8, "Argentina Macro Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")
        self.set_draw_color(200, 200, 200)
        self.line(self.MARGIN, self.get_y(), self.PAGE_W - self.MARGIN, self.get_y())
        self.ln(2)

    def footer(self):
        self.set_y(-13)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def section_title(self, text: str):
        self.ln(4)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(20, 80, 160)
        self.cell(0, 8, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(20, 80, 160)
        self.line(self.MARGIN, self.get_y(), self.PAGE_W - self.MARGIN, self.get_y())
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def body_text(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5.5, _safe(text))
        self.ln(2)

    def add_chart(self, img_path: str | None, caption: str = ""):
        if not img_path or not Path(img_path).exists():
            self.body_text("[Chart unavailable]")
            return
        avail_w = self.PAGE_W - 2 * self.MARGIN
        img_h = avail_w * 0.45
        if self.get_y() + img_h + 10 > self.h - 20:
            self.add_page()
        self.image(img_path, x=self.MARGIN, w=avail_w)
        if caption:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(100, 100, 100)
            self.cell(0, 5, caption, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
            self.set_text_color(0, 0, 0)
        self.ln(3)

    def add_table(self, df: pd.DataFrame, cols: list[str], fmt: dict | None = None,
                  title: str = ""):
        fmt = fmt or {}
        subset = df[cols].dropna().tail(12).reset_index(drop=True)
        if subset.empty:
            return
        if title:
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(60, 60, 60)
            self.cell(0, 6, _safe(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(1)
        avail_w = self.PAGE_W - 2 * self.MARGIN
        col_w = avail_w / len(cols)
        # Header
        self.set_font("Helvetica", "B", 8.5)
        self.set_fill_color(30, 100, 200)
        self.set_text_color(255, 255, 255)
        for c in cols:
            label = c.replace("_", " ").replace("usd bn", "(USD bn)").replace("pct", "%").title()
            self.cell(col_w, 6, label, border=0, fill=True, align="C")
        self.ln()
        # Rows
        self.set_font("Helvetica", "", 8.5)
        for i, (_, row) in enumerate(subset.iterrows()):
            bg = (240, 247, 255) if i % 2 == 0 else (255, 255, 255)
            self.set_fill_color(*bg)
            self.set_text_color(40, 40, 40)
            for c in cols:
                v = row[c]
                if c == "date" or (hasattr(v, "strftime")):
                    try:    cell_str = pd.to_datetime(v).strftime("%Y-%m-%d")
                    except: cell_str = str(v).split(" ")[0]
                else:
                    f = fmt.get(c, "{}")
                    try:    cell_str = f.format(v)
                    except: cell_str = str(v)
                self.cell(col_w, 5.5, _safe(cell_str), border=0, fill=True, align="C")
            self.ln()
        self.set_draw_color(200, 200, 200)
        self.line(self.MARGIN, self.get_y(), self.PAGE_W - self.MARGIN, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def add_table_n(self, df: pd.DataFrame, cols: list[str],
                    fmt: dict | None = None, title: str = "", limit: int = 24):
        """Like add_table but shows up to `limit` rows."""
        fmt = fmt or {}
        subset = df[cols].dropna(how="all").tail(limit).reset_index(drop=True)
        if subset.empty:
            return
        if title:
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(60, 60, 60)
            self.cell(0, 6, _safe(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(1)
        avail_w = self.PAGE_W - 2 * self.MARGIN
        col_w = avail_w / len(cols)
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(30, 100, 200)
        self.set_text_color(255, 255, 255)
        for c in cols:
            label = (c.replace("_", " ").replace("usd bn", "(USD bn)")
                      .replace("pct", "%").replace("yoy", "YoY").title())
            self.cell(col_w, 6, _safe(label), border=0, fill=True, align="C")
        self.ln()
        self.set_font("Helvetica", "", 8)
        for i, (_, row) in enumerate(subset.iterrows()):
            bg = (240, 247, 255) if i % 2 == 0 else (255, 255, 255)
            self.set_fill_color(*bg)
            self.set_text_color(40, 40, 40)
            for c in cols:
                v = row[c]
                if c == "date" or hasattr(v, "strftime"):
                    try:    cell_str = pd.to_datetime(v).strftime("%b %Y")
                    except: cell_str = str(v).split(" ")[0]
                else:
                    f = fmt.get(c, "{}")
                    try:    cell_str = f.format(v)
                    except: cell_str = str(v)
                if c != "date":
                    try:
                        num = float(v)
                        self.set_text_color(0, 110, 50) if num > 0 else \
                            (self.set_text_color(180, 0, 0) if num < 0 else
                             self.set_text_color(80, 80, 80))
                    except (TypeError, ValueError):
                        self.set_text_color(40, 40, 40)
                self.cell(col_w, 5.5, _safe(cell_str), border=0, fill=True, align="C")
                self.set_text_color(40, 40, 40)
            self.ln()
        self.set_draw_color(200, 200, 200)
        self.line(self.MARGIN, self.get_y(), self.PAGE_W - self.MARGIN, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def subsection(self, text: str):
        self.ln(3)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(60, 60, 140)
        self.cell(0, 7, _safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.ln(1)

    def note(self, text: str):
        """Small italic footnote."""
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(110, 110, 110)
        self.set_x(self.l_margin)
        self.multi_cell(self.w - self.l_margin - self.r_margin, 4.5, _safe(text))
        self.set_text_color(0, 0, 0)
        self.ln(2)


# ---------------------------------------------------------------------------
# Main assembler
# ---------------------------------------------------------------------------
def build_report(
    external_data: dict,
    inflation_data: dict,
    gdp_data: dict,
    consumption_data: dict,
    labor_data: dict | None = None,
    production_data: dict | None = None,
    fiscal_data: dict | None = None,
    debt_data: dict | None = None,
) -> dict[str, Path]:
    """
    Assemble the full Argentina Macro Report.

    Each *_data dict contains the DataFrames for that module, e.g.:
        external_data    = {"trade_df": ..., "reserves_df": ..., "ca_df": ...}
        inflation_data   = {"cpi_df": ...}
        gdp_data         = {"gdp_df": ..., "components_df": ..., "emae_df": ...}
        consumption_data = {"consumption_df": ...}
        labor_data       = {"consumption_df": ..., "employment_df": ...}
        production_data  = {"production_df": ..., "agro_df": ...}

    Returns dict with keys 'pdf' and 'md'.
    """
    labor_data      = labor_data or {}
    production_data = production_data or {}
    fiscal_data     = fiscal_data or {}
    debt_data       = debt_data or {}

    today = date.today().strftime("%B %d, %Y")

    # =========================================================
    # PDF
    # =========================================================
    pdf = ArgentinaPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # Title block
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(20, 80, 160)
    pdf.cell(0, 12, "Argentina Macro Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 7, f"Generated {today}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_draw_color(20, 80, 160)
    pdf.set_line_width(0.5)
    pdf.line(15, pdf.get_y() + 2, 195, pdf.get_y() + 2)
    pdf.ln(8)

    exec_summary_md = build_executive_summary_section(pdf)

    ext_pdf(pdf, external_data)
    inf_pdf(pdf, inflation_data)
    fis_pdf(pdf, fiscal_data)
    dbt_pdf(pdf, debt_data)
    gdp_pdf(pdf, gdp_data)
    pro_pdf(pdf, production_data)
    lab_pdf(pdf, labor_data)
    con_pdf(pdf, consumption_data)
    svar_pdf(pdf, {})

    closing_md = build_closing_synthesis(pdf)
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin, 4.5, _safe(
        "Data sources: BCRA / Argentina Open Data API (apis.datos.gob.ar), "
        "World Bank (api.worldbank.org), IMF BOP (dataservices.imf.org -- fallback to WB when unavailable)."
    ))

    pdf_path = REPORTS_DIR / "argentina_macro_report.pdf"
    pdf.output(str(pdf_path))
    log.info("PDF written → %s", pdf_path)

    # =========================================================
    # Markdown
    # =========================================================
    ext_section = ext_md(external_data)
    inf_section = inf_md(inflation_data)
    fis_section = fis_md(fiscal_data)
    dbt_section = dbt_md(debt_data)
    gdp_section = gdp_md(gdp_data)
    pro_section = pro_md(production_data)
    lab_section = lab_md(labor_data)
    con_section  = con_md(consumption_data)
    svar_section = svar_md({})

    md = f"""# Argentina Macro Report
*Generated {today}*

---

{exec_summary_md}

---

{ext_section}

---

{inf_section}

---

{fis_section}

---

{dbt_section}

---

{gdp_section}

---

{pro_section}

---

{lab_section}

---

{con_section}

---

{svar_section}

---

{closing_md}

---
*Data sources: BCRA / Argentina Open Data API (apis.datos.gob.ar), World Bank (api.worldbank.org),
IMF BOP (dataservices.imf.org -- fallback to WB when unavailable).*
"""

    md_path = REPORTS_DIR / "argentina_macro_report.md"
    md_path.write_text(md, encoding="utf-8")
    log.info("Markdown written → %s", md_path)

    return {"md": md_path, "pdf": pdf_path}
