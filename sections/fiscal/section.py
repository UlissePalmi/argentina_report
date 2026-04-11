"""
Fiscal Balance module -- section builder.

Chart: Monthly primary balance % GDP (bars) + financial balance % GDP (line).
       Green bars = surplus, red bars = deficit.
       The gap between primary and financial = interest cost.
Table: Last 12 months -- primary % GDP and financial % GDP side by side.
Signal: Reads signals_fiscal.json via report.signal_text.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

from utils import CHARTS_DIR, get_logger
from report.signal_text import load_signal, render_signal_callout, render_signal_callout_md

log = get_logger("fiscal.section")

GREEN  = "#2f9e44"
RED    = "#c92a2a"
BLUE   = "#1971c2"
ORANGE = "#e67700"

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


def _best_cols(df: pd.DataFrame) -> tuple[str | None, str | None]:
    """Return (primary_col, financial_col) -- prefers % GDP over ARS bn."""
    primary   = next((c for c in ["fiscal_primary_pct_gdp",   "fiscal_primary_ars_bn"]   if c in df.columns), None)
    financial = next((c for c in ["fiscal_financial_pct_gdp", "fiscal_financial_ars_bn"] if c in df.columns), None)
    return primary, financial


def _unit_label(col: str) -> str:
    return "% of GDP" if "pct_gdp" in col else "ARS bn"


def chart_fiscal(fiscal_df: pd.DataFrame | None) -> str | None:
    """
    Bars = primary balance (% GDP preferred, green/red).
    Dashed line = financial balance after interest.
    The gap between bar top and line = monthly interest cost.
    """
    if fiscal_df is None or fiscal_df.empty:
        return None

    primary_col, financial_col = _best_cols(fiscal_df)
    if primary_col is None:
        return None

    df = fiscal_df[["date"] + [c for c in [primary_col, financial_col] if c]].copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=[primary_col]).tail(24)
    if df.empty:
        return None

    path       = str(CHARTS_DIR / "chart_fiscal.png")
    unit_label = _unit_label(primary_col)

    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 4.5))

        vals   = df[primary_col].tolist()
        dates  = df["date"].tolist()
        colors = [GREEN if v >= 0 else RED for v in vals]

        date_range = (df["date"].iloc[-1] - df["date"].iloc[0]).days
        bar_width  = max(15, int(date_range / len(df) * 0.7))

        ax.bar(dates, vals, color=colors, width=bar_width, alpha=0.85,
               label=f"Primary balance ({unit_label})")
        ax.axhline(0, color="#343a40", linewidth=1.0)

        if financial_col and financial_col in df.columns:
            fin = df[["date", financial_col]].dropna(subset=[financial_col])
            if not fin.empty:
                ax.plot(fin["date"], fin[financial_col],
                        color=ORANGE, linewidth=2.0, linestyle="--",
                        marker="o", markersize=3,
                        label=f"Financial balance incl. interest ({_unit_label(financial_col)})")

        # 1.5% GDP target line (only meaningful for % GDP chart)
        if "pct_gdp" in primary_col:
            ax.axhline(1.5, color=GREEN, linewidth=0.8, linestyle=":", alpha=0.6)
            ax.text(dates[0], 1.65, "1.5% target", color=GREEN, fontsize=7, alpha=0.8)

        ax.set_ylabel(unit_label, fontsize=9)
        ax.grid(True, axis="y", alpha=0.4)
        ax.set_title("Public Sector Fiscal Balance", fontsize=13, fontweight="bold", pad=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45, ha="right", fontsize=8)
        ax.legend(framealpha=0.8, fontsize=9, loc="upper left")

        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    log.info("Chart saved: %s", path)
    return path


def summarise(data: dict) -> str:
    fiscal_df = data.get("fiscal_df")
    sig       = load_signal("fiscal")

    if fiscal_df is None or fiscal_df.empty:
        return sig.get("summary", "Fiscal balance data unavailable.")

    primary_col, financial_col = _best_cols(fiscal_df)
    if primary_col is None:
        return sig.get("summary", "Fiscal balance data unavailable.")

    df = fiscal_df[["date", primary_col]].dropna(subset=[primary_col]).sort_values("date")
    if df.empty:
        return sig.get("summary", "Fiscal balance data unavailable.")

    latest_val  = float(df[primary_col].iloc[-1])
    latest_date = pd.to_datetime(df["date"].iloc[-1]).strftime("%B %Y")
    direction   = "surplus" if latest_val >= 0 else "deficit"
    val_str     = f"{abs(latest_val):.2f}% of GDP" if "pct_gdp" in primary_col else f"ARS {abs(latest_val):.1f}bn"

    streak = 0
    for v in reversed(df[primary_col].tolist()):
        if v > 0:
            streak += 1
        else:
            break

    # Financial balance line
    fin_str = ""
    if financial_col and financial_col in fiscal_df.columns:
        fin_df = fiscal_df[["date", financial_col]].dropna(subset=[financial_col]).sort_values("date")
        if not fin_df.empty:
            fin_val = float(fin_df[financial_col].iloc[-1])
            fin_dir = "surplus" if fin_val >= 0 else "deficit"
            fin_unit = _unit_label(financial_col)
            fin_str_val = f"{abs(fin_val):.2f}% of GDP" if "pct_gdp" in financial_col else f"ARS {abs(fin_val):.1f}bn"
            fin_str = (
                f" After interest payments, the financial balance shows a {fin_dir} of {fin_str_val} "
                f"-- the gap to the primary result reflects the sovereign interest burden."
            )

    parts = [
        f"Argentina's public sector recorded a primary {direction} of {val_str} in {latest_date}.{fin_str}"
    ]

    if streak >= 6:
        parts.append(
            f"This extends {streak} consecutive months of primary surplus, "
            f"suggesting the fiscal consolidation under Milei is structural rather than cyclical."
        )
    elif streak >= 2:
        parts.append(
            f"{streak} consecutive months in primary surplus -- "
            f"consolidation is building but too early to call structural."
        )
    elif streak == 0:
        parts.append("The latest month registered a deficit, interrupting any prior surplus run.")

    if sig:
        trend = sig.get("trend", "")
        if trend == "deteriorating":
            parts.append(
                "The 3-month trend is deteriorating -- the December seasonal deficit "
                "is dragging the recent average, though the underlying surplus appears intact."
            )
        elif trend == "improving":
            parts.append("The 3-month trend is improving, with consolidation momentum accelerating.")

    parts.append(
        "Fiscal discipline is a Level 3 enabler in the master variable framework: "
        "a sustained primary surplus removes the risk of a fiscal crisis that would "
        "wipe out real wage gains, and allows monetary policy to remain focused on disinflation."
    )

    return " ".join(parts)


def _render_yearly_table_pdf(pdf, yearly: pd.DataFrame) -> None:
    """Render the compact annual summary table into the PDF."""
    from report.build import _safe
    from fpdf import XPos, YPos

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 6, "Annual Fiscal Balance as % of GDP (2023 = pre-Milei baseline)",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)

    avail_w = pdf.w - pdf.l_margin - pdf.r_margin
    col_w   = avail_w / 3

    # Header
    headers = ["Year", "Primary Balance", "Financial Balance (incl. interest)"]
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_fill_color(30, 100, 200)
    pdf.set_text_color(255, 255, 255)
    for h in headers:
        pdf.cell(col_w, 6, _safe(h), border=0, fill=True, align="C")
    pdf.ln()

    # Rows
    pdf.set_font("Helvetica", "", 8.5)
    for i, (_, row) in enumerate(yearly.iterrows()):
        bg = (240, 247, 255) if i % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*bg)

        # Year label
        pdf.set_text_color(40, 40, 40)
        pdf.cell(col_w, 6, _safe(str(row["year_label"])), border=0, fill=True, align="C")

        # Primary
        p = row["primary_pct_gdp"]
        pdf.set_text_color(0, 110, 50) if p > 0 else pdf.set_text_color(180, 0, 0)
        pdf.cell(col_w, 6, f"{p:+.2f}%", border=0, fill=True, align="C")

        # Financial
        f = row["financial_pct_gdp"]
        pdf.set_text_color(0, 110, 50) if f > 0 else pdf.set_text_color(180, 0, 0)
        pdf.cell(col_w, 6, f"{f:+.2f}%", border=0, fill=True, align="C")
        pdf.ln()

    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)


def _yearly_summary(fiscal_df: pd.DataFrame, start_year: int = 2023) -> pd.DataFrame | None:
    """
    Compute annual primary and financial balance as % of GDP.

    Formula: annual % GDP = sum of monthly % GDP values / 12
    (works because each monthly_pct = monthly_ars / (annual_gdp/12) * 100,
    so sum/12 = annual_ars / annual_gdp * 100 for a full year,
    and for a partial year gives the YTD % of estimated annual GDP).
    """
    pct_col = "fiscal_primary_pct_gdp"
    fin_col = "fiscal_financial_pct_gdp"
    if pct_col not in fiscal_df.columns:
        return None

    df = fiscal_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df = df[df["year"] >= start_year]
    if df.empty:
        return None

    agg = df.groupby("year", as_index=False).agg(
        primary_sum=(pct_col, "sum"),
        financial_sum=(fin_col, "sum") if fin_col in df.columns else (pct_col, "sum"),
        months=("date", "count"),
    )
    agg["primary_pct_gdp"]   = (agg["primary_sum"]   / 12).round(2)
    agg["financial_pct_gdp"] = (agg["financial_sum"] / 12).round(2)

    # Label partial years
    current_year = pd.Timestamp.now().year
    agg["year_label"] = agg.apply(
        lambda r: f"{int(r['year'])} ({int(r['months'])}mo YTD)"
                  if r["months"] < 12 and r["year"] == current_year
                  else str(int(r["year"])),
        axis=1,
    )
    return agg[["year_label", "primary_pct_gdp", "financial_pct_gdp"]]


def build_pdf_section(pdf, data: dict) -> None:
    fiscal_df = data.get("fiscal_df")
    chart_path = chart_fiscal(fiscal_df)

    pdf.section_title("Fiscal Balance")
    pdf.body_text(summarise(data))

    # Annual summary table (2023 onwards)
    if fiscal_df is not None and not fiscal_df.empty:
        yearly = _yearly_summary(fiscal_df, start_year=2023)
        if yearly is not None and not yearly.empty:
            _render_yearly_table_pdf(pdf, yearly)

    # Monthly detail table -- prefer % GDP; show both primary and financial
    if fiscal_df is not None and not fiscal_df.empty:
        pct_cols = [c for c in ["fiscal_primary_pct_gdp", "fiscal_financial_pct_gdp"]
                    if c in fiscal_df.columns]
        ars_cols = [c for c in ["fiscal_primary_ars_bn", "fiscal_financial_ars_bn"]
                    if c in fiscal_df.columns and c.replace("ars_bn", "pct_gdp") not in fiscal_df.columns]
        show_cols = pct_cols or ars_cols

        if show_cols:
            rename_map = {
                "fiscal_primary_pct_gdp":    "primary_pct_gdp",
                "fiscal_financial_pct_gdp":  "financial_pct_gdp",
                "fiscal_primary_ars_bn":     "primary_ars_bn",
                "fiscal_financial_ars_bn":   "financial_ars_bn",
            }
            display_df   = fiscal_df[["date"] + show_cols].rename(columns=rename_map).copy()
            display_cols = ["date"] + [rename_map[c] for c in show_cols]
            fmt          = {rename_map[c]: ("{:.2f}%" if "pct" in c else "{:.1f}") for c in show_cols}
            title = "Public Sector Balance as % of GDP (last 12 months)" if pct_cols else \
                    "Public Sector Balance, ARS bn (last 12 months)"
            pdf.add_table(display_df.tail(12), display_cols, fmt=fmt, title=title)

    pdf.add_chart(
        chart_path,
        "Bars = primary balance; dashed = financial balance (after interest). "
        "Green = surplus, red = deficit. Dotted line = 1.5% GDP target.",
    )
    render_signal_callout(pdf, load_signal("fiscal"), label="Fiscal Balance")


def build_md_section(data: dict) -> str:
    fiscal_df = data.get("fiscal_df")

    def _md_table(df, cols, fmt=None):
        fmt = fmt or {}
        subset = df[cols].dropna().tail(12)
        if subset.empty:
            return ""
        header = "| " + " | ".join(cols) + " |"
        sep    = "| " + " | ".join(["---"] * len(cols)) + " |"
        rows   = []
        for _, row in subset.iterrows():
            cells = []
            for c in cols:
                v = row[c]
                if c == "date":
                    try:    cells.append(pd.to_datetime(v).strftime("%Y-%m"))
                    except: cells.append(str(v)[:7])
                    continue
                f = fmt.get(c, "{:.2f}")
                try:    cells.append(f.format(v))
                except: cells.append(str(v))
            rows.append("| " + " | ".join(cells) + " |")
        return "\n".join([header, sep] + rows)

    # Annual summary table
    yearly_md = ""
    if fiscal_df is not None and not fiscal_df.empty:
        yearly = _yearly_summary(fiscal_df, start_year=2023)
        if yearly is not None and not yearly.empty:
            rows = ["| Year | Primary % GDP | Financial % GDP (incl. interest) |",
                    "|---|---|---|"]
            for _, r in yearly.iterrows():
                p = r["primary_pct_gdp"]
                f = r["financial_pct_gdp"]
                rows.append(f"| {r['year_label']} | {p:+.2f}% | {f:+.2f}% |")
            yearly_md = "\n**Annual Fiscal Balance as % of GDP (2023 = pre-Milei baseline)**\n\n" + \
                        "\n".join(rows)

    # Monthly detail table
    table_md = ""
    if fiscal_df is not None and not fiscal_df.empty:
        pct_cols = [c for c in ["fiscal_primary_pct_gdp", "fiscal_financial_pct_gdp"]
                    if c in fiscal_df.columns]
        show_cols = pct_cols or [c for c in ["fiscal_primary_ars_bn", "fiscal_financial_ars_bn"]
                                  if c in fiscal_df.columns]
        if show_cols:
            title = "% of GDP" if pct_cols else "ARS bn"
            table_md = f"\n**Monthly detail ({title}, last 12 months)**\n\n" + \
                       _md_table(fiscal_df.tail(12), ["date"] + show_cols,
                                 fmt={c: ("{:.2f}%" if "pct" in c else "{:.1f}") for c in show_cols})

    chart_path = str(CHARTS_DIR / "chart_fiscal.png")
    def _img(p):
        return f"![chart](data/charts/{Path(p).name})\n" if p and Path(p).exists() else "_Chart unavailable._\n"

    return f"""## Fiscal Balance

{summarise(data)}
{yearly_md}
{table_md}

{_img(chart_path)}
{render_signal_callout_md(load_signal("fiscal"), label="Fiscal Balance")}"""
