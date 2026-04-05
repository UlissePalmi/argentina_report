"""
Financing report — Credit Expansion + Savings & Deposits.
Outputs: data/reports/financing_report.pdf
"""

from datetime import date
from pathlib import Path

import pandas as pd
from fpdf import XPos, YPos

from consumption.report import ConsumptionPDF, chart_yoy_mom, _avg3, _pct
from report.build import _safe
from utils import REPORTS_DIR, get_logger

log = get_logger("financing.report")


def build_financing_report(consumption_df: pd.DataFrame | None) -> Path:
    today = date.today().strftime("%B %d, %Y")

    pdf = ConsumptionPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(20, 80, 160)
    pdf.cell(0, 12, "Argentina -- Financing Deep Dive",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 7, f"Generated {today}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_draw_color(20, 80, 160)
    pdf.set_line_width(0.5)
    pdf.line(15, pdf.get_y() + 2, 195, pdf.get_y() + 2)
    pdf.ln(8)

    if consumption_df is None or consumption_df.empty:
        pdf.body_text("Consumption/financing data unavailable.")
        out = REPORTS_DIR / "financing_report.pdf"
        pdf.output(str(out))
        return out

    df = consumption_df.copy()
    df["date"] = pd.to_datetime(df["date"])

    # =========================================================
    # Section 1 — Credit Expansion
    # =========================================================
    pdf.section_title("1. Credit Expansion")

    pdf.body_text(
        "Credit is split into three groups: "
        "(1) Consumption lending -- personal loans and credit cards, which go directly to "
        "household spending. "
        "(2) Business borrowing -- overdrafts and commercial paper, which finance firms. "
        "(3) Asset credit -- mortgages and auto loans, mixed consumption/investment. "
        "All figures are real (Fisher-adjusted). "
        "When interpreting YoY: always check MoM first -- if MoM is positive, "
        "a decelerating YoY is mechanical base-effect normalization, not a genuine slowdown."
    )

    CONSUMPTION_COLS = ["real_personal_loans_pct", "real_credit_cards_pct"]
    PRODUCTIVE_COLS  = ["real_overdrafts_pct", "real_commercial_paper_pct"]
    ASSET_COLS       = ["real_mortgages_pct", "real_auto_loans_pct"]

    def _credit_subsection(pdf, df, title, yoy_cols, mom_col_map, chart_defs, note_text, interp_fn=None):
        avail_yoy = [c for c in yoy_cols if c in df.columns]
        if not avail_yoy:
            return
        pdf.subsection(title)
        label_map = {
            "real_personal_loans_pct":   "personal_loans",
            "real_credit_cards_pct":     "credit_cards",
            "real_mortgages_pct":        "mortgages",
            "real_auto_loans_pct":       "auto_loans",
            "real_overdrafts_pct":       "overdrafts",
            "real_commercial_paper_pct": "commercial_paper",
        }
        disp = df.copy()
        disp["date"] = disp["date"].dt.strftime("%b %Y")
        rename = {c: label_map.get(c, c) for c in avail_yoy}
        disp = disp.rename(columns=rename)
        display_cols = [rename[c] for c in avail_yoy]
        pdf.add_table_n(disp, ["date"] + display_cols,
                        fmt={c: "{:+.1f}%" for c in display_cols},
                        title=f"{title} -- Real YoY %", limit=24)
        mom_avail = [(src, dst) for src, dst in mom_col_map if src in df.columns]
        if mom_avail:
            disp_mom = df.copy()
            disp_mom["date"] = disp_mom["date"].dt.strftime("%b %Y")
            disp_mom = disp_mom.rename(columns={src: dst for src, dst in mom_avail})
            mom_cols = [dst for _, dst in mom_avail]
            pdf.add_table_n(disp_mom, ["date"] + mom_cols,
                            fmt={c: "{:+.1f}%" for c in mom_cols},
                            title=f"{title} -- Real MoM %", limit=24)
        if interp_fn:
            pdf.body_text(interp_fn(df))
        for yoy_col, mom_col, label, fname in chart_defs:
            chart = chart_yoy_mom(df, yoy_col, mom_col,
                                  title=f"{label} -- Real YoY % & MoM %", filename=fname)
            pdf.add_chart(chart, caption=f"{label}: bars=YoY %, line=MoM % (RHS)")
        pdf.note(note_text)

    def _interp_consumption(df):
        cons_avg = sum(v for c in CONSUMPTION_COLS
                       if c in df.columns and (v := _avg3(df[c])) is not None) or None
        wage_avg = _avg3(df.get("real_wage_yoy_pct", pd.Series(dtype=float)))
        pl_mom = _avg3(df.get("real_personal_loans_mom_pct",  pd.Series(dtype=float)))
        cc_mom = _avg3(df.get("real_credit_cards_mom_pct",    pd.Series(dtype=float)))
        mom_signal = ""
        if pl_mom is not None and cc_mom is not None:
            if pl_mom > 0 and cc_mom > 0:
                mom_signal = "MoM still positive -- YoY deceleration is base-effect normalization."
            elif pl_mom < 0 or cc_mom < 0:
                mom_signal = "MoM turning negative -- genuine consumption credit contraction."
        lines = []
        if cons_avg is not None and wage_avg is not None:
            spread = cons_avg - wage_avg
            if spread > 20:
                lines.append(f"Consumption credit ({_pct(cons_avg)}) outpacing real wages ({_pct(wage_avg)}) by {_pct(spread)} -- households leveraging up materially.")
            elif spread > 5:
                lines.append(f"Moderate leverage: consumption credit ({_pct(cons_avg)}) exceeds real wages ({_pct(wage_avg)}) by {_pct(spread)}.")
            else:
                lines.append(f"Consumption credit ({_pct(cons_avg)}) in line with real wages ({_pct(wage_avg)}) -- no leverage signal.")
        if mom_signal:
            lines.append(mom_signal)
        return " ".join(lines) if lines else ""

    def _interp_business(df):
        prod_avg = sum(v for c in PRODUCTIVE_COLS
                       if c in df.columns and (v := _avg3(df[c])) is not None) or None
        od_mom = _avg3(df.get("real_overdrafts_mom_pct",       pd.Series(dtype=float)))
        cp_mom = _avg3(df.get("real_commercial_paper_mom_pct", pd.Series(dtype=float)))
        mom_signal = ""
        if od_mom is not None and cp_mom is not None:
            if od_mom > 0 and cp_mom > 0:
                mom_signal = "MoM positive -- business borrowing still expanding in real terms."
            elif od_mom < 0 or cp_mom < 0:
                mom_signal = "MoM turning negative -- firms reducing borrowing."
        lines = []
        if prod_avg is not None:
            lines.append(f"Business credit 3-month avg: {_pct(prod_avg)} real YoY.")
        if mom_signal:
            lines.append(mom_signal)
        return " ".join(lines) if lines else ""

    _credit_subsection(
        pdf, df,
        title="1a. Consumption Lending (Personal Loans + Credit Cards)",
        yoy_cols=CONSUMPTION_COLS,
        mom_col_map=[
            ("real_personal_loans_mom_pct", "personal_loans_mom"),
            ("real_credit_cards_mom_pct",   "credit_cards_mom"),
        ],
        chart_defs=[
            ("real_personal_loans_pct", "real_personal_loans_mom_pct", "Personal Loans", "credit_personal_loans.png"),
            ("real_credit_cards_pct",   "real_credit_cards_mom_pct",   "Credit Cards",   "credit_cards.png"),
        ],
        note_text="Personal loans (91.1_DETALLE_PRLES_0_0_52) and credit cards (91.1_DETALLE_PRTAS_0_0_60).",
        interp_fn=_interp_consumption,
    )

    _credit_subsection(
        pdf, df,
        title="1b. Business Borrowing (Overdrafts + Commercial Paper)",
        yoy_cols=PRODUCTIVE_COLS,
        mom_col_map=[
            ("real_overdrafts_mom_pct",      "overdrafts_mom"),
            ("real_commercial_paper_mom_pct", "commercial_paper_mom"),
        ],
        chart_defs=[
            ("real_overdrafts_pct",       "real_overdrafts_mom_pct",       "Overdrafts",       "credit_overdrafts.png"),
            ("real_commercial_paper_pct", "real_commercial_paper_mom_pct", "Commercial Paper", "credit_commercial_paper.png"),
        ],
        note_text="Adelantos (91.1_DETALLE_PRTOS_0_0_55) and documentos (91.1_DETALLE_PRTOS_0_0_56).",
        interp_fn=_interp_business,
    )

    _credit_subsection(
        pdf, df,
        title="1c. Asset Credit (Mortgages + Auto Loans)",
        yoy_cols=ASSET_COLS,
        mom_col_map=[
            ("real_mortgages_mom_pct",  "mortgages_mom"),
            ("real_auto_loans_mom_pct", "auto_loans_mom"),
        ],
        chart_defs=[
            ("real_mortgages_pct",  "real_mortgages_mom_pct",  "Mortgages",  "credit_mortgages.png"),
            ("real_auto_loans_pct", "real_auto_loans_mom_pct", "Auto Loans", "credit_auto_loans.png"),
        ],
        note_text="Hipotecarios (91.1_DETALLE_PRPOT_0_0_53) and prendarios (91.1_DETALLE_PREND_0_0_53).",
    )

    # Aggregate leverage signal
    pdf.subsection("1d. Aggregate Consumer Credit vs Real Wages")
    credit_cols_avail = [c for c in [
        "date",
        "consumer_credit_yoy_pct", "real_consumer_credit_yoy_pct",
        "total_credit_yoy_pct",    "real_total_credit_yoy_pct",
    ] if c in df.columns]
    if len(credit_cols_avail) > 1:
        disp = df.copy()
        disp["date"] = disp["date"].dt.strftime("%b %Y")
        pct_cols = [c for c in credit_cols_avail if c != "date"]
        pdf.add_table_n(disp, credit_cols_avail,
                        fmt={c: "{:+.1f}%" for c in pct_cols},
                        title="Aggregate Credit -- Nominal vs Real YoY %", limit=24)
    if "real_consumer_credit_yoy_pct" in df.columns and "real_wage_yoy_pct" in df.columns:
        sub = df[["date", "real_wage_yoy_pct", "real_consumer_credit_yoy_pct"]].dropna().tail(3)
        if not sub.empty:
            spread = sub["real_consumer_credit_yoy_pct"].mean() - sub["real_wage_yoy_pct"].mean()
            if spread > 20:
                verdict = "households leveraging up materially -- credit outpacing income by " + _pct(spread)
            elif spread > 5:
                verdict = "moderate leverage build-up -- credit exceeds wages by " + _pct(spread)
            elif spread > -5:
                verdict = "credit in line with wages -- no material leverage signal"
            else:
                verdict = "credit growing slower than wages -- deleveraging"
            pdf.body_text(f"Real credit vs real wage spread (3-month avg): {verdict}.")
    pdf.note("Fisher-adjusted real columns are the actionable signal. Nominal credit at 200% YoY with CPI at 200% = 0% real growth.")

    # =========================================================
    # Section 2 — Savings & Deposits
    # =========================================================
    pdf.section_title("2. Savings & Deposits")

    pdf.body_text(
        "Fixed-term peso deposits (BCRA series 334.2_SIST_FINANIJO__54, system-wide) are the most "
        "liquid formal savings vehicle tracked in this dataset. Falling real deposits suggest "
        "households are either spending savings or dollarising. "
        "Important caveat: dollar deposits and real estate are not captured here."
    )

    dep_cols_avail = [c for c in ["date", "deposits_yoy_pct", "cpi_yoy_pct", "real_deposits_yoy_pct"]
                      if c in df.columns]
    if len(dep_cols_avail) > 1:
        disp = df.copy()
        disp["date"] = disp["date"].dt.strftime("%b %Y")
        pct_cols = [c for c in dep_cols_avail if c != "date"]
        pdf.add_table_n(disp, dep_cols_avail,
                        fmt={c: "{:+.1f}%" for c in pct_cols},
                        title="Fixed-Term Deposits vs CPI -- Nominal vs Real YoY %", limit=24)

    if "real_deposits_yoy_pct" in df.columns:
        dep_latest = df["real_deposits_yoy_pct"].dropna().tail(1)
        if not dep_latest.empty:
            v = dep_latest.iloc[0]
            if v > 10:
                dep_read = "Real deposits growing solidly -- households saving, not dissaving."
            elif v > -10:
                dep_read = "Real deposits roughly flat -- neutral savings signal."
            elif v > -30:
                dep_read = "Real deposits declining -- households accumulating less in real terms. Monitor."
            else:
                dep_read = "Real deposits falling sharply -- dissaving or dollarisation. Flag as headwind once buffer exhausted."
            pdf.body_text(dep_read)

    pdf.note(
        "Fixed-term deposits: 334.2_SIST_FINANIJO__54 (BCRA, system-wide). "
        "Dollar deposits and real assets not captured."
    )

    # Footer
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 4.5, _safe(
        "Data sources: BCRA / datos.gob.ar. "
        "All real series Fisher-adjusted: ((1 + nominal/100) / (1 + CPI/100) - 1) * 100."
    ))

    out = REPORTS_DIR / "financing_report.pdf"
    pdf.output(str(out))
    log.info("Financing report written -> %s", out)
    return out
