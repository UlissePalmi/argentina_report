"""Productivity: SIPA employment, UCII capacity utilization, productivity + ULC computation."""

import pandas as pd

from utils import PRODUCTIVITY_DIR, get_logger
from .client import DatosClient, _start

log = get_logger("fetch.productivity")
_d  = DatosClient()

EMP_TOTAL_ID    = "151.1_TL_ESTADAD_2012_M_20"
EMP_INDUSTRY_ID = "155.1_ISTRIARIA_C_0_0_9"
EMP_CONSTR_ID   = "155.1_CTRUCCIION_C_0_0_12"
EMP_SERVICES_ID = "155.1_SICIOSIOS_C_0_0_9"
UCII_METALS_ID  = "31.3_UIMB_2004_M_33"
UCII_TEXT_ID    = "29.3_UPT_2006_M_23"
UCII_AUTO_ID    = "29.3_UV_2006_M_25"


def fetch_employment(quarters: int = 12) -> pd.DataFrame | None:
    """
    Columns: date, emp_total_yoy_pct, emp_total_mom_pct,
             emp_industry_yoy_pct, emp_construction_yoy_pct, emp_services_yoy_pct
    """
    start, limit = _start(quarters * 3, buffer=18), quarters + 8

    b_m = _d.fetch([EMP_TOTAL_ID], limit=limit * 3, start_date=start)
    b_q = _d.fetch([EMP_INDUSTRY_ID, EMP_CONSTR_ID, EMP_SERVICES_ID],
                   limit=limit, start_date=start)

    result = None
    if b_m is not None and EMP_TOTAL_ID in b_m.columns:
        result = b_m[["date"]].copy()
        result["emp_total_yoy_pct"] = b_m[EMP_TOTAL_ID].pct_change(12) * 100
        result["emp_total_mom_pct"] = b_m[EMP_TOTAL_ID].pct_change(1)  * 100

    if b_q is not None and not b_q.empty:
        for sid, col in [(EMP_INDUSTRY_ID, "emp_industry_yoy_pct"),
                         (EMP_CONSTR_ID,   "emp_construction_yoy_pct"),
                         (EMP_SERVICES_ID, "emp_services_yoy_pct")]:
            if sid in b_q.columns:
                b_q[col] = b_q[sid].pct_change(4) * 100
        q_cols = [c for c in ["emp_industry_yoy_pct", "emp_construction_yoy_pct",
                               "emp_services_yoy_pct"] if c in b_q.columns]
        if q_cols:
            q_sub  = b_q[["date"] + q_cols].dropna(subset=q_cols, how="all")
            result = result.merge(q_sub, on="date", how="left") if result is not None else q_sub
    else:
        log.warning("fetch_employment: sector employment batch failed.")

    if result is None or result.empty:
        log.warning("fetch_employment: no data.")
        return None

    result = result.dropna(subset=[c for c in result.columns if c != "date"], how="all")
    result = result.tail(quarters * 3).reset_index(drop=True)
    result.to_csv(PRODUCTIVITY_DIR / "employment.csv", index=False)
    log.info("Employment saved -> employment.csv  (%d rows, latest: %s)",
             len(result), result["date"].max().strftime("%Y-%m"))
    return result


UCII_CSV_URL = (
    "https://infra.datos.gob.ar/catalog/sspm/dataset/31/distribution/31.3/"
    "download/utilizacion-capacidad-instalada-industria-valores-mensuales-base-2004.csv"
)
UCII_COL_MAP = {
    "ucii_industrias_metalicas_basicas":       "ucii_metals_pct",
    "ucii_productos_textiles":                 "ucii_textiles_pct",
    "ucii_vehiculosautomotores":               "ucii_auto_pct",
}


def fetch_ucii(months: int = 24) -> pd.DataFrame | None:
    """
    Capacity utilization by sector (% of installed capacity).
    Fetches the full INDEC CSV directly — the series API no longer exposes
    textiles and auto individually.
    Columns: date, ucii_metals_pct, ucii_textiles_pct, ucii_auto_pct, ucii_avg_pct
    """
    from io import StringIO
    from utils import fetch_json
    import requests, warnings
    warnings.filterwarnings("ignore")

    cache_key = f"ucii_csv_{months}"
    cached = __import__("utils").load_cache(cache_key)
    if cached:
        df = pd.DataFrame(cached)
    else:
        try:
            r = requests.get(UCII_CSV_URL, timeout=30, verify=False)
            r.raise_for_status()
            df = pd.read_csv(StringIO(r.text))
            __import__("utils").save_cache(cache_key, df.to_dict(orient="records"))
        except Exception as e:
            log.warning("fetch_ucii: CSV download failed (%s) -- falling back to series API", e)
            batch = _d.fetch([UCII_METALS_ID], limit=months + 20, start_date=_start(months))
            if batch is None or batch.empty:
                return None
            batch = batch.rename(columns={UCII_METALS_ID: "ucii_metals_pct"})
            batch["ucii_avg_pct"] = batch["ucii_metals_pct"]
            batch = batch.tail(months).reset_index(drop=True)
            batch.to_csv(PRODUCTIVITY_DIR / "ucii.csv", index=False)
            return batch

    df = df.rename(columns={"indice_tiempo": "date"})
    df["date"] = pd.to_datetime(df["date"])
    df = df.rename(columns={k: v for k, v in UCII_COL_MAP.items() if k in df.columns})

    cols = [v for v in UCII_COL_MAP.values() if v in df.columns]
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    if cols:
        df["ucii_avg_pct"] = df[cols].mean(axis=1)

    start = _start(months)
    df = df[df["date"] >= start].dropna(subset=cols, how="all").tail(months).reset_index(drop=True)
    df.to_csv(PRODUCTIVITY_DIR / "ucii.csv", index=False)
    log.info("UCII saved -> ucii.csv  (%d rows)", len(df))
    return df


def compute_productivity(emae_df: pd.DataFrame,
                         employment_df: pd.DataFrame,
                         consumption_df: pd.DataFrame | None = None) -> pd.DataFrame | None:
    """
    Productivity YoY = EMAE sector YoY - employment sector YoY
    ULC YoY          = real wage YoY  - productivity YoY  (positive = costs rising faster than output)
    """
    SECTOR_MAP = {"industry":     ("industria_pct",   "emp_industry_yoy_pct"),
                  "construction": ("construccion_pct", "emp_construction_yoy_pct"),
                  "services":     ("comercio_pct",     "emp_services_yoy_pct")}

    def _to_month(df):
        d = df.copy()
        d["date"] = pd.to_datetime(d["date"]).dt.to_period("M").dt.to_timestamp()
        return d

    emae = _to_month(emae_df)
    emp  = _to_month(employment_df)
    base = emae[["date"]].merge(emp, on="date", how="outer").sort_values("date")
    for col in [v[0] for v in SECTOR_MAP.values()]:
        if col in emae.columns:
            base = base.merge(emae[["date", col]], on="date", how="left")

    rows = []
    for sector, (e_col, emp_col) in SECTOR_MAP.items():
        if e_col not in base.columns or emp_col not in base.columns:
            continue
        sub = base[["date", e_col, emp_col]].dropna().copy()
        sub[f"productivity_{sector}_yoy_pct"] = sub[e_col] - sub[emp_col]
        rows.append(sub[["date", f"productivity_{sector}_yoy_pct"]])

    if not rows:
        log.warning("compute_productivity: no sectors computed.")
        return None

    prod = rows[0]
    for df in rows[1:]:
        prod = prod.merge(df, on="date", how="outer")
    prod = prod.sort_values("date")

    if consumption_df is not None and "real_wage_yoy_pct" in consumption_df.columns:
        wages = _to_month(consumption_df[["date", "real_wage_yoy_pct"]])
        prod  = prod.merge(wages, on="date", how="left")
        for sector in SECTOR_MAP:
            p_col = f"productivity_{sector}_yoy_pct"
            if p_col in prod.columns:
                prod[f"ulc_{sector}_yoy_pct"] = prod["real_wage_yoy_pct"] - prod[p_col]

    prod.to_csv(PRODUCTIVITY_DIR / "productivity.csv", index=False)
    log.info("Productivity saved -> productivity.csv  (%d rows)", len(prod))
    return prod
