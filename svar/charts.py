"""
SVAR chart generation — Layer 3.5.

Reads IRF and FEVD JSON results and produces:
  - svar_irf_to_cpi.png    — IRF: response of inflation to each shock (2x2 grid)
  - svar_fevd_cpi.png      — FEVD: variance decomposition of inflation
  - svar_irf_fx_all.png    — IRF: response of all variables to FX shock
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from utils import CHARTS_DIR, get_logger

log = get_logger("svar.charts")

SVAR_DIR = Path(__file__).parent.parent / "data" / "svar"

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

SHOCK_COLORS = {
    "m2_yoy_pct":                 "#0c8599",   # teal — monetary policy (M2)
    "fx_mom_pct":                 "#c92a2a",   # red — FX/exchange rate
    "emae_yoy_pct":               "#1971c2",   # blue — activity
    "real_total_credit_yoy_pct":  "#e67700",   # orange — credit
    "real_wage_yoy_pct":          "#2f9e44",   # green — wages
    "cpi_mom_pct":                "#7950f2",   # purple — inflation
}
SHOCK_LABELS = {
    "m2_yoy_pct":                 "M2 growth shock (monetary policy)",
    "fx_mom_pct":                 "FX depreciation shock",
    "emae_yoy_pct":               "Activity shock (EMAE)",
    "real_total_credit_yoy_pct":  "Real credit shock",
    "real_wage_yoy_pct":          "Real wage shock",
    "cpi_mom_pct":                "Inflation shock",
}


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        log.warning("SVAR charts: %s not found.", path)
        return None
    with open(path) as f:
        return json.load(f)


def _irf_axes(ax, periods: list[float], point: list[float],
              lower: list[float], upper: list[float],
              color: str, title: str, ylabel: str = "pp"):
    """Render a single IRF panel with shaded CI band."""
    x = list(range(len(periods)))
    line, = ax.plot(x, point, color=color, linewidth=2, label="IRF (point estimate)")
    fill  = ax.fill_between(x, lower, upper, color=color, alpha=0.18, label="95% CI")
    ax.axhline(0, color="#495057", linewidth=0.8, linestyle="--")
    ax.set_title(title, fontsize=9, fontweight="bold", pad=4)
    ax.set_xlabel("Months after shock", fontsize=8)
    ax.set_ylabel(ylabel, fontsize=8)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))
    ax.grid(axis="y", alpha=0.4)
    ax.set_xlim(0, len(x) - 1)
    ax.legend(handles=[line, fill], fontsize=7, framealpha=0.85, loc="upper right")


def chart_irf_to_cpi(irf_data: dict) -> str | None:
    """
    2×2 grid: IRF of CPI inflation to each of the 4 non-inflation shocks.
    Each panel shows the response of cpi_mom_pct to a 1-sd shock.
    """
    shocks_to_plot = [c for c in irf_data["variable_names"] if c != "cpi_mom_pct"]
    n = len(shocks_to_plot)
    if n == 0 or "cpi_mom_pct" not in irf_data["variable_names"]:
        return None

    ncols = 2
    nrows = (n + 1) // 2
    path = str(CHARTS_DIR / "svar_irf_to_cpi.png")

    with plt.rc_context(CHART_STYLE):
        fig, axes = plt.subplots(nrows, ncols, figsize=(11, 3.5 * nrows), squeeze=False)
        fig.suptitle("IRF: Response of CPI Inflation to a 1 s.d. Shock\n"
                     "(orthogonalized, Cholesky identification; 95% CI shaded)",
                     fontsize=11, fontweight="bold", y=1.01)

        for i, shock_col in enumerate(shocks_to_plot):
            row, col = divmod(i, ncols)
            ax = axes[row][col]
            shock_data = irf_data["shocks"].get(shock_col, {}).get("cpi_mom_pct")
            if shock_data is None:
                ax.set_visible(False)
                continue
            _irf_axes(
                ax,
                periods=shock_data["point"],
                point=shock_data["point"],
                lower=shock_data["lower"],
                upper=shock_data["upper"],
                color=SHOCK_COLORS.get(shock_col, "#333333"),
                title=SHOCK_LABELS.get(shock_col, shock_col),
            )

        # Hide unused axes
        for idx in range(n, nrows * ncols):
            axes[idx // ncols][idx % ncols].set_visible(False)

        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    log.info("SVAR chart saved: %s", path)
    return path


def chart_irf_fx_all(irf_data: dict) -> str | None:
    """
    IRF: response of ALL variables to a 1-sd FX depreciation shock.
    Shows full transmission channel (FX → activity → credit → wages → CPI).
    """
    fx_col = "fx_mom_pct"
    if fx_col not in irf_data["shocks"]:
        return None

    var_names = irf_data["variable_names"]
    n = len(var_names)
    path = str(CHARTS_DIR / "svar_irf_fx_all.png")

    ncols = min(3, n)
    nrows = (n + ncols - 1) // ncols

    with plt.rc_context(CHART_STYLE):
        fig, axes = plt.subplots(nrows, ncols, figsize=(4.5 * ncols, 3.5 * nrows), squeeze=False)
        fig.suptitle("IRF: Response of All Variables to a 1 s.d. FX Depreciation Shock\n"
                     "(Cholesky, 95% CI shaded)",
                     fontsize=11, fontweight="bold", y=1.01)

        for i, resp_col in enumerate(var_names):
            row, col = divmod(i, ncols)
            ax = axes[row][col]
            resp_data = irf_data["shocks"][fx_col].get(resp_col)
            if resp_data is None:
                ax.set_visible(False)
                continue
            _irf_axes(
                ax,
                periods=resp_data["point"],
                point=resp_data["point"],
                lower=resp_data["lower"],
                upper=resp_data["upper"],
                color=SHOCK_COLORS.get(resp_col, "#333333"),
                title=SHOCK_LABELS.get(resp_col, resp_col),
            )

        for idx in range(n, nrows * ncols):
            axes[idx // ncols][idx % ncols].set_visible(False)

        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    log.info("SVAR chart saved: %s", path)
    return path


def chart_fevd_cpi(fevd_data: dict) -> str | None:
    """
    Stacked bar: FEVD of CPI inflation at horizons 1, 6, 12, 24 months.
    Shows which shocks explain how much of inflation variance at each horizon.
    """
    fevd_cpi = fevd_data.get("fevd", {}).get("cpi_mom_pct")
    if fevd_cpi is None:
        return None

    horizons = [str(h) for h in fevd_data.get("horizons", [1, 6, 12, 24]) if str(h) in fevd_cpi]
    if not horizons:
        return None

    var_names = fevd_data["variable_names"]
    path = str(CHARTS_DIR / "svar_fevd_cpi.png")

    x = list(range(len(horizons)))
    with plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(8, 5))
        bottom = np.zeros(len(horizons))
        for var in var_names:
            values = np.array([fevd_cpi[h].get(var, 0) for h in horizons])
            ax.bar(x, values, bottom=bottom,
                   color=SHOCK_COLORS.get(var, "#aaaaaa"), alpha=0.85,
                   label=SHOCK_LABELS.get(var, var))
            # Label bars if share > 5%
            for xi, (v, b) in enumerate(zip(values, bottom)):
                if v > 5:
                    ax.text(xi, b + v / 2, f"{v:.0f}%",
                            ha="center", va="center", fontsize=8, color="white", fontweight="bold")
            bottom += values

        ax.set_xticks(x)
        ax.set_xticklabels([f"{h}M" for h in horizons], fontsize=9)
        ax.set_ylabel("% of forecast error variance", fontsize=9)
        ax.set_ylim(0, 105)
        ax.set_title("Forecast Error Variance Decomposition of CPI Inflation\n"
                     "(% contribution by shock at each horizon)",
                     fontsize=11, fontweight="bold", pad=8)
        ax.legend(fontsize=8, framealpha=0.9, loc="upper right")
        ax.grid(axis="y", alpha=0.4)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    log.info("SVAR chart saved: %s", path)
    return path


def chart_forecast(forecast_data: dict) -> str | None:
    """
    History + forecast path for CPI inflation and FX, with 95% CI shading.
    Two-panel chart: top = CPI MoM%, bottom = FX MoM%.
    """
    fc = forecast_data.get("forecasts", {})
    history      = forecast_data.get("history", {})
    hist_dates   = forecast_data.get("history_dates", [])
    fc_dates     = forecast_data.get("forecast_dates", [])
    horizons     = forecast_data.get("horizons", [6, 12])
    as_of        = forecast_data.get("as_of_date", "")

    vars_to_plot = [
        ("cpi_mom_pct", "CPI Inflation (MoM %)", "Monthly CPI inflation (%)"),
        ("fx_mom_pct",  "FX Depreciation (MoM %)", "ARS/USD monthly change (%)"),
    ]
    vars_to_plot = [(c, t, y) for c, t, y in vars_to_plot if c in fc and c in history]
    if not vars_to_plot:
        return None

    path = str(CHARTS_DIR / "svar_forecast.png")
    n_panels = len(vars_to_plot)

    with plt.rc_context(CHART_STYLE):
        fig, axes = plt.subplots(n_panels, 1, figsize=(12, 4 * n_panels), squeeze=False)
        fig.suptitle(
            f"VAR Model Forecasts (as of {as_of})\n"
            f"6-month and 12-month horizon, 95% confidence bands",
            fontsize=11, fontweight="bold"
        )

        for ax, (col, title, ylabel) in zip(axes[:, 0], vars_to_plot):
            color = SHOCK_COLORS.get(col, "#333333")

            # History
            hist_vals = history[col]
            hx = list(range(len(hist_vals)))
            ax.plot(hx, hist_vals, color=color, linewidth=1.8, label="Historical")

            # Forecast path (full max_horizon)
            fc_col   = fc[col]
            fc_point = fc_col["point"]
            fc_lower = fc_col["lower"]
            fc_upper = fc_col["upper"]
            max_h    = len(fc_point)

            offset = len(hist_vals) - 1   # connect forecast to last historical point
            fx_full = [offset + i for i in range(max_h + 1)]
            pt_full = [hist_vals[-1]] + fc_point
            lo_full = [hist_vals[-1]] + fc_lower
            hi_full = [hist_vals[-1]] + fc_upper

            ax.plot(fx_full, pt_full, color=color, linewidth=1.8,
                    linestyle="--", label="Forecast (point)")
            ax.fill_between(fx_full, lo_full, hi_full,
                            color=color, alpha=0.15, label="95% CI")

            # Vertical markers at 6M and 12M horizons
            for h in horizons:
                if h <= max_h:
                    xh = offset + h
                    ax.axvline(xh, color=color, linewidth=0.8, linestyle=":")
                    pt_h = fc_point[h - 1]
                    ax.annotate(f"+{h}M: {pt_h:+.2f}%",
                                xy=(xh, pt_h), xytext=(xh + 0.4, pt_h),
                                fontsize=7.5, color=color, va="center")

            # Divider between history and forecast
            ax.axvline(offset, color="#6c757d", linewidth=1.0, linestyle="-", alpha=0.5)

            ax.axhline(0, color="#495057", linewidth=0.7, linestyle="--")
            ax.set_title(title, fontsize=9, fontweight="bold")
            ax.set_ylabel(ylabel, fontsize=8)
            ax.grid(axis="y", alpha=0.4)

            # X-axis: show a subset of date labels
            all_dates = hist_dates + fc_dates
            tick_step = max(1, len(all_dates) // 10)
            tick_xs   = list(range(0, len(all_dates), tick_step))
            ax.set_xticks(tick_xs)
            ax.set_xticklabels([all_dates[i] for i in tick_xs], rotation=30, fontsize=7)
            ax.set_xlim(0, len(all_dates) - 1)
            ax.legend(fontsize=8, framealpha=0.85, loc="upper left")

        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    log.info("SVAR forecast chart saved: %s", path)
    return path


def build_charts() -> list[str]:
    """
    Load JSON results and build all SVAR charts.
    Returns list of saved file paths (empty list if data unavailable).
    """
    irf_data      = _load_json(SVAR_DIR / "irf_results.json")
    fevd_data     = _load_json(SVAR_DIR / "fevd_results.json")
    forecast_data = _load_json(SVAR_DIR / "forecast_results.json")

    paths: list[str] = []

    if irf_data:
        p = chart_irf_to_cpi(irf_data)
        if p: paths.append(p)
        p = chart_irf_fx_all(irf_data)
        if p: paths.append(p)

    if fevd_data:
        p = chart_fevd_cpi(fevd_data)
        if p: paths.append(p)

    if forecast_data:
        p = chart_forecast(forecast_data)
        if p: paths.append(p)

    log.info("SVAR charts: %d charts saved.", len(paths))
    return paths
