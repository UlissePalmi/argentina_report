"""
External module — section builder.
Generates charts and builds the "Dollar Situation" PDF section and markdown.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

from utils import CHARTS_DIR, get_logger
from report.signal_text import load_signal, render_signal_callout, render_signal_callout_md

log = get_logger("external.section")

BLUE   = "#1864ab"
GREEN  = "#2f9e44"
RED    = "#c92a2a"

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


def chart_trade(trade_df: pd.DataFrame | None) -> str | None:
    if trade_df is None or trade_df.empty:
        return None
    path = str(CHARTS_DIR / "chart_trade.png")
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 4.5))
        dates = pd.to_datetime(trade_df["date"])
        if "exports_usd_bn" in trade_df.columns and "imports_usd_bn" in trade_df.columns:
            ax.plot(dates, trade_df["exports_usd_bn"], color=GREEN, label="Exports (FOB)", linewidth=2.2)
            ax.plot(dates, trade_df["imports_usd_bn"], color=RED,   label="Imports (CIF)", linewidth=2.2)
            surplus = trade_df["exports_usd_bn"] >= trade_df["imports_usd_bn"]
            ax.fill_between(dates, trade_df["exports_usd_bn"], trade_df["imports_usd_bn"],
                            where=surplus,  alpha=0.12, color=GREEN)
            ax.fill_between(dates, trade_df["exports_usd_bn"], trade_df["imports_usd_bn"],
                            where=~surplus, alpha=0.12, color=RED)
        elif "trade_balance_usd_bn" in trade_df.columns:
            colors = [GREEN if v >= 0 else RED for v in trade_df["trade_balance_usd_bn"]]
            ax.bar(dates, trade_df["trade_balance_usd_bn"], color=colors, width=20)
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


def chart_reserves(reserves_df: pd.DataFrame | None) -> str | None:
    if reserves_df is None or reserves_df.empty:
        return None
    path = str(CHARTS_DIR / "chart_reserves.png")
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 4.5))
        dates = pd.to_datetime(reserves_df["date"])
        col = "reserves_usd_bn" if "reserves_usd_bn" in reserves_df.columns else reserves_df.columns[-1]
        ax.plot(dates, reserves_df[col], color=BLUE, linewidth=2.4)
        ax.fill_between(dates, reserves_df[col], alpha=0.1, color=BLUE)
        last_val = reserves_df[col].dropna().iloc[-1]
        last_date = pd.to_datetime(reserves_df["date"].iloc[-1])
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


def summarise(data: dict) -> str:
    trade_df    = data.get("trade_df")
    reserves_df = data.get("reserves_df")
    ca_df       = data.get("ca_df")
    parts = []
    if reserves_df is not None and not reserves_df.empty and "reserves_usd_bn" in reserves_df.columns:
        latest   = reserves_df["reserves_usd_bn"].dropna().iloc[-1]
        earliest = reserves_df["reserves_usd_bn"].dropna().iloc[0]
        trend    = "risen" if latest > earliest else "fallen"
        parts.append(
            f"Gross international reserves stand at ${latest:.1f} billion, "
            f"having {trend} from ${earliest:.1f} billion over the past {len(reserves_df)} months."
        )
    if trade_df is not None and not trade_df.empty:
        if "trade_balance_usd_bn" in trade_df.columns:
            avg_bal = trade_df["trade_balance_usd_bn"].dropna().tail(4).mean()
            direction = "surplus" if avg_bal > 0 else "deficit"
            parts.append(
                f"The average monthly trade balance over the last four months is "
                f"${abs(avg_bal):.2f} billion -- a trade {direction}."
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


def build_pdf_section(pdf, data: dict) -> None:
    """Write the Dollar Situation section into the PDF."""
    from report.build import _safe
    trade_df    = data.get("trade_df")
    reserves_df = data.get("reserves_df")
    ca_df       = data.get("ca_df")

    trade_chart_path   = chart_trade(trade_df)
    reserves_chart_path = chart_reserves(reserves_df)

    pdf.section_title("1. Dollar Situation")
    pdf.body_text(summarise(data))

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

    pdf.add_chart(trade_chart_path,    "Figure 1: Exports vs Imports (USD billions)")
    pdf.add_chart(reserves_chart_path, "Figure 2: Gross International Reserves (USD billions)")

    render_signal_callout(pdf, load_signal("external"), label="Dollar Situation")


def build_md_section(data: dict) -> str:
    """Return the markdown string for the Dollar Situation section."""
    trade_df    = data.get("trade_df")
    reserves_df = data.get("reserves_df")
    ca_df       = data.get("ca_df")

    def _md_table(df, cols, fmt=None):
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
                    try:    cells.append(pd.to_datetime(v).strftime("%Y-%m-%d"))
                    except: cells.append(str(v).split(" ")[0])
                    continue
                f = fmt.get(c, "{}")
                try:    cells.append(f.format(v))
                except: cells.append(str(v))
            rows.append("| " + " | ".join(cells) + " |")
        return "\n".join([header, sep] + rows)

    ca_table = trade_table = ""
    if ca_df is not None and not ca_df.empty:
        ca_col = [c for c in ca_df.columns if "current_account" in c]
        if ca_col:
            ca_table = "\n**Current Account Balance (last 8 years)**\n\n" + \
                       _md_table(ca_df.tail(8), ["date", ca_col[0]], fmt={ca_col[0]: "{:.2f}%"})
    if trade_df is not None and not trade_df.empty:
        tc = [c for c in ["exports_usd_bn", "imports_usd_bn", "trade_balance_usd_bn"]
              if c in trade_df.columns]
        if tc:
            trade_table = "\n**Trade Balance (last 12 months)**\n\n" + \
                          _md_table(trade_df, ["date"] + tc, fmt={c: "${:.2f}bn" for c in tc})

    trade_chart_path   = str(CHARTS_DIR / "chart_trade.png")
    reserves_chart_path = str(CHARTS_DIR / "chart_reserves.png")

    def _img(p):
        return f"![chart](data/charts/{Path(p).name})\n" if p and Path(p).exists() else "_Chart unavailable._\n"

    sig_block = render_signal_callout_md(load_signal("external"), label="Dollar Situation")

    return f"""## 1. Dollar Situation

{summarise(data)}
{ca_table}
{trade_table}

{_img(trade_chart_path)}{_img(reserves_chart_path)}
{sig_block}"""
