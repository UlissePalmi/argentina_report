"""
Consumption module — section builder for the main Argentina Macro Report.

Shows a concise key-findings summary (last 6 months, key real columns).
Full detail is in consumption/report.py -> data/reports/consumption_report.pdf.
"""

import pandas as pd

from utils import get_logger

log = get_logger("consumption.section")


def _avg3(series: pd.Series) -> float | None:
    vals = series.dropna().tail(3)
    return float(vals.mean()) if len(vals) >= 1 else None


def _pct(v) -> str:
    try:
        return f"{float(v):+.1f}%"
    except (TypeError, ValueError):
        return "n/a"


def _classify_config(df: pd.DataFrame) -> str:
    real_wage   = _avg3(df.get("real_wage_yoy_pct",            pd.Series(dtype=float)))
    real_credit = _avg3(df.get("real_consumer_credit_yoy_pct", pd.Series(dtype=float)))
    real_dep    = _avg3(df.get("real_deposits_yoy_pct",        pd.Series(dtype=float)))

    if real_wage is None:
        return "data-insufficient"
    if real_wage > 0:
        if real_credit is not None and real_credit > real_wage + 15:
            return "credit-led"
        return "wage-led"
    if real_dep is not None and real_dep < 0:
        return "savings-drawdown"
    if real_credit is not None and real_credit > 0:
        return "credit-led"
    return "savings-drawdown"


def _key_findings(df: pd.DataFrame) -> str:
    config = _classify_config(df)
    label = {
        "wage-led":          "Wage-Led (healthy)",
        "credit-led":        "Credit-Led (monitor)",
        "savings-drawdown":  "Savings Drawdown (fragile)",
        "data-insufficient": "Insufficient Data",
    }.get(config, config)

    real_w   = _avg3(df.get("real_wage_yoy_pct",            pd.Series(dtype=float)))
    nom_w    = _avg3(df.get("nominal_wage_yoy_pct",         pd.Series(dtype=float)))
    cpi_v    = _avg3(df.get("cpi_yoy_pct",                  pd.Series(dtype=float)))
    real_cr  = _avg3(df.get("real_consumer_credit_yoy_pct", pd.Series(dtype=float)))
    real_dep = _avg3(df.get("real_deposits_yoy_pct",        pd.Series(dtype=float)))

    lines = [
        f"Configuration: {label}",
        "",
        f"Real wages (3-mo avg):       {_pct(real_w)}  (nominal {_pct(nom_w)}, CPI {_pct(cpi_v)})",
        f"Real consumer credit (3-mo): {_pct(real_cr)}",
        f"Real deposits (3-mo):        {_pct(real_dep)}",
        "",
        "For full 24-month detail see data/reports/consumption_report.pdf",
    ]
    return "\n".join(lines)


def _real_cols(df: pd.DataFrame) -> list[str]:
    """Return the real-adjusted columns that exist in df, in display order."""
    preferred = ["real_wage_yoy_pct", "real_consumer_credit_yoy_pct",
                 "real_total_credit_yoy_pct", "real_deposits_yoy_pct"]
    fallback  = ["nominal_wage_yoy_pct", "consumer_credit_yoy_pct",
                 "total_credit_yoy_pct", "deposits_yoy_pct"]
    cols = [c for c in preferred if c in df.columns]
    if not cols:
        cols = [c for c in fallback if c in df.columns]
    return cols


def build_pdf_section(pdf, data: dict) -> None:
    consumption_df = data.get("consumption_df")
    if consumption_df is None or consumption_df.empty:
        return

    has_real = "real_wage_yoy_pct" in consumption_df.columns

    pdf.section_title("4. Consumption Drivers")
    pdf.body_text(_key_findings(consumption_df))

    # Last 6 months of real columns as a compact table
    cons_display = consumption_df.tail(6).copy()
    cons_display["date"] = pd.to_datetime(cons_display["date"]).dt.strftime("%b %Y")
    cols = ["date"] + _real_cols(cons_display)
    pdf.add_table(
        cons_display, cols,
        fmt={c: "{:+.1f}%" for c in cols if c != "date"},
        title="Key Consumption Signals -- Real YoY % (last 6 months)"
    )

    note = (
        "Real series use Fisher equation: ((1 + nominal) / (1 + CPI)) - 1. "
        "See data/reports/consumption_report.pdf for full 24-month analysis."
        if has_real else
        "Nominal figures shown (CPI unavailable for adjustment). "
        "See data/reports/consumption_report.pdf for detail."
    )
    pdf.body_text(note)


def build_md_section(data: dict) -> str:
    consumption_df = data.get("consumption_df")
    if consumption_df is None or consumption_df.empty:
        return ""

    def _md_table(df, cols, fmt=None):
        fmt = fmt or {}
        subset = df[cols].dropna(how="all").tail(6)
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

    cons_disp = consumption_df.tail(6).copy()
    cons_disp["date"] = pd.to_datetime(cons_disp["date"]).dt.strftime("%b %Y")
    ccols = ["date"] + _real_cols(cons_disp)
    table = _md_table(cons_disp, ccols, fmt={c: "{:+.1f}%" for c in ccols if c != "date"})

    findings = _key_findings(consumption_df)
    has_real = "real_wage_yoy_pct" in cons_disp.columns
    note = ("*Real series: Fisher equation ((1 + nominal) / (1 + CPI)) - 1. "
            "Full 24-month analysis: `data/reports/consumption_report.pdf`*"
            if has_real else
            "*Nominal figures (CPI unavailable for adjustment). "
            "Full detail: `data/reports/consumption_report.pdf`*")

    return f"""## 4. Consumption Drivers

```
{findings}
```

**Key Consumption Signals -- Real YoY % (last 6 months)**

{table}

{note}"""
