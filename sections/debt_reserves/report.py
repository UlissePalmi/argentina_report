"""
Debt & Reserves deep-dive report.

Covers:
  1. BCRA reserves (gross vs net estimate)
  2. Exchange rate (ARS/USD)
  3. External debt by sector — full INDEC IIP breakdown
  4. Government external debt — bonds vs loans
  5. Trade balance & current account
  6. Debt service ratios (World Bank)

Output: data/reports/debt_reserves_report.pdf
"""

from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import pandas as pd
from fpdf import XPos, YPos

from report.build import ArgentinaPDF, _safe
from utils import CHARTS_DIR, REPORTS_DIR, get_logger

log = get_logger("debt_reserves.report")

BLUE    = "#1971c2"
ORANGE  = "#e67700"
GREEN   = "#2f9e44"
RED     = "#c92a2a"
GREY    = "#868e96"
PURPLE  = "#7048e8"
TEAL    = "#0c8599"

SECTOR_COLORS = [BLUE, ORANGE, GREEN, PURPLE]

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


class DebtReservesPDF(ArgentinaPDF):
    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(130, 130, 130)
        self.cell(0, 8, "Argentina -- Debt & Reserves Report",
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

    def kpi_row(self, items: list[tuple[str, str, str]]):
        """Render a row of KPI boxes: [(label, value, sub), ...]."""
        n = len(items)
        avail = self.PAGE_W - 2 * self.MARGIN
        box_w = avail / n
        box_h = 18
        x0 = self.MARGIN
        y0 = self.get_y()
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

def chart_reserves(reserves_df: pd.DataFrame) -> str | None:
    df = reserves_df.dropna(subset=["reserves_usd_bn"]).copy()
    df["date"] = pd.to_datetime(df["date"])
    if df.empty:
        return None
    path = str(CHARTS_DIR / "dr_reserves.png")
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.fill_between(df["date"], df["reserves_usd_bn"], alpha=0.15, color=BLUE)
        ax.plot(df["date"], df["reserves_usd_bn"], color=BLUE, linewidth=2.2,
                label="Gross reserves")
        if "net_reserves_usd_bn" in df.columns:
            net = df["net_reserves_usd_bn"]
            ax.plot(df["date"], net, color=ORANGE, linewidth=1.8,
                    linestyle="--", label="Net reserves (est.)")
            ax.fill_between(df["date"], net, alpha=0.08, color=ORANGE)
        ax.axhline(0, color=RED, linewidth=0.8, linestyle=":", alpha=0.7)
        ax.set_ylabel("USD billions", fontsize=9)
        ax.set_title("BCRA International Reserves", fontsize=13, fontweight="bold", pad=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45, ha="right", fontsize=8)
        ax.legend(framealpha=0.8, fontsize=9)
        ax.grid(True, axis="y", alpha=0.4)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    log.info("Chart saved: %s", path)
    return path


def chart_fx(fx_df: pd.DataFrame) -> str | None:
    df = fx_df.dropna(subset=["usd_ars"]).copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.tail(36)
    if df.empty:
        return None
    path = str(CHARTS_DIR / "dr_fx.png")
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 3.5))
        ax.plot(df["date"], df["usd_ars"], color=ORANGE, linewidth=2.2)
        ax.fill_between(df["date"], df["usd_ars"], alpha=0.1, color=ORANGE)
        ax.set_ylabel("ARS per USD", fontsize=9)
        ax.set_title("Official Exchange Rate (ARS/USD)", fontsize=13, fontweight="bold", pad=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45, ha="right", fontsize=8)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
        ax.grid(True, axis="y", alpha=0.4)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    log.info("Chart saved: %s", path)
    return path


def chart_ext_debt_by_sector(df: pd.DataFrame) -> str | None:
    # Include S12R (other financial) if available
    base_cols  = ["govt_total_usd_bn", "bcra_total_usd_bn", "banks_total_usd_bn", "private_total_usd_bn"]
    extra_cols = ["other_fin_total_usd_bn"]
    needed = [c for c in base_cols if c in df.columns]
    if not needed:
        return None
    has_other = all(c in df.columns for c in extra_cols)

    cols   = needed + ([extra_cols[0]] if has_other else [])
    labels = (["Government (S13)", "BCRA (S121)", "Banks (S122)", "Private (S1V)"] +
              (["Other financial (S12R)"] if has_other else []))
    colors = SECTOR_COLORS[:len(needed)] + ([TEAL] if has_other else [])

    plot_df = df.dropna(subset=needed).tail(16).copy()
    if plot_df.empty:
        return None

    dates = pd.to_datetime(plot_df["quarter_start"]).tolist()
    path  = str(CHARTS_DIR / "dr_ext_debt_sector.png")
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 5))
        bar_w = max(30, int((dates[-1] - dates[0]).days / len(dates) * 0.55)) if len(dates) > 1 else 60
        bottoms = [0.0] * len(dates)
        for col, label, color in zip(cols, labels, colors):
            vals = plot_df[col].fillna(0).tolist()
            ax.bar(dates, vals, width=bar_w, bottom=bottoms, color=color,
                   alpha=0.85, label=label)
            bottoms = [b + v for b, v in zip(bottoms, vals)]

        for d, b in zip(dates, bottoms):
            ax.text(d, b + 2, f"${b:.0f}B", ha="center", va="bottom", fontsize=7, color="#212529")

        ax.set_ylabel("USD billions", fontsize=9)
        ax.set_title("Argentina Gross External Debt by Sector -- Nominal Value (INDEC EDE)",
                     fontsize=13, fontweight="bold", pad=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45, ha="right", fontsize=8)
        ax.legend(framealpha=0.8, fontsize=9, loc="upper left")
        ax.grid(True, axis="y", alpha=0.4)
        ax.set_ylim(0, max(bottoms) * 1.12)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    log.info("Chart saved: %s", path)
    return path


def chart_sector_donut(df: pd.DataFrame) -> str | None:
    base_cols = ["govt_total_usd_bn", "bcra_total_usd_bn", "banks_total_usd_bn", "private_total_usd_bn"]
    all_cols  = base_cols + (["other_fin_total_usd_bn"] if "other_fin_total_usd_bn" in df.columns else [])
    needed    = [c for c in all_cols if c in df.columns]
    if not needed:
        return None
    row  = df.dropna(subset=needed).iloc[-1]
    vals = [row[c] for c in needed]
    label_names = ["Government", "BCRA", "Banks", "Private", "Other fin."]
    colors = SECTOR_COLORS + [TEAL]
    labels = [f"{label_names[i]}\n${vals[i]:.0f}B" for i in range(len(needed))]

    path = str(CHARTS_DIR / "dr_sector_donut.png")
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(6, 5))
        wedges, texts, autotexts = ax.pie(
            vals, labels=labels, colors=colors[:len(needed)],
            autopct="%1.1f%%", startangle=90,
            wedgeprops={"linewidth": 1, "edgecolor": "white"},
            pctdistance=0.75,
        )
        for t in autotexts:
            t.set_fontsize(8)
        centre = plt.Circle((0, 0), 0.5, color="white")
        ax.add_artist(centre)
        total = sum(vals)
        ax.text(0, 0, f"${total:.0f}B\ntotal", ha="center", va="center",
                fontsize=9, fontweight="bold", color="#212529")
        qtr = str(df.iloc[-1].get("year_quarter", "latest"))
        ax.set_title(f"External Debt by Sector -- {qtr}\n(Nominal value, debt instruments only)",
                     fontsize=10, fontweight="bold", pad=12)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    log.info("Chart saved: %s", path)
    return path


def chart_private_detail(df: pd.DataFrame) -> str | None:
    # EDE columns: bonds, loans, trade credits, FDI intercompany debt
    needed = ["private_bonds_usd_bn", "private_loans_usd_bn",
              "private_trade_credits_usd_bn", "private_fdi_debt_usd_bn"]
    avail = [c for c in needed if c in df.columns]
    if not avail:
        return None
    plot_df = df.dropna(subset=avail, how="all").tail(12).copy()
    if plot_df.empty:
        return None

    items = [
        ("private_bonds_usd_bn",         "Bonds / debt securities", BLUE),
        ("private_loans_usd_bn",          "Loans", ORANGE),
        ("private_trade_credits_usd_bn",  "Trade credits", GREEN),
        ("private_fdi_debt_usd_bn",       "FDI intercompany debt", PURPLE),
    ]
    items = [(c, l, col) for c, l, col in items if c in plot_df.columns]

    dates = pd.to_datetime(plot_df["quarter_start"]).tolist()
    path  = str(CHARTS_DIR / "dr_private_detail.png")
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 4))
        bar_w = max(30, int((dates[-1] - dates[0]).days / len(dates) * 0.55)) if len(dates) > 1 else 60
        bottoms = [0.0] * len(dates)
        for col, label, color in items:
            vals = plot_df[col].fillna(0).tolist()
            ax.bar(dates, vals, width=bar_w, bottom=bottoms, color=color,
                   alpha=0.85, label=label)
            bottoms = [b + v for b, v in zip(bottoms, vals)]

        ax.set_ylabel("USD billions", fontsize=9)
        ax.set_title("Private Sector (S1V) External Debt -- Debt Instruments Only", fontsize=13,
                     fontweight="bold", pad=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45, ha="right", fontsize=8)
        ax.legend(framealpha=0.8, fontsize=9)
        ax.grid(True, axis="y", alpha=0.4)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    log.info("Chart saved: %s", path)
    return path


def chart_bonds_nom_vs_mv(ede_df: pd.DataFrame, iip_df: pd.DataFrame) -> str | None:
    """Line chart comparing government bonds at nominal value (EDE) vs market value (IIP)."""
    if ede_df is None or iip_df is None:
        return None
    if "govt_bonds_usd_bn" not in ede_df.columns or "govt_bonds_mv_usd_bn" not in iip_df.columns:
        return None

    nom = ede_df[["quarter_start", "govt_bonds_usd_bn"]].dropna().copy()
    mv  = iip_df[["quarter_start", "govt_bonds_mv_usd_bn"]].dropna().copy()
    nom["quarter_start"] = pd.to_datetime(nom["quarter_start"])
    mv["quarter_start"]  = pd.to_datetime(mv["quarter_start"])

    if nom.empty or mv.empty:
        return None

    path = str(CHARTS_DIR / "dr_bonds_nom_vs_mv.png")
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(nom["quarter_start"], nom["govt_bonds_usd_bn"],
                color=BLUE, linewidth=2.2, marker="o", markersize=4,
                label="Nominal / face value (INDEC EDE)")
        ax.plot(mv["quarter_start"], mv["govt_bonds_mv_usd_bn"],
                color=ORANGE, linewidth=2.2, marker="s", markersize=4,
                linestyle="--", label="Market value (INDEC IIP)")

        # Shade the gap between the two lines where they overlap
        merged = pd.merge(nom, mv, on="quarter_start", how="inner")
        if not merged.empty:
            ax.fill_between(merged["quarter_start"],
                            merged["govt_bonds_usd_bn"],
                            merged["govt_bonds_mv_usd_bn"],
                            alpha=0.12, color=RED, label="Price discount gap")

        ax.set_ylabel("USD billions", fontsize=9)
        ax.set_title("Government Bonds: Nominal Value vs Market Value", fontsize=13,
                     fontweight="bold", pad=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
        plt.xticks(rotation=45, ha="right", fontsize=8)
        ax.legend(framealpha=0.8, fontsize=9)
        ax.grid(True, axis="y", alpha=0.4)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    log.info("Chart saved: %s", path)
    return path


def chart_sector_totals_nom_vs_mv(ede_df: pd.DataFrame, iip_df: pd.DataFrame) -> str | None:
    """Side-by-side stacked bars: EDE nominal (left) vs IIP market value (right) for latest common quarter."""
    if ede_df is None or iip_df is None:
        return None

    nom_cols = ["govt_total_usd_bn", "bcra_total_usd_bn", "banks_total_usd_bn", "private_total_usd_bn"]
    mv_cols  = ["govt_total_mv_usd_bn", "bcra_total_mv_usd_bn", "banks_total_mv_usd_bn", "private_total_mv_usd_bn"]

    if not all(c in ede_df.columns for c in nom_cols) or not all(c in iip_df.columns for c in mv_cols):
        return None

    nom_row = ede_df.dropna(subset=nom_cols).iloc[-1]
    mv_row  = iip_df.dropna(subset=mv_cols).iloc[-1]

    nom_vals = [nom_row[c] for c in nom_cols]
    mv_vals  = [mv_row[c]  for c in mv_cols]
    labels   = ["Government", "BCRA", "Banks", "Private"]
    colors   = SECTOR_COLORS

    nom_qtr = str(nom_row.get("year_quarter", "EDE"))
    mv_qtr  = str(mv_row.get("year_quarter",  "IIP"))

    path = str(CHARTS_DIR / "dr_nom_vs_mv.png")
    with plt.rc_context(CHART_STYLE):
        fig, axes = plt.subplots(1, 2, figsize=(10, 5), sharey=True)

        for ax, vals, title_qtr, note in [
            (axes[0], nom_vals, nom_qtr, "Nominal / face value\n(INDEC EDE dataset 161)"),
            (axes[1], mv_vals,  mv_qtr,  "Market value\n(INDEC IIP 144.4_ series)"),
        ]:
            bottoms = 0.0
            for val, label, color in zip(vals, labels, colors):
                ax.bar(0, val, bottom=bottoms, color=color, alpha=0.85,
                       width=0.5, label=label)
                if val > 5:
                    ax.text(0, bottoms + val / 2, f"${val:.0f}B",
                            ha="center", va="center", fontsize=8.5,
                            color="white", fontweight="bold")
                bottoms += val
            ax.text(0, bottoms + 3, f"${bottoms:.0f}B total",
                    ha="center", va="bottom", fontsize=9, fontweight="bold", color="#212529")
            ax.set_xlim(-0.5, 0.5)
            ax.set_xticks([])
            ax.set_title(f"{title_qtr}\n{note}", fontsize=9, pad=8)
            ax.grid(True, axis="y", alpha=0.4)

        axes[0].set_ylabel("USD billions", fontsize=9)
        handles, lbls = axes[0].get_legend_handles_labels()
        fig.legend(handles, lbls, loc="lower center", ncol=4, fontsize=9,
                   framealpha=0.8, bbox_to_anchor=(0.5, -0.02))
        fig.suptitle("External Debt by Sector: Nominal vs Market Value", fontsize=13,
                     fontweight="bold", y=1.01)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    log.info("Chart saved: %s", path)
    return path


def chart_govt_debt_instruments(debt_df: pd.DataFrame) -> str | None:
    needed = ["bonds_usd_bn", "loans_usd_bn"]
    if not all(c in debt_df.columns for c in needed):
        return None
    df = debt_df.dropna(subset=needed).tail(16).copy()
    if df.empty:
        return None

    date_col = "quarter_start" if "quarter_start" in df.columns else "date"
    dates = pd.to_datetime(df[date_col]).tolist()
    bonds = df["bonds_usd_bn"].tolist()
    loans = df["loans_usd_bn"].tolist()
    path  = str(CHARTS_DIR / "dr_govt_instruments.png")

    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 4.5))
        bar_w = max(30, int((dates[-1] - dates[0]).days / len(dates) * 0.55)) if len(dates) > 1 else 60
        ax.bar(dates, loans, width=bar_w, color=ORANGE, alpha=0.85,
               label="Loans & other investment (IMF, multilaterals, bilateral)")
        ax.bar(dates, bonds, width=bar_w, color=BLUE, alpha=0.85,
               label="Portfolio / sovereign bonds", bottom=loans)
        for d, b, l in zip(dates, bonds, loans):
            total = b + l
            ax.text(d, total + 1.5, f"${total:.0f}B", ha="center", va="bottom",
                    fontsize=7.5, color="#212529")
        ax.set_ylabel("USD billions", fontsize=9)
        ax.set_title("Government External Liabilities by Instrument", fontsize=13,
                     fontweight="bold", pad=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45, ha="right", fontsize=8)
        ax.legend(framealpha=0.8, fontsize=9, loc="upper left")
        ax.grid(True, axis="y", alpha=0.4)
        ax.set_ylim(0, max(b + l for b, l in zip(bonds, loans)) * 1.15)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    log.info("Chart saved: %s", path)
    return path


def chart_trade(trade_df: pd.DataFrame) -> str | None:
    df = trade_df.dropna(subset=["exports_usd_bn", "imports_usd_bn"]).copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.tail(24)
    if df.empty:
        return None
    path = str(CHARTS_DIR / "dr_trade.png")
    with plt.rc_context(CHART_STYLE):
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True,
                                        gridspec_kw={"height_ratios": [2, 1]})
        ax1.plot(df["date"], df["exports_usd_bn"], color=GREEN,  linewidth=2, label="Exports")
        ax1.plot(df["date"], df["imports_usd_bn"], color=RED,    linewidth=2, label="Imports")
        ax1.set_ylabel("USD billions", fontsize=9)
        ax1.set_title("Trade Balance", fontsize=13, fontweight="bold", pad=10)
        ax1.legend(framealpha=0.8, fontsize=9)
        ax1.grid(True, axis="y", alpha=0.4)

        bal = df["trade_balance_usd_bn"]
        colors = [GREEN if v >= 0 else RED for v in bal]
        ax2.bar(df["date"], bal, color=colors, width=20, alpha=0.85)
        ax2.axhline(0, color=GREY, linewidth=0.8)
        ax2.set_ylabel("Balance (USD bn)", fontsize=9)
        ax2.grid(True, axis="y", alpha=0.4)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45, ha="right", fontsize=8)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    log.info("Chart saved: %s", path)
    return path


def chart_current_account(ca_df: pd.DataFrame) -> str | None:
    df = ca_df.dropna(subset=["current_account_usd_bn"]).copy()
    dates_col = "quarter_start" if "quarter_start" in df.columns else "date"
    df[dates_col] = pd.to_datetime(df[dates_col])
    df = df.tail(20)
    if df.empty:
        return None
    path = str(CHARTS_DIR / "dr_current_account.png")
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 4))
        vals   = df["current_account_usd_bn"].tolist()
        dates  = df[dates_col].tolist()
        colors = [GREEN if v >= 0 else RED for v in vals]
        ax.bar(dates, vals, color=colors, width=55, alpha=0.85)
        ax.axhline(0, color=GREY, linewidth=0.8)
        ax.set_ylabel("USD billions", fontsize=9)
        ax.set_title("Current Account Balance (Quarterly)", fontsize=13, fontweight="bold", pad=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
        plt.xticks(rotation=45, ha="right", fontsize=8)
        ax.grid(True, axis="y", alpha=0.4)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    log.info("Chart saved: %s", path)
    return path


def chart_debt_service(debt_df: pd.DataFrame) -> str | None:
    if "debt_service_pct_exports" not in debt_df.columns:
        return None
    df = debt_df[["date", "debt_service_pct_exports"]].dropna().copy()
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df = df.groupby("year", as_index=False).first().tail(10)
    if len(df) < 2:
        return None
    path = str(CHARTS_DIR / "dr_debt_service.png")
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.bar(df["year"], df["debt_service_pct_exports"],
               color=[RED if v > 30 else BLUE for v in df["debt_service_pct_exports"]],
               alpha=0.85, width=0.6)
        ax.axhline(30, color=GREY, linewidth=1, linestyle="--", alpha=0.8)
        ax.text(df["year"].iloc[0], 31.5, "30% threshold", color=GREY, fontsize=7.5)
        ax.set_ylabel("% of goods & services exports", fontsize=9)
        ax.set_title("Debt Service as % of Export Revenues (World Bank)", fontsize=13,
                     fontweight="bold", pad=10)
        ax.set_xticks(df["year"].tolist())
        ax.set_xticklabels([str(y) for y in df["year"]], fontsize=8)
        ax.grid(True, axis="y", alpha=0.4)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    log.info("Chart saved: %s", path)
    return path


# ---------------------------------------------------------------------------
# Table helper
# ---------------------------------------------------------------------------

def _add_data_table(pdf: DebtReservesPDF, df: pd.DataFrame, cols: list[str],
                    fmt: dict, title: str, limit: int = 20):
    subset = df[cols].dropna(how="all").tail(limit).reset_index(drop=True)
    if subset.empty:
        return
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 6, _safe(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)

    avail_w = pdf.PAGE_W - 2 * pdf.MARGIN
    col_w   = avail_w / len(cols)

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(30, 100, 200)
    pdf.set_text_color(255, 255, 255)
    for c in cols:
        label = (c.replace("_", " ")
                  .replace("usd bn", "(B)")
                  .replace("pct", "%")
                  .title())
        pdf.cell(col_w, 6, _safe(label), border=0, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for i, (_, row) in enumerate(subset.iterrows()):
        bg = (240, 247, 255) if i % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*bg)
        pdf.set_text_color(40, 40, 40)
        for c in cols:
            v = row[c]
            if c in ("date", "year_quarter", "quarter_start", "quarter_end") or (
                    hasattr(v, "strftime")):
                try:
                    parsed = pd.to_datetime(v)
                    cell_str = parsed.strftime("%b %Y") if c != "year_quarter" else str(v)
                except Exception:
                    cell_str = str(v)
            else:
                f = fmt.get(c, "{:.1f}")
                try:
                    cell_str = f.format(float(v))
                except Exception:
                    cell_str = str(v)
            pdf.cell(col_w, 5.5, _safe(cell_str), border=0, fill=True, align="C")
        pdf.ln()

    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.MARGIN, pdf.get_y(), pdf.PAGE_W - pdf.MARGIN, pdf.get_y())
    pdf.ln(4)
    pdf.set_text_color(0, 0, 0)


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_debt_reserves_report(
    reserves_df:            pd.DataFrame | None,
    fx_df:                  pd.DataFrame | None,
    ext_debt_sector_df:     pd.DataFrame | None,
    ext_debt_sector_iip_df: pd.DataFrame | None,
    govt_ext_debt_df:       pd.DataFrame | None,
    trade_df:               pd.DataFrame | None,
    ca_df:                  pd.DataFrame | None,
) -> Path:
    today = date.today().strftime("%B %d, %Y")

    pdf = DebtReservesPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # =========================================================
    # Title
    # =========================================================
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(20, 80, 160)
    pdf.cell(0, 13, "Argentina -- Debt & Reserves", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, "External Position Deep Dive", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 7, f"Generated {today} -- Sources: INDEC IIP, BCRA, World Bank",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_draw_color(20, 80, 160)
    pdf.set_line_width(0.5)
    pdf.line(15, pdf.get_y() + 2, 195, pdf.get_y() + 2)
    pdf.ln(8)

    # =========================================================
    # KPI row
    # =========================================================
    kpis = []

    if reserves_df is not None and not reserves_df.empty:
        latest_res = reserves_df.dropna(subset=["reserves_usd_bn"]).iloc[-1]
        gross = latest_res["reserves_usd_bn"]
        net   = latest_res.get("net_reserves_usd_bn")
        kpis.append(("Gross Reserves", f"${gross:.1f}B",
                      pd.to_datetime(latest_res["date"]).strftime("%b %Y")))
        if net is not None:
            kpis.append(("Net Reserves (est.)", f"${net:.1f}B", "gross - swap - other liab"))

    if fx_df is not None and not fx_df.empty:
        latest_fx = fx_df.dropna(subset=["usd_ars"]).iloc[-1]
        kpis.append(("ARS/USD", f"{latest_fx['usd_ars']:,.0f}",
                     pd.to_datetime(latest_fx["date"]).strftime("%b %Y")))

    if ext_debt_sector_df is not None and not ext_debt_sector_df.empty:
        latest_d = ext_debt_sector_df.dropna(subset=["grand_total_usd_bn"]).iloc[-1]
        kpis.append(("Total Ext. Liabilities", f"${latest_d['grand_total_usd_bn']:.0f}B",
                     str(latest_d.get("year_quarter", ""))))

    if trade_df is not None and not trade_df.empty:
        bal = trade_df.dropna(subset=["trade_balance_usd_bn"]).iloc[-1]
        kpis.append(("Trade Balance", f"${bal['trade_balance_usd_bn']:+.2f}B",
                     pd.to_datetime(bal["date"]).strftime("%b %Y")))

    if kpis:
        for i in range(0, len(kpis), 4):
            pdf.kpi_row(kpis[i:i+4])

    pdf.ln(2)

    # =========================================================
    # Section 1 — Reserves
    # =========================================================
    pdf.section_title("1. BCRA International Reserves")
    pdf.body_text(
        "Argentina's gross international reserves measure the total foreign assets held by the "
        "central bank (BCRA). The net reserves estimate subtracts the drawn portion of the "
        "PBoC renminbi swap line (~USD 18.5B as of 2024) and minor short-term liabilities. "
        "Net reserves are the more relevant metric for assessing available liquidity buffers, "
        "as the swap funds are not freely usable for general debt service."
    )

    if reserves_df is not None and not reserves_df.empty:
        chart = chart_reserves(reserves_df)
        pdf.add_chart(chart,
                      "Blue = gross reserves. Orange dashed = net reserves (gross minus China swap ~18.5B "
                      "minus other short-term liabilities ~1.5B). Source: BCRA via datos.gob.ar.")

        cols_show = [c for c in ["date", "reserves_usd_bn", "net_reserves_usd_bn"]
                     if c in reserves_df.columns]
        _add_data_table(pdf, reserves_df, cols_show,
                        fmt={"reserves_usd_bn": "${:.1f}", "net_reserves_usd_bn": "${:.1f}"},
                        title="BCRA Reserves (monthly, USD bn)", limit=24)
    else:
        pdf.body_text("Reserves data unavailable.")

    pdf.note(
        "Net reserves methodology: gross minus drawn PBoC RMB swap (~USD 18.5B) minus "
        "repos and minor short-term items (~USD 1.5B). BCRA does not publish a net figure directly. "
        "Update CHINA_SWAP_BN in ingestion/reserves.py if BCRA discloses changes."
    )

    # =========================================================
    # Section 2 — Exchange Rate
    # =========================================================
    pdf.section_title("2. Exchange Rate (ARS/USD)")
    pdf.body_text(
        "The official ARS/USD rate is set daily by the BCRA. Following the April 2025 IMF "
        "Stand-By Arrangement, Argentina moved to a managed float with a crawling-peg band. "
        "The trajectory of the exchange rate determines import costs, external debt service "
        "in peso terms, and the real value of dollar-denominated wages."
    )

    if fx_df is not None and not fx_df.empty:
        chart = chart_fx(fx_df)
        pdf.add_chart(chart, "Official ARS/USD exchange rate (end-of-month). Source: BCRA via datos.gob.ar.")
    else:
        pdf.body_text("Exchange rate data unavailable.")

    # =========================================================
    # Section 3 — External Debt by Sector (INDEC IIP)
    # =========================================================
    pdf.section_title("3. Gross External Debt by Sector (INDEC EDE -- Nominal Value)")
    pdf.body_text(
        "The INDEC Estadistica de Deuda Externa (EDE) publishes Argentina's gross external debt "
        "at nominal (face) value broken down by resident sector. This is the dataset behind "
        "INDEC's quarterly infographic. It covers only DEBT instruments (bonds, loans, trade "
        "credits, intercompany FDI loans) -- equity stakes in Argentine companies are excluded. "
        "The five sectors are: S13 General Government (national + provincial + SOE bonds and "
        "multilateral loans); S121 BCRA (SDR allocations, PBoC swap drawn, IMF loans to BCRA); "
        "S122 Banks; S12R Other financial corporations; and S1V Non-financial private sector. "
        "Note: this dataset has approximately a 4-quarter publication lag."
    )

    if ext_debt_sector_df is not None and not ext_debt_sector_df.empty:
        stacked = chart_ext_debt_by_sector(ext_debt_sector_df)
        donut   = chart_sector_donut(ext_debt_sector_df)
        priv    = chart_private_detail(ext_debt_sector_df)

        pdf.add_chart(stacked,
                      "Stacked bars by sector: blue=Government, orange=BCRA, green=Banks, purple=Private, "
                      "teal=Other financial. INDEC EDE at nominal value. Data lags ~4 quarters.")

        if donut:
            pdf.add_chart(donut,
                          "Latest available quarter sector breakdown at nominal value. "
                          "Private sector shows debt instruments only (bonds + loans + trade credits "
                          "+ FDI intercompany loans) -- equity stakes excluded.")

        if priv:
            pdf.add_chart(priv,
                          "Private sector (S1V) external debt by instrument at nominal value. "
                          "FDI intercompany debt = loans between related companies (parent-subsidiary). "
                          "Equity stakes in Argentine companies are NOT included here.")

        # Sector summary table
        tbl_cols = [c for c in [
            "year_quarter", "grand_total_usd_bn",
            "govt_total_usd_bn", "bcra_total_usd_bn",
            "banks_total_usd_bn", "other_fin_total_usd_bn", "private_total_usd_bn",
        ] if c in ext_debt_sector_df.columns]
        _add_data_table(pdf, ext_debt_sector_df, tbl_cols,
                        fmt={c: "${:.1f}" for c in tbl_cols if c != "year_quarter"},
                        title="Gross External Debt by Sector -- Nominal Value (USD bn, quarterly)",
                        limit=8)

        # Government breakdown table
        govt_cols = [c for c in [
            "year_quarter", "govt_total_usd_bn", "govt_bonds_usd_bn", "govt_loans_usd_bn",
        ] if c in ext_debt_sector_df.columns]
        if len(govt_cols) > 2:
            _add_data_table(pdf, ext_debt_sector_df, govt_cols,
                            fmt={c: "${:.1f}" for c in govt_cols if c != "year_quarter"},
                            title="Government (S13) Breakdown: Bonds vs Loans (USD bn)", limit=8)

        # Private detail table
        priv_cols = [c for c in [
            "year_quarter", "private_total_usd_bn",
            "private_bonds_usd_bn", "private_loans_usd_bn",
            "private_trade_credits_usd_bn", "private_fdi_debt_usd_bn",
        ] if c in ext_debt_sector_df.columns]
        if len(priv_cols) > 2:
            _add_data_table(pdf, ext_debt_sector_df, priv_cols,
                            fmt={c: "${:.1f}" for c in priv_cols if c != "year_quarter"},
                            title="Private Sector (S1V) Debt Instruments (USD bn)", limit=8)

        # Nominal vs market value comparison
        bonds_cmp = chart_bonds_nom_vs_mv(ext_debt_sector_df, ext_debt_sector_iip_df)
        if bonds_cmp:
            pdf.add_chart(bonds_cmp,
                          "Government bonds: solid blue = face value (EDE), dashed orange = market value (IIP). "
                          "Red shading = price discount gap. When Argentina trades at a discount the gap widens; "
                          "as bond prices recover the two lines converge.")

        sector_cmp = chart_sector_totals_nom_vs_mv(ext_debt_sector_df, ext_debt_sector_iip_df)
        if sector_cmp:
            pdf.add_chart(sector_cmp,
                          "Left bar = EDE nominal value (latest available quarter). "
                          "Right bar = IIP market value (most recent quarter, may be more current). "
                          "Private sector is not directly comparable: IIP includes FDI equity; EDE shows debt only.")
    else:
        pdf.body_text("External debt by sector data unavailable.")

    pdf.note(
        "Source: INDEC EDE (Estadistica de Deuda Externa), datos.gob.ar dataset 161.1. "
        "All values at nominal (face) value in USD billions -- matches INDEC's published infographics. "
        "Private sector 'FDI debt' = intercompany loans within FDI relationships (parent/subsidiary); "
        "equity stakes are excluded from external DEBT statistics. "
        "Publication lag: approximately 4 quarters."
    )

    # =========================================================
    # Section 4 — Government External Debt (bonds vs loans)
    # =========================================================
    pdf.section_title("4. Government External Debt -- Bonds vs Loans")
    pdf.body_text(
        "The government sector (S13) external liabilities break down into two main instruments. "
        "Portfolio investment / bonds: primarily the 2020 restructured sovereign bonds (AL and GD "
        "series, NY-law and local-law) traded in international markets. Their price drives Argentina's "
        "country risk spread (EMBI) and determines re-access to capital markets. "
        "Loans and other investment: official creditor exposure -- IMF (largest single creditor), "
        "World Bank, IDB, CAF, and bilateral lenders. These carry negotiable terms but come with "
        "conditionality attached."
    )

    if govt_ext_debt_df is not None and not govt_ext_debt_df.empty:
        chart = chart_govt_debt_instruments(govt_ext_debt_df)
        pdf.add_chart(chart,
                      "Orange = loans and other investment (IMF, multilaterals, bilateral creditors). "
                      "Blue = portfolio / sovereign bonds. Labels show total government external stock.")

        svc_chart = chart_debt_service(govt_ext_debt_df)
        if svc_chart:
            pdf.add_chart(svc_chart,
                          "Annual debt service (principal + interest) as % of export revenues. "
                          "Red bars = above 30% threshold. Source: World Bank IDS.")

        tbl_cols = [c for c in [
            "year_quarter", "total_liab_usd_bn",
            "bonds_usd_bn", "loans_usd_bn", "bonds_pct", "loans_pct",
            "debt_service_pct_exports",
        ] if c in govt_ext_debt_df.columns]
        _add_data_table(pdf, govt_ext_debt_df, tbl_cols,
                        fmt={
                            "total_liab_usd_bn":       "${:.1f}",
                            "bonds_usd_bn":            "${:.1f}",
                            "loans_usd_bn":            "${:.1f}",
                            "bonds_pct":               "{:.1f}%",
                            "loans_pct":               "{:.1f}%",
                            "debt_service_pct_exports":"{:.1f}%",
                        },
                        title="Government External Liabilities by Instrument (USD bn, quarterly)",
                        limit=12)
    else:
        pdf.body_text("Government external debt data unavailable.")

    # =========================================================
    # Section 5 — Trade Balance & Current Account
    # =========================================================
    pdf.section_title("5. Trade Balance & Current Account")
    pdf.body_text(
        "The trade balance (exports minus imports of goods) and current account (trade balance "
        "plus services, income, and transfers) determine whether Argentina is earning or spending "
        "foreign currency. A sustained current account surplus is the primary mechanism for "
        "rebuilding reserves without new debt. Under the 2025 IMF program, current account "
        "improvement is a key structural target alongside the fiscal primary surplus."
    )

    if trade_df is not None and not trade_df.empty:
        chart = chart_trade(trade_df)
        pdf.add_chart(chart,
                      "Top panel: exports (green) vs imports (red) in USD bn. "
                      "Bottom panel: trade balance -- green bars = surplus, red = deficit.")

        tbl_cols = [c for c in [
            "date", "exports_usd_bn", "imports_usd_bn", "trade_balance_usd_bn",
        ] if c in trade_df.columns]
        _add_data_table(pdf, trade_df, tbl_cols,
                        fmt={
                            "exports_usd_bn":       "${:.2f}",
                            "imports_usd_bn":       "${:.2f}",
                            "trade_balance_usd_bn": "${:+.2f}",
                        },
                        title="Monthly Trade Balance (USD bn)", limit=24)
    else:
        pdf.body_text("Trade balance data unavailable.")

    if ca_df is not None and not ca_df.empty:
        chart = chart_current_account(ca_df)
        pdf.add_chart(chart,
                      "Quarterly current account balance (green=surplus, red=deficit). "
                      "Source: INDEC via datos.gob.ar.")
    else:
        pdf.body_text("Current account data unavailable.")

    # =========================================================
    # Footer note
    # =========================================================
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 4.5, _safe(
        "Data sources: INDEC IIP (datos.gob.ar, 144.4_ series). "
        "BCRA reserves: datos.gob.ar series 92.2_RESERVAS_IRES_0_0_32_40. "
        "Trade balance: INDEC datos.gob.ar series 75.3_IETG and 76.3_ITG. "
        "Debt service % exports: World Bank IDS DT.TDS.DECT.EX.ZS. "
        "All USD figures. Quarterly IIP data has a ~2-quarter publication lag."
    ))

    out = REPORTS_DIR / "debt_reserves_report.pdf"
    pdf.output(str(out))
    log.info("Debt & Reserves report written -> %s", out)
    return out
