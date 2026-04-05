"""
Production module — section builder for the consumption deep-dive report.
Renders Section 3: Production & Output.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

from utils import CHARTS_DIR, get_logger

log = get_logger("production.section")

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


def chart_production(production_df: pd.DataFrame, cols: list[str],
                     title: str, filename: str) -> str | None:
    """Bar chart for YoY columns, line for MoM if available."""
    yoy_cols = [c for c in cols if "yoy" in c and c in production_df.columns]
    if not yoy_cols:
        return None
    sub = production_df[["date"] + yoy_cols].dropna(subset=yoy_cols, how="all").tail(24)
    if sub.empty:
        return None

    path = str(CHARTS_DIR / filename)
    dates = pd.to_datetime(sub["date"])

    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 4))
        colors = ["#2f9e44", "#1971c2", "#e67700", "#c92a2a"]
        for i, col in enumerate(yoy_cols):
            label = col.replace("_yoy_pct", "").replace("_", " ").title()
            if len(yoy_cols) == 1:
                bar_colors = ["#2f9e44" if v >= 0 else "#c92a2a" for v in sub[col]]
                ax.bar(dates, sub[col], color=bar_colors, width=20, alpha=0.8, label=label)
            else:
                ax.plot(dates, sub[col], color=colors[i % len(colors)],
                        linewidth=2, marker="o", markersize=3, label=label)
        ax.axhline(0, color="#495057", linewidth=0.8)
        ax.set_ylabel("YoY %")
        ax.set_title(title, fontsize=11, fontweight="bold", pad=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=8)
        ax.legend(fontsize=8, framealpha=0.8)
        ax.grid(axis="y", alpha=0.5)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    log.info("Chart saved: %s", path)
    return path


def build_section(pdf, production_df: pd.DataFrame | None,
                  agro_df: pd.DataFrame | None) -> None:
    """
    Section 3: Production & Output.
    Commodity (oil + gas + agriculture) vs domestic (IPI + ISAC construction).
    """
    from report.build import _safe

    pdf.section_title("3. Production & Output")

    if production_df is None or production_df.empty:
        pdf.body_text("Production data unavailable.")
        return

    df = production_df.copy()
    df["date"] = pd.to_datetime(df["date"])

    # --- Two-speed economy flag ---
    commodity_cols = [c for c in ["oil_yoy_pct", "gas_yoy_pct"] if c in df.columns]
    domestic_cols  = [c for c in ["ipi_yoy_pct", "isac_cement_yoy_pct"] if c in df.columns]

    comm_avg = None
    dom_avg  = None
    if commodity_cols:
        comm_avg = sum(_avg3(df[c]) or 0 for c in commodity_cols) / len(commodity_cols)
    if domestic_cols:
        dom_avg = sum(_avg3(df[c]) or 0 for c in domestic_cols) / len(domestic_cols)

    if comm_avg is not None and dom_avg is not None:
        if comm_avg > 5 and dom_avg < -5:
            flag = (
                f"TWO-SPEED ECONOMY: Commodity production ({_pct(comm_avg)} avg, "
                f"3-month) is expanding while domestic production ({_pct(dom_avg)} avg) "
                f"is contracting. Dollar-generating sectors growing, peso economy weak."
            )
        elif comm_avg > 0 and dom_avg > 0:
            flag = (
                f"Broad-based production growth: both commodity ({_pct(comm_avg)}) "
                f"and domestic ({_pct(dom_avg)}) sectors expanding."
            )
        else:
            flag = (
                f"Mixed signals: commodity production {_pct(comm_avg)}, "
                f"domestic production {_pct(dom_avg)} (3-month avg)."
            )
        pdf.body_text(flag)

    # ---- 3a: Domestic production (peso economy) ----
    pdf.subsection("3a. Domestic Production (Manufacturing + Construction)")
    pdf.body_text(
        "IPI = Indice de Produccion Industrial (INDEC, monthly). "
        "ISAC proxy = cement inputs to construction (seasonally adjusted; "
        "no monthly headline ISAC available on datos.gob.ar). "
        "Both are peso-economy indicators linked to domestic demand."
    )

    dom_yoy_cols = [c for c in ["ipi_yoy_pct", "ipi_food_yoy_pct",
                                  "ipi_steel_yoy_pct", "ipi_auto_yoy_pct",
                                  "isac_cement_yoy_pct"] if c in df.columns]
    dom_mom_cols = [c for c in ["ipi_mom_pct", "isac_cement_mom_pct"] if c in df.columns]

    if dom_yoy_cols:
        disp = df.copy()
        disp["date"] = disp["date"].dt.strftime("%b %Y")
        rename = {c: c.replace("_yoy_pct", "").replace("_", " ") for c in dom_yoy_cols}
        disp = disp.rename(columns=rename)
        display_cols = ["date"] + list(rename.values())
        pdf.add_table_n(
            disp, display_cols,
            fmt={c: "{:+.1f}%" for c in rename.values()},
            title="Domestic Production -- YoY %",
            limit=24,
        )

    if dom_mom_cols:
        disp_m = df.copy()
        disp_m["date"] = disp_m["date"].dt.strftime("%b %Y")
        rename_m = {c: c.replace("_mom_pct", " MoM").replace("_", " ") for c in dom_mom_cols}
        disp_m = disp_m.rename(columns=rename_m)
        pdf.add_table_n(
            disp_m, ["date"] + list(rename_m.values()),
            fmt={c: "{:+.1f}%" for c in rename_m.values()},
            title="Domestic Production -- MoM %",
            limit=24,
        )

    chart = chart_production(
        df, ["ipi_yoy_pct", "ipi_food_yoy_pct", "ipi_steel_yoy_pct"],
        title="IPI Manufacturing -- Real YoY % by Subsector",
        filename="production_ipi.png"
    )
    pdf.add_chart(chart, caption="IPI: headline + food & beverages + steel (YoY %)")

    chart_isac = chart_production(
        df, ["isac_cement_yoy_pct"],
        title="ISAC Proxy (Cement Inputs) -- YoY %",
        filename="production_isac.png"
    )
    pdf.add_chart(chart_isac, caption="Construction activity proxy (cement inputs, YoY %)")

    # ---- 3b: Commodity production (dollar economy) ----
    pdf.subsection("3b. Commodity Production (Oil + Gas)")
    pdf.body_text(
        "Oil and gas are Argentina's primary dollar-generating production sectors. "
        "Growth here supports the trade surplus and BCRA reserve accumulation. "
        "Source: Secretaria de Energia via datos.gob.ar."
    )

    energy_yoy = [c for c in ["oil_yoy_pct", "gas_yoy_pct"] if c in df.columns]
    energy_mom  = [c for c in ["oil_mom_pct", "gas_mom_pct"]  if c in df.columns]

    if energy_yoy:
        disp = df.copy()
        disp["date"] = disp["date"].dt.strftime("%b %Y")
        rename = {c: c.replace("_yoy_pct", "").replace("_", " ") for c in energy_yoy}
        disp = disp.rename(columns=rename)
        pdf.add_table_n(
            disp, ["date"] + list(rename.values()),
            fmt={c: "{:+.1f}%" for c in rename.values()},
            title="Energy Production -- YoY %",
            limit=24,
        )
    if energy_mom:
        disp_m = df.copy()
        disp_m["date"] = disp_m["date"].dt.strftime("%b %Y")
        rename_m = {c: c.replace("_mom_pct", " MoM").replace("_", " ") for c in energy_mom}
        disp_m = disp_m.rename(columns=rename_m)
        pdf.add_table_n(
            disp_m, ["date"] + list(rename_m.values()),
            fmt={c: "{:+.1f}%" for c in rename_m.values()},
            title="Energy Production -- MoM %",
            limit=24,
        )

    chart_energy = chart_production(
        df, ["oil_yoy_pct", "gas_yoy_pct"],
        title="Oil & Gas Production -- YoY %",
        filename="production_energy.png"
    )
    pdf.add_chart(chart_energy, caption="Crude oil and natural gas production YoY %")

    # ---- 3c: Agriculture (annual) ----
    pdf.subsection("3c. Agricultural Harvest (Annual)")
    pdf.body_text(
        "Soy, corn, and wheat harvest volumes (tonnes). "
        "Annual data only — no monthly breakdown available. "
        "Agriculture is Argentina's largest single source of export dollars."
    )
    if agro_df is not None and not agro_df.empty:
        agro_disp = agro_df.copy()
        agro_disp["date"] = pd.to_datetime(agro_disp["date"]).dt.strftime("%Y")
        vol_cols = [c for c in ["soy_tonnes", "corn_tonnes", "wheat_tonnes"] if c in agro_disp.columns]
        yoy_cols_agro = [c for c in ["soy_yoy_pct", "corn_yoy_pct", "wheat_yoy_pct"] if c in agro_disp.columns]
        if vol_cols:
            pdf.add_table_n(
                agro_disp, ["date"] + vol_cols,
                fmt={c: "{:,.0f}" for c in vol_cols},
                title="Harvest Volumes (tonnes)",
                limit=10,
            )
        if yoy_cols_agro:
            disp_yoy = agro_disp.copy()
            rename_a = {c: c.replace("_yoy_pct", " YoY") for c in yoy_cols_agro}
            disp_yoy = disp_yoy.rename(columns=rename_a)
            pdf.add_table_n(
                disp_yoy, ["date"] + list(rename_a.values()),
                fmt={c: "{:+.1f}%" for c in rename_a.values()},
                title="Harvest YoY % Change",
                limit=10,
            )
    else:
        pdf.body_text("Agricultural harvest data unavailable.")

    pdf.note(
        "IPI: 309.1_PRODUCCIONNAL_0_M_30 (INDEC). "
        "ISAC proxy: 33.4_ISAC_CEMENAND_0_0_21_24 (cement inputs, sa). "
        "Oil: 363.3_PRODUCCIONUDO__28. Gas: 364.3_PRODUCCIoNRAL__25. "
        "Agriculture: AGRO_A_Soja/Maiz/Trigo_0003 (Ministerio de Agricultura, annual)."
    )
