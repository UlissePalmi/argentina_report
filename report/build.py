"""
Report assembler — combines all module sections into PDF and markdown.

This file owns:
  - ArgentinaPDF class (fpdf2 subclass)
  - _safe() latin-1 sanitiser
  - build_report() — calls each module's section builder in order
"""

from datetime import date
from pathlib import Path

import pandas as pd
from fpdf import FPDF, XPos, YPos

from utils import REPORTS_DIR, get_logger
from external.section    import build_pdf_section as ext_pdf,  build_md_section as ext_md
from inflation.section   import build_pdf_section as inf_pdf,  build_md_section as inf_md
from gdp.section         import build_pdf_section as gdp_pdf,  build_md_section as gdp_md
from consumption.section import build_pdf_section as con_pdf,  build_md_section as con_md

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
) -> dict[str, Path]:
    """
    Assemble the full Argentina Macro Report.

    Each *_data dict contains the DataFrames for that module, e.g.:
        external_data    = {"trade_df": ..., "reserves_df": ..., "ca_df": ...}
        inflation_data   = {"cpi_df": ...}
        gdp_data         = {"gdp_df": ..., "components_df": ..., "emae_df": ...}
        consumption_data = {"consumption_df": ...}

    Returns dict with keys 'pdf' and 'md'.
    """
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

    ext_pdf(pdf, external_data)
    inf_pdf(pdf, inflation_data)
    gdp_pdf(pdf, gdp_data)
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
    con_section = con_md(consumption_data)

    md = f"""# Argentina Macro Report
*Generated {today}*

---

{ext_section}

---

{inf_section}

---

{gdp_section}

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
