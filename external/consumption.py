"""Consumption: wages, credit, deposits + Fisher real adjustment."""

import pandas as pd

from utils import CONSUMPTION_DIR, get_logger
from external.client import DatosClient, _start

log = get_logger("fetch.consumption")
_d  = DatosClient()

WAGE_ID     = "149.1_SOR_PRIADO_OCTU_0_25"
CREDIT_ID   = "91.1_PEFPGR_0_0_60"
TOTAL_CR_ID = "174.1_PTAMOS_O_0_0_29"
DEPOSITS_ID = "334.2_SIST_FINANIJO__54"
CREDIT_SERIES = {
    "personal_loans_pct":   "91.1_DETALLE_PRLES_0_0_52",
    "credit_cards_pct":     "91.1_DETALLE_PRTAS_0_0_60",
    "mortgages_pct":        "91.1_DETALLE_PRPOT_0_0_53",
    "auto_loans_pct":       "91.1_DETALLE_PREND_0_0_53",
    "overdrafts_pct":       "91.1_DETALLE_PRTOS_0_0_55",
    "commercial_paper_pct": "91.1_DETALLE_PRTOS_0_0_56",
}


def fetch_consumption(months: int = 24) -> pd.DataFrame | None:
    """
    Monthly consumption drivers.
    Columns: date, nominal_wage_yoy_pct, nominal_wage_mom_pct,
             consumer_credit_yoy_pct, total_credit_yoy_pct, deposits_yoy_pct,
             + granular credit YoY and MoM columns for each CREDIT_SERIES entry.
    """
    start, limit = _start(months), months + 20

    b_wage    = _d.fetch([WAGE_ID], limit=limit, start_date=start)
    b_credit  = _d.fetch([CREDIT_ID, TOTAL_CR_ID, DEPOSITS_ID], limit=limit, start_date=start)
    b_granular = _d.fetch(list(CREDIT_SERIES.values()), limit=limit, start_date=start)

    if b_wage is None or b_wage.empty:
        log.warning("fetch_consumption: wages batch failed.")
        return None

    result = b_wage[["date"]].copy()
    if WAGE_ID in b_wage.columns:
        result["nominal_wage_yoy_pct"] = b_wage[WAGE_ID].pct_change(12) * 100
        result["nominal_wage_mom_pct"] = b_wage[WAGE_ID].pct_change(1)  * 100

    if b_credit is not None and not b_credit.empty:
        for src, dst in [(CREDIT_ID, "consumer_credit_yoy_pct"),
                         (TOTAL_CR_ID, "total_credit_yoy_pct"),
                         (DEPOSITS_ID, "deposits_yoy_pct")]:
            if src in b_credit.columns:
                b_credit[dst] = b_credit[src].pct_change(12) * 100
        fin_cols = [c for c in ["consumer_credit_yoy_pct", "total_credit_yoy_pct", "deposits_yoy_pct"]
                    if c in b_credit.columns]
        if fin_cols:
            result = result.merge(
                b_credit[["date"] + fin_cols].dropna(subset=fin_cols, how="all"),
                on="date", how="left")
    else:
        log.warning("fetch_consumption: credit/deposits batch failed.")

    if b_granular is not None and not b_granular.empty:
        id_to_col = {v: k for k, v in CREDIT_SERIES.items()}
        for sid, col in id_to_col.items():
            if sid in b_granular.columns:
                b_granular[col]                             = b_granular[sid].pct_change(12) * 100
                b_granular[col.replace("_pct", "_mom_pct")] = b_granular[sid].pct_change(1)  * 100
        gran_cols = [c for c in b_granular.columns
                     if any(c in (n, n.replace("_pct", "_mom_pct")) for n in id_to_col.values())]
        if gran_cols:
            result = result.merge(
                b_granular[["date"] + gran_cols].dropna(subset=gran_cols, how="all"),
                on="date", how="left")
    else:
        log.warning("fetch_consumption: granular credit batch failed.")

    result = result.dropna(subset=[c for c in result.columns if c != "date"], how="all")
    result = result.tail(months).reset_index(drop=True)
    if result.empty:
        return None

    result.to_csv(CONSUMPTION_DIR / "consumption.csv", index=False)
    log.info("Consumption drivers saved -> consumption.csv  (%d rows, latest: %s)",
             len(result), result["date"].max().strftime("%Y-%m"))
    return result


def compute_real_values(consumption_df: pd.DataFrame, cpi_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge CPI into consumption_df and Fisher-adjust all nominal columns.

    Fisher: real = ((1 + nominal/100) / (1 + CPI/100) - 1) * 100
    Simple subtraction is badly wrong at Argentina's inflation levels.
    """
    cpi = cpi_df[[c for c in ["date", "cpi_yoy_pct", "cpi_mom_pct"] if c in cpi_df.columns]].copy()
    cpi["date"] = pd.to_datetime(cpi["date"]).dt.to_period("M").dt.to_timestamp()

    df = consumption_df.copy()
    df["_m"] = pd.to_datetime(df["date"]).dt.to_period("M").dt.to_timestamp()
    df = df.merge(cpi.rename(columns={"date": "_m"}), on="_m", how="left").drop(columns=["_m"])

    def _fisher(nom, cpi_col):
        return (((1 + df[nom] / 100) / (1 + df[cpi_col] / 100)) - 1) * 100

    YOY = {"nominal_wage_yoy_pct":    "real_wage_yoy_pct",
           "consumer_credit_yoy_pct": "real_consumer_credit_yoy_pct",
           "total_credit_yoy_pct":    "real_total_credit_yoy_pct",
           "deposits_yoy_pct":        "real_deposits_yoy_pct",
           "personal_loans_pct":      "real_personal_loans_pct",
           "credit_cards_pct":        "real_credit_cards_pct",
           "mortgages_pct":           "real_mortgages_pct",
           "auto_loans_pct":          "real_auto_loans_pct",
           "overdrafts_pct":          "real_overdrafts_pct",
           "commercial_paper_pct":    "real_commercial_paper_pct"}
    MOM = {"nominal_wage_mom_pct":     "real_wage_mom_pct",
           "personal_loans_mom_pct":   "real_personal_loans_mom_pct",
           "credit_cards_mom_pct":     "real_credit_cards_mom_pct",
           "mortgages_mom_pct":        "real_mortgages_mom_pct",
           "auto_loans_mom_pct":       "real_auto_loans_mom_pct",
           "overdrafts_mom_pct":       "real_overdrafts_mom_pct",
           "commercial_paper_mom_pct": "real_commercial_paper_mom_pct"}

    for nom, real in YOY.items():
        if nom in df.columns and "cpi_yoy_pct" in df.columns:
            df[real] = _fisher(nom, "cpi_yoy_pct")
    for nom, real in MOM.items():
        if nom in df.columns and "cpi_mom_pct" in df.columns:
            df[real] = _fisher(nom, "cpi_mom_pct")

    df.to_csv(CONSUMPTION_DIR / "consumption.csv", index=False)
    log.info("Consumption (real-adjusted) saved -> consumption.csv")
    return df
