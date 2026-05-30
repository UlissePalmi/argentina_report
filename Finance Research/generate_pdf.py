"""
Finance Research — PDF generator via headless Microsoft Edge.

Reads pipeline signals from data/signals/*.json, builds context,
renders template.html to a temp file, then calls Edge headless to
print it to A4 PDF at data/reports/fr_weekly.pdf.

Run standalone:
    uv run python "Finance Research/generate_pdf.py"

No extra dependencies beyond jinja2 (already installed).
Edge is built into Windows — no additional install required.
"""

import json
import math
import subprocess
from datetime import date
from pathlib import Path

import jinja2

HERE    = Path(__file__).parent
ROOT    = HERE.parent
SIG_DIR = ROOT / "data" / "signals"
CHARTS  = ROOT / "data" / "charts"
OUT     = ROOT / "data" / "reports" / "fr_weekly.pdf"

EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun",
          "Jul","Aug","Sep","Oct","Nov","Dec"]

VERDICT_LABELS = {
    "crisis_risk":                                "Crisis Risk",
    "fragile_recovery":                           "Fragile Recovery",
    "structural_improvement_underway_unconfirmed":"Structural Improvement — Unconfirmed",
    "recovery_confirmed_watch_sustainability":    "Recovery Confirmed — Watch Sustainability",
    "sustainable_growth":                         "Sustainable Growth",
}

VERDICT_SUBTITLES = {
    "Crisis Risk":                              "BoP stress is the dominant risk. Reserve drawdown requires immediate policy response.",
    "Fragile Recovery":                         "Stabilization underway but the foundation is fragile. Wage and investment recovery not confirmed.",
    "Structural Improvement — Unconfirmed":     "The stabilization trade is in place but the last mile on wages, investment and inflation has yet to clear.",
    "Recovery Confirmed — Watch Sustainability":"Recovery confirmed. Sustainability depends on investment quality and the external position.",
    "Sustainable Growth":                       "Structural growth confirmed. Monitor inflation and fiscal discipline to sustain expansion.",
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _sig(name: str) -> dict:
    p = SIG_DIR / f"signals_{name}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _f(v, fallback: float = 0.0) -> float:
    try:
        r = float(v)
        return fallback if math.isnan(r) else r
    except (TypeError, ValueError):
        return fallback


def _chart(name: str) -> str:
    """Return file:// URL if chart exists, else empty string."""
    p = CHARTS / name
    return p.as_uri() if p.exists() else ""


def _sig_class(signal_str: str) -> str:
    """Map 'green'/'yellow'/'red' → CSS class suffix."""
    mapping = {"green": "green", "yellow": "amber", "red": "red"}
    return mapping.get(str(signal_str).lower(), "amber")


# ─── Context builder ──────────────────────────────────────────────────────────

def build_context() -> dict:
    master = _sig("master")
    inf    = _sig("inflation")
    fx     = _sig("fx")
    fiscal = _sig("fiscal")
    wages  = _sig("wages")
    invest = _sig("investment")
    prod   = _sig("production")
    ext    = _sig("external")

    im  = inf.get("metrics",    {})
    fxm = fx.get("metrics",     {})
    fm  = fiscal.get("metrics", {})
    wm  = wages.get("metrics",  {})
    em  = ext.get("metrics",    {})
    pm  = prod.get("metrics",   {})
    iv  = invest.get("metrics", {})

    verdict_key = master.get("verdict", "")
    verdict_str = VERDICT_LABELS.get(verdict_key, "Macro Monitor")
    today       = date.today()
    today_str   = today.strftime("%d %b %Y")
    week_str    = today.strftime("Weekly · %Y-W%V")

    # ── CPI lag detection ──────────────────────────────────────────────────────
    # If today is past the 15th of the month after the latest CPI data point,
    # INDEC has likely published a new print that the API hasn't surfaced yet.
    cpi_lag_note = ""
    cpi_as_of = inf.get("as_of_date", "")
    if cpi_as_of:
        try:
            from datetime import datetime
            lat = datetime.strptime(cpi_as_of[:7], "%Y-%m").date().replace(day=1)
            # first day of the month after the latest data
            if lat.month == 12:
                next_m = lat.replace(year=lat.year + 1, month=1)
            else:
                next_m = lat.replace(month=lat.month + 1)
            expected_release = next_m.replace(day=15)
            if today >= expected_release:
                cpi_lag_note = (
                    f"Note: {next_m.strftime('%B %Y')} CPI has been released by INDEC "
                    f"but is not yet available on the datos.gob.ar API. "
                    f"This report reflects data through {lat.strftime('%B %Y')}."
                )
        except Exception:
            pass

    cpi_now  = _f(im.get("cpi_mom_latest"))
    res_now  = _f(em.get("gross_reserves_bn"))
    res_6m   = _f(em.get("reserves_change_6m"))
    wage_now = _f(wm.get("real_wage_yoy_latest"))
    fisc_now = _f(fm.get("fiscal_primary_pct_gdp"))
    off_fx   = _f(fxm.get("official_fx_latest"))
    brecha   = _f(fxm.get("brecha_ccl_pct"))
    reer_pct = _f(fxm.get("reer_percentile"), 4.0)
    fbcf     = _f(iv.get("fbcf_yoy_proxy"))
    ipi      = _f(pm.get("ipi_yoy_latest"))

    # ── Hero strip ────────────────────────────────────────────────────────────
    hero = [
        {"k": "ARS/USD",        "v": f"{off_fx:,.0f}",      "d": "Official"},
        {"k": "CCL Brecha",     "v": f"{brecha:.1f}%",       "d": "vs official"},
        {"k": "CPI MoM",        "v": f"{cpi_now:.1f}%",      "d": "latest"},
        {"k": "Reserves ($B)",  "v": f"${res_now:.1f}B",     "d": f"+${res_6m:.1f}B 6m"},
        {"k": "Real Wages YoY", "v": f"{wage_now:+.1f}%",    "d": "latest"},
        {"k": "Fiscal % GDP",   "v": f"{fisc_now:+.1f}%",    "d": "primary"},
    ]

    # ── Intro paragraphs ──────────────────────────────────────────────────────
    ann = ((1 + cpi_now / 100) ** 12 - 1) * 100
    intro_body1 = (
        f"Argentina's stabilization program is {verdict_str.lower()}. "
        f"Headline CPI is running at {cpi_now:.1f}%/month (annualized ~{ann:.0f}%), "
        f"down sharply from the December 2023 peak of 25.5%. "
        f"Gross reserves have recovered to ${res_now:.0f}B (+${res_6m:.0f}B over six months), "
        f"the CCL brecha sits at a contained {brecha:.1f}%, "
        f"and the primary fiscal surplus holds at {fisc_now:+.1f}% of GDP. "
        "These anchors are intact but the real-economy last mile has not cleared."
    ) if cpi_now else "Macro summary — pending signal computation."

    intro_body2 = (
        f"The key pressure points are real wages (still {wage_now:.1f}% YoY), "
        f"fixed investment (FBCF {fbcf:+.1f}% YoY), and sticky core inflation. "
        f"The peso sits at the {reer_pct:.0f}th REER percentile of its two-year history, "
        "flagging real overvaluation driven by core inflation running ahead of the crawl."
    ) if cpi_now else ""

    # ── Bottom line ───────────────────────────────────────────────────────────
    bottomline = (
        f"{verdict_str}. Real wages {wage_now:+.1f}% YoY, FBCF {fbcf:+.1f}% YoY, "
        f"CPI {cpi_now:.1f}%/month, gross reserves ${res_now:.1f}B, "
        f"fiscal surplus {fisc_now:+.1f}% GDP, CCL brecha {brecha:.1f}%."
    ) if cpi_now else "Bottom line — pending signal computation."

    # ── Thesis ────────────────────────────────────────────────────────────────
    tag_map = {
        "[WAGES]":"Wages","[CREDIT]":"Credit","[INVESTMENT]":"Investment",
        "[INFLATION]":"Inflation","[EXTERNAL]":"External",
        "[PRODUCTION]":"Production","[LABOR]":"Labor",
    }
    thesis = []
    for flag in master.get("flags", []):
        clean = flag
        for k in tag_map:
            clean = clean.replace(k + " ", "")
        for k in ("CRITICAL: ", "WARNING: ", "POSITIVE: ", "NOTE: "):
            clean = clean.replace(k, "")
        clean = clean.replace(" -- ", " — ").replace("--", "—").strip()
        if len(clean) > 20:
            thesis.append(clean)
        if len(thesis) == 4:
            break
    if not thesis:
        thesis = ["Signal computation pending — run main.py first."]

    # ── Scenario table ────────────────────────────────────────────────────────
    scenario_cols = ["Bear", "Base", "Bull"]
    scenario_rows = [
        {"label": "Real Wages YoY",   "vals": ["-8%",  f"{wage_now:+.0f}%", "+3%"],    "bold": False},
        {"label": "CPI MoM, Q4 2026", "vals": ["4.0%", "2.2%",              "1.5%"],   "bold": False},
        {"label": "ARS/USD (YE 2026)","vals": ["2,200","1,700",             "1,550"],  "bold": False},
        {"label": "Reserves ($B)",    "vals": ["38",   f"{res_now:.0f}",     "55"],     "bold": False},
        {"label": "Fiscal Bal. % GDP","vals": ["+0.5%",f"{fisc_now:+.1f}%", "+2.5%"], "bold": False},
        {"label": "REER Percentile",  "vals": ["2nd",  f"{reer_pct:.0f}th",  "25th"],  "bold": False},
        {"label": "Verdict",          "vals": ["Fragile","Stabilizing","Recovery"],    "bold": True},
    ]

    # ── FX metrics table ──────────────────────────────────────────────────────
    brecha_sig = "green" if brecha < 5 else ("amber" if brecha < 15 else "red")
    reer_sig   = "red"   if reer_pct < 10 else ("amber" if reer_pct < 25 else "green")
    fx_metrics = [
        {"label": "CCL Brecha",         "sig": brecha_sig, "value": f"{brecha:.1f}%"},
        {"label": "MEP Brecha",         "sig": brecha_sig, "value": f"{_f(fxm.get('brecha_mep_pct')):.1f}%"},
        {"label": "Official Rate",      "sig": "amber",    "value": f"ARS {off_fx:,.0f}"},
        {"label": "REER Percentile",    "sig": reer_sig,   "value": f"{reer_pct:.0f}th"},
    ]

    # ── Heatmap ───────────────────────────────────────────────────────────────
    sc      = master.get("scorecard", {})
    sig_num = {"green": 1, "yellow": 0, "red": -1}
    short_names = {
        "Master Variable (real wages YoY)":  "Real Wages",
        "Investment (FBCF YoY proxy)":       "Investment",
        "Inflation (monthly CPI)":           "CPI MoM",
        "Gross Reserves ($B)":               "Reserves",
        "Current Account (quarterly $B)":    "Curr. Acc.",
        "Formal Employment (YoY)":           "Employment",
        "Oil Production (YoY)":              "Oil Prod.",
        "Fiscal Balance (% GDP)":            "Fiscal",
    }
    metric_val = {
        "Real Wages":  f"{wage_now:+.1f}%",
        "Investment":  f"{fbcf:+.1f}%",
        "CPI MoM":     f"{cpi_now:.1f}%",
        "Reserves":    f"${res_now:.1f}B",
        "Curr. Acc.":  f"{_f(em.get('ca_latest_bn')):.1f}B",
        "Employment":  f"{_f(em.get('employment_yoy', 0) if 'employment_yoy' in em else 0):.1f}%",
        "Oil Prod.":   f"{_f(pm.get('oil_yoy')):.1f}%",
        "Fiscal":      f"{fisc_now:+.1f}%",
    }
    im3 = _f(im.get("cpi_mom_trend_3m"))
    wm3 = _f(wm.get("real_wage_trend_3m"), wage_now)
    avg_val = {
        "Real Wages": f"{wm3:+.1f}%",
        "CPI MoM":    f"{im3:.1f}%",
        "Fiscal":     f"{fisc_now:+.1f}%",
    }
    heatmap = []
    for k, v in sc.items():
        short = short_names.get(k, k[:12])
        heatmap.append({
            "label": short,
            "sig":   _sig_class(v.get("signal", "red")),
            "value": metric_val.get(short, f"{_f(v.get('value')):.1f}"),
            "avg":   avg_val.get(short, "—"),
        })

    # ── Risks ─────────────────────────────────────────────────────────────────
    risks = []
    for flag in master.get("flags", []):
        if "CRITICAL" not in flag and "WARNING" not in flag:
            continue
        tag_label = next((v for k, v in tag_map.items() if k in flag), "Macro")
        clean = flag
        for k in tag_map:
            clean = clean.replace(k + " CRITICAL: ", "").replace(k + " WARNING: ", "")
        clean = clean.replace(" -- ", " — ").replace("--", "—")
        parts = clean.split(" — ", 1) if " — " in clean else [clean, ""]
        risks.append({
            "tag":   tag_label,
            "title": parts[0].strip()[:80],
            "body":  parts[1].strip()[:160] if len(parts) > 1 else "",
        })
        if len(risks) == 5:
            break
    if not risks:
        risks = [{"tag": "Monitor", "title": "Watch stabilization progress", "body": ""}]

    # ── Catalysts ─────────────────────────────────────────────────────────────
    catalysts = [
        {"date": "12 Jun", "label": "INDEC CPI May",   "accent": True},
        {"date": "19 Jun", "label": "INDEC Wages Q1",  "accent": True},
        {"date": "26 Jun", "label": "EMAE Apr",        "accent": False},
        {"date": "10 Jul", "label": "INDEC CPI Jun",   "accent": True},
        {"date": "17 Jul", "label": "GDP Q1 2026",     "accent": True},
        {"date": "14 Aug", "label": "INDEC CPI Jul",   "accent": True},
    ]

    # ── CPI release schedule ──────────────────────────────────────────────────
    # Generate the next 5 expected INDEC CPI release dates starting from the
    # month after the latest available data. INDEC releases ~12th of the
    # following month; we use the 12th as the expected date.
    cpi_schedule = []
    if cpi_as_of:
        try:
            from datetime import datetime as _dt
            def _add_months(d, n):
                m = d.month - 1 + n
                return d.replace(year=d.year + m // 12, month=m % 12 + 1, day=1)
            lat_m = _dt.strptime(cpi_as_of[:7], "%Y-%m").date().replace(day=1)
            for i in range(1, 6):
                ref   = _add_months(lat_m, i)           # month the data covers
                rel   = _add_months(lat_m, i + 1).replace(day=12)  # expected release
                cpi_schedule.append({
                    "ref":      ref.strftime("%b %Y"),
                    "date":     rel.strftime("%d %b %Y"),
                    "past":     rel <= today,
                })
        except Exception:
            pass

    # ── Action tags ───────────────────────────────────────────────────────────
    cpi_sig  = "green" if cpi_now  < 3.5 else ("amber" if cpi_now  < 5.0 else "red")
    res_sig  = "green" if res_6m   > 2   else ("amber" if res_6m   > -2  else "red")
    fisc_sig = "green" if fisc_now > 0.5 else ("amber" if fisc_now > 0   else "red")
    wage_sig = "green" if wage_now > 2   else ("amber" if wage_now > -2  else "red")

    action_tags = [
        {"label": "CPI: Disinflating" if cpi_now < 3.0 else ("CPI: Sticky" if cpi_now < 5.0 else "CPI: Elevated"), "sig": cpi_sig},
        {"label": "Reserves: Building" if res_6m  > 0  else "Reserves: Drawing",  "sig": res_sig},
        {"label": "Fiscal: Surplus"    if fisc_now > 0 else "Fiscal: Deficit",    "sig": fisc_sig},
        {"label": "Wages: Recovering"  if wage_now > 0 else "Wages: Negative",    "sig": wage_sig},
    ]

    # ── Prints ────────────────────────────────────────────────────────────────
    prints = [
        {"date": "Mar 2026", "label": "INDEC CPI MoM",        "actual": f"{cpi_now:.1f}%",      "accent": True},
        {"date": "Jan 2026", "label": "INDEC Real Wages YoY",  "actual": f"{wage_now:+.1f}%",   "accent": True},
        {"date": "Feb 2026", "label": "Fiscal Primary % GDP",  "actual": f"{fisc_now:+.2f}%",   "accent": True},
        {"date": "Mar 2026", "label": "BCRA Gross Reserves",   "actual": f"${res_now:.1f}B",     "accent": False},
        {"date": "Q4 2025",  "label": "FBCF YoY",              "actual": f"{fbcf:+.1f}%",        "accent": False},
        {"date": "Feb 2026", "label": "IPI YoY",               "actual": f"{ipi:+.1f}%",         "accent": False},
    ]

    # ── Charts ────────────────────────────────────────────────────────────────
    charts = {
        "fx_dollar_fan":    _chart("fx_dollar_fan.png"),
        "fx_reer":          _chart("fx_reer.png"),
        "chart_inflation":  _chart("chart_inflation.png"),
        "chart_fiscal":     _chart("chart_fiscal.png"),
    }

    return {
        "firm":          "Argentina Macro Monitor",
        "vol":           week_str,
        "date":          today_str,
        "title":         verdict_str,
        "subtitle":      VERDICT_SUBTITLES.get(verdict_str, ""),
        "intro_body1":   intro_body1,
        "intro_body2":   intro_body2,
        "bottomline":    bottomline,
        "hero":          hero,
        "thesis":        thesis,
        "scenario_cols": scenario_cols,
        "scenario_rows": scenario_rows,
        "fx_metrics":    fx_metrics,
        "heatmap":       heatmap,
        "risks":         risks,
        "catalysts":     catalysts,
        "prints":        prints,
        "charts":        charts,
        "action_tags":   action_tags,
        "cpi_lag_note":   cpi_lag_note,
        "cpi_schedule":   cpi_schedule,
    }


# ─── Render ───────────────────────────────────────────────────────────────────

def generate() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)

    ctx = build_context()
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(HERE)),
        autoescape=True,
    )
    tmpl = env.get_template("template.html")

    # Pre-render with dummy total to count actual pages, then re-render with real count
    draft = tmpl.render(**{**ctx, "total_pages": 0})
    total_pages = draft.count('class="doc-page"')
    ctx["total_pages"] = total_pages

    html_str = tmpl.render(**ctx)

    # Write rendered HTML to a stable path (temp files get deleted before Edge reads them)
    render_path = HERE / "_render.html"
    render_path.write_text(html_str, encoding="utf-8")

    result = subprocess.run(
        [
            str(EDGE),
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--no-first-run",
            "--disable-extensions",
            "--disable-background-networking",
            "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=5000",
            f"--print-to-pdf={OUT}",
            "--print-to-pdf-no-header",
            render_path.as_uri(),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        print(f"Edge stderr: {result.stderr[:500]}")
        raise RuntimeError(f"Edge exited with code {result.returncode}")

    print(f"Written: {OUT}")


if __name__ == "__main__":
    generate()
