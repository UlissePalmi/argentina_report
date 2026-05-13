"""
BCRA balance sheet and reserves: weekly PDF snapshot, monthly gross reserves, FX rate.
"""

import re

import pandas as pd

from utils import RESERVES_DIR, get_logger
from .client import DatosClient, PdfClient, _start, to_monthly_last

log = get_logger("fetch.reserves")
_d   = DatosClient()
_pdf = PdfClient(timeout=30)

RESERVES_DAILY   = "92.2_RESERVAS_IRES_0_0_32_40"
RESERVES_MONTHLY = "92.1_RID_0_0_32"

_MONTHS_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

_NUM_RE       = re.compile(r'\(\s*\d{1,3}(?:\.\d{3})*\s*\)|\d{1,3}(?:\.\d{3})+|\d{5,}')
_SPLIT_NUM    = re.compile(r'\b(\d{1,2})\s+(\d(?:\.\d{3})+)')   # fix "5 0.602.176" → "50.602.176"
_SPACED_LINE  = re.compile(r'^[A-Z](\s[A-Z]){2,}')              # spaced-caps total lines
_TRAILING_INT = re.compile(r'(?:(?<=\s)|^)(\d+)\s*$')           # small integer at end (or alone) on a line

_SECTION_PARENTS = ['ASSETS', 'LIABILITIES', 'NET_EQUITY']

KNOWN_ASSETS = [
    "RESERVAS INTERNACIONALES",
    "TITULOS PUBLICOS",
    "ADELANTOS TRANSITORIOS AL GOBIERNO NACIONAL",
    "CREDITOS AL SISTEMA FINANCIERO DEL PAIS",
    "APORTES A ORGANISMOS INTERNACIONALES POR CUENTA DEL GOBIERNO NACIONAL Y OTROS",
    "DERECHOS PROVENIENTES DE OTROS INSTRUMENTOS FINANCIEROS DERIVADOS",
    "DERECHOS POR OPERACIONES DE PASES",
    "OTROS ACTIVOS",
]

KNOWN_LIABILITIES = [
    "BASE MONETARIA",
    "MEDIOS DE PAGO EN OTRAS MONEDAS",
    "CUENTAS CORRIENTES EN OTRAS MONEDAS",
    "DEPOSITOS DEL GOBIERNO NACIONAL Y OTROS",
    "OTROS DEPOSITOS",
    "ASIGNACIONES DE DEG",
    "OBLIGACIONES CON ORGANISMOS INTERNACIONALES",
    "TITULOS EMITIDOS POR EL B.C.R.A.",
    "CONTRAPARTIDA DE APORTES DEL GOBIERNO NACIONAL A ORGANISMOS INTERNACIONALES",
    "OBLIGACIONES PROVENIENTES DE OTROS INSTRUMENTOS FINANCIEROS DERIVADOS",
    "OBLIGACIONES POR OPERACIONES DE PASE",
    "DEUDAS POR CONVENIOS MULTILATERALES DE CREDITO",
    "OTROS PASIVOS",
    "PREVISIONES",
]


def _parse_ars_int(s: str) -> int | None:
    try:
        return int(s.replace(".", "").replace(",", ""))
    except (ValueError, AttributeError):
        return None


def _norm(s: str) -> str:
    """Uppercase, collapse whitespace, strip Spanish diacritics — for section-name matching."""
    s = s.upper()
    for a, b in [('Á','A'),('É','E'),('Í','I'),('Ó','O'),('Ú','U'),('Ü','U'),('Ñ','N')]:
        s = s.replace(a, b)
    return re.sub(r'\s+', ' ', s).strip()


def _parse_balance_sheet(text: str) -> dict:
    """
    Schema-anchored parser. KNOWN_ASSETS / KNOWN_LIABILITIES are the fixed section anchors.
    Lines between two consecutive anchors belong to the first anchor's section.
      - 1 number in the block  → _total only  (e.g. OTROS PASIVOS = 33.926.128.247)
      - multiple numbers       → extract (label, value) items; rightmost column = _total
    Only ALL-CAPS lines trigger section detection (mixed-case lines are always items).
    Unknown ALL-CAPS lines that don't match any known section trigger a warning.
    """
    known = {
        'ASSETS':      {_norm(s): s for s in KNOWN_ASSETS},
        'LIABILITIES': {_norm(s): s for s in KNOWN_LIABILITIES},
    }
    result: dict = {
        'ASSETS':      {s: {} for s in KNOWN_ASSETS},
        'LIABILITIES': {s: {} for s in KNOWN_LIABILITIES},
        'NET_EQUITY':  {},
    }

    current_parent: str | None = None
    current_section: str | None = None
    section_lines: list[str] = []
    accumulated: str = ''   # partial section name built across wrapped lines

    def flush(parent, section, raw_lines):
        """
        Process the lines collected for one section and write into result[parent][section].

        Single-number rule: if the entire block contains exactly one number, that number
        is the section total (e.g. OTROS PASIVOS = 33.926.128.247).

        Multi-number rule: extract (label, value) pairs from each line.
          - Rightmost number on a line with two numbers = section total
            (e.g. Instrumentos Derivados  50.602.176  63.904.438.642 → total = 63.904.438.642)
          - ALL-CAPS label that matches the section name = subtotal line, not a data item
            (e.g. CREDITOS AL SISTEMA FINANCIERO DEL PAIS  50.318.589 at the bottom of that box)
        """
        if parent is None or section is None or not raw_lines:
            return

        final_items: dict = {}   # confirmed items
        group_header: str | None = None
        group_items: dict = {}   # items accumulated since last no-number header
        section_total: int | None = None
        all_nums: list[str] = []

        for ln in raw_lines:
            ln = _SPLIT_NUM.sub(r'\1\2', ln)
            nums = _NUM_RE.findall(ln)
            if not nums:
                tm = _TRAILING_INT.search(ln)
                if tm:
                    nums = [tm.group(1)]

            if not nums:
                # No-number mixed-case line = group header (e.g. "Títulos Públicos bajo Ley Nacional")
                label = re.sub(r'\s+', ' ', ln).strip()
                if len(label) >= 2 and re.search(r'[a-z]', label) and not label[0].islower():
                    final_items.update(group_items)   # flush any un-closed group items
                    group_header = label
                    group_items = {}
                continue

            all_nums.extend(nums)

            m = _NUM_RE.search(ln) or _TRAILING_INT.search(ln)
            label = re.sub(r'\s+', ' ', ln[:m.start()]).strip()
            label = re.sub(r'\s+\d\s*$', '', label).strip()

            raw0 = nums[0]
            val = (-(_parse_ars_int(raw0[1:-1]) or 0)
                   if raw0.startswith('(') and raw0.endswith(')')
                   else _parse_ars_int(raw0))
            if val is None:
                continue

            is_caps = not re.search(r'[a-z]', label)

            if len(nums) >= 2:
                right = _parse_ars_int(nums[-1])
                if group_header is not None and not is_caps and raw0.startswith('('):
                    # Parenthetical first number = netting adjustment that closes the group subtotal.
                    # e.g. Regularización (3.853.326)  112.112.908.726 → Ley Nacional: 112112908726
                    final_items[group_header] = right
                    group_header = None
                    group_items = {}
                else:
                    # No group collapse: flush group items and store this line normally.
                    # e.g. Cuentas Corrientes en Pesos  15.794.846.585  41.186.003.948
                    #       → item + right is running section total
                    final_items.update(group_items)
                    group_header = None
                    group_items = {}
                    if is_caps and _norm(label) == _norm(section):
                        section_total = right   # section subtotal line, not stored as item
                    else:
                        if len(label) >= 2 and not label[0].islower():
                            final_items[label] = val
                        section_total = right
            else:
                # Single-number line: ALL-CAPS matching section name = section total on its own line
                if is_caps and _norm(label) == _norm(section):
                    section_total = val
                elif len(label) >= 2 and not label[0].islower():
                    target = group_items if group_header is not None else final_items
                    target[label] = val

        # Flush any remaining un-closed group items
        final_items.update(group_items)

        # Single-number rule: 1 number in the whole block = _total, nothing else to store
        if len(all_nums) == 1:
            result[parent][section]['_total'] = _parse_ars_int(all_nums[0])
            return

        result[parent][section].update(final_items)
        if section_total is not None:
            result[parent][section]['_total'] = section_total

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        # Spaced-caps lines: ACTIVO / PASIVO switches and PATRIMONIO NETO total
        if _SPACED_LINE.match(line):
            flat = line.replace(' ', '').upper()
            if flat == 'ACTIVO':
                flush(current_parent, current_section, section_lines)
                current_parent, current_section, section_lines, accumulated = 'ASSETS', None, [], ''
            elif flat == 'PASIVO':
                flush(current_parent, current_section, section_lines)
                current_parent, current_section, section_lines, accumulated = 'LIABILITIES', None, [], ''
            elif 'PATRIMONIO' in flat and 'PASIVO' not in flat:
                nums = _NUM_RE.findall(line)
                if nums:
                    result['NET_EQUITY']['_total'] = _parse_ars_int(nums[-1])
                flush(current_parent, current_section, section_lines)  # flush last section
                current_section, section_lines = None, []              # stop collecting (footnotes follow)
            continue

        if current_parent is None or current_section is None and not accumulated:
            # Haven't entered a section yet, or just flushed for PATRIMONIO
            if current_parent is None:
                continue

        # Only attempt section matching for ALL-CAPS lines (mixed-case = item line)
        # Strip formatted numbers AND standalone integers so "DERECHOS...  0" → "DERECHOS..."
        label_only = re.sub(r'\s+', ' ', re.sub(r'\b\d+\b', '', _NUM_RE.sub('', line))).strip()
        is_caps = bool(label_only) and not re.search(r'[a-z]', label_only)

        if is_caps or accumulated:
            norm_no_num = _norm(label_only)
            candidate = (accumulated + ' ' + norm_no_num).strip() if accumulated else norm_no_num
            parent_known = known[current_parent]

            if candidate in parent_known:
                matched = parent_known[candidate]
                if matched != current_section:          # new section boundary
                    flush(current_parent, current_section, section_lines)
                    current_section = matched
                    section_lines = [line] if _NUM_RE.search(line) or _TRAILING_INT.search(line) else []
                else:                                   # same section name re-appears = subtotal line
                    section_lines.append(line)
                accumulated = ''
                continue

            if any(k.startswith(candidate) for k in parent_known):
                accumulated = candidate                 # partial match — wait for next line
                continue

            accumulated = ''

            # Unmatched ALL-CAPS line with no number → possible new section
            if (current_section is not None
                    and not _NUM_RE.search(line) and not _TRAILING_INT.search(line)
                    and len(norm_no_num) >= 8):
                log.warning("balance sheet: possible new section in %s: '%s'",
                            current_parent, norm_no_num)
        else:
            accumulated = ''

        if current_section is not None:
            section_lines.append(line)

    flush(current_parent, current_section, section_lines)
    _validate_totals(result)
    return result


def _validate_totals(bs: dict) -> None:
    """Check that sub-item values sum to _total for each section; log discrepancies."""
    for parent, sections in bs.items():
        if parent == 'NET_EQUITY':
            continue
        for section, items in sections.items():
            total = items.get('_total')
            if total is None:
                continue
            item_sum = sum(v for k, v in items.items() if k != '_total' and isinstance(v, (int, float)))
            if item_sum == 0:
                continue
            if abs(item_sum - total) > 1:
                log.warning("balance sheet total mismatch [%s|%s]: sum %d != total %d (diff %d)",
                            parent, section, item_sum, total, item_sum - total)


def _flatten(bs: dict) -> dict:
    """Flatten to {'ASSETS|RESERVAS INTERNACIONALES|Divisas': value, ...}"""
    flat: dict = {}
    for parent in _SECTION_PARENTS:
        if parent == 'NET_EQUITY':
            if '_total' in bs.get('NET_EQUITY', {}):
                flat['NET_EQUITY|_total'] = bs['NET_EQUITY']['_total']
        else:
            known = KNOWN_ASSETS if parent == 'ASSETS' else KNOWN_LIABILITIES
            for section in known:
                for label, val in bs.get(parent, {}).get(section, {}).items():
                    flat[f"{parent}|{section}|{label}"] = val
    return flat


def _col_sort_key(col: str) -> tuple:
    """Sort columns by parent section, then by known section order within that parent."""
    parts = col.split('|')
    parent_idx = _SECTION_PARENTS.index(parts[0]) if parts[0] in _SECTION_PARENTS else 99
    known = KNOWN_ASSETS if parts[0] == 'ASSETS' else KNOWN_LIABILITIES if parts[0] == 'LIABILITIES' else []
    section_idx = known.index(parts[1]) if len(parts) > 1 and parts[1] in known else 99
    return (parent_idx, section_idx, col)


def fetch_bcra_balance_sheet() -> dict | None:
    """Fetch and parse the weekly BCRA Estado Resumido de Activos y Pasivos PDF.

    Extracts every line that has a text label and a number, stores raw ARS values
    (in thousands, as printed). Appends a new row to bcra_balance_sheet.csv with
    one column per unique line label. New labels seen in future PDFs get new columns.
    Skips if the reference date is already in the CSV.
    """
    url = "https://www.bcra.gob.ar/archivos/Pdfs/PublicacionesEstadisticas/econ0200.pdf"
    
    # Fetch and extract text from PDF
    text = _pdf.fetch_text(url, cache_key="bcra_balance_sheet_pdf")
    if text is None:
        return None

    # Extract reference date from text (e.g. "al 31 de diciembre de 2023")
    dm = _pdf.find(text, r"al\s+(\d+)\s+de\s+(\w+)\s+de\s+(\d{4})", re.IGNORECASE,
                   warn="BCRA balance sheet: reference date not found")
    if not dm:
        return None
    
    # Convert Spanish month name to month number (e.g. "al 30 de abril de 2025" → "2025-04-30")
    month_num = _MONTHS_ES.get(dm.group(2).lower())
    if month_num is None:
        log.warning("BCRA balance sheet: unrecognised month '%s'", dm.group(2))
        return None
    ref_date = str(pd.Timestamp(year=int(dm.group(3)), month=month_num, day=int(dm.group(1))).date())

    # Exchange rate for USD conversion (e.g. "$ 350,50 = USD")
    fxm = _pdf.find(text, r"\$\s*([\d\.]+),([\d]+)\s*=\s*USD", warn="BCRA balance sheet: exchange rate not found")
    fx = (float(fxm.group(1).replace(".", "")) + float("0." + fxm.group(2))) if fxm else None

    # Parse into {section: {subsection: {label: value}}} then flatten to section-ordered columns
    bs = _parse_balance_sheet(text)
    if not bs:
        log.warning("BCRA balance sheet: no items extracted")
        return None
    flat = _flatten(bs)

    row_ars = {"date": ref_date, **flat}
    row_usd = {"date": ref_date,
               **{col: round(val / fx / 1e6, 3) if fx and val is not None else None
                  for col, val in flat.items()}}

    _append_to_balance_sheet_csv(row_ars, "bcra_balance_sheet_ars.csv")
    _append_to_balance_sheet_csv(row_usd, "bcra_balance_sheet_usd.csv")
    log.info("BCRA balance sheet %s: %d line items across %d sections",
             ref_date, len(flat), len(bs))
    return row_ars


def _append_to_balance_sheet_csv(row: dict, filename: str) -> None:
    """Append a row to the CSV; new columns are inserted in section order, not at the end."""
    path = RESERVES_DIR / filename
    date_str = row["date"]

    data_cols = sorted([c for c in row if c != "date"], key=_col_sort_key)

    if path.exists():
        existing = pd.read_csv(path)
        if date_str in existing["date"].astype(str).values:
            log.info("BCRA balance sheet: %s already in %s, skipping", date_str, filename)
            return
        all_cols = sorted(
            set(c for c in existing.columns if c != "date") | set(data_cols),
            key=_col_sort_key,
        )
        new_row = {col: row.get(col) for col in ["date"] + all_cols}
        df = pd.concat([existing.reindex(columns=["date"] + all_cols),
                        pd.DataFrame([new_row])], ignore_index=True)
    else:
        df = pd.DataFrame([{c: row.get(c) for c in ["date"] + data_cols}])

    df.to_csv(path, index=False)
    log.info("BCRA balance sheet -> %s (%d rows, %d cols)", filename, len(df), len(df.columns))















# Separate function -------------------------------------------------------

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
