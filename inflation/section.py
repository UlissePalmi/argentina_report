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

log = get_logger("inflation.section")

GREEN  = "#2f9e44"
RED    = "#c92a2a"
ORANGE = "#e67700"

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


def chart_inflation(cpi_df: pd.DataFrame | None) -> str | None:
    if cpi_df is None or cpi_df.empty:
        return None
    path = str(CHARTS_DIR / "chart_inflation.png")
    df12 = cpi_df.tail(12)
    with plt.rc_context(CHART_STYLE):
        fig, ax1 = plt.subplots(figsize=(10, 4.5))
        dates = pd.to_datetime(df12["date"])
        bar_colors = [RED if v > 5 else ORANGE if v > 2 else GREEN
                      for v in df12["cpi_mom_pct"].fillna(0)]
        ax1.bar(dates, df12["cpi_mom_pct"], color=bar_colors, width=20, label="MoM CPI % (LHS)")
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
    return (
        f"Monthly CPI inflation in {latest_date} was {current_mom:.1f}%{yoy_str}. "
        f"The peak over the sample period was {peak_mom:.1f}% in {peak_date}.{trend}"
    )


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

    return f"""## 2. Inflation

{summarise(data)}
{cpi_table}

{_img(chart_path)}"""
