"""
Report assembler — combines all module sections into PDF and markdown.

Structure:
  report/pdf_base.py          — ArgentinaPDF class + _safe()
  report/executive_summary.py — verdict banner, scorecard, four-level snapshot
  report/closing_synthesis.py — reconnect paragraph, watch items, bull/bear
  report/build.py             — this file: thin assembler only
"""

from datetime import date
from pathlib import Path

from fpdf import XPos, YPos

from utils import REPORTS_DIR, get_logger
from .pdf_base            import ArgentinaPDF, _safe
from .executive_summary   import build_executive_summary_section
from .closing_synthesis   import build_closing_synthesis

from ingestion.section             import build_pdf_section as ext_pdf,  build_md_section as ext_md
from sections.inflation.section   import build_pdf_section as inf_pdf,  build_md_section as inf_md
from sections.fiscal.section      import build_pdf_section as fis_pdf,  build_md_section as fis_md
from sections.gdp.section         import build_pdf_section as gdp_pdf,  build_md_section as gdp_md
from sections.production.section  import build_pdf_section as pro_pdf,  build_md_section as pro_md
from sections.consumption.section import build_pdf_section as con_pdf,  build_md_section as con_md
from sections.labor.section       import build_pdf_section as lab_pdf,  build_md_section as lab_md
from sections.debt.section        import build_pdf_section as dbt_pdf,  build_md_section as dbt_md
from svar.section                 import build_pdf_section as svar_pdf, build_md_section as svar_md

log = get_logger("report.build")

_SOURCES_NOTE = (
    "Data sources: BCRA / Argentina Open Data API (apis.datos.gob.ar), "
    "World Bank (api.worldbank.org), IMF BOP (dataservices.imf.org -- fallback to WB when unavailable)."
)


def build_report(
    external_data:    dict,
    inflation_data:   dict,
    gdp_data:         dict,
    consumption_data: dict,
    labor_data:       dict | None = None,
    production_data:  dict | None = None,
    fiscal_data:      dict | None = None,
    debt_data:        dict | None = None,
) -> dict[str, Path]:
    """
    Assemble the full Argentina Macro Report (PDF + Markdown).

    Each *_data dict contains the DataFrames for that module, e.g.:
        external_data    = {"trade_df": ..., "reserves_df": ..., "ca_df": ...}
        inflation_data   = {"cpi_df": ...}
        gdp_data         = {"gdp_df": ..., "components_df": ..., "emae_df": ...}
        consumption_data = {"consumption_df": ...}
        labor_data       = {"consumption_df": ..., "employment_df": ...}
        production_data  = {"production_df": ..., "agro_df": ...}

    Returns dict with keys 'pdf' and 'md'.
    """
    labor_data      = labor_data      or {}
    production_data = production_data or {}
    fiscal_data     = fiscal_data     or {}
    debt_data       = debt_data       or {}

    today = date.today().strftime("%B %d, %Y")

    # -------------------------------------------------------------------------
    # PDF
    # -------------------------------------------------------------------------
    pdf = ArgentinaPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

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
    pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin, 4.5, _safe(_SOURCES_NOTE))

    pdf_path = REPORTS_DIR / "argentina_macro_report.pdf"
    pdf.output(str(pdf_path))
    log.info("PDF written -> %s", pdf_path)

    # -------------------------------------------------------------------------
    # Markdown
    # -------------------------------------------------------------------------
    sections = [
        exec_summary_md,
        ext_md(external_data),
        inf_md(inflation_data),
        fis_md(fiscal_data),
        dbt_md(debt_data),
        gdp_md(gdp_data),
        pro_md(production_data),
        lab_md(labor_data),
        con_md(consumption_data),
        svar_md({}),
        closing_md,
    ]

    md = f"# Argentina Macro Report\n*Generated {today}*\n\n---\n\n"
    md += "\n\n---\n\n".join(sections)
    md += f"\n\n---\n*{_SOURCES_NOTE}*\n"

    md_path = REPORTS_DIR / "argentina_macro_report.md"
    md_path.write_text(md, encoding="utf-8")
    log.info("Markdown written -> %s", md_path)

    return {"md": md_path, "pdf": pdf_path}
