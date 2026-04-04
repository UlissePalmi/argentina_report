"""
Build the Argentina Macro Report.

Generates:
  - output/chart_trade.png
  - output/chart_reserves.png
  - output/chart_inflation.png
  - output/argentina_macro_report.md
  - output/argentina_macro_report.pdf
"""

from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from fpdf import FPDF, XPos, YPos

from utils import OUTPUT_DIR, get_logger

log = get_logger("build_report")

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

BLUE   = "#1864ab"
GREEN  = "#2f9e44"
RED    = "#c92a2a"
ORANGE = "#e67700"


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def chart_trade(df: pd.DataFrame | None) -> str | None:
    if df is None or df.empty:
        log.warning("chart_trade: no data — skipping")
        return None

    path = str(OUTPUT_DIR / "chart_trade.png")
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 4.5))
        dates = pd.to_datetime(df["date"])

        if "exports_usd_bn" in df.columns and "imports_usd_bn" in df.columns:
            ax.plot(dates, df["exports_usd_bn"], color=GREEN, label="Exports (FOB)", linewidth=2.2)
            ax.plot(dates, df["imports_usd_bn"], color=RED,   label="Imports (CIF)", linewidth=2.2)
            surplus = df["exports_usd_bn"] >= df["imports_usd_bn"]
            ax.fill_between(dates, df["exports_usd_bn"], df["imports_usd_bn"],
                            where=surplus,  alpha=0.12, color=GREEN)
            ax.fill_between(dates, df["exports_usd_bn"], df["imports_usd_bn"],
                            where=~surplus, alpha=0.12, color=RED)
        elif "trade_balance_usd_bn" in df.columns:
            colors = [GREEN if v >= 0 else RED for v in df["trade_balance_usd_bn"]]
            ax.bar(dates, df["trade_balance_usd_bn"], color=colors, width=20)

        ax.set_title("Trade Balance — Exports vs Imports", fontsize=13, fontweight="bold", pad=10)
        ax.set_ylabel("USD Billions")
        ax.axhline(0, color="#868e96", linewidth=0.8, linestyle="--")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45, ha="right", fontsize=8)
        ax.legend(framealpha=0.8, fontsize=9)
        ax.grid(True, axis="y", alpha=0.6)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    log.info("Chart saved: %s", path)
    return path


def chart_reserves(df: pd.DataFrame | None) -> str | None:
    if df is None or df.empty:
        log.warning("chart_reserves: no data — skipping")
        return None

    path = str(OUTPUT_DIR / "chart_reserves.png")
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 4.5))
        dates = pd.to_datetime(df["date"])
        col = "reserves_usd_bn" if "reserves_usd_bn" in df.columns else df.columns[-1]

        ax.plot(dates, df[col], color=BLUE, linewidth=2.4)
        ax.fill_between(dates, df[col], alpha=0.1, color=BLUE)

        last_val = df[col].dropna().iloc[-1]
        last_date = pd.to_datetime(df["date"].iloc[-1])
        ax.annotate(f"  ${last_val:.1f}bn", xy=(last_date, last_val),
                    fontsize=10, color=BLUE, va="center")

        ax.set_title("Gross International Reserves", fontsize=13, fontweight="bold", pad=10)
        ax.set_ylabel("USD Billions")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45, ha="right", fontsize=8)
        ax.grid(True, axis="y", alpha=0.6)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    log.info("Chart saved: %s", path)
    return path


def chart_inflation(df: pd.DataFrame | None) -> str | None:
    if df is None or df.empty:
        log.warning("chart_inflation: no data — skipping")
        return None

    path = str(OUTPUT_DIR / "chart_inflation.png")
    df12 = df.tail(12)

    with plt.rc_context(CHART_STYLE):
        fig, ax1 = plt.subplots(figsize=(10, 4.5))
        dates = pd.to_datetime(df12["date"])

        bar_colors = [RED if v > 5 else ORANGE if v > 2 else GREEN
                      for v in df12["cpi_mom_pct"].fillna(0)]
        ax1.bar(dates, df12["cpi_mom_pct"], color=bar_colors, width=20,
                label="MoM CPI % (LHS)")
        ax1.set_ylabel("Monthly CPI Change (%)")

        if "cpi_yoy_pct" in df12.columns and df12["cpi_yoy_pct"].notna().any():
            ax2 = ax1.twinx()
            ax2.plot(dates, df12["cpi_yoy_pct"], color=ORANGE, linewidth=2,
                     linestyle="--", label="Annual CPI % (RHS)")
            ax2.set_ylabel("Annual CPI Change (%)", color=ORANGE)
            ax2.tick_params(axis="y", labelcolor=ORANGE)
            lines2, labels2 = ax2.get_legend_handles_labels()
        else:
            lines2, labels2 = [], []

        ax1.set_title("CPI Inflation", fontsize=13, fontweight="bold", pad=10)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        plt.xticks(rotation=45, ha="right", fontsize=8)
        ax1.grid(True, axis="y", alpha=0.4)
        lines1, labels1 = ax1.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, framealpha=0.8, fontsize=9)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    log.info("Chart saved: %s", path)
    return path


# ---------------------------------------------------------------------------
# Text summaries
# ---------------------------------------------------------------------------
def _fmt_quarter(val) -> str:
    """Convert '2025Q4' → 'Q4 2025' for display."""
    s = str(val)
    if len(s) == 6 and "Q" in s:
        year, q = s.split("Q")
        return f"Q{q} {year}"
    return s


def _first_sentence(text: str) -> str:
    idx = text.find(". ")
    return text[:idx + 1] if idx != -1 else text.rstrip(".") + "."


def _summarise_dollars(trade_df, reserves_df, ca_df) -> str:
    parts = []
    if reserves_df is not None and not reserves_df.empty:
        col = "reserves_usd_bn"
        if col in reserves_df.columns:
            latest = reserves_df[col].dropna().iloc[-1]
            earliest = reserves_df[col].dropna().iloc[0]
            trend = "risen" if latest > earliest else "fallen"
            parts.append(
                f"Gross international reserves stand at ${latest:.1f} billion, "
                f"having {trend} from ${earliest:.1f} billion over the past "
                f"{len(reserves_df)} months."
            )
    if trade_df is not None and not trade_df.empty:
        if "trade_balance_usd_bn" in trade_df.columns:
            avg_bal = trade_df["trade_balance_usd_bn"].dropna().tail(4).mean()
            direction = "surplus" if avg_bal > 0 else "deficit"
            parts.append(
                f"The average monthly trade balance over the last four months is "
                f"${abs(avg_bal):.2f} billion — a trade {direction}."
            )
        if "exports_usd_bn" in trade_df.columns:
            exp_trend = trade_df["exports_usd_bn"].dropna().tail(6)
            slope = np.polyfit(range(len(exp_trend)), exp_trend, 1)[0]
            parts.append(f"Exports are {'rising' if slope > 0 else 'declining'} on recent trend.")
    if ca_df is not None and not ca_df.empty:
        col = [c for c in ca_df.columns if "current_account" in c]
        if col:
            latest_ca = ca_df[col[0]].dropna().iloc[-1]
            parts.append(
                f"The latest current account reading is {latest_ca:.2f}% of GDP "
                f"({'surplus' if latest_ca > 0 else 'deficit'})."
            )
    return " ".join(parts) if parts else "Insufficient data to assess the dollar situation."


def _summarise_inflation(cpi_df) -> str:
    if cpi_df is None or cpi_df.empty:
        return "CPI data unavailable."
    df = cpi_df.dropna(subset=["cpi_mom_pct"])
    if df.empty:
        return "CPI data unavailable."
    latest = df.iloc[-1]
    latest_date = pd.to_datetime(latest["date"]).strftime("%B %Y")
    peak_mom = df["cpi_mom_pct"].max()
    peak_date = pd.to_datetime(df.loc[df["cpi_mom_pct"].idxmax(), "date"]).strftime("%B %Y")
    current_mom = latest["cpi_mom_pct"]
    current_yoy = latest.get("cpi_yoy_pct", None)
    yoy_str = f", translating to a {current_yoy:.1f}% annual rate" if pd.notna(current_yoy) else ""
    slope = np.polyfit(range(3), df["cpi_mom_pct"].tail(3), 1)[0] if len(df) >= 3 else 0
    trend = " Inflation is on a downward trend." if slope < -0.5 else \
            " Inflation is on an upward trend." if slope > 0.5 else \
            " Monthly inflation has been roughly stable in recent months."
    return (
        f"Monthly CPI inflation in {latest_date} was {current_mom:.1f}%{yoy_str}. "
        f"The peak over the sample period was {peak_mom:.1f}% in {peak_date}.{trend}"
    )


def _summarise_gdp(gdp_df) -> str:
    if gdp_df is None or gdp_df.empty:
        return "GDP growth data unavailable."
    col = [c for c in gdp_df.columns if "gdp" in c]
    if not col:
        return "GDP growth data unavailable."
    df = gdp_df.dropna(subset=[col[0]])
    if df.empty:
        return "GDP growth data unavailable."
    latest = df.iloc[-1]
    latest_val = latest[col[0]]
    sign = "grew" if latest_val > 0 else "contracted"
    recent = df[col[0]].tail(3).tolist()
    accel = "accelerating" if len(recent) >= 2 and recent[-1] > recent[-2] else "decelerating"
    return (
        f"Real GDP {sign} by {abs(latest_val):.1f}% YoY in the latest period ({latest['date']}). "
        f"The economy appears to be {accel} based on the last three readings "
        f"({', '.join(f'{v:.1f}%' for v in recent)})."
    )


# ---------------------------------------------------------------------------
# PDF builder
# ---------------------------------------------------------------------------
def _safe(text: str) -> str:
    """Replace characters outside Latin-1 with safe ASCII equivalents."""
    return (text
            .replace("\u2014", "--")   # em dash
            .replace("\u2013", "-")    # en dash
            .replace("\u2019", "'")    # right single quote
            .replace("\u2018", "'")    # left single quote
            .replace("\u201c", '"')    # left double quote
            .replace("\u201d", '"')    # right double quote
            .replace("\u2192", "->")   # rightwards arrow
            .replace("\u2022", "*")    # bullet
            .encode("latin-1", errors="replace").decode("latin-1"))


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
        img_h = avail_w * 0.45         # preserve ~10:4.5 aspect ratio
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
        """Render a pandas DataFrame as a PDF table."""
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

        # Header row
        self.set_font("Helvetica", "B", 8.5)
        self.set_fill_color(30, 100, 200)
        self.set_text_color(255, 255, 255)
        for c in cols:
            label = c.replace("_", " ").replace("usd bn", "(USD bn)").replace("pct", "%").title()
            self.cell(col_w, 6, label, border=0, fill=True, align="C")
        self.ln()

        # Data rows
        self.set_font("Helvetica", "", 8.5)
        for i, (_, row) in enumerate(subset.iterrows()):
            bg = (240, 247, 255) if i % 2 == 0 else (255, 255, 255)
            self.set_fill_color(*bg)
            self.set_text_color(40, 40, 40)
            for c in cols:
                v = row[c]
                if c == "date" or (hasattr(v, "strftime")):
                    try:
                        cell_str = pd.to_datetime(v).strftime("%Y-%m-%d")
                    except Exception:
                        cell_str = str(v).split(" ")[0]
                else:
                    f = fmt.get(c, "{}")
                    try:
                        cell_str = f.format(v)
                    except Exception:
                        cell_str = str(v)
                self.cell(col_w, 5.5, _safe(cell_str), border=0, fill=True, align="C")
            self.ln()

        self.set_draw_color(200, 200, 200)
        self.line(self.MARGIN, self.get_y(), self.PAGE_W - self.MARGIN, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------
def build_report(
    trade_df: pd.DataFrame | None,
    reserves_df: pd.DataFrame | None,
    cpi_df: pd.DataFrame | None,
    gdp_df: pd.DataFrame | None,
    ca_df: pd.DataFrame | None,
    gdp_components_df: pd.DataFrame | None = None,
) -> dict[str, Path]:
    """
    Build charts, markdown report, and PDF.
    Returns dict with keys 'md' and 'pdf' pointing to output files.
    """
    # --- Charts ---
    trade_chart  = chart_trade(trade_df)
    res_chart    = chart_reserves(reserves_df)
    inf_chart    = chart_inflation(cpi_df)

    # --- Summaries ---
    dollars_text   = _summarise_dollars(trade_df, reserves_df, ca_df)
    inflation_text = _summarise_inflation(cpi_df)
    gdp_text       = _summarise_gdp(gdp_df)
    synthesis = (
        "Argentina's macroeconomic picture remains complex. "
        + _first_sentence(dollars_text) + " "
        + _first_sentence(inflation_text) + " "
        + _first_sentence(gdp_text) + " "
        "Sustained fiscal adjustment and reserve accumulation will be critical "
        "to anchor expectations and restore sustainable growth."
    )

    # =========================================================
    # PDF
    # =========================================================
    today = date.today().strftime("%B %d, %Y")

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

    # ------ Section 1: Dollar Situation ------
    pdf.section_title("1. Dollar Situation")
    pdf.body_text(dollars_text)

    if ca_df is not None and not ca_df.empty:
        ca_col = [c for c in ca_df.columns if "current_account" in c]
        if ca_col:
            pdf.add_table(
                ca_df.tail(8), ["date", ca_col[0]],
                fmt={ca_col[0]: "{:.2f}%"},
                title="Current Account Balance (% of GDP, last 8 years)"
            )

    if trade_df is not None and not trade_df.empty:
        trade_cols = [c for c in ["exports_usd_bn", "imports_usd_bn", "trade_balance_usd_bn"]
                      if c in trade_df.columns]
        if trade_cols:
            pdf.add_table(
                trade_df, ["date"] + trade_cols,
                fmt={c: "${:.2f}bn" for c in trade_cols},
                title="Trade Balance (last 12 months, USD billions)"
            )

    pdf.add_chart(trade_chart,  "Figure 1: Exports vs Imports (USD billions)")
    pdf.add_chart(res_chart,    "Figure 2: Gross International Reserves (USD billions)")

    # ------ Section 2: Inflation ------
    pdf.section_title("2. Inflation")
    pdf.body_text(inflation_text)

    if cpi_df is not None and not cpi_df.empty:
        cpi_cols = [c for c in ["cpi_mom_pct", "cpi_yoy_pct"] if c in cpi_df.columns]
        if cpi_cols:
            pdf.add_table(
                cpi_df.tail(12), ["date"] + cpi_cols,
                fmt={c: "{:.1f}%" for c in cpi_cols},
                title="CPI Inflation (last 12 months)"
            )

    pdf.add_chart(inf_chart, "Figure 3: Monthly and Annual CPI Inflation (%)")

    # ------ Section 3: Real GDP ------
    pdf.section_title("3. Real GDP")
    pdf.body_text(gdp_text)

    if gdp_df is not None and not gdp_df.empty:
        gdp_col = [c for c in gdp_df.columns if "gdp" in c]
        if gdp_col:
            gdp_display = gdp_df.tail(8).copy()
            gdp_display["quarter"] = gdp_display["date"].apply(_fmt_quarter)
            pdf.add_table(
                gdp_display, ["quarter", gdp_col[0]],
                fmt={gdp_col[0]: "{:.1f}%"},
                title="Real GDP Growth YoY (last 8 periods)"
            )

    # ------ GDP Components table ------
    if gdp_components_df is not None and not gdp_components_df.empty:
        comp_cols = ["C_pct", "G_pct", "I_pct", "X_pct", "M_pct", "GDP_pct"]
        comp_fmt = {c: "{:.1f}%" for c in comp_cols}
        pdf.add_table(
            gdp_components_df, ["quarter"] + comp_cols,
            fmt=comp_fmt,
            title="GDP Expenditure Components — YoY Growth (C, G, I, X, M, GDP)"
        )

    # ------ Summary ------
    pdf.section_title("Summary")
    pdf.body_text(synthesis)

    # Footer note
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 4.5, _safe(
        "Data sources: BCRA / Argentina Open Data API (apis.datos.gob.ar), "
        "World Bank (api.worldbank.org), IMF BOP (dataservices.imf.org -- fallback to WB when unavailable)."
    ))

    pdf_path = OUTPUT_DIR / "argentina_macro_report.pdf"
    pdf.output(str(pdf_path))
    log.info("PDF written → %s", pdf_path)

    # =========================================================
    # Markdown (kept as a companion)
    # =========================================================
    def img(p):
        return f"![chart](output/{Path(p).name})\n" if p else "_Chart unavailable._\n"

    def md_table(df, cols, fmt=None):
        fmt = fmt or {}
        subset = df[cols].dropna().tail(12)
        header = "| " + " | ".join(cols) + " |"
        sep    = "| " + " | ".join(["---"] * len(cols)) + " |"
        rows = []
        for _, row in subset.iterrows():
            cells = []
            for c in cols:
                v = row[c]
                if c == "date":
                    try:
                        cells.append(pd.to_datetime(v).strftime("%Y-%m-%d"))
                    except Exception:
                        cells.append(str(v).split(" ")[0])
                    continue
                f = fmt.get(c, "{}")
                try:
                    cells.append(f.format(v))
                except Exception:
                    cells.append(str(v))
            rows.append("| " + " | ".join(cells) + " |")
        return "\n".join([header, sep] + rows)

    ca_table = trade_table = cpi_table = gdp_table = ""
    if ca_df is not None and not ca_df.empty:
        ca_col = [c for c in ca_df.columns if "current_account" in c]
        if ca_col:
            ca_table = "\n**Current Account Balance (last 8 years)**\n\n" + \
                       md_table(ca_df.tail(8), ["date", ca_col[0]], fmt={ca_col[0]: "{:.2f}%"})
    if trade_df is not None and not trade_df.empty:
        tc = [c for c in ["exports_usd_bn","imports_usd_bn","trade_balance_usd_bn"] if c in trade_df.columns]
        if tc:
            trade_table = "\n**Trade Balance (last 12 months)**\n\n" + \
                          md_table(trade_df, ["date"]+tc, fmt={c:"${:.2f}bn" for c in tc})
    if cpi_df is not None and not cpi_df.empty:
        cc = [c for c in ["cpi_mom_pct","cpi_yoy_pct"] if c in cpi_df.columns]
        if cc:
            cpi_table = "\n**CPI Inflation (last 12 months)**\n\n" + \
                        md_table(cpi_df.tail(12), ["date"]+cc, fmt={c:"{:.1f}%" for c in cc})
    if gdp_df is not None and not gdp_df.empty:
        gc = [c for c in gdp_df.columns if "gdp" in c]
        if gc:
            gdp_display = gdp_df.tail(8).copy()
            gdp_display["quarter"] = gdp_display["date"].apply(_fmt_quarter)
            gdp_table = "\n**Real GDP Growth YoY (last 8 periods)**\n\n" + \
                        md_table(gdp_display, ["quarter", gc[0]], fmt={gc[0]:"{:.1f}%"})
    if gdp_components_df is not None and not gdp_components_df.empty:
        comp_cols = ["C_pct", "G_pct", "I_pct", "X_pct", "M_pct", "GDP_pct"]
        gdp_table += "\n\n**GDP Expenditure Components — YoY Growth**\n\n" + \
                     md_table(gdp_components_df, ["quarter"] + comp_cols,
                              fmt={c: "{:.1f}%" for c in comp_cols})

    md = f"""# Argentina Macro Report
*Generated {today}*

---

## 1. Dollar Situation

{dollars_text}
{ca_table}
{trade_table}

{img(trade_chart)}{img(res_chart)}

---

## 2. Inflation

{inflation_text}
{cpi_table}

{img(inf_chart)}

---

## 3. Real GDP

{gdp_text}
{gdp_table}

---

## Summary

{synthesis}

---
*Data sources: BCRA / Argentina Open Data API (apis.datos.gob.ar), World Bank (api.worldbank.org),
IMF BOP (dataservices.imf.org — fallback to WB when unavailable).*
"""

    md_path = OUTPUT_DIR / "argentina_macro_report.md"
    md_path.write_text(md, encoding="utf-8")
    log.info("Markdown written → %s", md_path)

    return {"md": md_path, "pdf": pdf_path}


if __name__ == "__main__":
    build_report(None, None, None, None, None)
