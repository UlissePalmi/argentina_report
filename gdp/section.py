"""
GDP module — section builder.
Builds the "Real GDP" PDF section and markdown.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

from utils import CHARTS_DIR, get_logger

log = get_logger("gdp.section")

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

# FBCF sub-component display metadata
FBCF_META = {
    "fbcf_constr":    ("Construction",        "dollar-neutral",  "#2f9e44"),
    "fbcf_maq_nac":   ("Domestic machinery",  "dollar-neutral",  "#1971c2"),
    "fbcf_maq_imp":   ("Imported machinery",  "dollar-draining", "#e67700"),
    "fbcf_transport": ("Transport equipment", "dollar-draining", "#c92a2a"),
}


def _fmt_quarter(val) -> str:
    s = str(val)
    if len(s) == 6 and "Q" in s:
        year, q = s.split("Q")
        return f"Q{q} {year}"
    return s


def _pct(v) -> str:
    try:
        return f"{float(v):+.1f}%"
    except (TypeError, ValueError):
        return "n/a"


def chart_gdp_nominal(nominal_df: pd.DataFrame,
                      filename: str = "gdp_composition_nominal.png") -> str | None:
    """Stacked area (C, G, I) + line (NX) — nominal shares % of GDP."""
    cols = ["C_share_nom", "G_share_nom", "I_share_nom", "NX_share_nom"]
    avail = [c for c in cols if c in nominal_df.columns]
    if not avail:
        return None
    sub = nominal_df[["date"] + avail].dropna(subset=avail, how="all").copy()
    if sub.empty:
        return None

    sub["date"] = pd.PeriodIndex(sub["date"], freq="Q").to_timestamp()
    path = str(CHARTS_DIR / filename)

    colors = {"C_share_nom": "#1971c2", "G_share_nom": "#e67700",
              "I_share_nom": "#2f9e44", "NX_share_nom": "#c92a2a"}
    labels = {"C_share_nom": "C — Private consumption",
              "G_share_nom": "G — Government",
              "I_share_nom": "I — Investment (FBCF)",
              "NX_share_nom": "NX — Net exports"}

    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(11, 5))
        dates = sub["date"].values
        stack_cols = [c for c in ["C_share_nom", "G_share_nom", "I_share_nom"] if c in avail]
        bottom = None
        for col in stack_cols:
            vals = sub[col].values
            if bottom is None:
                ax.fill_between(dates, vals, alpha=0.55, color=colors[col], label=labels[col])
                bottom = vals.copy()
            else:
                ax.fill_between(dates, bottom, bottom + vals, alpha=0.55,
                                color=colors[col], label=labels[col])
                bottom = bottom + vals
        if "NX_share_nom" in avail:
            ax.plot(dates, sub["NX_share_nom"].values, color=colors["NX_share_nom"],
                    linewidth=2.2, marker="o", markersize=4, label=labels["NX_share_nom"])
            ax.axhline(0, color="#495057", linewidth=0.6, linestyle="--")
        ax.set_ylabel("% of GDP (current prices)")
        ax.set_title("GDP Expenditure Composition -- % of GDP (current prices)",
                     fontsize=11, fontweight="bold", pad=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=8)
        ax.legend(fontsize=8, framealpha=0.9, loc="upper left")
        ax.grid(axis="y", alpha=0.4)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    log.info("Chart saved: %s", path)
    return path


def chart_gdp_composition(components_df: pd.DataFrame,
                          filename: str = "gdp_composition.png") -> str | None:
    """Stacked area (C, G, I) + line (NX) — real (constant 2004 price) shares."""
    cols = ["C_share_real", "G_share_real", "I_share_real", "NX_share_real"]
    avail = [c for c in cols if c in components_df.columns]
    if not avail:
        return None
    sub = components_df[["date"] + avail].dropna(subset=avail, how="all").copy()
    if sub.empty:
        return None

    sub["date"] = pd.PeriodIndex(sub["date"], freq="Q").to_timestamp()
    path = str(CHARTS_DIR / filename)

    colors = {"C_share_real": "#1971c2", "G_share_real": "#e67700",
              "I_share_real": "#2f9e44", "NX_share_real": "#c92a2a"}
    labels = {"C_share_real": "C — Private consumption",
              "G_share_real": "G — Government",
              "I_share_real": "I — Investment (FBCF)",
              "NX_share_real": "NX — Net exports"}

    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(11, 5))
        dates = sub["date"].values
        stack_cols = [c for c in ["C_share_real", "G_share_real", "I_share_real"] if c in avail]
        bottom = None
        for col in stack_cols:
            vals = sub[col].values
            if bottom is None:
                ax.fill_between(dates, vals, alpha=0.55, color=colors[col], label=labels[col])
                bottom = vals.copy()
            else:
                ax.fill_between(dates, bottom, bottom + vals, alpha=0.55,
                                color=colors[col], label=labels[col])
                bottom = bottom + vals
        if "NX_share_real" in avail:
            ax.plot(dates, sub["NX_share_real"].values, color=colors["NX_share_real"],
                    linewidth=2.2, marker="o", markersize=4, label=labels["NX_share_real"])
            ax.axhline(0, color="#495057", linewidth=0.6, linestyle="--")
        ax.set_ylabel("% of GDP (constant 2004 prices)")
        ax.set_title("GDP Expenditure Composition -- % of GDP (constant 2004 prices)",
                     fontsize=11, fontweight="bold", pad=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=8)
        ax.legend(fontsize=8, framealpha=0.9, loc="upper left")
        ax.grid(axis="y", alpha=0.4)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    log.info("Chart saved: %s", path)
    return path


def chart_fbcf_breakdown(fbcf_df: pd.DataFrame,
                         filename: str = "gdp_fbcf.png") -> str | None:
    """Stacked bar: FBCF sub-component share of total FBCF over time."""
    share_cols = [f"{k}_share" for k in FBCF_META if f"{k}_share" in fbcf_df.columns]
    if not share_cols:
        return None
    sub = fbcf_df[["date"] + share_cols].dropna(subset=share_cols, how="all").tail(12).copy()
    if sub.empty:
        return None

    path = str(CHARTS_DIR / filename)
    x = list(range(len(sub)))
    quarters = sub["date"].tolist()

    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(12, 5))
        bottom = [0.0] * len(sub)
        for col in share_cols:
            key = col.replace("_share", "")
            label_name, category, color = FBCF_META.get(key, (key, "", "#888888"))
            vals = sub[col].fillna(0).tolist()
            ax.bar(x, vals, bottom=bottom, color=color, alpha=0.85,
                   label=f"{label_name} ({category})")
            bottom = [b + v for b, v in zip(bottom, vals)]
        ax.set_xticks(x)
        ax.set_xticklabels(quarters, rotation=45, ha="right", fontsize=8)
        ax.set_ylabel("% of total FBCF")
        ax.set_title("FBCF Investment Composition by Sub-component (% of total fixed investment)",
                     fontsize=11, fontweight="bold", pad=8)
        ax.legend(fontsize=8, framealpha=0.9, loc="upper left")
        ax.set_ylim(0, 115)
        ax.grid(axis="y", alpha=0.4)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    log.info("Chart saved: %s", path)
    return path


def chart_fbcf_growth(fbcf_df: pd.DataFrame,
                      filename: str = "gdp_fbcf_growth.png") -> str | None:
    """Line chart: FBCF sub-component YoY growth rates."""
    yoy_cols = [f"{k}_yoy" for k in FBCF_META if f"{k}_yoy" in fbcf_df.columns]
    if not yoy_cols:
        return None
    sub = fbcf_df[["date"] + yoy_cols].dropna(subset=yoy_cols, how="all").tail(12).copy()
    if sub.empty:
        return None

    sub["date"] = pd.PeriodIndex(sub["date"], freq="Q").to_timestamp()
    path = str(CHARTS_DIR / filename)

    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(11, 4))
        for col in yoy_cols:
            key = col.replace("_yoy", "")
            label_name, category, color = FBCF_META.get(key, (key, "", "#888888"))
            ax.plot(sub["date"], sub[col], color=color, linewidth=2,
                    marker="o", markersize=3, label=f"{label_name} ({category})")
        ax.axhline(0, color="#495057", linewidth=0.8)
        ax.set_ylabel("YoY %")
        ax.set_title("FBCF Sub-component YoY Growth (constant 2004 prices)",
                     fontsize=11, fontweight="bold", pad=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=8)
        ax.legend(fontsize=8, framealpha=0.9)
        ax.grid(axis="y", alpha=0.4)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    log.info("Chart saved: %s", path)
    return path


def _fbcf_analytical_text(fbcf_df: pd.DataFrame, consumption_df=None) -> str:
    """Generate analytical text about FBCF drivers and mortgage connection."""
    lines = []

    latest_yoys = {}
    for key, (label, category, _) in FBCF_META.items():
        col = f"{key}_yoy"
        if col in fbcf_df.columns:
            vals = fbcf_df[col].dropna()
            if not vals.empty:
                latest_yoys[key] = (label, category, float(vals.iloc[-1]))

    if not latest_yoys:
        return "FBCF sub-component data unavailable for detailed analysis."

    declining = sorted([(l, c, v) for l, c, v in latest_yoys.values() if v < 0], key=lambda x: x[2])
    growing   = sorted([(l, c, v) for l, c, v in latest_yoys.values() if v > 0],
                       key=lambda x: x[2], reverse=True)

    constr_yoy  = latest_yoys.get("fbcf_constr",    (None, None, None))[2]
    maq_imp_yoy = latest_yoys.get("fbcf_maq_imp",   (None, None, None))[2]

    if declining:
        top = declining[0]
        text = (f"Investment driver: the largest drag on FBCF is {top[0]} "
                f"({_pct(top[2])} YoY, {top[1]}). ")
        if top[1] == "dollar-draining":
            text += ("A contraction in dollar-draining imported machinery is SHORT-TERM POSITIVE "
                     "for reserves -- fewer import dollars required. However it signals weak domestic "
                     "capital formation and reduced future productive capacity. ")
        else:
            text += ("A contraction in dollar-neutral construction drags domestic employment "
                     "and infrastructure without improving the reserve position. ")
    elif growing:
        top = growing[0]
        text = (f"Investment driver: {top[0]} is the strongest contributor to FBCF growth "
                f"({_pct(top[2])} YoY, {top[1]}). ")
    else:
        text = "FBCF sub-components show mixed signals. "

    lines.append(text)

    # Mortgage vs construction contradiction
    if consumption_df is not None and "real_mortgages_pct" in consumption_df.columns:
        mort_vals = consumption_df["real_mortgages_pct"].dropna()
        if not mort_vals.empty and constr_yoy is not None:
            mortgage_yoy = float(mort_vals.iloc[-1])
            if constr_yoy < 0 and mortgage_yoy > 10:
                lines.append(
                    f"CONTRADICTION FLAGGED: Real mortgage credit is booming "
                    f"({_pct(mortgage_yoy)} YoY) while construction FBCF is contracting "
                    f"({_pct(constr_yoy)} YoY). Mortgages are financing transfers of existing "
                    f"homes -- not new construction. This drives price appreciation without "
                    f"expanding housing supply. Risk: affordability crisis builds while "
                    f"construction employment stagnates."
                )
            elif constr_yoy > 0 and mortgage_yoy > 10:
                lines.append(
                    f"Construction FBCF ({_pct(constr_yoy)} YoY) and real mortgage credit "
                    f"({_pct(mortgage_yoy)} YoY) are both expanding -- supply and demand for "
                    f"housing moving together. Watch for imported construction materials "
                    f"pressuring the reserve position as activity accelerates."
                )

    return " ".join(lines)


def summarise(data: dict) -> str:
    gdp_df = data.get("gdp_df")
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


def build_pdf_section(pdf, data: dict) -> None:
    gdp_df        = data.get("gdp_df")
    components_df = data.get("components_df")
    nominal_df    = data.get("nominal_df")
    fbcf_df       = data.get("fbcf_df")
    emae_df       = data.get("emae_df")
    consumption_df = data.get("consumption_df")  # optional — for mortgage cross-check

    pdf.section_title("3. Real GDP")
    pdf.body_text(summarise(data))

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

    if components_df is not None and not components_df.empty:
        comp_cols = ["C_pct", "G_pct", "I_pct", "X_pct", "M_pct", "GDP_pct"]
        comp_cols = [c for c in comp_cols if c in components_df.columns]
        pdf.add_table(
            components_df, ["quarter"] + comp_cols,
            fmt={c: "{:.1f}%" for c in comp_cols},
            title="GDP Expenditure Components -- YoY Growth (C, G, I, X, M, GDP)"
        )

    # ---- GDP composition (nominal shares — primary) ----
    pdf.section_title("3b. GDP Composition: C + G + I + NX as % of GDP")

    if nominal_df is not None and not nominal_df.empty:
        pdf.body_text(
            "Component shares of GDP at CURRENT PRICES (nominal pesos). "
            "I = sum of 4 FBCF sub-components (construction, domestic/imported machinery, transport). "
            "C = private consumption, G = government consumption, NX = net exports (X - M)."
        )
        nom_share_cols = [c for c in ["C_share_nom", "G_share_nom", "I_share_nom", "NX_share_nom"]
                          if c in nominal_df.columns]
        if nom_share_cols:
            disp = nominal_df[["quarter"] + nom_share_cols].dropna(
                subset=nom_share_cols, how="all").copy()
            rename = {"C_share_nom": "C %GDP", "G_share_nom": "G %GDP",
                      "I_share_nom": "I %GDP", "NX_share_nom": "NX %GDP"}
            rename = {k: v for k, v in rename.items() if k in nom_share_cols}
            disp = disp.rename(columns=rename)
            pdf.add_table(
                disp, ["quarter"] + list(rename.values()),
                fmt={v: "{:.1f}%" for v in rename.values()},
                title="GDP Composition -- % of GDP (current prices)"
            )
        pdf.add_chart(chart_gdp_nominal(nominal_df),
                      caption="GDP composition (nominal): C, G, I stacked + NX line (% of GDP)")

    elif components_df is not None and not components_df.empty:
        # Fallback to real shares if nominal unavailable
        pdf.body_text(
            "Nominal GDP composition unavailable -- showing constant-2004-price shares as reference."
        )

    # Real shares as secondary reference
    if components_df is not None and not components_df.empty:
        real_share_cols = [c for c in ["C_share_real", "G_share_real", "I_share_real", "NX_share_real"]
                           if c in components_df.columns]
        if real_share_cols:
            disp_r = components_df[["quarter"] + real_share_cols].dropna(
                subset=real_share_cols, how="all").copy()
            rename_r = {"C_share_real": "C %GDP (real)", "G_share_real": "G %GDP (real)",
                        "I_share_real": "I %GDP (real)", "NX_share_real": "NX %GDP (real)"}
            rename_r = {k: v for k, v in rename_r.items() if k in real_share_cols}
            disp_r = disp_r.rename(columns=rename_r)
            pdf.add_table(
                disp_r, ["quarter"] + list(rename_r.values()),
                fmt={v: "{:.1f}%" for v in rename_r.values()},
                title="GDP Composition -- % of GDP (constant 2004 prices, reference)"
            )
            pdf.add_chart(chart_gdp_composition(components_df),
                          caption="GDP composition (real): constant 2004 prices")

        pdf.body_text(
            "NOTE: Shares in constant 2004 prices (real) diverge from nominal shares due to base-year "
            "effects and relative price changes. NX appears negative in real terms even when the nominal "
            "trade balance is positive -- import VOLUMES grew faster than export volumes (real exchange "
            "rate appreciation effect). For dollar flow analysis use the current account section, "
            "not NX share here."
        )

    # ---- FBCF breakdown ----
    if fbcf_df is not None and not fbcf_df.empty:
        pdf.section_title("3c. FBCF Investment Breakdown")
        pdf.body_text(
            "FBCF (Formacion Bruta de Capital Fijo) sub-components at constant 2004 prices. "
            "Dollar classification: Construction and domestic machinery are dollar-neutral "
            "(no direct FX impact). Imported machinery and transport equipment are dollar-draining "
            "(each peso of investment requires FX for the import component)."
        )

        share_cols = [f"{k}_share" for k in FBCF_META if f"{k}_share" in fbcf_df.columns]
        yoy_cols   = [f"{k}_yoy"   for k in FBCF_META if f"{k}_yoy"   in fbcf_df.columns]
        if share_cols or yoy_cols:
            disp_f = fbcf_df[["quarter"] + share_cols + yoy_cols].dropna(
                subset=share_cols + yoy_cols, how="all").copy()
            col_rename = {}
            for key, (label, category, _) in FBCF_META.items():
                short = label.split()[0]  # "Construction", "Domestic", "Imported", "Transport"
                if f"{key}_share" in disp_f.columns:
                    col_rename[f"{key}_share"] = f"{short} % FBCF"
                if f"{key}_yoy" in disp_f.columns:
                    col_rename[f"{key}_yoy"] = f"{short} YoY"
            disp_f = disp_f.rename(columns=col_rename)
            display_cols = ["quarter"] + list(col_rename.values())
            display_cols = [c for c in display_cols if c in disp_f.columns]
            fmt_f = {v: "{:.1f}%" for v in col_rename.values()}
            pdf.add_table(disp_f, display_cols, fmt=fmt_f,
                          title="FBCF Sub-components: Share of Total FBCF + YoY Growth")

        pdf.add_chart(chart_fbcf_breakdown(fbcf_df),
                      caption="FBCF composition: dollar-neutral (green/blue) vs dollar-draining (orange/red)")
        pdf.add_chart(chart_fbcf_growth(fbcf_df),
                      caption="FBCF sub-component YoY growth % (constant 2004 prices)")

        analysis = _fbcf_analytical_text(fbcf_df, consumption_df)
        if analysis:
            pdf.body_text(analysis)

    if emae_df is not None and not emae_df.empty:
        emae_display = emae_df.tail(12).copy()
        emae_display["date"] = pd.to_datetime(emae_display["date"]).dt.strftime("%b %Y")
        sector_cols = [c for c in emae_display.columns
                       if c.endswith("_pct") and c != "emae_yoy_pct"]
        all_cols = ["date", "emae_yoy_pct"] + sector_cols
        all_cols = [c for c in all_cols if c in emae_display.columns]
        pdf.add_table(
            emae_display, all_cols,
            fmt={c: "{:.1f}%" for c in all_cols if c != "date"},
            title="EMAE -- Monthly Activity YoY % (last 12 months)"
        )


def build_md_section(data: dict) -> str:
    gdp_df        = data.get("gdp_df")
    components_df = data.get("components_df")
    nominal_df    = data.get("nominal_df")
    fbcf_df       = data.get("fbcf_df")
    emae_df       = data.get("emae_df")
    consumption_df = data.get("consumption_df")

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
                if c in ("date", "quarter"):
                    cells.append(str(v))
                    continue
                f = fmt.get(c, "{}")
                try:    cells.append(f.format(v))
                except: cells.append(str(v))
            rows.append("| " + " | ".join(cells) + " |")
        return "\n".join([header, sep] + rows)

    out = f"## 3. Real GDP\n\n{summarise(data)}\n"

    if gdp_df is not None and not gdp_df.empty:
        gc = [c for c in gdp_df.columns if "gdp" in c]
        if gc:
            disp = gdp_df.tail(8).copy()
            disp["quarter"] = disp["date"].apply(_fmt_quarter)
            out += "\n**Real GDP Growth YoY (last 8 periods)**\n\n" + \
                   _md_table(disp, ["quarter", gc[0]], fmt={gc[0]: "{:.1f}%"})

    if components_df is not None and not components_df.empty:
        comp_cols = [c for c in ["C_pct", "G_pct", "I_pct", "X_pct", "M_pct", "GDP_pct"]
                     if c in components_df.columns]
        out += "\n\n**GDP Expenditure Components -- YoY Growth**\n\n" + \
               _md_table(components_df, ["quarter"] + comp_cols,
                         fmt={c: "{:.1f}%" for c in comp_cols})

    if nominal_df is not None and not nominal_df.empty:
        nom_cols = [c for c in ["C_share_nom", "G_share_nom", "I_share_nom", "NX_share_nom"]
                    if c in nominal_df.columns]
        if nom_cols:
            out += "\n\n**GDP Composition -- % of GDP (current prices)**\n\n" + \
                   _md_table(nominal_df, ["quarter"] + nom_cols,
                             fmt={c: "{:.1f}%" for c in nom_cols})

    if components_df is not None and not components_df.empty:
        real_cols = [c for c in ["C_share_real", "G_share_real", "I_share_real", "NX_share_real"]
                     if c in components_df.columns]
        if real_cols:
            out += "\n\n**GDP Composition -- % of GDP (constant 2004 prices, reference)**\n\n" + \
                   _md_table(components_df, ["quarter"] + real_cols,
                             fmt={c: "{:.1f}%" for c in real_cols})

    if fbcf_df is not None and not fbcf_df.empty:
        share_cols = [f"{k}_share" for k in FBCF_META if f"{k}_share" in fbcf_df.columns]
        yoy_cols   = [f"{k}_yoy"   for k in FBCF_META if f"{k}_yoy"   in fbcf_df.columns]
        if share_cols or yoy_cols:
            out += "\n\n**FBCF Investment Sub-components**\n\n" + \
                   _md_table(fbcf_df, ["quarter"] + share_cols + yoy_cols,
                             fmt={c: "{:.1f}%" for c in share_cols + yoy_cols})
        analysis = _fbcf_analytical_text(fbcf_df, consumption_df)
        out += f"\n\n{analysis}"

    if emae_df is not None and not emae_df.empty:
        emae_disp = emae_df.tail(12).copy()
        emae_disp["date"] = pd.to_datetime(emae_disp["date"]).dt.strftime("%b %Y")
        sector_cols = [c for c in emae_disp.columns if c.endswith("_pct") and c != "emae_yoy_pct"]
        ecols = ["date", "emae_yoy_pct"] + sector_cols
        ecols = [c for c in ecols if c in emae_disp.columns]
        out += "\n\n**EMAE -- Monthly Activity YoY % (last 12 months)**\n\n" + \
               _md_table(emae_disp, ecols, fmt={c: "{:.1f}%" for c in ecols if c != "date"})

    return out
