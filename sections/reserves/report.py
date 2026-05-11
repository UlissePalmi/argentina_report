"""
BCRA Reserves deep-dive report.

Covers:
  1. KPI snapshot: gross reserves, net reserves, import coverage, FX rate
  2. Gross vs net reserves (24-month trend)
  3. Import coverage ratio (months of imports covered)
  4. External flows: trade balance (monthly) + current account (quarterly)
  5. FX rate (ARS/USD)
  6. Reserves vs M2 monetary coverage

Output: data/reports/reserves_report.pdf
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from fpdf import XPos, YPos

from report.build import ArgentinaPDF, _safe
from utils import CHARTS_DIR, REPORTS_DIR, get_logger

log = get_logger("reserves.report")

BLUE   = "#1971c2"
ORANGE = "#e67700"
GREEN  = "#2f9e44"
RED    = "#c92a2a"
GREY   = "#868e96"
TEAL   = "#0c8599"

CHART_STYLE = {
    "figure.facecolor": "#ffffff",
    "axes.facecolor":   "#f8f9fa",
    "axes.edgecolor":   "#dee2e6",
    "axes.labelcolor":  "#212529",
    "xtick.color":      "#495057",
    "ytick.color":      "#495057",
    "text.color":       "#212529",
    "grid.color":       "#dee2e6",
    "grid.linewidth":   0.8,
    "lines.linewidth":  2.0,
    "font.family":      "DejaVu Sans",
}


class ReservesPDF(ArgentinaPDF):
    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(130, 130, 130)
        self.cell(0, 8, "Argentina -- BCRA Reserves Report",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")
        self.set_draw_color(200, 200, 200)
        self.line(self.MARGIN, self.get_y(), self.PAGE_W - self.MARGIN, self.get_y())
        self.ln(2)

    def footer(self):
        self.set_y(-13)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def subsection(self, text: str):
        self.ln(3)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(60, 60, 140)
        self.cell(0, 7, _safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.ln(1)

    def note(self, text: str):
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(110, 110, 110)
        self.multi_cell(0, 4.5, _safe(text))
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def formula_block(self, lines: list[tuple[str, str]]):
        """Render a formula box. Each tuple is (bold_prefix, normal_text)."""
        avail = self.PAGE_W - 2 * self.MARGIN
        self.set_fill_color(240, 244, 255)
        self.set_draw_color(180, 200, 240)
        x0, y0 = self.MARGIN, self.get_y()
        row_h = 5.5
        pad   = 3
        total_h = len(lines) * row_h + 2 * pad
        self.rect(x0, y0, avail, total_h, style="DF")
        self.set_y(y0 + pad)
        for bold, normal in lines:
            self.set_x(x0 + pad)
            if bold:
                self.set_font("Courier", "B", 8.5)
                self.set_text_color(20, 60, 140)
                self.cell(self.get_string_width(bold) + 1, row_h, _safe(bold))
            self.set_font("Courier", "", 8.5)
            self.set_text_color(40, 40, 40)
            self.cell(avail - pad * 2, row_h, _safe(normal), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_y(y0 + total_h + 3)
        self.set_text_color(0, 0, 0)

    def kpi_row(self, items: list[tuple[str, str, str]]):
        n = len(items)
        avail = self.PAGE_W - 2 * self.MARGIN
        box_w = avail / n
        box_h = 18
        x0, y0 = self.MARGIN, self.get_y()
        for i, (label, value, sub) in enumerate(items):
            x = x0 + i * box_w
            self.set_fill_color(240, 246, 255)
            self.rect(x, y0, box_w - 1, box_h, style="F")
            self.set_xy(x, y0 + 2)
            self.set_font("Helvetica", "", 7.5)
            self.set_text_color(80, 80, 80)
            self.cell(box_w - 1, 5, _safe(label), align="C")
            self.set_xy(x, y0 + 7)
            self.set_font("Helvetica", "B", 12)
            self.set_text_color(20, 80, 160)
            self.cell(box_w - 1, 6, _safe(value), align="C")
            self.set_xy(x, y0 + 13)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(120, 120, 120)
            self.cell(box_w - 1, 4, _safe(sub), align="C")
        self.set_xy(self.MARGIN, y0 + box_h + 2)
        self.set_text_color(0, 0, 0)
        self.ln(2)


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def _chart(path: str, fig, ax_or_axes=None):
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info("Chart saved: %s", path)
    return path


def chart_reserves_trend(reserves_df: pd.DataFrame) -> str | None:
    df = reserves_df.dropna(subset=["reserves_usd_bn"]).copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.tail(36)
    if df.empty:
        return None
    path = str(CHARTS_DIR / "res_trend.png")
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.fill_between(df["date"], df["reserves_usd_bn"], alpha=0.12, color=BLUE)
        ax.plot(df["date"], df["reserves_usd_bn"], color=BLUE, linewidth=2.2,
                label="Gross reserves")
        if "net_reserves_usd_bn" in df.columns:
            net = df["net_reserves_usd_bn"]
            ax.plot(df["date"], net, color=ORANGE, linewidth=1.8,
                    linestyle="--", label="Net reserves (est.)")
            ax.fill_between(df["date"], net, alpha=0.08, color=ORANGE)
        ax.axhline(0, color=RED, linewidth=0.9, linestyle=":", alpha=0.7)
        last = df.iloc[-1]
        ax.annotate(f"${last['reserves_usd_bn']:.1f}B",
                    xy=(last["date"], last["reserves_usd_bn"]),
                    xytext=(8, 4), textcoords="offset points",
                    fontsize=8, color=BLUE, fontweight="bold")
        if "net_reserves_usd_bn" in df.columns and pd.notna(last.get("net_reserves_usd_bn")):
            ax.annotate(f"${last['net_reserves_usd_bn']:.1f}B (net)",
                        xy=(last["date"], last["net_reserves_usd_bn"]),
                        xytext=(8, -12), textcoords="offset points",
                        fontsize=8, color=ORANGE)
        ax.set_ylabel("USD billions", fontsize=9)
        ax.set_title("BCRA International Reserves -- Gross vs Net", fontsize=13,
                     fontweight="bold", pad=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45, ha="right", fontsize=8)
        ax.legend(framealpha=0.8, fontsize=9)
        ax.grid(True, axis="y", alpha=0.4)
    return _chart(path, fig)


def chart_import_coverage(reserves_df: pd.DataFrame,
                           trade_df: pd.DataFrame) -> str | None:
    res = reserves_df.dropna(subset=["reserves_usd_bn"]).copy()
    res["date"] = pd.to_datetime(res["date"])
    trd = trade_df.dropna(subset=["imports_usd_bn"]).copy()
    trd["date"] = pd.to_datetime(trd["date"])

    # 3-month rolling average of imports as denominator
    trd = trd.sort_values("date")
    trd["imports_3m"] = trd["imports_usd_bn"].rolling(3).mean()

    merged = pd.merge(res, trd[["date", "imports_3m"]], on="date", how="inner")
    merged = merged.dropna(subset=["imports_3m"])
    merged["coverage_months"] = merged["reserves_usd_bn"] / merged["imports_3m"]
    merged = merged.tail(36)
    if merged.empty:
        return None

    path = str(CHARTS_DIR / "res_import_coverage.png")
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 3.8))
        ax.fill_between(merged["date"], merged["coverage_months"],
                        alpha=0.15, color=TEAL)
        ax.plot(merged["date"], merged["coverage_months"],
                color=TEAL, linewidth=2.2)
        # IMF adequacy threshold: 3 months
        ax.axhline(3, color=ORANGE, linewidth=1.2, linestyle="--",
                   label="IMF adequacy threshold (3 months)", alpha=0.9)
        last = merged.iloc[-1]
        ax.annotate(f"{last['coverage_months']:.1f} months",
                    xy=(last["date"], last["coverage_months"]),
                    xytext=(8, 4), textcoords="offset points",
                    fontsize=8, color=TEAL, fontweight="bold")
        ax.set_ylabel("Months of imports", fontsize=9)
        ax.set_title("Import Coverage Ratio (Gross Reserves / 3m Avg Imports)",
                     fontsize=12, fontweight="bold", pad=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45, ha="right", fontsize=8)
        ax.legend(framealpha=0.8, fontsize=9)
        ax.grid(True, axis="y", alpha=0.4)
    return _chart(path, fig)


def chart_trade(trade_df: pd.DataFrame) -> str | None:
    df = trade_df.dropna(subset=["exports_usd_bn", "imports_usd_bn"]).copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.tail(30).sort_values("date")
    if df.empty:
        return None
    path = str(CHARTS_DIR / "res_trade.png")
    with plt.rc_context(CHART_STYLE):
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

        # Top: exports & imports as lines
        ax1.plot(df["date"], df["exports_usd_bn"], color=GREEN,
                 linewidth=2, label="Exports")
        ax1.plot(df["date"], df["imports_usd_bn"], color=RED,
                 linewidth=2, label="Imports")
        ax1.set_ylabel("USD billions", fontsize=9)
        ax1.set_title("Trade Balance -- Monthly", fontsize=12,
                      fontweight="bold", pad=8)
        ax1.legend(framealpha=0.8, fontsize=9)
        ax1.grid(True, axis="y", alpha=0.4)

        # Bottom: net balance as bars
        colors = [GREEN if v >= 0 else RED for v in df["trade_balance_usd_bn"]]
        ax2.bar(df["date"], df["trade_balance_usd_bn"],
                width=20, color=colors, alpha=0.8, label="Trade balance")
        ax2.axhline(0, color=GREY, linewidth=0.8)
        ax2.set_ylabel("USD billions", fontsize=9)
        ax2.legend(framealpha=0.8, fontsize=9)
        ax2.grid(True, axis="y", alpha=0.4)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45, ha="right", fontsize=8)
        fig.subplots_adjust(hspace=0.08)
    return _chart(path, fig)


def chart_current_account(ca_df: pd.DataFrame) -> str | None:
    df = ca_df.dropna(subset=["current_account_usd_bn"]).copy()
    if "quarter_start" in df.columns:
        df["date"] = pd.to_datetime(df["quarter_start"])
    else:
        df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").tail(24)
    if df.empty:
        return None
    path = str(CHARTS_DIR / "res_ca.png")
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 3.5))
        colors = [GREEN if v >= 0 else RED for v in df["current_account_usd_bn"]]
        ax.bar(df["date"], df["current_account_usd_bn"],
               width=55, color=colors, alpha=0.8)
        ax.axhline(0, color=GREY, linewidth=0.8)
        # 4-quarter rolling sum
        df = df.copy()
        df["rolling_4q"] = df["current_account_usd_bn"].rolling(4).sum()
        ax2 = ax.twinx()
        ax2.plot(df["date"], df["rolling_4q"], color=BLUE,
                 linewidth=1.6, linestyle="--", label="Rolling 4Q sum")
        ax2.set_ylabel("4Q rolling sum (USD bn)", fontsize=8, color=BLUE)
        ax2.tick_params(axis="y", labelcolor=BLUE)
        ax.set_ylabel("USD billions (quarterly)", fontsize=9)
        ax.set_title("Current Account Balance (Quarterly)", fontsize=12,
                     fontweight="bold", pad=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%YQ"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
        plt.xticks(rotation=45, ha="right", fontsize=8)
        ax.grid(True, axis="y", alpha=0.3)
        ax2.legend(loc="upper left", framealpha=0.8, fontsize=8)
    return _chart(path, fig)


def chart_fx(fx_df: pd.DataFrame) -> str | None:
    df = fx_df.dropna(subset=["usd_ars"]).copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.tail(36).sort_values("date")
    if df.empty:
        return None
    path = str(CHARTS_DIR / "res_fx.png")
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 3.5))
        PURPLE = "#7048e8"
        ax.fill_between(df["date"], df["usd_ars"], alpha=0.1, color=PURPLE)
        ax.plot(df["date"], df["usd_ars"], color=PURPLE, linewidth=2)
        last = df.iloc[-1]
        ax.annotate(f"ARS {last['usd_ars']:,.0f}",
                    xy=(last["date"], last["usd_ars"]),
                    xytext=(8, -12), textcoords="offset points",
                    fontsize=8, color=PURPLE, fontweight="bold")
        ax.set_ylabel("ARS per USD", fontsize=9)
        ax.set_title("Official Exchange Rate (ARS/USD)", fontsize=12,
                     fontweight="bold", pad=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45, ha="right", fontsize=8)
        ax.grid(True, axis="y", alpha=0.4)
    return _chart(path, fig)


def chart_reserves_vs_m2(reserves_df: pd.DataFrame,
                          fx_df: pd.DataFrame,
                          m2_df: pd.DataFrame) -> str | None:
    res = reserves_df.dropna(subset=["reserves_usd_bn"]).copy()
    res["date"] = pd.to_datetime(res["date"])
    fx  = fx_df.dropna(subset=["usd_ars"]).copy()
    fx["date"] = pd.to_datetime(fx["date"])
    m2  = m2_df.dropna(subset=["m2_ars_bn"]).copy()
    m2["date"] = pd.to_datetime(m2["date"])

    df = res.merge(fx, on="date").merge(m2, on="date")
    df["reserves_ars_bn"] = df["reserves_usd_bn"] * df["usd_ars"]
    df["reserves_pct_m2"] = df["reserves_ars_bn"] / df["m2_ars_bn"] * 100
    df = df.tail(36).sort_values("date")
    if df.empty:
        return None

    path = str(CHARTS_DIR / "res_m2.png")
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 3.5))
        ax.fill_between(df["date"], df["reserves_pct_m2"], alpha=0.12, color=GREEN)
        ax.plot(df["date"], df["reserves_pct_m2"], color=GREEN, linewidth=2)
        last = df.iloc[-1]
        ax.annotate(f"{last['reserves_pct_m2']:.0f}%",
                    xy=(last["date"], last["reserves_pct_m2"]),
                    xytext=(8, 4), textcoords="offset points",
                    fontsize=8, color=GREEN, fontweight="bold")
        ax.set_ylabel("Reserves / M2 (%)", fontsize=9)
        ax.set_title("Monetary Coverage: Gross Reserves as % of M2",
                     fontsize=12, fontweight="bold", pad=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45, ha="right", fontsize=8)
        ax.grid(True, axis="y", alpha=0.4)
    return _chart(path, fig)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_reserves_report(
    reserves_df: pd.DataFrame | None,
    fx_df:       pd.DataFrame | None,
    trade_df:    pd.DataFrame | None,
    ca_df:       pd.DataFrame | None,
    m2_df:       pd.DataFrame | None,
) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    out = REPORTS_DIR / "reserves_report.pdf"
    pdf = ReservesPDF()
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(20, 60, 140)
    pdf.cell(0, 12, "Argentina -- BCRA Reserves", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, "Sources: BCRA via datos.gob.ar | INDEC | IMF",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(4)

    # KPI snapshot
    gross, net, coverage, rate = "n/a", "n/a", "n/a", "n/a"
    if reserves_df is not None and not reserves_df.empty:
        last_res = reserves_df.dropna(subset=["reserves_usd_bn"]).iloc[-1]
        gross = f"${last_res['reserves_usd_bn']:.1f}B"
        if pd.notna(last_res.get("net_reserves_usd_bn")):
            net = f"${last_res['net_reserves_usd_bn']:.1f}B"

    if (reserves_df is not None and trade_df is not None
            and not reserves_df.empty and not trade_df.empty):
        try:
            res_last = reserves_df.dropna(subset=["reserves_usd_bn"]).iloc[-1]
            imp_avg  = (trade_df.dropna(subset=["imports_usd_bn"])
                        .tail(3)["imports_usd_bn"].mean())
            coverage = f"{res_last['reserves_usd_bn'] / imp_avg:.1f} months"
        except Exception:
            pass

    if fx_df is not None and not fx_df.empty:
        last_fx = fx_df.dropna(subset=["usd_ars"]).iloc[-1]
        rate = f"ARS {last_fx['usd_ars']:,.0f}"

    pdf.kpi_row([
        ("Gross Reserves",    gross,    "latest month"),
        ("Net Reserves",      net,      "est. excl. swaps/repos"),
        ("Import Coverage",   coverage, "gross / 3m avg imports"),
        ("Official FX Rate",  rate,     "ARS per USD"),
    ])

    # Section 1: Reserves trend
    pdf.subsection("1. Gross vs Net Reserves")
    if reserves_df is not None:
        p = chart_reserves_trend(reserves_df)
        if p:
            pdf.image(p, w=pdf.PAGE_W - 2 * pdf.MARGIN)
    pdf.note(
        "Gross reserves = total BCRA international assets (USD, gold, SDRs, repo). "
        "Net reserves estimate excludes swap lines (mainly China), repo obligations, "
        "and IMF deposits. Source: BCRA via datos.gob.ar."
    )

    # Section 2: Import coverage
    pdf.subsection("2. Import Coverage Ratio")
    if reserves_df is not None and trade_df is not None:
        p = chart_import_coverage(reserves_df, trade_df)
        if p:
            pdf.image(p, w=pdf.PAGE_W - 2 * pdf.MARGIN)
    pdf.note(
        "Months of imports covered by gross reserves, using a 3-month rolling average of "
        "imports as the denominator. IMF adequacy benchmark: 3 months of imports. "
        "Sources: BCRA reserves, INDEC trade."
    )

    # Section 3: External flows (trade balance + current account)
    pdf.add_page()
    pdf.subsection("3. External Flows")
    pdf.formula_block([
        ("CA  =", "  Goods trade balance  +  Services balance"),
        ("",      "      +  Primary income  (investment returns, profit remittances, interest)"),
        ("",      "      +  Secondary income  (transfers, remittances)"),
        ("",      ""),
        ("Goods trade balance  =", "  Exports of goods  -  Imports of goods  [monthly, INDEC]"),
        ("CA  [quarterly, BOP]=", "  Goods + Services + Primary income + Secondary income"),
    ])
    pdf.body_text(
        "The trade balance (goods, monthly) is the highest-frequency read on Argentina's "
        "external position. The current account (quarterly, BOP basis) adds services, "
        "primary income (investment returns, profit remittances), and secondary income "
        "(transfers). Together they determine whether the external sector is a net source "
        "or drain on reserves."
    )
    if trade_df is not None:
        p = chart_trade(trade_df)
        if p:
            pdf.image(p, w=pdf.PAGE_W - 2 * pdf.MARGIN)
    pdf.note(
        "Monthly goods exports and imports (USD bn). Bottom panel: goods trade balance "
        "(green = surplus, red = deficit). Source: INDEC via datos.gob.ar."
    )
    if ca_df is not None:
        p = chart_current_account(ca_df)
        if p:
            pdf.image(p, w=pdf.PAGE_W - 2 * pdf.MARGIN)
    pdf.note(
        "Quarterly current account balance (USD bn, bars). "
        "Dashed line = 4-quarter rolling sum (proxy for annual CA position). "
        "Includes goods, services, primary income, and secondary income. "
        "Source: IMF BOP data."
    )

    # Section 4: FX rate
    pdf.add_page()
    pdf.subsection("4. Official Exchange Rate")
    if fx_df is not None:
        p = chart_fx(fx_df)
        if p:
            pdf.image(p, w=pdf.PAGE_W - 2 * pdf.MARGIN)
    pdf.note(
        "Monthly average official ARS/USD rate. Source: BCRA via datos.gob.ar."
    )

    # Section 5: Monetary coverage
    pdf.subsection("5. Monetary Coverage (Reserves / M2)")
    if reserves_df is not None and fx_df is not None and m2_df is not None:
        p = chart_reserves_vs_m2(reserves_df, fx_df, m2_df)
        if p:
            pdf.image(p, w=pdf.PAGE_W - 2 * pdf.MARGIN)
    pdf.note(
        "Gross reserves converted to ARS at the official rate, expressed as a percentage of M2. "
        "A higher ratio indicates greater monetary backing for the peso. "
        "Sources: BCRA reserves, BCRA official FX, BCRA M2."
    )

    pdf.output(str(out))
    log.info("Reserves report written: %s", out)
    return out
