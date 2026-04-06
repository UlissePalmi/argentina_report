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
from external.section    import build_pdf_section as ext_pdf,  build_md_section as ext_md
from inflation.section   import build_pdf_section as inf_pdf,  build_md_section as inf_md
from gdp.section         import build_pdf_section as gdp_pdf,  build_md_section as gdp_md
from consumption.section import build_pdf_section as con_pdf,  build_md_section as con_md
from labor.section       import build_pdf_section as lab_pdf,  build_md_section as lab_md

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


def _first_sentence(text: str) -> str:
    idx = text.find(". ")
    return text[:idx + 1] if idx != -1 else text.rstrip(".") + "."


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

    _render_level_row(pdf, "ENABLERS",
                      f"CPI {_fmt_pct(enablers.get('inflation_mom_latest'))} /month. "
                      f"Disinflation confirmed: {enablers.get('disinflation_confirmed', 'unknown')}. "
                      f"Gross reserves ${enablers.get('gross_reserves_bn') or 0:.1f}B "
                      f"({enablers.get('reserves_trend', 'unknown')}).",
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
    lines.append(f"- **ENABLERS**: CPI {_fmt_pct(enablers.get('inflation_mom_latest'))}/month | "
                 f"Disinflation confirmed: {enablers.get('disinflation_confirmed')} | "
                 f"Gross reserves ${enablers.get('gross_reserves_bn') or 0:.1f}B")
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


# ---------------------------------------------------------------------------
# Main assembler
# ---------------------------------------------------------------------------
def build_report(
    external_data: dict,
    inflation_data: dict,
    gdp_data: dict,
    consumption_data: dict,
    labor_data: dict | None = None,
) -> dict[str, Path]:
    """
    Assemble the full Argentina Macro Report.

    Each *_data dict contains the DataFrames for that module, e.g.:
        external_data    = {"trade_df": ..., "reserves_df": ..., "ca_df": ...}
        inflation_data   = {"cpi_df": ...}
        gdp_data         = {"gdp_df": ..., "components_df": ..., "emae_df": ...}
        consumption_data = {"consumption_df": ...}
        labor_data       = {"consumption_df": ..., "employment_df": ...}

    Returns dict with keys 'pdf' and 'md'.
    """
    labor_data = labor_data or {}
    from external.section import summarise as ext_summary
    from inflation.section import summarise as inf_summary
    from gdp.section import summarise as gdp_summary

    today = date.today().strftime("%B %d, %Y")

    synthesis = (
        "Argentina's macroeconomic picture remains complex. "
        + _first_sentence(ext_summary(external_data)) + " "
        + _first_sentence(inf_summary(inflation_data)) + " "
        + _first_sentence(gdp_summary(gdp_data)) + " "
        "Sustained fiscal adjustment and reserve accumulation will be critical "
        "to anchor expectations and restore sustainable growth."
    )

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
    gdp_pdf(pdf, gdp_data)
    lab_pdf(pdf, labor_data)
    con_pdf(pdf, consumption_data)

    # Summary
    pdf.section_title("Summary")
    pdf.body_text(synthesis)
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 4.5, _safe(
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
    gdp_section = gdp_md(gdp_data)
    lab_section = lab_md(labor_data)
    con_section = con_md(consumption_data)

    md = f"""# Argentina Macro Report
*Generated {today}*

---

{exec_summary_md}

---

{ext_section}

---

{inf_section}

---

{gdp_section}

---

{lab_section}

---

{con_section}

---

## Summary

{synthesis}

---
*Data sources: BCRA / Argentina Open Data API (apis.datos.gob.ar), World Bank (api.worldbank.org),
IMF BOP (dataservices.imf.org -- fallback to WB when unavailable).*
"""

    md_path = REPORTS_DIR / "argentina_macro_report.md"
    md_path.write_text(md, encoding="utf-8")
    log.info("Markdown written → %s", md_path)

    return {"md": md_path, "pdf": pdf_path}
