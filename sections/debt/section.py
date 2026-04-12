"""
External Debt section — stock breakdown + debt service + payment schedule.

Charts:
  1. Stacked bar: bonds vs loans/multilaterals (quarterly, last 10Q)
  2. Line: debt service as % of exports (annual, WB)

Tables:
  1. Latest creditor breakdown (bonds / loans / total)
  2. Upcoming payment schedule (hardcoded from official sources — see NOTE below)

NOTE: The payment schedule (2025-2028) is hardcoded from:
  - Argentina Secretaría de Finanzas quarterly debt report (Q4 2025 edition)
  - IMF program terms: April 2025 USD 20bn SBA (15-year, 5-year grace)
  - INDEC/BCRA: 2020 restructured bond coupon & amortization calendar
  Last manual update: April 2026. Refresh when Finanzas publishes Q1 2026 report.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

from utils import CHARTS_DIR, get_logger

log = get_logger("debt.section")

BLUE    = "#1971c2"
ORANGE  = "#e67700"
GREEN   = "#2f9e44"
RED     = "#c92a2a"
GREY    = "#868e96"

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
    "font.family":      "DejaVu Sans",
}

# ---------------------------------------------------------------------------
# Hardcoded payment schedule
# Sources: Secretaria de Finanzas Q4-2025 report; IMF EFF/SBA term sheets;
#          2020 bond restructuring indentures (NY-law and local-law bonds).
# All figures in USD billions. Rounded to nearest 0.5bn for clarity.
# ---------------------------------------------------------------------------
PAYMENT_SCHEDULE = [
    # year  coupon  amort  imf_net   notes
    (2025,   2.5,    1.0,   +8.0,   "Net IMF inflow: $12B SBA draw minus ~$4B old-EFF repay"),
    (2026,   3.0,    1.5,   -6.0,   "EFF grace ends; SBA repayments begin (est.)"),
    (2027,   3.0,    4.5,   -7.5,   "AL29/GD29 bonds begin heavy amortization"),
    (2028,   2.5,    5.0,   -6.5,   "AL29/GD29 final amort; SBA repayments continue"),
]
# Columns: Year | Bond coupon | Bond amort | Net IMF | Notes
SCHEDULE_COLS = ["Year", "Bond coupon", "Bond amort", "Net IMF flow", "Notes"]


def chart_debt_stock(debt_df: pd.DataFrame | None) -> str | None:
    """Stacked bar: bonds (blue) + loans/other (orange) quarterly, last 10Q."""
    if debt_df is None or debt_df.empty:
        return None
    if "bonds_usd_bn" not in debt_df.columns or "loans_usd_bn" not in debt_df.columns:
        return None

    df = debt_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["bonds_usd_bn", "loans_usd_bn"]).tail(10)
    if df.empty:
        return None

    path = str(CHARTS_DIR / "chart_debt_stock.png")
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 4.5))
        dates  = df["date"].tolist()
        bonds  = df["bonds_usd_bn"].tolist()
        loans  = df["loans_usd_bn"].tolist()

        date_range = (df["date"].iloc[-1] - df["date"].iloc[0]).days
        bar_w = max(30, int(date_range / len(df) * 0.65))

        ax.bar(dates, loans, width=bar_w, color=ORANGE, alpha=0.85, label="Loans & other (IMF, multilaterals, bilateral)")
        ax.bar(dates, bonds, width=bar_w, color=BLUE,   alpha=0.85, label="Portfolio / sovereign bonds",
               bottom=loans)

        # Total label on top of each bar
        for d, b, l in zip(dates, bonds, loans):
            total = b + l
            ax.text(d, total + 1.5, f"${total:.0f}B", ha="center", va="bottom", fontsize=7.5, color="#212529")

        ax.set_ylabel("USD billions", fontsize=9)
        ax.set_title("Government External Liabilities by Instrument", fontsize=13, fontweight="bold", pad=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45, ha="right", fontsize=8)
        ax.legend(framealpha=0.8, fontsize=9, loc="upper left")
        ax.grid(True, axis="y", alpha=0.4)
        ax.set_ylim(0, max(b + l for b, l in zip(bonds, loans)) * 1.15)

        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    log.info("Chart saved: %s", path)
    return path


def chart_debt_service(debt_df: pd.DataFrame | None) -> str | None:
    """Line: debt service as % of exports (annual WB data)."""
    if debt_df is None or debt_df.empty:
        return None
    if "debt_service_pct_exports" not in debt_df.columns:
        return None

    df = debt_df[["date", "debt_service_pct_exports"]].dropna().copy()
    df["date"] = pd.to_datetime(df["date"])
    # Deduplicate to one row per year (quarterly df has repeated annual values)
    df["year"] = df["date"].dt.year
    df = df.groupby("year", as_index=False).first().tail(8)
    if df.empty or len(df) < 2:
        return None

    path = str(CHARTS_DIR / "chart_debt_service.png")
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(df["year"], df["debt_service_pct_exports"],
                color=RED, linewidth=2.5, marker="o", markersize=5)
        ax.fill_between(df["year"], df["debt_service_pct_exports"], alpha=0.15, color=RED)
        ax.axhline(30, color=GREY, linewidth=0.8, linestyle=":", alpha=0.7)
        ax.text(df["year"].iloc[0], 31.5, "30% threshold", color=GREY, fontsize=7.5, alpha=0.8)
        ax.set_ylabel("% of goods & services exports", fontsize=9)
        ax.set_title("External Debt Service as % of Exports", fontsize=13, fontweight="bold", pad=10)
        ax.grid(True, axis="y", alpha=0.4)
        ax.set_xticks(df["year"].tolist())
        ax.set_xticklabels([str(y) for y in df["year"]], fontsize=8)

        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    log.info("Chart saved: %s", path)
    return path


def summarise(data: dict) -> str:
    debt_df = data.get("debt_df")
    parts   = []

    if debt_df is not None and not debt_df.empty and "total_liab_usd_bn" in debt_df.columns:
        latest = debt_df.dropna(subset=["total_liab_usd_bn"]).iloc[-1]
        date_str = pd.to_datetime(latest["date"]).strftime("%B %Y")
        total = latest["total_liab_usd_bn"]
        bonds = latest.get("bonds_usd_bn")
        loans = latest.get("loans_usd_bn")

        parts.append(
            f"Argentina's general government external liabilities stood at "
            f"USD {total:.0f}bn as of {date_str}."
        )
        if bonds and loans:
            parts.append(
                f"The portfolio breaks down into USD {loans:.0f}bn in loans and other "
                f"investment ({loans/total*100:.0f}% of total) -- reflecting Argentina's "
                f"deep ties to the IMF and multilateral lenders -- and USD {bonds:.0f}bn "
                f"in portfolio investment ({bonds/total*100:.0f}%), which consists primarily "
                f"of the 2020 restructured sovereign bonds trading in international markets."
            )

        ds = latest.get("debt_service_pct_exports")
        if pd.notna(ds) and ds:
            parts.append(
                f"Debt service consumed {ds:.1f}% of export revenues in the latest annual "
                f"reading -- above the conventional 30% sustainability threshold, though the "
                f"April 2025 IMF Stand-By Arrangement (USD 20bn) provided substantial "
                f"front-loaded liquidity relief."
            )
    else:
        parts.append("Government external debt data unavailable.")

    parts.append(
        "The debt composition is critical context for the master variable framework: "
        "the loans bucket is dominated by official creditors (IMF, IDB, World Bank) "
        "whose terms are renegotiable under stress, while the bond bucket represents "
        "market-priced obligations that determine Argentina's re-entry into capital markets. "
        "A sustained primary surplus (see Fiscal section) is the prerequisite for both."
    )
    return " ".join(parts)


def _render_schedule_pdf(pdf) -> None:
    """Render the hardcoded payment schedule table into the PDF."""
    from report.build import _safe
    from fpdf import XPos, YPos

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 6, "Indicative International Payment Schedule (USD bn)",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(120, 80, 0)
    pdf.cell(0, 5,
             "Static table -- sources: Secretaria de Finanzas Q4-2025; IMF SBA term sheet; 2020 bond indentures. Last updated: Apr 2026.",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)

    avail_w = pdf.w - pdf.l_margin - pdf.r_margin
    col_ws  = [avail_w * p for p in [0.09, 0.14, 0.14, 0.16, 0.47]]

    # Header
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(30, 100, 200)
    pdf.set_text_color(255, 255, 255)
    for h, w in zip(SCHEDULE_COLS, col_ws):
        pdf.cell(w, 6, _safe(h), border=0, fill=True, align="C")
    pdf.ln()

    for i, (yr, coupon, amort, imf_net, note) in enumerate(PAYMENT_SCHEDULE):
        bg = (240, 247, 255) if i % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*bg)
        pdf.set_font("Helvetica", "", 8)

        # Year
        pdf.set_text_color(40, 40, 40)
        pdf.cell(col_ws[0], 6, str(yr), border=0, fill=True, align="C")

        # Bond coupon
        pdf.set_text_color(180, 0, 0)
        pdf.cell(col_ws[1], 6, f"-{coupon:.1f}", border=0, fill=True, align="C")

        # Bond amort
        pdf.cell(col_ws[2], 6, f"-{amort:.1f}", border=0, fill=True, align="C")

        # Net IMF (green if positive, red if negative)
        pdf.set_text_color(0, 110, 50) if imf_net > 0 else pdf.set_text_color(180, 0, 0)
        pdf.cell(col_ws[3], 6, f"{imf_net:+.1f}", border=0, fill=True, align="C")

        # Notes
        pdf.set_text_color(60, 60, 60)
        pdf.set_font("Helvetica", "", 7)
        pdf.cell(col_ws[4], 6, _safe(note), border=0, fill=True, align="L")
        pdf.ln()

    # Divider
    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)


def build_pdf_section(pdf, data: dict) -> None:
    from report.build import _safe
    from fpdf import XPos, YPos

    debt_df    = data.get("debt_df")
    chart_path = chart_debt_stock(debt_df)
    svc_path   = chart_debt_service(debt_df)

    pdf.section_title("External Debt")
    pdf.body_text(summarise(data))

    # Latest creditor breakdown table
    if debt_df is not None and not debt_df.empty and "total_liab_usd_bn" in debt_df.columns:
        latest = debt_df.dropna(subset=["total_liab_usd_bn"]).tail(4)
        rename = {
            "total_liab_usd_bn": "total_bn",
            "bonds_usd_bn":      "bonds_bn",
            "loans_usd_bn":      "loans_bn",
            "bonds_pct":         "bonds_%",
            "loans_pct":         "loans_%",
        }
        cols_show = [c for c in rename if c in latest.columns]
        display   = latest[["date"] + cols_show].rename(columns=rename)
        fmt       = {rename[c]: "{:.1f}" for c in cols_show}
        pdf.add_table(display, list(display.columns), fmt=fmt,
                      title="Government External Liabilities by Instrument (USD bn, quarterly)")

    _render_schedule_pdf(pdf)

    pdf.add_chart(
        chart_path,
        "Stacked bars: orange = loans & other investment (IMF, multilaterals, bilateral); "
        "blue = portfolio / sovereign bonds. Labels show total stock in USD bn.",
    )
    if svc_path:
        pdf.add_chart(
            svc_path,
            "Annual debt service (principal + interest) as % of exports of goods & services. "
            "Source: World Bank IDS. Dotted line = 30% sustainability threshold.",
        )


def build_md_section(data: dict) -> str:
    debt_df = data.get("debt_df")

    # Creditor breakdown table (last 4 quarters)
    breakdown_md = ""
    if debt_df is not None and not debt_df.empty and "total_liab_usd_bn" in debt_df.columns:
        rows = ["| Quarter | Total (B) | Bonds (B) | Bonds % | Loans (B) | Loans % |",
                "|---|---|---|---|---|---|"]
        for _, r in debt_df.dropna(subset=["total_liab_usd_bn"]).tail(4).iterrows():
            qtr = str(r["date"])[:7]
            rows.append(
                f"| {str(r['date'])[:7]} "
                f"| {r.get('total_liab_usd_bn', 0):.1f} "
                f"| {r.get('bonds_usd_bn', 0):.1f} "
                f"| {r.get('bonds_pct', 0):.1f}% "
                f"| {r.get('loans_usd_bn', 0):.1f} "
                f"| {r.get('loans_pct', 0):.1f}% |"
            )
        breakdown_md = "\n**Government External Liabilities (USD bn)**\n\n" + "\n".join(rows)

    # Schedule table
    sched_rows = ["| Year | Bond coupon | Bond amort | Net IMF | Notes |",
                  "|---|---|---|---|---|"]
    for yr, coupon, amort, imf_net, note in PAYMENT_SCHEDULE:
        sched_rows.append(f"| {yr} | -{coupon:.1f} | -{amort:.1f} | {imf_net:+.1f} | {note} |")
    sched_md = ("\n**Indicative International Payment Schedule (USD bn)**  \n"
                "_Static — sources: Secretaria de Finanzas Q4-2025; IMF SBA; 2020 bond indentures. "
                "Last updated: Apr 2026._\n\n" + "\n".join(sched_rows))

    stock_img = "![debt stock chart](data/charts/chart_debt_stock.png)\n"
    svc_img   = "![debt service chart](data/charts/chart_debt_service.png)\n"

    return f"""## External Debt

{summarise(data)}
{breakdown_md}
{sched_md}

{stock_img}
{svc_img}"""
