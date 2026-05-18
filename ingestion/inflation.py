"""Inflation: INDEC CPI index, MoM %, and YoY %."""

import io

import pandas as pd

from utils import INFLATION_DIR, get_logger, load_cache, save_cache
from .client import DatosClient, _start

log = get_logger("fetch.inflation")
_d  = DatosClient()

IPC_INDEX_ID = "148.3_INIVELNAL_DICI_M_26"
IPC_MOM_ID   = "145.3_INGNACUAL_DICI_M_38"

_CPI_DIVISIONS_URL = (
    "https://infra.datos.gob.ar/catalog/sspm/dataset/145/distribution/145.5"
    "/download/indice-precios-al-consumidor-apertura-por-capitulos-base-diciembre-2016-mensual.csv"
)

_DIVISION_COLS = {
    "ipc_alimentos_bebidas_no_alcoholicas_nacional": "food",
    "ipc_bebidas_alcoholicas_tabaco_nacional":        "alcohol_tobacco",
    "ipc_prendas_vestir_calzado_nacional":            "clothing",
    "ipc_vivienda_agua_electricidad_combustibles_nacional": "housing",
    "ipc_equipamiento_mantenimientos_hogar_nacional": "household_equipment",
    "ipc_salud_nacional":                            "health",
    "ipc_transporte_nacional":                       "transport",
    "ipc_comunicaciones_nacional":                   "communication",
    "ipc_recreacion_cultura_nacional":               "recreation",
    "ipc_educacion_nacional":                        "education",
    "ipc_restaurantes_hoteles_nacional":             "restaurants",
    "ipc_bienes_servicios_varios_nacional":          "misc_goods",
}


def fetch_cpi(months: int = 24):
    """Columns: date, cpi_index, cpi_mom_pct, cpi_yoy_pct"""
    df = _d.fetch([IPC_INDEX_ID, IPC_MOM_ID], limit=months + 20, start_date=_start(months))
    if df is None or df.empty:
        log.warning("INDEC CPI: fetch failed.")
        return None
    df = df.rename(columns={IPC_INDEX_ID: "cpi_index", IPC_MOM_ID: "cpi_mom_raw"})
    df["cpi_mom_pct"] = df["cpi_mom_raw"] * 100
    df["cpi_yoy_pct"] = df["cpi_index"].pct_change(12) * 100
    df = df.drop(columns=["cpi_mom_raw"]).dropna(subset=["cpi_mom_pct"]).tail(months).reset_index(drop=True)
    df.to_csv(INFLATION_DIR / "indec_cpi.csv", index=False)
    log.info("INDEC CPI saved -> indec_cpi.csv  (%d rows)", len(df))
    return df


def fetch_cpi_by_division(months: int = 36):
    """
    Download INDEC CPI by the 12 consumption divisions (national total).
    Columns: date, {division}_idx (base Dec-2016=100), {division}_mom (MoM %), {division}_yoy (YoY %)
    """
    cache_key = "indec_cpi_divisions_145_5"
    raw_df = None

    cached = load_cache(cache_key)
    if cached:
        try:
            raw_df = pd.read_csv(io.StringIO(bytes.fromhex(cached).decode("utf-8")))
        except Exception:
            pass

    if raw_df is None:
        try:
            import requests
            resp = requests.get(_CPI_DIVISIONS_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            save_cache(cache_key, resp.content.hex())
            raw_df = pd.read_csv(io.StringIO(resp.text))
        except Exception as e:
            log.warning("CPI by division: download failed: %s", e)
            return None

    raw_df["indice_tiempo"] = pd.to_datetime(raw_df["indice_tiempo"])

    src_cols = [c for c in _DIVISION_COLS if c in raw_df.columns]
    df = raw_df[["indice_tiempo"] + src_cols].rename(columns={"indice_tiempo": "date"})
    df = df.rename(columns=_DIVISION_COLS)
    df = df.sort_values("date").reset_index(drop=True)

    divisions = list(_DIVISION_COLS.values())
    for div in divisions:
        df[f"{div}_mom"] = df[div].pct_change(1) * 100
        df[f"{div}_yoy"] = df[div].pct_change(12) * 100
    df = df.drop(columns=list(divisions))

    df = df.tail(months).reset_index(drop=True)
    df.to_csv(INFLATION_DIR / "indec_cpi_divisions.csv", index=False)
    log.info("INDEC CPI divisions saved -> indec_cpi_divisions.csv  (%d rows)", len(df))
    return df


_CATEGORY_IDS = {
    "core":     "148.3_INUCLEONAL_DICI_M_19",
    "regulated": "148.3_IREGULANAL_DICI_M_22",
    "seasonal": "148.3_IESTACINAL_DICI_M_25",
}


def fetch_cpi_by_category(months: int = 36):
    """
    Núcleo (~62%), Regulados (~24%), Estacionales (~10%) — index values, MoM %, YoY %.
    Columns: date, {category}_mom, {category}_yoy  (for core, regulated, seasonal)
    """
    ids = list(_CATEGORY_IDS.values())
    df = _d.fetch(ids, limit=months + 14, start_date=_start(months))
    if df is None or df.empty:
        log.warning("CPI by category: fetch failed.")
        return None

    df = df.rename(columns={v: k for k, v in _CATEGORY_IDS.items()})

    for cat in _CATEGORY_IDS:
        df[f"{cat}_mom"] = df[cat].pct_change(1) * 100
        df[f"{cat}_yoy"] = df[cat].pct_change(12) * 100
    df = df.drop(columns=list(_CATEGORY_IDS.keys()))

    df = df.dropna(subset=["core_mom"]).tail(months).reset_index(drop=True)
    df.to_csv(INFLATION_DIR / "indec_cpi_categories.csv", index=False)
    log.info("INDEC CPI categories saved -> indec_cpi_categories.csv  (%d rows)", len(df))
    return df
