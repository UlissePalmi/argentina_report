"""
Labor module — section builder for the main macro report.

Covers the master variable: real wages, formal employment, and the
productivity-backing test. Reads signals for analytical flags.

build_pdf_section(pdf, data) — data keys:
    consumption_df  : DataFrame from external/fetch.py (has wage + CPI columns)
    employment_df   : DataFrame from external/fetch.py (SIPA employment)
"""

import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

from utils import CHARTS_DIR, SIGNALS_DIR, get_logger

log = get_logger("labor.section")

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

GREEN = "#2f9e44"
RED   = "#c92a2a"
BLUE  = "#1971c2"
AMBER = "#e67700"


# ---------------------------------------------------------------------------
# Signal helpers
# ---------------------------------------------------------------------------

def _load_signal(name: str) -> dict:
    path = SIGNALS_DIR / f"signals_{name}.json"
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _pct(v) -> str:
    try:
        return f"{float(v):+.1f}%"
    except (TypeError, ValueError):
        return "n/a"


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def chart_real_wages(consumption_df: pd.DataFrame,
                     filename: str = "labor_real_wages.png") -> str | None:
    """
    Dual-axis chart:
      Bars  (left)  — real wage YoY % (green if positive, red if negative)
      Line  (right) — nominal wage YoY % and CPI YoY % for context
    """
    needed = ["date", "real_wage_yoy_pct", "nominal_wage_yoy_pct", "cpi_yoy_pct"]
    avail  = [c for c in needed if c in consumption_df.columns]
    if "real_wage_yoy_pct" not in avail:
        return None

    df = consumption_df[avail].dropna(subset=["real_wage_yoy_pct"]).tail(18).copy()
    if df.empty:
        return None

    df["date"] = pd.to_datetime(df["date"])
    path = str(CHARTS_DIR / filename)

    with plt.rc_context(CHART_STYLE):
        fig, ax1 = plt.subplots(figsize=(11, 4.5))
        ax2 = ax1.twinx()

        # Bars: real wage YoY
        colors = [GREEN if v >= 0 else RED for v in df["real_wage_yoy_pct"]]
        ax1.bar(df["date"], df["real_wage_yoy_pct"], color=colors,
                alpha=0.85, width=20, zorder=2, label="Real wage YoY (left)")
        ax1.axhline(0, color="#495057", linewidth=0.9, zorder=3)
        ax1.set_ylabel("Real wage YoY %", color="#212529")
        ax1.tick_params(axis="y", labelcolor="#212529")

        # Lines: nominal wage + CPI (right axis)
        if "nominal_wage_yoy_pct" in df.columns:
            ax2.plot(df["date"], df["nominal_wage_yoy_pct"],
                     color=BLUE, linewidth=1.8, linestyle="--",
                     label="Nominal wage YoY (right)", alpha=0.8)
        if "cpi_yoy_pct" in df.columns:
            ax2.plot(df["date"], df["cpi_yoy_pct"],
                     color=AMBER, linewidth=1.8, linestyle=":",
                     label="CPI YoY (right)", alpha=0.8)
        ax2.set_ylabel("Nominal / CPI YoY %", color="#6c757d")
        ax2.tick_params(axis="y", labelcolor="#6c757d")

        # Combine legends
        h1, l1 = ax1.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax1.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper right", framealpha=0.9)

        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=8)
        ax1.set_title("Real Wages YoY % — The Master Variable",
                      fontsize=11, fontweight="bold", pad=8)
        ax1.grid(axis="y", alpha=0.4, zorder=0)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    log.info("Chart saved: %s", path)
    return path


def chart_employment(employment_df: pd.DataFrame,
                     filename: str = "labor_employment.png") -> str | None:
    """Line chart: formal employment (SIPA) total YoY % last 24 months."""
    if "emp_total_yoy_pct" not in employment_df.columns:
        return None

    df = employment_df[["date", "emp_total_yoy_pct"]].dropna().tail(24).copy()
    if df.empty:
        return None

    df["date"] = pd.to_datetime(df["date"])
    path = str(CHARTS_DIR / filename)

    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(11, 3.5))

        colors = [GREEN if v >= 0 else RED for v in df["emp_total_yoy_pct"]]
        ax.bar(df["date"], df["emp_total_yoy_pct"],
               color=colors, alpha=0.85, width=20, zorder=2)
        ax.plot(df["date"], df["emp_total_yoy_pct"],
                color=BLUE, linewidth=1.5, marker="o", markersize=3, zorder=3)
        ax.axhline(0, color="#495057", linewidth=0.9, zorder=3)

        ax.set_ylabel("YoY %")
        ax.set_title("Formal Employment YoY % (SIPA registered private workers)",
                     fontsize=11, fontweight="bold", pad=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=8)
        ax.grid(axis="y", alpha=0.4, zorder=0)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    log.info("Chart saved: %s", path)
    return path


# ---------------------------------------------------------------------------
# Analytical text (reads from signals)
# ---------------------------------------------------------------------------

def _build_analytical_text(wages_sig: dict, labor_sig: dict) -> str:
    """Generate the analytical paragraph from pre-computed signals."""
    lines = []

    # --- Real wages ---
    w_metrics = wages_sig.get("metrics", {})
    real_yoy   = w_metrics.get("real_wage_yoy_latest")
    nom_yoy    = w_metrics.get("nominal_wage_yoy_latest")
    cpi_yoy    = w_metrics.get("cpi_yoy_latest")
    trend_3m   = w_metrics.get("real_wage_trend_3m")
    consec     = w_metrics.get("consecutive_positive_months", 0)

    if real_yoy is not None:
        direction = "grew" if real_yoy >= 0 else "contracted"
        sustainability = ""
        if consec >= 9:
            sustainability = (f" This marks {consec} consecutive positive months "
                              f"(3+ quarters) -- the blueprint threshold for confirmed recovery.")
        elif consec >= 3:
            sustainability = (f" Real wages have been positive for {consec} consecutive months "
                              f"-- a trend, but not yet the 9-month threshold for confirmed recovery.")
        elif consec == 0 and real_yoy < 0:
            sustainability = (" Wages remain in negative territory -- the master variable has "
                              "not yet turned.")
        else:
            sustainability = (f" Real wages turned positive for {consec} month(s) "
                              f"-- too early to call a trend.")

        trend_note = ""
        if trend_3m is not None and real_yoy is not None:
            if trend_3m > real_yoy + 1:
                trend_note = (f" The 3-month average ({trend_3m:+.1f}%) sits above the latest print, "
                              f"indicating momentum is building.")
            elif trend_3m < real_yoy - 1:
                trend_note = (f" The 3-month average ({trend_3m:+.1f}%) is below the latest print -- "
                              f"momentum is fading.")

        line = (f"Real wages {direction} {abs(real_yoy):.1f}% YoY in the latest month "
                f"(nominal wages {_pct(nom_yoy)} minus CPI {_pct(cpi_yoy)})."
                f"{sustainability}{trend_note}")
        lines.append(line)

    # --- Productivity backing ---
    l_metrics   = labor_sig.get("metrics", {})
    prod_ind    = l_metrics.get("productivity_industry_yoy")
    ulc_ind     = l_metrics.get("ulc_industry_yoy")
    backed      = wages_sig.get("metrics", {})

    if prod_ind is not None and real_yoy is not None:
        if real_yoy > 0 and prod_ind > 0:
            lines.append(
                f"The wage recovery appears productivity-backed: industrial output per worker "
                f"grew {_pct(prod_ind)} YoY, providing a supply-side foundation for wage gains."
            )
        elif real_yoy > 0 and prod_ind < 0:
            lines.append(
                f"A concern: real wages are recovering ({_pct(real_yoy)}) while industrial "
                f"productivity fell {_pct(prod_ind)} YoY. Without output-per-worker growth, "
                f"wage gains are redistributive rather than productivity-backed -- "
                f"sustainable only in the short term."
            )
        elif real_yoy < 0 and prod_ind > 0:
            lines.append(
                f"Industrial productivity grew {_pct(prod_ind)} YoY while real wages are still "
                f"negative -- the productive capacity for wage recovery is building but "
                f"has not yet passed through to household income."
            )

    if ulc_ind is not None:
        if ulc_ind > 10:
            lines.append(
                f"Unit labor costs (ULC) rose {_pct(ulc_ind)} YoY in industry -- "
                f"wages are growing faster than output, which pressures margins and "
                f"can feed back into inflation if sustained."
            )
        elif ulc_ind < 0:
            lines.append(
                f"Unit labor costs fell {_pct(ulc_ind)} YoY in industry -- "
                f"productivity gains are outpacing wages, improving competitiveness."
            )

    # --- Employment ---
    sipa_yoy  = l_metrics.get("sipa_yoy_latest")
    sipa_trend = l_metrics.get("sipa_trend_3m")
    if sipa_yoy is not None:
        emp_dir = "expanded" if sipa_yoy > 0 else "contracted"
        emp_note = ""
        if sipa_yoy < -2:
            emp_note = (" Formal job destruction at this pace is a leading indicator of "
                        "delayed wage recovery -- the wage bill shrinks as fewer workers "
                        "are in the formal economy.")
        elif sipa_yoy > 3:
            emp_note = (" Sustained formal employment growth broadens the wage bill "
                        "and supports consumption without requiring credit.")
        lines.append(
            f"Formal employment (SIPA) {emp_dir} {_pct(sipa_yoy)} YoY.{emp_note}"
        )

    return " ".join(lines) if lines else "Labor market data unavailable."


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def summarise(data: dict) -> str:
    """One-sentence summary for the report cover / exec synthesis."""
    sig = _load_signal("wages")
    return sig.get("summary", "Real wage data unavailable.")


def build_pdf_section(pdf, data: dict) -> None:
    consumption_df = data.get("consumption_df")
    employment_df  = data.get("employment_df")

    wages_sig = _load_signal("wages")
    labor_sig = _load_signal("labor")

    pdf.section_title("4. Labor Market & Real Wages")

    # --- Lead sentence from signal ---
    lead = wages_sig.get("summary", "")
    if lead:
        pdf.body_text(lead)

    # --- Signal flags (CRITICAL and WARNING only) ---
    all_flags = wages_sig.get("flags", []) + labor_sig.get("flags", [])
    critical = [f for f in all_flags if f.startswith("CRITICAL:") or f.startswith("WARNING:")]
    if critical:
        for flag in critical[:3]:          # cap at 3 to avoid crowding
            pdf.body_text(flag)

    # --- Chart 1: real wages ---
    if consumption_df is not None and not consumption_df.empty:
        pdf.add_chart(
            chart_real_wages(consumption_df),
            caption="Real wages YoY % (bars, left) vs nominal wage and CPI YoY % (lines, right)"
        )

        # Wage table: last 8 months
        wage_cols = ["date", "nominal_wage_yoy_pct", "cpi_yoy_pct",
                     "real_wage_yoy_pct", "real_wage_mom_pct"]
        avail_wage = [c for c in wage_cols if c in consumption_df.columns]
        if len(avail_wage) > 1:
            disp = consumption_df[avail_wage].dropna(
                subset=["real_wage_yoy_pct"]).tail(8).copy()
            disp["date"] = pd.to_datetime(disp["date"]).dt.strftime("%b %Y")
            rename = {
                "nominal_wage_yoy_pct": "Nom. Wage YoY",
                "cpi_yoy_pct":          "CPI YoY",
                "real_wage_yoy_pct":    "Real Wage YoY",
                "real_wage_mom_pct":    "Real Wage MoM",
            }
            disp = disp.rename(columns=rename)
            display_cols = ["date"] + [rename[c] for c in avail_wage if c in rename]
            pdf.add_table(
                disp, display_cols,
                fmt={v: "{:+.1f}%" for v in rename.values()},
                title="Real Wages -- Last 8 Months"
            )

    # --- Chart 2: formal employment ---
    if employment_df is not None and not employment_df.empty:
        pdf.add_chart(
            chart_employment(employment_df),
            caption="Formal employment YoY % (SIPA registered private workers)"
        )

    # --- Analytical text ---
    analysis = _build_analytical_text(wages_sig, labor_sig)
    if analysis:
        pdf.body_text(analysis)

    # --- Sustainability verdict box ---
    mv        = wages_sig.get("metrics", {})
    consec    = mv.get("consecutive_positive_months", 0)
    real_yoy  = mv.get("real_wage_yoy_latest")
    backed    = labor_sig.get("metrics", {}).get("productivity_trend", "unknown")

    if real_yoy is not None:
        if consec >= 9:
            verdict = ("Master variable STATUS: CONFIRMED RECOVERY. "
                       f"Real wages positive for {consec} consecutive months (3+ quarters). "
                       "Productivity trend: " + backed + ".")
        elif real_yoy > 0:
            verdict = ("Master variable STATUS: RECOVERING -- NOT YET CONFIRMED. "
                       f"Real wages positive for {consec} month(s). "
                       "Requires 9 consecutive positive months for confirmation.")
        else:
            verdict = ("Master variable STATUS: PRE-RECOVERY. "
                       "Real wages remain negative. "
                       "Enablers (inflation, reserves) are in place; "
                       "the wage transmission has not yet materialized.")
        pdf.body_text(verdict)


def build_md_section(data: dict) -> str:
    consumption_df = data.get("consumption_df")
    employment_df  = data.get("employment_df")

    wages_sig = _load_signal("wages")
    labor_sig = _load_signal("labor")

    lines = ["## 4. Labor Market & Real Wages", ""]

    lead = wages_sig.get("summary", "")
    if lead:
        lines.append(lead)
        lines.append("")

    # Wage table
    if consumption_df is not None and not consumption_df.empty:
        wage_cols = ["date", "nominal_wage_yoy_pct", "cpi_yoy_pct",
                     "real_wage_yoy_pct", "real_wage_mom_pct"]
        avail = [c for c in wage_cols if c in consumption_df.columns]
        if len(avail) > 1:
            disp = consumption_df[avail].dropna(subset=["real_wage_yoy_pct"]).tail(8)
            lines.append("**Real Wages — Last 8 Months**")
            lines.append("")
            header = "| " + " | ".join(
                c.replace("_yoy_pct", " YoY").replace("_mom_pct", " MoM")
                 .replace("_", " ").replace("nominal wage", "Nom. Wage")
                 .replace("cpi", "CPI").replace("real wage", "Real Wage").title()
                for c in avail) + " |"
            sep = "| " + " | ".join(["---"] * len(avail)) + " |"
            rows = []
            for _, row in disp.iterrows():
                cells = []
                for c in avail:
                    v = row[c]
                    if c == "date":
                        cells.append(pd.to_datetime(v).strftime("%b %Y"))
                    else:
                        try:
                            cells.append(f"{float(v):+.1f}%")
                        except (TypeError, ValueError):
                            cells.append("n/a")
                rows.append("| " + " | ".join(cells) + " |")
            lines += [header, sep] + rows
            lines.append("")

    # Analysis
    analysis = _build_analytical_text(wages_sig, labor_sig)
    if analysis:
        lines.append(analysis)
        lines.append("")

    # Flags
    all_flags = wages_sig.get("flags", []) + labor_sig.get("flags", [])
    if all_flags:
        lines.append("**Signals:**")
        for f in all_flags:
            lines.append(f"- {f}")
        lines.append("")

    return "\n".join(lines)
