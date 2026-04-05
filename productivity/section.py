"""
Productivity module — section builder for the consumption deep-dive report.
Renders Section 4: Productivity & Unit Labor Costs.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

from utils import CHARTS_DIR, get_logger

log = get_logger("productivity.section")

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


def _pct(v) -> str:
    try:
        return f"{float(v):+.1f}%"
    except (TypeError, ValueError):
        return "n/a"


def _avg3(series: pd.Series) -> float | None:
    vals = series.dropna().tail(3)
    return float(vals.mean()) if len(vals) >= 1 else None


def _ulc_flag(series: pd.Series) -> str:
    """Return flag string if ULC positive for 3+ consecutive months."""
    vals = series.dropna().tail(6).tolist()
    # Check last 3 consecutive
    if len(vals) >= 3 and all(v > 0 for v in vals[-3:]):
        return "COMPETITIVENESS DETERIORATING: ULC positive for 3+ consecutive months."
    if len(vals) >= 1 and vals[-1] > 0:
        return "ULC positive (watch: not yet 3 consecutive months)."
    return "ULC negative or near zero -- no immediate competitiveness flag."


def chart_productivity(prod_df: pd.DataFrame, sectors: list[str],
                       filename: str) -> str | None:
    """Line chart of productivity YoY by sector."""
    cols = [f"productivity_{s}_yoy_pct" for s in sectors]
    avail = [c for c in cols if c in prod_df.columns]
    if not avail:
        return None

    sub = prod_df[["date"] + avail].dropna(subset=avail, how="all").tail(20)
    if sub.empty:
        return None

    path = str(CHARTS_DIR / filename)
    dates = pd.to_datetime(sub["date"])
    colors = ["#2f9e44", "#1971c2", "#e67700"]

    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 4))
        for i, col in enumerate(avail):
            label = col.replace("productivity_", "").replace("_yoy_pct", "").title()
            ax.plot(dates, sub[col], color=colors[i % len(colors)],
                    linewidth=2, marker="o", markersize=3, label=label)
        ax.axhline(0, color="#495057", linewidth=0.8)
        ax.set_ylabel("Productivity YoY %")
        ax.set_title("Output per Worker YoY % by Sector", fontsize=11, fontweight="bold", pad=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=8)
        ax.legend(fontsize=8, framealpha=0.8)
        ax.grid(axis="y", alpha=0.5)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    log.info("Chart saved: %s", path)
    return path


def chart_ulc(prod_df: pd.DataFrame, sectors: list[str], filename: str) -> str | None:
    """Bar chart of ULC YoY by sector."""
    cols = [f"ulc_{s}_yoy_pct" for s in sectors]
    avail = [c for c in cols if c in prod_df.columns]
    if not avail:
        return None

    sub = prod_df[["date"] + avail].dropna(subset=avail, how="all").tail(16)
    if sub.empty:
        return None

    path = str(CHARTS_DIR / filename)
    dates = pd.to_datetime(sub["date"])

    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 4))
        width = 18 / max(len(avail), 1)
        offsets = [(i - (len(avail) - 1) / 2) * width for i in range(len(avail))]
        colors = ["#2f9e44", "#1971c2", "#e67700"]
        for i, col in enumerate(avail):
            label = col.replace("ulc_", "").replace("_yoy_pct", "").title()
            bar_colors = ["#c92a2a" if v > 0 else "#2f9e44" for v in sub[col].fillna(0)]
            ax.bar(dates + pd.to_timedelta(offsets[i], unit="D"),
                   sub[col], width=width, color=bar_colors, alpha=0.8, label=label)
        ax.axhline(0, color="#495057", linewidth=0.8)
        ax.set_ylabel("ULC YoY %")
        ax.set_title("Unit Labor Costs YoY % (real wage - productivity)", fontsize=11, fontweight="bold", pad=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=8)
        ax.legend(fontsize=8, framealpha=0.8)
        ax.grid(axis="y", alpha=0.5)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    log.info("Chart saved: %s", path)
    return path


def build_section(pdf, productivity_df: pd.DataFrame | None,
                  ucii_df: pd.DataFrame | None,
                  employment_df: pd.DataFrame | None) -> None:
    """
    Section 4: Productivity & Unit Labor Costs.
    """
    pdf.section_title("4. Productivity & Unit Labor Costs")

    pdf.body_text(
        "Productivity YoY = EMAE sector output YoY minus sector employment YoY. "
        "Unit Labor Cost (ULC) YoY = real wage YoY minus productivity YoY. "
        "Positive ULC means labor costs are rising faster than output -- "
        "competitiveness is deteriorating. "
        "Flag: ULC positive for 3+ consecutive months = competitiveness warning."
    )

    SECTORS = ["industry", "construction", "services"]

    # ---- 4a: Productivity by sector ----
    if productivity_df is not None and not productivity_df.empty:
        prod_df = productivity_df.copy()
        prod_df["date"] = pd.to_datetime(prod_df["date"])

        pdf.subsection("4a. Output per Worker by Sector")

        prod_cols = [f"productivity_{s}_yoy_pct" for s in SECTORS
                     if f"productivity_{s}_yoy_pct" in prod_df.columns]
        if prod_cols:
            disp = prod_df.copy()
            disp["date"] = disp["date"].dt.strftime("%b %Y")
            rename = {c: c.replace("productivity_", "").replace("_yoy_pct", "").title()
                      for c in prod_cols}
            disp = disp.rename(columns=rename)
            pdf.add_table_n(
                disp, ["date"] + list(rename.values()),
                fmt={c: "{:+.1f}%" for c in rename.values()},
                title="Productivity YoY % by Sector (EMAE output - employment)",
                limit=20,
            )

        chart = chart_productivity(prod_df, SECTORS, "productivity_by_sector.png")
        pdf.add_chart(chart, caption="Output per worker YoY % (EMAE sector - employment sector)")

        # ---- 4b: ULC by sector ----
        pdf.subsection("4b. Unit Labor Costs by Sector")

        ulc_cols = [f"ulc_{s}_yoy_pct" for s in SECTORS
                    if f"ulc_{s}_yoy_pct" in prod_df.columns]
        if ulc_cols:
            disp_u = prod_df.copy()
            disp_u["date"] = disp_u["date"].dt.strftime("%b %Y")
            rename_u = {c: c.replace("ulc_", "").replace("_yoy_pct", " ULC").title()
                        for c in ulc_cols}
            disp_u = disp_u.rename(columns=rename_u)
            pdf.add_table_n(
                disp_u, ["date"] + list(rename_u.values()),
                fmt={c: "{:+.1f}%" for c in rename_u.values()},
                title="Unit Labor Cost YoY % (positive = competitiveness deteriorating)",
                limit=20,
            )

            # Flag per sector
            for sector in SECTORS:
                col = f"ulc_{sector}_yoy_pct"
                if col in prod_df.columns:
                    flag = _ulc_flag(prod_df[col])
                    pdf.body_text(f"{sector.title()}: {flag}")

        chart_u = chart_ulc(prod_df, SECTORS, "productivity_ulc.png")
        pdf.add_chart(chart_u,
                      caption="ULC YoY %: red=positive (costs rising faster than output), green=negative")

    else:
        pdf.body_text(
            "Productivity data unavailable -- requires both EMAE sectoral data "
            "and SIPA employment by sector."
        )

    # ---- 4c: Capacity utilization ----
    pdf.subsection("4c. Manufacturing Capacity Utilization")
    pdf.body_text(
        "Sector-level UCII (% of installed capacity used). "
        "No single headline UCII series available on datos.gob.ar; "
        "metals, textiles, and automotive are shown as a proxy basket."
    )

    if ucii_df is not None and not ucii_df.empty:
        ucii_disp = ucii_df.copy()
        ucii_disp["date"] = pd.to_datetime(ucii_disp["date"]).dt.strftime("%b %Y")
        ucii_cols = [c for c in ["ucii_metals_pct", "ucii_textiles_pct",
                                   "ucii_auto_pct", "ucii_avg_pct"] if c in ucii_disp.columns]
        rename_u = {c: c.replace("ucii_", "").replace("_pct", "").title()
                    for c in ucii_cols}
        ucii_disp = ucii_disp.rename(columns=rename_u)
        pdf.add_table_n(
            ucii_disp, ["date"] + list(rename_u.values()),
            fmt={c: "{:.1f}%" for c in rename_u.values()},
            title="Capacity Utilization by Sector (% of installed capacity)",
            limit=24,
        )
    else:
        pdf.body_text("Capacity utilization data unavailable.")

    pdf.note(
        "Employment: SIPA sector data (155.1_ISTRIARIA/CTRUCCIION/SICIOSIOS_C_0_0_*), quarterly. "
        "Output: EMAE sectoral YoY (gdp/emae.csv). "
        "UCII: 31.3_UIMB_2004_M_33 (metals), 29.3_UPT_2006_M_23 (textiles), "
        "29.3_UV_2006_M_25 (automotive)."
    )
