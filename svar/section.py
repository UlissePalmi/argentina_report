"""
SVAR section builder — Layer 3.5 → Layer 5.

Reads pre-computed IRF and FEVD JSON and writes a 2-3 page PDF/markdown section
interpreting Argentina inflation dynamics.
"""

from __future__ import annotations

import json
from pathlib import Path

from utils import get_logger

log = get_logger("svar.section")

SVAR_DIR = Path(__file__).parent.parent / "data" / "svar"

SHOCK_LABELS = {
    "fx_mom_pct":                 "FX depreciation",
    "emae_yoy_pct":               "Activity (EMAE)",
    "real_total_credit_yoy_pct":  "Real credit",
    "real_wage_yoy_pct":          "Real wages",
    "cpi_mom_pct":                "Own (inflation) shock",
}


def _load(filename: str) -> dict | None:
    path = SVAR_DIR / filename
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def _top_shock(fevd_cpi: dict, horizon: str) -> tuple[str, float]:
    """Return (shock_name, share%) for the largest contributor at a given horizon."""
    row = fevd_cpi.get(horizon, {})
    # exclude own inflation shock from "top driver"
    external = {k: v for k, v in row.items() if k != "cpi_mom_pct"}
    if not external:
        return "unknown", 0.0
    top = max(external, key=lambda k: external[k])
    return top, external[top]


def _irf_peak(irf_shocks: dict, shock: str, target: str = "cpi_mom_pct") -> tuple[float, int]:
    """Return (peak_value, period_of_peak) for IRF of target to shock."""
    data = irf_shocks.get(shock, {}).get(target, {}).get("point", [])
    if not data:
        return 0.0, 0
    peak_idx = max(range(len(data)), key=lambda i: abs(data[i]))
    return data[peak_idx], peak_idx


def _fmt(v: float, decimals: int = 2) -> str:
    return f"{v:+.{decimals}f}"


def _interpretation(irf_data: dict, fevd_data: dict) -> str:
    """Generate 3-paragraph analytical interpretation of the SVAR results."""
    n_obs   = irf_data.get("n_obs", 0)
    lag     = irf_data.get("lag_order", "?")
    shocks  = irf_data.get("shocks", {})
    fevd_cpi = fevd_data.get("fevd", {}).get("cpi_mom_pct", {})
    var_names = irf_data.get("variable_names", [])
    labels = irf_data.get("variable_labels", SHOCK_LABELS)

    data_note = (
        f"Model: VAR({lag}), {n_obs} monthly observations (Cholesky identification). "
        f"Note: Argentina's structural breaks (IMF 2018, COVID 2020, Milei 2024) limit structural "
        f"interpretation — treat as descriptive of the recent inflation regime."
        if n_obs < 80 else
        f"Model: VAR({lag}), {n_obs} monthly observations (Cholesky identification)."
    )

    # --- Paragraph 1: FEVD — which shocks matter most ---
    top_1,  top_1_share  = _top_shock(fevd_cpi, "1")
    top_12, top_12_share = _top_shock(fevd_cpi, "12")
    top_24, top_24_share = _top_shock(fevd_cpi, "24")
    own_12 = fevd_cpi.get("12", {}).get("cpi_mom_pct", 0)
    own_1  = fevd_cpi.get("1",  {}).get("cpi_mom_pct", 0)

    p1 = (
        f"Variance decomposition of inflation: "
        f"at the 1-month horizon, {own_1:.0f}% of inflation variance is unexplained by the "
        f"other variables (own shock dominates at short horizons as expected). "
        f"By 12 months, the picture shifts: "
        f"{labels.get(top_12, top_12)} accounts for {top_12_share:.0f}% of inflation variance, "
        f"while the own-inflation component drops to {own_12:.0f}%. "
        f"At 24 months, {labels.get(top_24, top_24)} remains the dominant external driver "
        f"({top_24_share:.0f}% of variance). "
    )

    # Add FX share explicitly if it's not the top shock
    fx_12  = fevd_cpi.get("12",  {}).get("fx_mom_pct",  0)
    wg_12  = fevd_cpi.get("12",  {}).get("real_wage_yoy_pct", 0)
    cr_12  = fevd_cpi.get("12",  {}).get("real_total_credit_yoy_pct", 0)
    act_12 = fevd_cpi.get("12",  {}).get("emae_yoy_pct", 0)

    p1 += (
        f"At 12 months: FX={fx_12:.0f}%, wages={wg_12:.0f}%, "
        f"credit={cr_12:.0f}%, activity={act_12:.0f}%."
    )

    # --- Paragraph 2: FX IRF — magnitude and persistence ---
    fx_peak, fx_peak_t = _irf_peak(shocks, "fx_mom_pct")
    wg_peak, wg_peak_t = _irf_peak(shocks, "real_wage_yoy_pct")
    cr_peak, cr_peak_t = _irf_peak(shocks, "real_total_credit_yoy_pct")

    # Cumulative FX effect over 12 months
    fx_irf_cpi = shocks.get("fx_mom_pct", {}).get("cpi_mom_pct", {}).get("point", [])
    fx_cum_12  = sum(fx_irf_cpi[:13]) if len(fx_irf_cpi) >= 13 else sum(fx_irf_cpi)

    p2 = (
        f"Exchange rate pass-through: a 1-standard-deviation FX depreciation shock "
        f"generates a peak CPI response of {_fmt(fx_peak)} pp at month {fx_peak_t}, "
        f"with a cumulative 12-month effect of {_fmt(fx_cum_12)} pp. "
    )

    # Check if FX effect fades or persists
    if len(fx_irf_cpi) >= 13:
        late_avg = sum(fx_irf_cpi[12:]) / max(1, len(fx_irf_cpi) - 12)
        if abs(late_avg) > 0.05 * abs(fx_peak):
            p2 += (
                "The pass-through is persistent -- FX shocks continue to affect inflation "
                "beyond the 12-month window, consistent with Argentina's history of indexation "
                "and dollarized pricing. "
            )
        else:
            p2 += (
                "The pass-through fades within the first year, suggesting the recent "
                "disinflation regime has reduced FX-inflation indexation somewhat. "
            )

    p2 += (
        f"By comparison, a 1-sd real wage shock peaks at {_fmt(wg_peak)} pp (month {wg_peak_t}) "
        f"and a 1-sd credit shock peaks at {_fmt(cr_peak)} pp (month {cr_peak_t}). "
    )

    # --- Paragraph 3: Policy implications ---
    # Determine if FX is the dominant driver
    fx_is_dominant = fx_12 == max(fx_12, wg_12, cr_12, act_12)
    wg_is_dominant = wg_12 == max(fx_12, wg_12, cr_12, act_12)

    if fx_is_dominant:
        p3 = (
            "Policy implications: the dominant role of FX shocks in inflation variance "
            "implies that exchange rate stability is the primary anchor for Argentine inflation -- "
            "more so than monetary aggregates or wage dynamics. The Milei administration's "
            "crawling-peg strategy is consistent with this finding: keeping the daily devaluation "
            "rate below monthly CPI is the mechanistic path to disinflation. The critical risk is "
            "a disorderly FX adjustment (reserve depletion or parallel premium widening) which "
            "would immediately reignite inflation. The wage and credit channels are secondary "
            "but become important once the FX anchor holds -- they represent the floor below "
            "which inflation cannot fall without income compression."
        )
    elif wg_is_dominant:
        p3 = (
            "Policy implications: wage dynamics are the dominant driver of inflation at medium "
            "horizons, pointing to an inertial inflation mechanism where backward-looking wage "
            "indexation propagates price shocks across sectors. Breaking this inertia requires "
            "either sustained real wage compression (politically costly) or an income policy "
            "that coordinates wage and price expectations. The FX channel matters at short "
            "horizons but its medium-term relevance is secondary -- exchange rate stability "
            "alone is insufficient to eliminate inertial inflation."
        )
    else:
        p3 = (
            "Policy implications: no single shock dominates Argentina's inflation variance, "
            "suggesting a multi-causal inflation process. Disinflation requires simultaneous "
            "management of FX expectations, credit expansion, and wage dynamics -- "
            "piecemeal stabilization attempts that address only one channel are likely to "
            "fail or require sustained external financing to compensate."
        )

    return "\n\n".join([data_note, p1, p2, p3])


def build_pdf_section(pdf, data: dict) -> None:
    from svar.charts import build_charts, chart_irf_to_cpi, chart_irf_fx_all, chart_fevd_cpi

    irf_data  = _load("irf_results.json")
    fevd_data = _load("fevd_results.json")

    pdf.section_title("SVAR: Argentine Inflation Dynamics")

    if irf_data is None or fevd_data is None:
        pdf.body_text(
            "SVAR results not available. Run the SVAR pipeline (svar/run.py) "
            "to generate impulse response functions and variance decomposition."
        )
        return

    n_obs = irf_data.get("n_obs", 0)
    lag   = irf_data.get("lag_order", "?")

    pdf.body_text(
        f"Structural VAR({lag}) estimated on {n_obs} monthly observations. "
        f"Variables: CPI inflation (MoM), exchange rate depreciation (MoM), "
        f"activity (EMAE YoY), real credit (YoY), real wages (YoY). "
        f"Identification: Cholesky decomposition, ordering FX -> Activity -> Credit -> Wages -> CPI. "
        f"Confidence bands: 95% bootstrap ({200} replications)."
    )

    # FEVD table
    fevd_cpi = fevd_data.get("fevd", {}).get("cpi_mom_pct", {})
    var_names = fevd_data.get("variable_names", [])
    labels    = fevd_data.get("variable_labels", SHOCK_LABELS)

    if fevd_cpi and var_names:
        import pandas as pd
        horizons = [h for h in ["1", "6", "12", "24"] if h in fevd_cpi]
        rows = []
        for var in var_names:
            row = {"Source": labels.get(var, var)}
            for h in horizons:
                row[f"{h}M"] = fevd_cpi[h].get(var, 0)
            rows.append(row)
        fevd_df = pd.DataFrame(rows)
        fmt = {f"{h}M": "{:.1f}%" for h in horizons}
        pdf.add_table(
            fevd_df,
            cols=["Source"] + [f"{h}M" for h in horizons],
            fmt=fmt,
            title="FEVD of CPI Inflation -- % variance explained by each shock"
        )

    # Charts
    irf_chart = chart_irf_to_cpi(irf_data)
    pdf.add_chart(irf_chart, caption="IRF: CPI response to each 1 s.d. shock (95% CI shaded)")

    fevd_chart = chart_fevd_cpi(fevd_data)
    pdf.add_chart(fevd_chart, caption="FEVD: variance decomposition of CPI inflation by shock")

    fx_chart = chart_irf_fx_all(irf_data)
    pdf.add_chart(fx_chart, caption="IRF: full transmission of 1 s.d. FX depreciation shock")

    # Interpretation
    pdf.section_title("SVAR: Interpretation")
    text = _interpretation(irf_data, fevd_data)
    for para in text.split("\n\n"):
        if para.strip():
            pdf.body_text(para.strip())


def build_md_section(data: dict) -> str:
    irf_data  = _load("irf_results.json")
    fevd_data = _load("fevd_results.json")

    if irf_data is None or fevd_data is None:
        return "## SVAR: Argentine Inflation Dynamics\n\nResults not yet available.\n"

    n_obs = irf_data.get("n_obs", 0)
    lag   = irf_data.get("lag_order", "?")
    var_names = fevd_data.get("variable_names", [])
    labels    = fevd_data.get("variable_labels", SHOCK_LABELS)
    fevd_cpi  = fevd_data.get("fevd", {}).get("cpi_mom_pct", {})

    out = f"## SVAR: Argentine Inflation Dynamics\n\n"
    out += f"VAR({lag}), {n_obs} monthly observations. Cholesky identification.\n\n"

    if fevd_cpi and var_names:
        horizons = [h for h in ["1", "6", "12", "24"] if h in fevd_cpi]
        header = "| Source | " + " | ".join(f"{h}M" for h in horizons) + " |"
        sep    = "|---|" + "---|" * len(horizons)
        rows = [header, sep]
        for var in var_names:
            cells = [labels.get(var, var)]
            for h in horizons:
                cells.append(f"{fevd_cpi[h].get(var, 0):.1f}%")
            rows.append("| " + " | ".join(cells) + " |")
        out += "**FEVD of CPI Inflation**\n\n" + "\n".join(rows) + "\n\n"

    out += _interpretation(irf_data, fevd_data)
    return out
