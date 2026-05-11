"""Government external debt stock and debt service. Output: data/external/govt_ext_debt.csv"""

import io

import pandas as pd
import requests

from utils import EXTERNAL_DIR, get_logger, add_quarter_cols, load_cache, save_cache
from .client import DatosClient, WorldBankClient

log = get_logger("fetch.debt")
_d  = DatosClient()
_wb = WorldBankClient()

# INDEC IIP (International Investment Position) — quarterly, USD millions, datos.gob.ar
IIP_TOTAL_ID  = "144.4_PVOSGOLES_0_T_32"   # total govt external liabilities
IIP_BONDS_ID  = "144.4_PVOSGOLES_0_T_50"   # portfolio / sovereign bonds (2020 restructured)
IIP_LOANS_ID  = "144.4_PVOSGOION_0_T_39"   # loans & other investment (IMF, multilaterals, bilateral)

# World Bank — annual
WB_DS_EXPORTS = "DT.TDS.DECT.EX.ZS"        # debt service as % of export revenues
WB_DEBT_GNI   = "DT.DOD.DECT.GN.ZS"        # total external debt as % of GNI

# Secretaría de Finanzas via datos.gob.ar — monthly, millions of ARS
DOM_AMORT_ID    = "379.7_AP_FIN_CAM006__58_29"  # principal repayments on domestic debt
DOM_INTEREST_ID = "379.7_GTOS_CORR_006__49_75"  # interest payments on domestic debt

# INDEC IIP — full sector breakdown (quarterly, USD millions)
IIP_GRAND_TOTAL_ID   = "144.4_PVOSTRLES_0_T_20"   # total external liabilities (all sectors) — NOT in API, derived from sector sum
IIP_BCRA_TOTAL_ID    = "144.4_PVOSBALES_0_T_29"   # S121 central bank total
IIP_BCRA_OI_ID       = "144.4_PVOSOTION_0_T_22"   # S121 other investment (SDRs + loans)
IIP_BANKS_TOTAL_ID   = "144.4_PVOSSOTOS_0_T_39"   # S122 deposit-taking institutions total
IIP_BANKS_OI_ID      = "144.4_PVOSOTIONIN_0_T_22" # S122 other investment
IIP_PRIVATE_TOTAL_ID = "144.4_PVOSOTRES_0_T_22"   # S1V non-financial corps + households total
IIP_PRIVATE_BOND_ID  = "144.4_PVOSOTERA_0_T_40"   # S1V portfolio / bonds
IIP_PRIVATE_OI_ID    = "144.4_PVOSOTIONC_0_T_22"  # S1V other investment (loans + trade credits)
IIP_PRIVATE_FDI_ID   = "144.4_PVOSOTCTA_0_T_40"   # S1V inward FDI


def fetch_ext_debt_by_sector(quarters: int = 40) -> pd.DataFrame | None:
    """
    Fetch INDEC Estadística de Deuda Externa (EDE) — gross external debt at nominal value,
    broken down by resident sector.  Source: INDEC / datos.gob.ar dataset 161.

    This is the correct source for matching INDEC's published infographics.
    Values are at NOMINAL (face) value in USD millions — differs from the IIP series
    (144.4_ on datos.gob.ar) which records bonds at MARKET value.

    Sectors:
      S13   General Government   — national + subnational + SOE bonds, multilateral loans
      S121  Central bank (BCRA)  — SDRs, PBoC swap, IMF loans to BCRA
      S122  Deposit-taking banks — interbank credit, trade lines
      S12R  Other financial corps
      S1V   Non-financial corps  — bonds, trade credits, intercompany FDI debt (NOT equity)

    Columns: year_quarter, quarter_start, quarter_end,
             grand_total_usd_bn,
             govt_total_usd_bn, govt_bonds_usd_bn, govt_loans_usd_bn,
             bcra_total_usd_bn, bcra_sdrs_usd_bn, bcra_loans_usd_bn,
             banks_total_usd_bn,
             other_fin_total_usd_bn,
             private_total_usd_bn, private_bonds_usd_bn, private_loans_usd_bn,
             private_trade_credits_usd_bn, private_fdi_debt_usd_bn
    Output: data/external/ext_debt_by_sector.csv
    """
    EDE_URL = ("https://infra.datos.gob.ar/catalog/sspm/dataset/161/distribution/161.1"
               "/download/estimacion-deuda-externa-bruta-por-sector-residente-saldos-"
               "fin-periodo-millones-dolares.csv")
    cache_key = "indec_ede_sector_161_1"

    raw_text = load_cache(cache_key)
    if raw_text is None:
        try:
            resp = requests.get(EDE_URL, timeout=30)
            resp.raise_for_status()
            raw_text = resp.text
            save_cache(cache_key, raw_text)
        except Exception as e:
            log.warning("EDE sector CSV download failed: %s", e)
            return None

    try:
        raw = pd.read_csv(io.StringIO(raw_text))
    except Exception as e:
        log.warning("EDE sector CSV parse failed: %s", e)
        return None

    raw["date"] = pd.to_datetime(raw["indice_tiempo"])

    rename = {
        "total_deuda_externa":                                    "grand_total_usd_bn",
        "total_deuda_gobierno_general":                           "govt_total_usd_bn",
        "deuda_gobierno_general_titulos_deuda":                   "govt_bonds_usd_bn",
        "deuda_gobierno_general_prestamos":                       "govt_loans_usd_bn",
        "total_deuda_banco_central":                              "bcra_total_usd_bn",
        "deuda_banco_central_derechos_especiales_giro":           "bcra_sdrs_usd_bn",
        "deuda_banco_central_prestamos":                          "bcra_loans_usd_bn",
        "total_deuda_soc_captadoras_depositos_no_banco_central":  "banks_total_usd_bn",
        "total_deuda_otras_entidades_financieras":                "other_fin_total_usd_bn",
        "total_deuda_sociedades_no_financieras":                  "private_total_usd_bn",
        "deuda_sociedades_no_financieras_titulos_deuda":          "private_bonds_usd_bn",
        "deuda_sociedades_no_financieras_prestamos":              "private_loans_usd_bn",
        "deuda_soc_no_financieras_creditos_anticipos_comerciales":"private_trade_credits_usd_bn",
        "deuda_sociedades_no_financieras_inversion_directa":      "private_fdi_debt_usd_bn",
    }

    keep = [c for c in rename if c in raw.columns]
    df = raw[["date"] + keep].rename(columns=rename)
    for col in rename.values():
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce") / 1_000

    df = df.dropna(subset=["grand_total_usd_bn"]).tail(quarters).reset_index(drop=True)
    if df.empty:
        log.warning("EDE sector: no data after filtering.")
        return None

    df = add_quarter_cols(df)
    ordered = [
        "year_quarter", "quarter_start", "quarter_end",
        "grand_total_usd_bn",
        "govt_total_usd_bn", "govt_bonds_usd_bn", "govt_loans_usd_bn",
        "bcra_total_usd_bn", "bcra_sdrs_usd_bn", "bcra_loans_usd_bn",
        "banks_total_usd_bn",
        "other_fin_total_usd_bn",
        "private_total_usd_bn", "private_bonds_usd_bn", "private_loans_usd_bn",
        "private_trade_credits_usd_bn", "private_fdi_debt_usd_bn",
    ]
    df = df[[c for c in ordered if c in df.columns]]
    df.to_csv(EXTERNAL_DIR / "ext_debt_by_sector.csv", index=False)
    log.info("EDE sector saved -> ext_debt_by_sector.csv (%d rows, latest: %s)",
             len(df), str(df["quarter_start"].iloc[-1])[:7])
    return df


def fetch_ext_debt_by_sector_iip(quarters: int = 40) -> pd.DataFrame | None:
    """
    Fetch INDEC IIP external liability breakdown at MARKET VALUE (datos.gob.ar 144.4_ series).

    Unlike the EDE (fetch_ext_debt_by_sector), this records bonds at current market prices,
    so it reflects price discounts/premia on Argentine sovereign bonds. Loans are identical
    between the two because loans don't have market prices.

    Advantage: ~current data (no publication lag).
    Limitation: bonds understated when Argentina trades at a discount; includes FDI equity
                in private totals (not comparable to EDE which is debt-instruments only).

    Columns: year_quarter, quarter_start, quarter_end,
             grand_total_mv_usd_bn,
             govt_total_mv_usd_bn, govt_bonds_mv_usd_bn, govt_loans_mv_usd_bn,
             bcra_total_mv_usd_bn,
             banks_total_mv_usd_bn,
             private_total_mv_usd_bn, private_bonds_mv_usd_bn, private_fdi_mv_usd_bn
    Output: data/external/ext_debt_by_sector_iip.csv
    """
    from .client import _start

    all_ids = [
        IIP_TOTAL_ID,
        IIP_BONDS_ID,
        IIP_LOANS_ID,
        IIP_BCRA_TOTAL_ID,
        IIP_BCRA_OI_ID,
        IIP_BANKS_TOTAL_ID,
        IIP_BANKS_OI_ID,
        IIP_PRIVATE_TOTAL_ID,
        IIP_PRIVATE_BOND_ID,
        IIP_PRIVATE_OI_ID,
        IIP_PRIVATE_FDI_ID,
    ]

    raw = _d.fetch(
        all_ids,
        limit=quarters + 4,
        start_date=_start(quarters * 3, buffer=6),
    )

    if raw is None or IIP_TOTAL_ID not in raw.columns:
        log.warning("Ext debt IIP (market value): fetch failed.")
        return None

    col_map = {
        IIP_TOTAL_ID:         "govt_total_mv_usd_bn",
        IIP_BONDS_ID:         "govt_bonds_mv_usd_bn",
        IIP_LOANS_ID:         "govt_loans_mv_usd_bn",
        IIP_BCRA_TOTAL_ID:    "bcra_total_mv_usd_bn",
        IIP_BCRA_OI_ID:       "bcra_oi_mv_usd_bn",
        IIP_BANKS_TOTAL_ID:   "banks_total_mv_usd_bn",
        IIP_BANKS_OI_ID:      "banks_oi_mv_usd_bn",
        IIP_PRIVATE_TOTAL_ID: "private_total_mv_usd_bn",
        IIP_PRIVATE_BOND_ID:  "private_bonds_mv_usd_bn",
        IIP_PRIVATE_OI_ID:    "private_oi_mv_usd_bn",
        IIP_PRIVATE_FDI_ID:   "private_fdi_mv_usd_bn",
    }

    df = raw[["date"]].copy()
    for series_id, col in col_map.items():
        if series_id in raw.columns:
            df[col] = raw[series_id] / 1_000

    sector_totals = [c for c in ["govt_total_mv_usd_bn", "bcra_total_mv_usd_bn",
                                  "banks_total_mv_usd_bn", "private_total_mv_usd_bn"]
                     if c in df.columns]
    if sector_totals:
        df["grand_total_mv_usd_bn"] = df[sector_totals].sum(axis=1, min_count=len(sector_totals))

    df = df.dropna(subset=["govt_total_mv_usd_bn"]).tail(quarters).reset_index(drop=True)
    if df.empty:
        log.warning("Ext debt IIP: no data.")
        return None

    df = add_quarter_cols(df)
    ordered = [
        "year_quarter", "quarter_start", "quarter_end",
        "grand_total_mv_usd_bn",
        "govt_total_mv_usd_bn", "govt_bonds_mv_usd_bn", "govt_loans_mv_usd_bn",
        "bcra_total_mv_usd_bn", "bcra_oi_mv_usd_bn",
        "banks_total_mv_usd_bn", "banks_oi_mv_usd_bn",
        "private_total_mv_usd_bn", "private_bonds_mv_usd_bn",
        "private_oi_mv_usd_bn", "private_fdi_mv_usd_bn",
    ]
    df = df[[c for c in ordered if c in df.columns]]
    df.to_csv(EXTERNAL_DIR / "ext_debt_by_sector_iip.csv", index=False)
    log.info("IIP (market value) saved -> ext_debt_by_sector_iip.csv (%d rows, latest: %s)",
             len(df), str(df["quarter_start"].iloc[-1])[:7])
    return df


def fetch_govt_ext_debt(quarters: int = 40) -> pd.DataFrame | None:
    """
    Fetch government external debt stock breakdown and debt service ratios.

    Returns DataFrame with columns:
      date, total_liab_usd_bn, bonds_usd_bn, loans_usd_bn,
      bonds_pct, loans_pct,
      debt_service_pct_exports, ext_debt_pct_gni
    """
    # ------------------------------------------------------------------
    # Step 1: INDEC IIP quarterly — government liabilities by instrument
    # ------------------------------------------------------------------
    from .client import _start
    raw = _d.fetch(
        [IIP_TOTAL_ID, IIP_BONDS_ID, IIP_LOANS_ID],
        limit=quarters + 4,
        start_date=_start(quarters * 3, buffer=6),
    )

    if raw is not None and IIP_TOTAL_ID in raw.columns:
        df = raw[["date"]].copy()
        df["total_liab_usd_bn"] = raw[IIP_TOTAL_ID] / 1_000
        if IIP_BONDS_ID in raw.columns:
            df["bonds_usd_bn"] = raw[IIP_BONDS_ID] / 1_000
        if IIP_LOANS_ID in raw.columns:
            df["loans_usd_bn"] = raw[IIP_LOANS_ID] / 1_000

        # Compute shares
        if "bonds_usd_bn" in df.columns and "loans_usd_bn" in df.columns:
            total = df["total_liab_usd_bn"]
            df["bonds_pct"] = (df["bonds_usd_bn"] / total * 100).round(1)
            df["loans_pct"] = (df["loans_usd_bn"] / total * 100).round(1)

        df = df.dropna(subset=["total_liab_usd_bn"]).tail(quarters).reset_index(drop=True)

        if not df.empty:
            log.info("Govt ext debt: INDEC IIP (%d rows, latest: %s)",
                     len(df), str(df["date"].iloc[-1])[:7])
    else:
        log.warning("Govt ext debt: INDEC IIP unavailable")
        df = pd.DataFrame()

    # ------------------------------------------------------------------
    # Step 2: World Bank annual service ratios — merge onto quarterly
    # ------------------------------------------------------------------
    for wb_id, col in [(WB_DS_EXPORTS, "debt_service_pct_exports"),
                       (WB_DEBT_GNI,   "ext_debt_pct_gni")]:
        raw_wb = _wb.fetch(wb_id, mrv=8)
        if raw_wb is not None and not raw_wb.empty:
            wb = raw_wb.rename(columns={"value": col}).copy()
            wb["date"] = pd.to_datetime(wb["date"].astype(str), format="%Y")
            if not df.empty:
                # Merge on year: map each quarterly row to its year's WB value
                df["_year"] = pd.to_datetime(df["date"]).dt.year
                wb["_year"] = wb["date"].dt.year
                df = df.merge(wb[["_year", col]], on="_year", how="left").drop(columns="_year")
            else:
                # Fallback: return WB-only frame (annual)
                df = wb[["date", col]].tail(8).reset_index(drop=True)
        else:
            log.warning("WB %s unavailable", wb_id)
            if not df.empty:
                df[col] = None

    if df.empty:
        log.warning("Govt ext debt: all sources failed.")
        return None

    df = add_quarter_cols(df)
    df.to_csv(EXTERNAL_DIR / "govt_ext_debt.csv", index=False)
    log.info("Govt ext debt saved -> govt_ext_debt.csv (%d rows)", len(df))
    return df


def fetch_domestic_debt_flows(months: int = 120) -> pd.DataFrame | None:
    """
    Fetch monthly domestic debt flows: principal amortization + interest payments.
    Both series in millions of ARS (nominal). Output: data/external/domestic_debt_flows.csv
    """
    from .client import _start
    raw = _d.fetch(
        [DOM_AMORT_ID, DOM_INTEREST_ID],
        limit=months + 6,
        start_date=_start(months),
        frequency="month",
    )
    if raw is None or DOM_AMORT_ID not in raw.columns:
        log.warning("Domestic debt flows: datos.gob.ar unavailable")
        return None

    df = raw[["date"]].copy()
    df["domestic_amort_ars_mn"]    = raw[DOM_AMORT_ID]
    df["domestic_interest_ars_mn"] = raw.get(DOM_INTEREST_ID)
    df["domestic_total_ars_mn"]    = df["domestic_amort_ars_mn"].fillna(0) + df["domestic_interest_ars_mn"].fillna(0)

    df = df.dropna(subset=["domestic_amort_ars_mn"]).tail(months).reset_index(drop=True)
    if df.empty:
        log.warning("Domestic debt flows: no data returned")
        return None

    df.to_csv(EXTERNAL_DIR / "domestic_debt_flows.csv", index=False)
    log.info("Domestic debt flows saved -> domestic_debt_flows.csv (%d rows, latest: %s)",
             len(df), str(df["date"].iloc[-1])[:7])
    return df
