"""Executive summary section — verdict banner, scorecard table, four-level snapshot."""

import json
from pathlib import Path

from fpdf import XPos, YPos

from utils import SIGNALS_DIR
from .pdf_base import ArgentinaPDF, _safe

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


def _fmt_pct(v) -> str:
    if v is None:
        return "n/a"
    return f"{v:+.1f}%"


def _render_level_row(pdf: ArgentinaPDF, level: str, text: str, signal: str):
    avail_w = pdf.PAGE_W - 2 * pdf.MARGIN
    dot_w   = 3
    label_w = avail_w * 0.22
    text_w  = avail_w - dot_w - label_w
    row_h   = 7

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


def build_executive_summary_section(pdf: ArgentinaPDF) -> str:
    """Render the executive summary page. Returns markdown equivalent."""
    master = _load_master_signal()
    if master is None:
        pdf.section_title("1. Executive Summary")
        pdf.body_text("Signal data unavailable -- run main.py to generate signals.")
        return "## 1. Executive Summary\n\nSignal data unavailable.\n"

    verdict_key    = master.get("verdict", "structural_improvement_underway_unconfirmed")
    label, bg, fg  = VERDICT_DISPLAY.get(verdict_key, VERDICT_DISPLAY["structural_improvement_underway_unconfirmed"])
    as_of          = master.get("as_of_date", "")
    scorecard      = master.get("scorecard", {})
    mv             = master.get("master_variable", {})
    enablers       = master.get("enablers", {})
    drivers        = master.get("drivers", {})
    accelerators   = master.get("accelerators", {})

    pdf.section_title("1. Executive Summary")

    avail_w  = pdf.PAGE_W - 2 * pdf.MARGIN
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

    # Scorecard table
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 6, "Key Metrics Scorecard", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)

    col_widths = [avail_w * 0.42, avail_w * 0.18, avail_w * 0.12, avail_w * 0.28]
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_fill_color(30, 100, 200)
    pdf.set_text_color(255, 255, 255)
    for h, w in zip(["Metric", "Value", "Signal", "Threshold"], col_widths):
        pdf.cell(w, 6, h, border=0, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 8.5)
    for i, (metric_name, item) in enumerate(scorecard.items()):
        value_raw  = item.get("value")
        signal_key = item.get("signal", "grey")
        note       = item.get("note", "")
        green_lbl  = item.get("green", "")

        if value_raw is None:
            value_str = "n/a"
        elif isinstance(value_raw, float):
            if "Reserve" in metric_name or "Account" in metric_name:
                value_str = f"${value_raw:.1f}B"
            else:
                value_str = f"{value_raw:+.1f}%" if abs(value_raw) < 1000 else f"${value_raw:.1f}B"
        else:
            value_str = str(value_raw)

        threshold  = note[:35] if note else green_lbl
        signal_rgb = SIGNAL_COLORS.get(signal_key, SIGNAL_COLORS["grey"])
        row_bg     = (248, 248, 248) if i % 2 == 0 else (255, 255, 255)

        pdf.set_fill_color(*row_bg)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(col_widths[0], 5.5, _safe(metric_name), border=0, fill=True, align="L")
        pdf.cell(col_widths[1], 5.5, _safe(value_str),   border=0, fill=True, align="C")
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

    # Four-level snapshot
    _net   = enablers.get("net_reserves_bn")
    _gross = enablers.get("gross_reserves_bn")
    _res   = f"Net reserves (est.) ${_net:.1f}B" if _net is not None else f"Gross reserves ${_gross or 0:.1f}B"
    _fisc  = enablers.get("fiscal_balance_pct_gdp")
    _fisc_s = f"  Fiscal {_fisc:+.1f}% GDP." if _fisc is not None else ""

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

    _render_level_row(pdf, "ENABLERS",
                      f"CPI {_fmt_pct(enablers.get('inflation_mom_latest'))} /month. "
                      f"Disinflation confirmed: {enablers.get('disinflation_confirmed', 'unknown')}. "
                      f"{_res} ({enablers.get('reserves_trend', 'unknown')}).{_fisc_s}",
                      "green" if enablers.get("disinflation_confirmed") else "yellow")

    _render_level_row(pdf, "ACCELERATORS",
                      f"Oil {_fmt_pct(accelerators.get('oil_yoy'))} YoY. "
                      f"Vaca Muerta: {accelerators.get('vaca_muerta_signal', 'unknown')}.",
                      "green" if (accelerators.get("oil_yoy") or 0) > 5 else "yellow")

    pdf.ln(3)
    return _exec_summary_md(label, as_of, scorecard, mv, drivers, enablers, accelerators)


def _exec_summary_md(label, as_of, scorecard, mv, drivers, enablers, accelerators) -> str:
    lines = ["## 1. Executive Summary", "", f"### Verdict: {label}"]
    if as_of:
        lines.append(f"*As of {as_of}*")
    lines.append("")
    lines += ["| Metric | Value | Signal | Target |", "|---|---|---|---|"]
    for metric, item in scorecard.items():
        v = item.get("value")
        val_str = "n/a"
        if v is not None:
            val_str = f"${v:.1f}B" if ("Reserve" in metric or "Account" in metric) else f"{v:+.1f}%"
        lines.append(f"| {metric} | {val_str} | {item.get('signal','grey').upper()} | {item.get('green','')} |")
    lines.append("")
    lines.append("### Framework Assessment")

    _net  = enablers.get("net_reserves_bn")
    _gr   = enablers.get("gross_reserves_bn")
    _res  = f"Net res. (est.) ${_net:.1f}B" if _net is not None else f"Gross res. ${_gr or 0:.1f}B"
    _fisc = enablers.get("fiscal_balance_pct_gdp")
    _fs   = f" | Fiscal {_fisc:+.1f}% GDP" if _fisc is not None else ""

    lines += [
        f"- **MASTER VARIABLE**: Real wages {_fmt_pct(mv.get('value'))} YoY "
        f"({mv.get('consecutive_positive_months', 0)} consecutive positive months)",
        f"- **DRIVERS**: FBCF {_fmt_pct(drivers.get('investment_fbcf_yoy'))} YoY | "
        f"Employment {_fmt_pct(drivers.get('formal_employment_yoy'))} YoY | "
        f"Credit discipline: {drivers.get('credit_discipline', 'unknown')}",
        f"- **ENABLERS**: CPI {_fmt_pct(enablers.get('inflation_mom_latest'))}/month | "
        f"Disinflation confirmed: {enablers.get('disinflation_confirmed')} | {_res}{_fs}",
        f"- **ACCELERATORS**: Oil {_fmt_pct(accelerators.get('oil_yoy'))} YoY | "
        f"Vaca Muerta: {accelerators.get('vaca_muerta_signal', 'unknown')}",
        "",
    ]
    return "\n".join(lines)
