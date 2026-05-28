"""
FX Regime — section builder.

Two charts: the dollar fan (official vs parallels, brecha) and the real
exchange rate vs its own history (overvaluation gauge). Independent of net
reserves. Parallel history accumulates one row per run.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

from utils import CHARTS_DIR, get_logger
from report.signal_text import load_signal, render_signal_callout, render_signal_callout_md

log = get_logger("fx.section")

BLUE   = "#1971c2"
ORANGE = "#e67700"
GREEN  = "#2f9e44"
RED    = "#c92a2a"
PURPLE = "#7048e8"
GREY   = "#868e96"

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


def chart_dollar_fan(parallel_df: pd.DataFrame | None) -> str | None:
    if parallel_df is None or parallel_df.empty:
        return None
    df = parallel_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").tail(52)
    path = str(CHARTS_DIR / "fx_dollar_fan.png")
    series = [("oficial", BLUE, "Official"), ("ccl", RED, "CCL"),
              ("mep", ORANGE, "MEP"), ("blue", GREEN, "Blue")]
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 4))
        for col, color, label in series:
            if col in df.columns and df[col].notna().any():
                ax.plot(df["date"], df[col], color=color, marker="o", markersize=3,
                        linewidth=1.8, label=label)
        # Shade the official->CCL gap (brecha)
        if {"oficial", "ccl"}.issubset(df.columns):
            ax.fill_between(df["date"], df["oficial"], df["ccl"],
                            where=df["ccl"] >= df["oficial"], alpha=0.10, color=RED)
        last = df.iloc[-1]
        if pd.notna(last.get("brecha_ccl_pct")):
            ax.set_title(f"Dollar Fan -- Official vs Parallels (CCL brecha {last['brecha_ccl_pct']:.1f}%)",
                         fontsize=13, fontweight="bold", pad=10)
        else:
            ax.set_title("Dollar Fan -- Official vs Parallels", fontsize=13, fontweight="bold", pad=10)
        ax.set_ylabel("ARS per USD", fontsize=9)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        plt.xticks(rotation=45, ha="right", fontsize=8)
        ax.legend(framealpha=0.8, fontsize=9, ncol=4)
        ax.grid(True, axis="y", alpha=0.4)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    log.info("Chart saved: %s", path)
    return path


def chart_reer(reer_df: pd.DataFrame | None) -> str | None:
    if reer_df is None or reer_df.empty or "reer_index" not in reer_df.columns:
        return None
    df = reer_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["reer_index"]).sort_values("date")
    if df.empty:
        return None
    path = str(CHARTS_DIR / "fx_reer.png")
    mean = df["reer_index"].mean()
    std  = df["reer_index"].std()
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 3.8))
        ax.fill_between(df["date"], df["reer_index"], alpha=0.10, color=PURPLE)
        ax.plot(df["date"], df["reer_index"], color=PURPLE, linewidth=2.2, label="REER index")
        ax.axhline(mean, color=GREY, linewidth=1.0, linestyle="--", label="Mean")
        if pd.notna(std):
            ax.axhspan(mean - std, mean + std, alpha=0.06, color=GREY)
            # Below mean - 1sd = real-expensive peso (overvaluation zone)
            ax.axhspan(df["reer_index"].min(), mean - std, alpha=0.05, color=RED)
        last = df.iloc[-1]
        ax.annotate(f"{last['reer_index']:.0f}", xy=(last["date"], last["reer_index"]),
                    xytext=(8, 4), textcoords="offset points", fontsize=8,
                    color=PURPLE, fontweight="bold")
        ax.set_ylabel("Index (start = 100)", fontsize=9)
        ax.set_title("Real Exchange Rate -- higher = more competitive (lower = peso real-expensive)",
                     fontsize=11.5, fontweight="bold", pad=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45, ha="right", fontsize=8)
        ax.legend(framealpha=0.8, fontsize=8)
        ax.grid(True, axis="y", alpha=0.4)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    log.info("Chart saved: %s", path)
    return path


def summarise(data: dict) -> str:
    sig = load_signal("fx")
    metrics = sig.get("metrics", {}) if sig else {}
    official = metrics.get("official_fx_latest")
    brecha   = metrics.get("brecha_ccl_pct")
    reer_pct = metrics.get("reer_percentile")

    if official is None and brecha is None:
        return "FX regime data unavailable (parallel-dollar source unreachable or no history yet)."

    parts = []
    if official is not None:
        parts.append(f"The official rate is ARS {official:,.0f}/USD")
    if brecha is not None:
        gap_desc = ("a contained gap that signals FX-regime credibility" if brecha < 10
                    else "a moderate gap worth monitoring" if brecha < 25
                    else "a wide gap signalling devaluation pressure")
        parts.append(f"with a CCL brecha of {brecha:.1f}% -- {gap_desc}")
    text = ", ".join(parts) + "."
    if reer_pct is not None:
        if reer_pct < 20:
            text += (f" The real exchange rate sits at the {reer_pct:.0f}th percentile of its recent "
                     f"history -- the peso is real-expensive, an overvaluation/competitiveness risk even "
                     f"while the nominal gap stays calm.")
        elif reer_pct > 80:
            text += (f" The real exchange rate is at the {reer_pct:.0f}th percentile -- the peso is "
                     f"real-cheap and competitive.")
        else:
            text += f" The real exchange rate is mid-range at the {reer_pct:.0f}th percentile."
    return text


def build_pdf_section(pdf, data: dict) -> None:
    parallel_df = data.get("fx_parallel_df")
    reer_df     = data.get("reer_df")
    fan_path  = chart_dollar_fan(parallel_df)
    reer_path = chart_reer(reer_df)

    pdf.section_title("1b. Exchange Rate & FX Regime")
    pdf.body_text(summarise(data))

    pdf.add_chart(fan_path, "Figure: Official vs parallel dollars (history accumulates weekly)")
    pdf.add_chart(reer_path, "Figure: Real exchange rate vs its own distribution")

    render_signal_callout(pdf, load_signal("fx"), label="FX Regime")


def build_md_section(data: dict) -> str:
    fan_path  = str(CHARTS_DIR / "fx_dollar_fan.png")
    reer_path = str(CHARTS_DIR / "fx_reer.png")

    def _img(p, alt):
        return f"![{alt}](data/charts/{Path(p).name})\n" if p and Path(p).exists() else ""

    sig_block = render_signal_callout_md(load_signal("fx"), label="FX Regime")

    return f"""## 1b. Exchange Rate & FX Regime

{summarise(data)}

{_img(fan_path, "dollar fan")}
{_img(reer_path, "reer")}
{sig_block}"""
