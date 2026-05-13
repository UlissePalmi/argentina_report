"""
BCRA balance sheet and reserves: weekly PDF snapshot, monthly gross reserves, FX rate.
"""

import io
import re

import pandas as pd

from utils import RESERVES_DIR, get_logger
from .client import DatosClient, _start, to_monthly_last

log = get_logger("fetch.reserves")
_d  = DatosClient()

RESERVES_DAILY   = "92.2_RESERVAS_IRES_0_0_32_40"
RESERVES_MONTHLY = "92.1_RID_0_0_32"

_MONTHS_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

_NUM_RE = re.compile(r'\(\d{1,3}(?:\.\d{3})*\)|\d{1,3}(?:\.\d{3})+|\d{5,}')


def _parse_ars_int(s: str) -> int | None:
    try:
        return int(s.replace(".", "").replace(",", ""))
    except (ValueError, AttributeError):
        return None


def _extract_line_items(text: str) -> dict[str, int]:
    """Extract every (label, value) pair from the balance sheet text.

    label = text before the first number on the line.
    value = last number on the line (ARS thousands, as printed).
    Skips lines where the label starts lowercase (footnotes), has < 4 chars,
    or > 80 chars. Also strips orphaned single digits at the end of labels
    caused by PDF rendering artefacts (e.g. "50.602.176" → "5 0.602.176").
    """
    items = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = _NUM_RE.search(line)
        if not m:
            continue
        label = re.sub(r'\s+', ' ', line[:m.start()].strip())
        label = re.sub(r'\s+\d\s*$', '', label).strip()  # strip orphaned digit at end
        if not (4 <= len(label) <= 80):
            continue
        if label[0].islower():  # skip footnote sentences
            continue
        last = _NUM_RE.findall(line)[-1]
        if last.startswith('(') and last.endswith(')'):
            val = -(_parse_ars_int(last[1:-1]) or 0)
        else:
            val = _parse_ars_int(last)
        if val is not None:
            items[label] = val
    return items


def fetch_bcra_balance_sheet() -> dict | None:
    """Fetch and parse the weekly BCRA Estado Resumido de Activos y Pasivos PDF.

    Extracts every line that has a text label and a number, stores raw ARS values
    (in thousands, as printed). Appends a new row to bcra_balance_sheet.csv with
    one column per unique line label. New labels seen in future PDFs get new columns.
    Skips if the reference date is already in the CSV.
    """
    import requests
    import pdfplumber

    url = "https://www.bcra.gob.ar/archivos/Pdfs/PublicacionesEstadisticas/econ0200.pdf"
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        pdf_bytes = io.BytesIO(resp.content)
    except Exception as e:
        log.warning("BCRA balance sheet: download failed: %s", e)
        return None

    try:
        with pdfplumber.open(pdf_bytes) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    except Exception as e:
        log.warning("BCRA balance sheet: PDF parse failed: %s", e)
        return None

    dm = re.search(r"al\s+(\d+)\s+de\s+(\w+)\s+de\s+(\d{4})", text, re.IGNORECASE)
    if not dm:
        log.warning("BCRA balance sheet: reference date not found")
        return None
    month_num = _MONTHS_ES.get(dm.group(2).lower())
    if month_num is None:
        log.warning("BCRA balance sheet: unrecognised month '%s'", dm.group(2))
        return None
    ref_date = str(pd.Timestamp(year=int(dm.group(3)), month=month_num, day=int(dm.group(1))).date())

    # Exchange rate for USD conversion (not stored as a column)
    fxm = re.search(r"\$\s*([\d\.]+),([\d]+)\s*=\s*USD", text)
    fx = (float(fxm.group(1).replace(".", "")) + float("0." + fxm.group(2))) if fxm else None

    ars_items = _extract_line_items(text)
    if not ars_items:
        log.warning("BCRA balance sheet: no line items extracted")
        return None

    row_ars: dict = {"date": ref_date}
    row_usd: dict = {"date": ref_date}
    for label, ars_val in ars_items.items():
        row_ars[label] = ars_val
        row_usd[label] = round(ars_val / fx / 1e6, 3) if fx else None

    _append_to_balance_sheet_csv(row_ars, "bcra_balance_sheet_ars.csv")
    _append_to_balance_sheet_csv(row_usd, "bcra_balance_sheet_usd.csv")
    log.info("BCRA balance sheet %s: %d line items", ref_date, len(ars_items))
    return {**row_ars, **{f"{k}_usd_bn": v for k, v in row_usd.items() if k != "date"}}


def _append_to_balance_sheet_csv(row: dict, filename: str) -> None:
    """Append a row to the given CSV; add new columns if the PDF has new lines."""
    path = RESERVES_DIR / filename
    date_str = row["date"]

    if path.exists():
        existing = pd.read_csv(path)
        if date_str in existing["date"].astype(str).values:
            log.info("BCRA balance sheet: %s already saved in %s, skipping", date_str, filename)
            return
        for col in row:
            if col not in existing.columns:
                existing[col] = None
        new_row = {col: row.get(col) for col in existing.columns}
        df = pd.concat([existing, pd.DataFrame([new_row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])

    df.to_csv(path, index=False)
    log.info("BCRA balance sheet -> %s (%d rows, %d cols)", filename, len(df), len(df.columns))


def fetch_reserves(months: int = 24) -> pd.DataFrame | None:
    """Fetch BCRA gross international reserves (monthly time series).

    Tries the daily datos.gob.ar series first (collapsed to month-end), falls
    back to the monthly series. Columns: date, reserves_usd_bn.
    """
    start = _start(months, buffer=1)
    df = None

    raw = _d.fetch([RESERVES_DAILY], limit=months * 31, start_date=start)
    if raw is not None and RESERVES_DAILY in raw.columns:
        raw = raw.rename(columns={RESERVES_DAILY: "reserves_usd_m"})
        df  = to_monthly_last(raw, "reserves_usd_m")
        log.info("BCRA reserves: datos.gob.ar daily -> monthly")

    if df is None:
        raw2 = _d.fetch([RESERVES_MONTHLY], limit=months + 6, start_date=start)
        if raw2 is not None and RESERVES_MONTHLY in raw2.columns:
            df = raw2.rename(columns={RESERVES_MONTHLY: "reserves_usd_m"})[["date", "reserves_usd_m"]]

    if df is None:
        log.warning("BCRA reserves: all sources failed.")
        return None

    df["reserves_usd_bn"] = df["reserves_usd_m"] / 1_000
    df = df[["date", "reserves_usd_bn"]].dropna().tail(months).reset_index(drop=True)

    df.to_csv(RESERVES_DIR / "bcra_reserves.csv", index=False)
    log.info("BCRA reserves saved -> bcra_reserves.csv  (%d rows)", len(df))
    return df


