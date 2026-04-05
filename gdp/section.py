"""
GDP module — section builder.
Builds the "Real GDP" PDF section and markdown.
"""

import pandas as pd

from utils import get_logger

log = get_logger("gdp.section")


def _fmt_quarter(val) -> str:
    s = str(val)
    if len(s) == 6 and "Q" in s:
        year, q = s.split("Q")
        return f"Q{q} {year}"
    return s


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
    emae_df       = data.get("emae_df")

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
            title="GDP Expenditure Components — YoY Growth (C, G, I, X, M, GDP)"
        )

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
            title="EMAE — Monthly Activity YoY % (last 12 months)"
        )


def build_md_section(data: dict) -> str:
    gdp_df        = data.get("gdp_df")
    components_df = data.get("components_df")
    emae_df       = data.get("emae_df")

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

    gdp_table = ""
    if gdp_df is not None and not gdp_df.empty:
        gc = [c for c in gdp_df.columns if "gdp" in c]
        if gc:
            gdp_display = gdp_df.tail(8).copy()
            gdp_display["quarter"] = gdp_display["date"].apply(_fmt_quarter)
            gdp_table = "\n**Real GDP Growth YoY (last 8 periods)**\n\n" + \
                        _md_table(gdp_display, ["quarter", gc[0]], fmt={gc[0]: "{:.1f}%"})

    if components_df is not None and not components_df.empty:
        comp_cols = ["C_pct", "G_pct", "I_pct", "X_pct", "M_pct", "GDP_pct"]
        comp_cols = [c for c in comp_cols if c in components_df.columns]
        gdp_table += "\n\n**GDP Expenditure Components — YoY Growth**\n\n" + \
                     _md_table(components_df, ["quarter"] + comp_cols,
                               fmt={c: "{:.1f}%" for c in comp_cols})

    if emae_df is not None and not emae_df.empty:
        emae_disp = emae_df.tail(12).copy()
        emae_disp["date"] = pd.to_datetime(emae_disp["date"]).dt.strftime("%b %Y")
        sector_cols = [c for c in emae_disp.columns if c.endswith("_pct") and c != "emae_yoy_pct"]
        ecols = ["date", "emae_yoy_pct"] + sector_cols
        ecols = [c for c in ecols if c in emae_disp.columns]
        gdp_table += "\n\n**EMAE — Monthly Activity YoY % (last 12 months)**\n\n" + \
                     _md_table(emae_disp, ecols, fmt={c: "{:.1f}%" for c in ecols if c != "date"})

    return f"""## 3. Real GDP

{summarise(data)}
{gdp_table}"""
