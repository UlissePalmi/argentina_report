"""
Consumption module — standalone detailed report builder.

Outputs: data/reports/consumption_report.pdf

This report goes into full depth on Argentina's three consumption drivers:
  1. Real wages (purchasing power)
  2. Credit expansion (leverage)
  3. Savings drawdown (deposits)

Plus activity context from EMAE and GDP components.

The main argentina_macro_report.pdf shows only the key-findings summary;
this file produces the full 24-month deep-dive.
"""

from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from fpdf import XPos, YPos

from report.build import ArgentinaPDF, _safe
from utils import CHARTS_DIR, REPORTS_DIR, get_logger

log = get_logger("consumption.report")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _pct(v) -> str:
    try:
        return f"{float(v):+.1f}%"
    except (TypeError, ValueError):
        return "n/a"


def _real_sign(v) -> str:
    """Arrow + colour hint for inline text (returns plain text for PDF)."""
    try:
        f = float(v)
        return "positive" if f > 0 else "negative"
    except (TypeError, ValueError):
        return "unknown"


class ConsumptionPDF(ArgentinaPDF):
    """ArgentinaPDF subclass — overrides header/footer for the consumption report,
    and exposes add_table_n() that accepts an explicit row limit."""

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(130, 130, 130)
        self.cell(0, 8, "Argentina -- Consumption Deep Dive",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")
        self.set_draw_color(200, 200, 200)
        self.line(self.MARGIN, self.get_y(), self.PAGE_W - self.MARGIN, self.get_y())
        self.ln(2)

    def footer(self):
        self.set_y(-13)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def add_table_n(self, df: pd.DataFrame, cols: list[str],
                    fmt: dict | None = None, title: str = "", limit: int = 24):
        """Like add_table but shows up to `limit` rows (default 24)."""
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
        # Header row
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(30, 100, 200)
        self.set_text_color(255, 255, 255)
        for c in cols:
            label = (c.replace("_", " ")
                      .replace("usd bn", "(USD bn)")
                      .replace("pct", "%")
                      .replace("yoy", "YoY")
                      .title())
            self.cell(col_w, 6, _safe(label), border=0, fill=True, align="C")
        self.ln()
        # Data rows
        self.set_font("Helvetica", "", 8)
        for i, (_, row) in enumerate(subset.iterrows()):
            bg = (240, 247, 255) if i % 2 == 0 else (255, 255, 255)
            self.set_fill_color(*bg)
            self.set_text_color(40, 40, 40)
            for c in cols:
                v = row[c]
                if c == "date" or (hasattr(v, "strftime")):
                    try:    cell_str = pd.to_datetime(v).strftime("%b %Y")
                    except: cell_str = str(v).split(" ")[0]
                else:
                    f = fmt.get(c, "{}")
                    try:    cell_str = f.format(v)
                    except: cell_str = str(v)
                # Colour-code numeric cells: positive=dark green, negative=dark red
                if c != "date":
                    try:
                        num = float(v)
                        if num > 0:
                            self.set_text_color(0, 110, 50)
                        elif num < 0:
                            self.set_text_color(180, 0, 0)
                        else:
                            self.set_text_color(80, 80, 80)
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
        """Small italic note / methodology footnote."""
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(110, 110, 110)
        self.multi_cell(0, 4.5, _safe(text))
        self.set_text_color(0, 0, 0)
        self.ln(2)


# ---------------------------------------------------------------------------
# Section helpers
# ---------------------------------------------------------------------------
def _latest_real_wages(df: pd.DataFrame) -> tuple[float | None, float | None, float | None]:
    """Return (nominal_wage_yoy_pct, cpi_yoy_pct, real_wage_yoy_pct) for the latest valid row."""
    for col in ["real_wage_yoy_pct", "nominal_wage_yoy_pct", "cpi_yoy_pct"]:
        if col not in df.columns:
            return None, None, None
    sub = df[["nominal_wage_yoy_pct", "cpi_yoy_pct", "real_wage_yoy_pct"]].dropna()
    if sub.empty:
        return None, None, None
    row = sub.iloc[-1]
    return row["nominal_wage_yoy_pct"], row["cpi_yoy_pct"], row["real_wage_yoy_pct"]


def _avg3(series: pd.Series) -> float | None:
    vals = series.dropna().tail(3)
    return float(vals.mean()) if len(vals) >= 1 else None


def _classify_config(df: pd.DataFrame) -> str:
    """Return 'wage-led', 'credit-led', or 'savings-drawdown' based on last 3-month averages."""
    real_wage   = _avg3(df.get("real_wage_yoy_pct",            pd.Series(dtype=float)))
    real_credit = _avg3(df.get("real_consumer_credit_yoy_pct", pd.Series(dtype=float)))
    real_dep    = _avg3(df.get("real_deposits_yoy_pct",        pd.Series(dtype=float)))
    cpi_avg     = _avg3(df.get("cpi_yoy_pct",                  pd.Series(dtype=float)))

    if real_wage is None:
        return "data-insufficient"

    # Wage-led: real wages positive, credit not materially outpacing wages
    if real_wage > 0:
        if real_credit is not None and real_credit > real_wage + 15:
            return "credit-led"
        return "wage-led"

    # Savings drawdown: real wages negative + real deposits falling
    if real_dep is not None and real_dep < 0:
        return "savings-drawdown"

    # Default: credit-led if real wages negative but credit growing
    if real_credit is not None and real_credit > 0:
        return "credit-led"

    return "savings-drawdown"


CHART_STYLE = {
    "figure.facecolor": "#ffffff",
    "axes.facecolor": "#f8f9fa",
    "axes.edgecolor": "#dee2e6",
    "axes.labelcolor": "#212529",
    "xtick.color": "#495057",
    "ytick.color": "#495057",
    "text.color": "#212529",
    "grid.color": "#dee2e6",
    "grid.linewidth": 0.8,
    "lines.linewidth": 2.0,
    "font.family": "DejaVu Sans",
}


def chart_real_wages(df: pd.DataFrame) -> str | None:
    """Bars: real_wage_yoy_pct. Line (RHS): real_wage_mom_pct."""
    if "real_wage_yoy_pct" not in df.columns:
        return None
    needed = ["date", "real_wage_yoy_pct"] + (
        ["real_wage_mom_pct"] if "real_wage_mom_pct" in df.columns else []
    )
    sub = df[needed].dropna(subset=["real_wage_yoy_pct"]).tail(24).copy()
    if sub.empty:
        return None

    dates = pd.to_datetime(sub["date"])
    path = str(CHARTS_DIR / "consumption_real_wages.png")

    with plt.rc_context(CHART_STYLE):
        fig, ax1 = plt.subplots(figsize=(10, 4.5))

        # Bars — YoY level
        bar_colors = ["#2f9e44" if v >= 0 else "#c92a2a"
                      for v in sub["real_wage_yoy_pct"]]
        ax1.bar(dates, sub["real_wage_yoy_pct"], color=bar_colors, width=20, alpha=0.8,
                label="Real wage YoY %")
        ax1.axhline(0, color="#495057", linewidth=0.8)
        ax1.set_ylabel("Real Wage YoY %")

        # Line — actual MoM real wage change
        ax2 = ax1.twinx()
        if "real_wage_mom_pct" in sub.columns and sub["real_wage_mom_pct"].notna().any():
            ax2.plot(dates, sub["real_wage_mom_pct"], color="#1971c2", linewidth=1.8,
                     marker="o", markersize=3, label="Real wage MoM %")
        ax2.set_ylabel("Real Wage MoM %", color="#1971c2")
        ax2.tick_params(axis="y", labelcolor="#1971c2")

        # Align zeros: keep each axis' max, extend the min so zero sits at the same fraction
        def _align_zeros(a1, a2):
            for ax in (a1, a2):
                lo, hi = ax.get_ylim()
                if hi <= 0:
                    continue  # all negative — don't adjust
                r1 = abs(a1.get_ylim()[0]) / (a1.get_ylim()[1] - a1.get_ylim()[0])
                r2 = abs(a2.get_ylim()[0]) / (a2.get_ylim()[1] - a2.get_ylim()[0])
                r = max(r1, r2)
                for a in (a1, a2):
                    _, h = a.get_ylim()
                    a.set_ylim(-r * h / (1 - r), h)
                break
        _align_zeros(ax1, ax2)

        h1, l1 = ax1.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax1.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8, framealpha=0.8)

        ax1.set_title("Real Wage Growth: YoY % & MoM % (Fisher-adjusted)",
                      fontsize=12, fontweight="bold", pad=10)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=8)
        ax1.grid(axis="y", alpha=0.5)

        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    log.info("Chart saved: %s", path)
    return path


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------
def build_consumption_report(consumption_df: pd.DataFrame | None,
                              cpi_df:         pd.DataFrame | None = None,
                              components_df:  pd.DataFrame | None = None,
                              emae_df:        pd.DataFrame | None = None) -> Path:
    """
    Build the standalone consumption deep-dive PDF.

    Parameters
    ----------
    consumption_df : DataFrame with columns from consumption/fetch.py
                     (both nominal and real* columns expected)
    cpi_df         : optional — CPI DataFrame (used for cross-check only)
    components_df  : optional — GDP expenditure components (for C_pct)
    emae_df        : optional — EMAE monthly activity (for sector context)

    Returns
    -------
    Path to the written PDF.
    """
    today = date.today().strftime("%B %d, %Y")

    pdf = ConsumptionPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # =========================================================
    # Title
    # =========================================================
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(20, 80, 160)
    pdf.cell(0, 12, "Argentina -- Consumption Deep Dive",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 7, f"Generated {today}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_draw_color(20, 80, 160)
    pdf.set_line_width(0.5)
    pdf.line(15, pdf.get_y() + 2, 195, pdf.get_y() + 2)
    pdf.ln(8)

    if consumption_df is None or consumption_df.empty:
        pdf.body_text("Consumption data unavailable — pipeline fetch failed.")
        out = REPORTS_DIR / "consumption_report.pdf"
        pdf.output(str(out))
        return out

    df = consumption_df.copy()
    df["date"] = pd.to_datetime(df["date"])

    config = _classify_config(df)
    config_label = {
        "wage-led":          "Wage-Led (healthy)",
        "credit-led":        "Credit-Led (monitor)",
        "savings-drawdown":  "Savings Drawdown (fragile)",
        "data-insufficient": "Insufficient Data",
    }.get(config, config)

    # =========================================================
    # Section 1 — Executive Summary
    # =========================================================
    pdf.section_title("1. Executive Summary")

    nom_w, cpi_v, real_w = _latest_real_wages(df)
    real_cr = _avg3(df.get("real_consumer_credit_yoy_pct", pd.Series(dtype=float)))
    real_dep = _avg3(df.get("real_deposits_yoy_pct", pd.Series(dtype=float)))

    summary_lines = [
        f"Current configuration: {config_label}",
        "",
        "Three-driver snapshot (3-month average of most recent data):",
        f"  Real wages:       {_pct(real_w) if real_w is not None else 'n/a'}  "
        f"(nominal {_pct(nom_w)}, CPI {_pct(cpi_v)})",
        f"  Real cons. credit:{_pct(real_cr) if real_cr is not None else 'n/a'}",
        f"  Real deposits:    {_pct(real_dep) if real_dep is not None else 'n/a'}",
    ]

    # GDP consumption anchor
    if components_df is not None and not components_df.empty:
        c_col = next((c for c in components_df.columns if c.lower() in ("c_pct", "consumption_pct")), None)
        if c_col:
            c_vals = components_df[["date", c_col]].dropna(subset=[c_col]).tail(3)
            if not c_vals.empty:
                c_latest = c_vals.iloc[-1]
                try:
                    q_label = pd.to_datetime(c_latest["date"]).strftime("Q%q %Y")
                except Exception:
                    q_label = str(c_latest["date"])
                summary_lines += [
                    "",
                    f"Real private consumption (GDP accounts): {_pct(c_latest[c_col])} YoY "
                    f"(latest: {q_label})",
                ]

    pdf.body_text("\n".join(summary_lines))

    config_desc = {
        "wage-led": (
            "Real wages are positive — households' purchasing power is growing. "
            "Consumption is backed by income gains, the most sustainable driver. "
            "Monitor whether credit is accelerating faster than wages (leverage build-up)."
        ),
        "credit-led": (
            "Real wages are negative or credit is outpacing income growth by a material margin. "
            "Households are borrowing to maintain consumption. "
            "This is sustainable only if real wages recover within 2-3 quarters; "
            "otherwise credit quality deteriorates."
        ),
        "savings-drawdown": (
            "Real wages are contracting and real deposits are falling. "
            "Households are spending down savings to maintain consumption — "
            "a structurally fragile configuration that will compress once buffers are exhausted."
        ),
        "data-insufficient": "Insufficient data to classify configuration.",
    }
    pdf.body_text(config_desc.get(config, ""))
    pdf.note(
        "Methodology: All 'real' series use the Fisher equation: "
        "real = ((1 + nominal/100) / (1 + CPI/100) - 1) * 100. "
        "Simple subtraction (nominal - CPI) is inaccurate at Argentina's inflation levels "
        "(e.g. 430% nominal, 84% CPI: simple = 346%, Fisher = 188%)."
    )

    # =========================================================
    # Section 2 — Real Wages
    # =========================================================
    pdf.section_title("2. Real Wages (Purchasing Power)")

    pdf.body_text(
        "Nominal private-sector wage index (INDEC, base Oct 2016=100) is converted to "
        "YoY % change, then deflated by INDEC CPI using the Fisher equation. "
        "Positive real wages mean purchasing power is rising; negative means households "
        "are earning less in real terms each month."
    )

    wage_chart = chart_real_wages(df)
    pdf.add_chart(wage_chart, caption="Bars: real wage YoY % (green/red). Line: real wage MoM % (RHS).")

    wage_cols_avail = [c for c in ["date", "nominal_wage_yoy_pct", "cpi_yoy_pct", "real_wage_yoy_pct"]
                       if c in df.columns]
    if len(wage_cols_avail) > 1:
        disp = df.copy()
        disp["date"] = disp["date"].dt.strftime("%b %Y")
        extra = ["real_wage_mom_pct"] if "real_wage_mom_pct" in disp.columns else []
        table_cols = wage_cols_avail + extra
        pct_cols = [c for c in table_cols if c != "date"]
        pdf.add_table_n(
            disp, table_cols,
            fmt={c: "{:+.1f}%" for c in pct_cols},
            title="Wages vs CPI -- YoY % and MoM % (last 24 months)",
            limit=24,
        )

    # 3-month trend
    if "real_wage_yoy_pct" in df.columns:
        trend = df["real_wage_yoy_pct"].dropna().tail(3).tolist()
        if len(trend) >= 2:
            direction = "improving" if trend[-1] > trend[-2] else "deteriorating"
            pdf.body_text(
                f"3-month real wage trend: {', '.join(_pct(v) for v in trend)} -- {direction}."
            )

    pdf.note(
        "Source: INDEC wage index series 149.1_SOR_PRIADO_OCTU_0_25 (private sector, monthly). "
        "CPI: INDEC national CPI series 148.3_INIVELNAL_DICI_M_26."
    )

    # =========================================================
    # Section 3 — Credit Expansion
    # =========================================================
    pdf.section_title("3. Credit Expansion")

    pdf.body_text(
        "Consumer and personal loans (BCRA series 91.1_PEFPGR_0_0_60) and total private-sector "
        "loans (174.1_PTAMOS_O_0_0_29) are shown in nominal YoY % and real (Fisher-adjusted) YoY %. "
        "In Argentina's high-inflation environment, nominal credit growth above 100% YoY may still "
        "represent real contraction -- always read the real column."
    )

    credit_cols_avail = [c for c in [
        "date",
        "consumer_credit_yoy_pct", "real_consumer_credit_yoy_pct",
        "total_credit_yoy_pct",    "real_total_credit_yoy_pct",
    ] if c in df.columns]

    if len(credit_cols_avail) > 1:
        disp = df.copy()
        disp["date"] = disp["date"].dt.strftime("%b %Y")
        pct_cols = [c for c in credit_cols_avail if c != "date"]
        pdf.add_table_n(
            disp, credit_cols_avail,
            fmt={c: "{:+.1f}%" for c in pct_cols},
            title="Credit Growth — Nominal vs Real YoY % (last 24 months)",
            limit=24,
        )

    # Credit vs wage spread
    if "real_consumer_credit_yoy_pct" in df.columns and "real_wage_yoy_pct" in df.columns:
        sub = df[["date", "real_wage_yoy_pct", "real_consumer_credit_yoy_pct"]].dropna().tail(3)
        if not sub.empty:
            spread = sub["real_consumer_credit_yoy_pct"].mean() - sub["real_wage_yoy_pct"].mean()
            if spread > 20:
                verdict = "households are leveraging up materially -- credit is outpacing income by " + _pct(spread)
            elif spread > 5:
                verdict = "moderate leverage build-up -- credit exceeds wage growth by " + _pct(spread)
            elif spread > -5:
                verdict = "credit growing in line with wages -- no material leverage signal"
            else:
                verdict = "credit growing slower than wages -- deleveraging / conservative borrowing"
            pdf.body_text(f"Real credit vs real wage spread (3-month avg): {verdict}.")

    pdf.note(
        "Key distinction: if nominal credit YoY is 200% and CPI is 200%, real credit growth is 0%. "
        "The Fisher-adjusted real columns are the actionable signal."
    )

    # =========================================================
    # Section 4 — Savings Drawdown (Deposits)
    # =========================================================
    pdf.section_title("4. Savings & Deposits")

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
        pdf.add_table_n(
            disp, dep_cols_avail,
            fmt={c: "{:+.1f}%" for c in pct_cols},
            title="Fixed-Term Deposits vs CPI -- Nominal vs Real YoY % (last 24 months)",
            limit=24,
        )

    if "real_deposits_yoy_pct" in df.columns:
        dep_latest = df["real_deposits_yoy_pct"].dropna().tail(1)
        if not dep_latest.empty:
            v = dep_latest.iloc[0]
            if v > 10:
                dep_read = "Real deposits are growing solidly -- households are saving, not dissaving."
            elif v > -10:
                dep_read = "Real deposits roughly flat (within +-10pp of CPI) -- neutral savings signal."
            elif v > -30:
                dep_read = "Real deposits declining -- households accumulating less in real terms. Monitor."
            else:
                dep_read = (
                    "Real deposits falling sharply -- significant dissaving or dollarisation signal. "
                    "Flag as consumption headwind once buffer exhausted."
                )
            pdf.body_text(dep_read)

    # =========================================================
    # Section 5 — Activity Context
    # =========================================================
    pdf.section_title("5. Activity Context")

    # GDP components: C_pct
    if components_df is not None and not components_df.empty:
        pdf.subsection("5a. GDP Expenditure Components")
        c_col  = next((c for c in components_df.columns if c.lower() in ("c_pct", "consumption_pct")), None)
        gdp_col = next((c for c in components_df.columns if c.lower() in ("gdp_pct", "gdp_growth")), None)
        comp_cols = ["date"] + [c for c in [c_col, gdp_col] if c is not None]
        if len(comp_cols) > 1:
            pdf.add_table_n(
                components_df, comp_cols,
                fmt={c: "{:+.1f}%" for c in comp_cols if c != "date"},
                title="Private Consumption (C) vs GDP -- Real YoY % (last 8 quarters)",
                limit=8,
            )
            pdf.note(
                "C_pct: real private consumption YoY % from GDP expenditure accounts (INDEC). "
                "GDP_pct: headline real GDP growth. Consumption growing above GDP = C is "
                "disproportionately driving growth."
            )
        else:
            pdf.body_text("GDP components data loaded but C_pct column not found.")
    else:
        pdf.body_text("GDP components data unavailable.")

    # EMAE sectoral
    if emae_df is not None and not emae_df.empty:
        pdf.subsection("5b. EMAE Sectoral Activity")
        sector_cols = [c for c in emae_df.columns
                       if c not in ("date",) and "pct" in c and "emae" not in c.lower()]
        emae_display_cols = ["date"] + sector_cols[:6]  # up to 6 sectors
        if len(emae_display_cols) > 1:
            pdf.add_table_n(
                emae_df, emae_display_cols,
                fmt={c: "{:+.1f}%" for c in emae_display_cols if c != "date"},
                title="EMAE Sector Activity -- YoY % (last 12 months)",
                limit=12,
            )
            pdf.note(
                "comercio_pct (wholesale/retail trade) is the closest EMAE proxy for "
                "consumption-linked activity. industria_pct (manufacturing) indicates "
                "whether real wage gains are productivity-backed."
            )
        else:
            pdf.body_text("EMAE data loaded but sector columns not found.")
    else:
        pdf.body_text("EMAE sectoral data unavailable.")

    # =========================================================
    # Section 6 — Full Data Appendix
    # =========================================================
    pdf.section_title("6. Full Data Appendix (24 months)")

    all_pct_cols = [c for c in df.columns if c != "date"]
    all_cols = ["date"] + all_pct_cols
    disp = df.copy()
    disp["date"] = disp["date"].dt.strftime("%b %Y")
    pdf.add_table_n(
        disp, all_cols,
        fmt={c: "{:+.1f}%" for c in all_pct_cols},
        title="All Consumption Driver Series -- YoY % (24 months)",
        limit=24,
    )
    pdf.note(
        "Columns: nominal_wage = private sector wage index YoY; "
        "consumer_credit = consumer + personal loans YoY; "
        "total_credit = all private sector loans YoY; "
        "deposits = fixed-term peso deposits YoY; "
        "cpi = INDEC national CPI YoY; "
        "real_* = Fisher-adjusted real YoY."
    )

    # =========================================================
    # Footer note
    # =========================================================
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 4.5, _safe(
        "Data sources: INDEC / datos.gob.ar series API (apis.datos.gob.ar/series/api). "
        "Wage index: 149.1_SOR_PRIADO_OCTU_0_25. "
        "Consumer credit: 91.1_PEFPGR_0_0_60. "
        "Total private credit: 174.1_PTAMOS_O_0_0_29. "
        "Fixed-term deposits: 334.2_SIST_FINANIJO__54. "
        "CPI: 148.3_INIVELNAL_DICI_M_26."
    ))

    out = REPORTS_DIR / "consumption_report.pdf"
    pdf.output(str(out))
    log.info("Consumption report written -> %s", out)
    return out
