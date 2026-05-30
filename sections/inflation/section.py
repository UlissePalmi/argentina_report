"""
Inflation module — section builder.
Generates charts and builds the "Inflation" PDF section and markdown.
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

log = get_logger("inflation.section")

PAPER   = "#f4f0e6"
ACCENT  = "#a23b1f"
INK     = "#1a1714"
INK_3   = "#6b625a"
INK_4   = "#9a9087"
RULE    = "#c9bfae"

CHART_STYLE = {
    "figure.facecolor": PAPER,
    "axes.facecolor":   PAPER,
    "axes.edgecolor":   RULE,
    "axes.labelcolor":  INK_3,
    "xtick.color":      INK_4,
    "ytick.color":      INK_4,
    "text.color":       INK,
    "grid.color":       RULE,
    "grid.linewidth":   0.6,
    "lines.linewidth":  1.8,
    "font.family":      "DejaVu Sans",
    "font.size":        8,
}


def chart_inflation(cpi_df: pd.DataFrame | None) -> str | None:
    if cpi_df is None or cpi_df.empty:
        return None
    path = str(CHARTS_DIR / "chart_inflation.png")
    df12 = cpi_df.tail(12)
    with plt.rc_context(CHART_STYLE):
        fig, ax1 = plt.subplots(figsize=(10, 4.2))
        dates = pd.to_datetime(df12["date"])
        ax1.bar(dates, df12["cpi_mom_pct"], color=ACCENT, width=20, alpha=0.9, label="MoM CPI %")
        ax1.set_ylabel("MoM %", fontsize=7.5, color=INK_3)
        ax1.tick_params(axis="y", labelsize=7.5)
        # Remove top/right spines
        ax1.spines["top"].set_visible(False)
        ax1.spines["right"].set_visible(False)
        ax1.spines["left"].set_color(RULE)
        ax1.spines["bottom"].set_color(RULE)
        if "cpi_yoy_pct" in df12.columns and df12["cpi_yoy_pct"].notna().any():
            ax2 = ax1.twinx()
            ax2.plot(dates, df12["cpi_yoy_pct"], color=INK_3, linewidth=1.5,
                     linestyle="--", label="YoY CPI %")
            ax2.set_ylabel("YoY %", fontsize=7.5, color=INK_3)
            ax2.tick_params(axis="y", labelsize=7.5, labelcolor=INK_4)
            ax2.spines["top"].set_visible(False)
            ax2.spines["right"].set_color(RULE)
            lines2, labels2 = ax2.get_legend_handles_labels()
        else:
            lines2, labels2 = [], []
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%m/%y"))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.xticks(rotation=35, ha="right", fontsize=7.5)
        ax1.grid(True, axis="y", alpha=0.5, linewidth=0.5)
        lines1, labels1 = ax1.get_legend_handles_labels()
        ax1.legend(
            lines1 + lines2, labels1 + labels2,
            frameon=True, framealpha=0.85, facecolor=PAPER,
            edgecolor=RULE, fontsize=7.5, loc="upper right",
        )
        fig.tight_layout(pad=0.6)
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=PAPER)
        plt.close(fig)
    log.info("Chart saved: %s", path)
    return path


def summarise(data: dict) -> str:
    cpi_df = data.get("cpi_df")
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
    base = (
        f"Monthly CPI inflation in {latest_date} was {current_mom:.1f}%{yoy_str}. "
        f"The peak over the sample period was {peak_mom:.1f}% in {peak_date}.{trend}"
    )
    return base + _last_mile_text()


def _last_mile_text() -> str:
    """Append the core (nucleo) run-rate and real-appreciation read from the
    precomputed inflation signal (no arithmetic here)."""
    m = load_signal("inflation").get("metrics", {})
    core = m.get("core_mom_latest")
    ann  = m.get("core_3m_annualized")
    ra   = m.get("real_peso_appreciation_3m")
    out = ""
    if core is not None:
        ann_str = f" (~{ann:.0f}% annualized)" if ann is not None else ""
        out += (f" Core (nucleo) inflation -- the sticky last-mile component -- is running "
                f"{core:.1f}%/month{ann_str}.")
    if ra is not None and ra > 1:
        out += (f" With the peso flat-to-stronger in nominal terms, that implies roughly "
                f"{ra:.1f}%/month of real appreciation, the core driver of the exchange-rate "
                f"overvaluation flagged in the FX section.")
    return out


def build_pdf_section(pdf, data: dict) -> None:
    cpi_df = data.get("cpi_df")
    inf_chart_path = chart_inflation(cpi_df)

    pdf.section_title("2. Inflation")
    pdf.body_text(summarise(data))

    if cpi_df is not None and not cpi_df.empty:
        cpi_cols = [c for c in ["cpi_mom_pct", "cpi_yoy_pct"] if c in cpi_df.columns]
        if cpi_cols:
            pdf.add_table(
                cpi_df.tail(12), ["date"] + cpi_cols,
                fmt={c: "{:.1f}%" for c in cpi_cols},
                title="CPI Inflation (last 12 months)"
            )

    pdf.add_chart(inf_chart_path, "Figure 3: Monthly and Annual CPI Inflation (%)")

    render_signal_callout(pdf, load_signal("inflation"), label="Inflation")


def build_md_section(data: dict) -> str:
    cpi_df = data.get("cpi_df")

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

    cpi_table = ""
    if cpi_df is not None and not cpi_df.empty:
        cc = [c for c in ["cpi_mom_pct", "cpi_yoy_pct"] if c in cpi_df.columns]
        if cc:
            cpi_table = "\n**CPI Inflation (last 12 months)**\n\n" + \
                        _md_table(cpi_df.tail(12), ["date"] + cc, fmt={c: "{:.1f}%" for c in cc})

    chart_path = str(CHARTS_DIR / "chart_inflation.png")
    def _img(p):
        return f"![chart](data/charts/{Path(p).name})\n" if p and Path(p).exists() else "_Chart unavailable._\n"

    sig_block = render_signal_callout_md(load_signal("inflation"), label="Inflation")

    return f"""## 2. Inflation

{summarise(data)}
{cpi_table}

{_img(chart_path)}
{sig_block}"""
