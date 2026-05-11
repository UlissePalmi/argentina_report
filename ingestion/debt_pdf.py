"""
Parse INDEC quarterly EDE PDF (Balanza de pagos / Deuda Externa publication).

Downloads the latest PDF from INDEC, extracts the government debt tables, and
writes structured CSVs to data/external/.

Tables extracted:
  Cuadro III.3  — Govt general: central vs subnational (current quarter)
  Cuadro III.4  — Central govt by creditor type: multilateral / bonds / other
  Cuadro III.5  — Multilateral breakdown: IMF, IDB, World Bank, CAF, etc.
  Cuadro III.6  — Central govt bonds: nominal residual vs market value
  Cuadro III.7  — Bond stock time series (quarterly, back to 2023)
  Cuadro III.8  — Non-resident holdings % by bond ISIN

Output files (all in data/external/):
  govt_debt_levels.csv      — central vs subnational, creditor-type shares
  multilateral_creditors.csv — IMF, IDB, World Bank, CAF, etc.
  bonds_nom_vs_market.csv   — bonds at nominal + market value (quarterly series)
  bond_nonresident_pct.csv  — % non-resident holdings per bond, quarterly
"""

import io
import re

import pandas as pd
import requests

from utils import EXTERNAL_DIR, get_logger, load_cache, save_cache

log = get_logger("fetch.debt_pdf")

PDF_URL       = "https://www.indec.gob.ar/uploads/informesdeprensa/bal_03_262210251315.pdf"
PDF_CACHE_KEY = "indec_ede_pdf_bal_03_26"


def _download_pdf() -> bytes | None:
    cached = load_cache(PDF_CACHE_KEY)
    if cached:
        return cached.encode("latin-1") if isinstance(cached, str) else None

    try:
        import pdfplumber  # noqa: F401 — just to give an early ImportError if missing
    except ImportError:
        log.error("pdfplumber not installed. Run: uv add pdfplumber")
        return None

    try:
        resp = requests.get(PDF_URL, timeout=60)
        resp.raise_for_status()
        save_cache(PDF_CACHE_KEY, resp.content.hex())
        return resp.content
    except Exception as e:
        log.warning("EDE PDF download failed: %s", e)
        return None


def _load_pdf_bytes() -> bytes | None:
    cached = load_cache(PDF_CACHE_KEY)
    if cached:
        try:
            return bytes.fromhex(cached)
        except Exception:
            pass
    try:
        resp = requests.get(PDF_URL, timeout=60)
        resp.raise_for_status()
        save_cache(PDF_CACHE_KEY, resp.content.hex())
        return resp.content
    except Exception as e:
        log.warning("EDE PDF download failed: %s", e)
        return None


def _num(s: str) -> float | None:
    """Parse Spanish-format number: '174.999' → 174999.0, '2,1' → 2.1"""
    s = s.strip().replace("\xa0", "").replace(" ", "")
    if not s or s in ("-", ""):
        return None
    # If contains both . and , → thousands dot + decimal comma
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    elif "." in s:
        # Could be thousands separator (174.999) or decimal (3.9)
        parts = s.split(".")
        if len(parts) == 2 and len(parts[1]) == 3:
            s = s.replace(".", "")   # thousands separator
        # else leave as decimal
    try:
        return float(s)
    except ValueError:
        return None


def _page_text(pdf, page_num: int) -> str:
    return pdf.pages[page_num].extract_text() or ""


def _find_page(pdf, marker: str) -> int | None:
    for i, page in enumerate(pdf.pages):
        if marker in (page.extract_text() or ""):
            return i
    return None


# ---------------------------------------------------------------------------
# Cuadro III.3 — central vs subnational
# ---------------------------------------------------------------------------
_RE_III3 = re.compile(
    r"Deuda externa bruta del gobierno general\s+([\d.,]+).*?"
    r"Gobierno central\s+([\d.,]+).*?"
    r"Gobiernos subnacionales\s+([\d.,]+)",
    re.DOTALL,
)

def _parse_cuadro_iii3(text: str, quarter: str) -> pd.DataFrame | None:
    m = _RE_III3.search(text)
    if not m:
        return None
    return pd.DataFrame([{
        "year_quarter":         quarter,
        "govt_total_nom_usd_m": _num(m.group(1)),
        "central_nom_usd_m":    _num(m.group(2)),
        "subnational_nom_usd_m":_num(m.group(3)),
    }])


# ---------------------------------------------------------------------------
# Cuadro III.4 — central govt by creditor type
# ---------------------------------------------------------------------------
_RE_III4 = re.compile(
    r"Organismos internacionales\s+([\d.,]+)\s+([\d.,]+).*?"
    r"Acreedores oficiales.*?\s+([\d.,]+)\s+([\d.,]+).*?"
    r"Tenedores de t.tulos de deuda\s+([\d.,]+)\s+([\d.,]+)",
    re.DOTALL,
)

def _parse_cuadro_iii4(text: str, quarter: str) -> pd.DataFrame | None:
    m = _RE_III4.search(text)
    if not m:
        return None
    return pd.DataFrame([{
        "year_quarter":              quarter,
        "multilateral_usd_m":        _num(m.group(1)),
        "multilateral_pct":          _num(m.group(2)),
        "official_other_usd_m":      _num(m.group(3)),
        "official_other_pct":        _num(m.group(4)),
        "bondholders_usd_m":         _num(m.group(5)),
        "bondholders_pct":           _num(m.group(6)),
    }])


# ---------------------------------------------------------------------------
# Cuadro III.5 — multilateral creditors
# ---------------------------------------------------------------------------
_CREDITORS = ["FMI", "BID", "BIRF", "CAF", "FIDA", "FONPLATA"]

def _parse_cuadro_iii5(text: str, quarter: str) -> pd.DataFrame | None:
    rows = []
    for creditor in _CREDITORS:
        pat = re.compile(rf"{creditor}\s+([\d.,]+)\s+([\d.,]+)")
        m = pat.search(text)
        if m:
            rows.append({
                "year_quarter": quarter,
                "creditor":     creditor,
                "current_usd_m":_num(m.group(1)),
                "prev_usd_m":   _num(m.group(2)),
            })
    # Others (BEI, OFID, BCIE)
    m_other = re.search(r"Otros organismos.*?\s+([\d.,]+)\s+([\d.,]+)", text)
    if m_other:
        rows.append({
            "year_quarter": quarter,
            "creditor":     "Otros (BEI/OFID/BCIE)",
            "current_usd_m":_num(m_other.group(1)),
            "prev_usd_m":   _num(m_other.group(2)),
        })
    return pd.DataFrame(rows) if rows else None


# ---------------------------------------------------------------------------
# Cuadro III.6 — bonds nominal vs market
# ---------------------------------------------------------------------------
_RE_III6_NOM = re.compile(r"A valor nominal residual\s+([\d.,]+)\s+([\d.,]+)")
_RE_III6_MKT = re.compile(r"A valor de mercado\s+([\d.,]+)\s+([\d.,]+)")

def _parse_cuadro_iii6(text: str, quarter: str) -> pd.DataFrame | None:
    mn = _RE_III6_NOM.search(text)
    mm = _RE_III6_MKT.search(text)
    if not mn:
        return None
    return pd.DataFrame([{
        "year_quarter":       quarter,
        "bonds_nominal_usd_m":_num(mn.group(1)),
        "bonds_market_usd_m": _num(mm.group(1)) if mm else None,
        "discount_pct":       round(
            (1 - _num(mm.group(1)) / _num(mn.group(1))) * 100, 1
        ) if mm and _num(mn.group(1)) else None,
    }])


# ---------------------------------------------------------------------------
# Cuadro III.7 — bond stock quarterly time series
# ---------------------------------------------------------------------------
_QUARTERS_2023_2025 = [
    "2023Q1","2023Q2","2023Q3","2023Q4",
    "2024Q1","2024Q2","2024Q3","2024Q4",
    "2025Q1","2025Q2","2025Q3","2025Q4",
]
_RE_III7 = re.compile(
    r"T.tulos de deuda\s*\(a valor nominal residual\)\s*([\d.,\s]+)"
)
_RE_III7_CANJE2020 = re.compile(r"Bonos canje 2020\s+([\d,\s]+)")

def _parse_cuadro_iii7(text: str) -> pd.DataFrame | None:
    m = _RE_III7.search(text)
    if not m:
        return None
    raw = m.group(1).strip().split()
    vals = [_num(v) for v in raw if re.match(r"[\d.,]+", v)]
    quarters = _QUARTERS_2023_2025[:len(vals)]
    rows = [{"year_quarter": q, "bonds_nominal_usd_m": v}
            for q, v in zip(quarters, vals)]

    # Canje 2020 share
    mc = _RE_III7_CANJE2020.search(text)
    if mc:
        pcts = [_num(v) for v in mc.group(1).strip().split() if re.match(r"[\d,]+", v)]
        for i, row in enumerate(rows):
            if i < len(pcts):
                row["canje2020_pct"] = pcts[i]

    return pd.DataFrame(rows) if rows else None


# ---------------------------------------------------------------------------
# Cuadro III.8 — non-resident holdings % by bond
# ---------------------------------------------------------------------------
_BONDS_III8 = [
    ("ARARGE3209S6", "AL30", "USD", "Interna"),
    ("ARARGE3209T4", "AL35", "USD", "Interna"),
    ("ARARGE3209U2", "AL38", "USD", "Interna"),
    ("US040114HS26", "GD30", "USD", "Extranjera"),
    ("US040114HT09", "GD35", "USD", "Extranjera"),
    ("US040114HU71", "GD38", "USD", "Extranjera"),
]

def _parse_cuadro_iii8(text: str) -> pd.DataFrame | None:
    rows = []
    for isin, ticker, currency, law in _BONDS_III8:
        pat = re.compile(rf"{isin}.*?([\d,\s]+)", re.DOTALL)
        m = pat.search(text)
        if not m:
            continue
        raw = m.group(1).strip().split()
        vals = [_num(v) for v in raw if re.match(r"\d+[,.]?\d*", v)]
        quarters = _QUARTERS_2023_2025[:len(vals)]
        for q, v in zip(quarters, vals):
            rows.append({
                "year_quarter":      q,
                "isin":              isin,
                "ticker":            ticker,
                "law":               law,
                "nonresident_pct":   v,
            })
    return pd.DataFrame(rows) if rows else None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def fetch_govt_debt_pdf() -> dict[str, pd.DataFrame | None]:
    """
    Download and parse the latest INDEC EDE quarterly PDF.
    Returns dict with keys: levels, creditor_types, multilateral, bonds, bond_series, nonresident
    Writes CSVs to data/external/.
    """
    try:
        import pdfplumber
    except ImportError:
        log.error("pdfplumber not installed — run: uv add pdfplumber")
        return {}

    pdf_bytes = _load_pdf_bytes()
    if not pdf_bytes:
        return {}

    results = {}

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        # Find pages containing the relevant tables
        p_iii3 = _find_page(pdf, "III.3")
        p_iii5 = _find_page(pdf, "III.5")
        p_iii8 = _find_page(pdf, "III.8")

        if p_iii3 is None:
            log.warning("EDE PDF: Cuadro III.3 not found")
            return {}

        text_iii3 = _page_text(pdf, p_iii3)
        text_iii45 = _page_text(pdf, p_iii3 + 1) if p_iii5 is None else _page_text(pdf, p_iii5)
        text_iii8  = _page_text(pdf, p_iii8) if p_iii8 is not None else ""

        # Detect quarter from page text
        m_qtr = re.search(r"Cuarto trimestre de (\d{4})", text_iii3)
        quarter = f"{m_qtr.group(1)}Q4" if m_qtr else "unknown"
        log.info("EDE PDF: detected quarter %s", quarter)

        # III.3 — central vs subnational
        df_levels = _parse_cuadro_iii3(text_iii3, quarter)
        if df_levels is not None:
            df_levels.to_csv(EXTERNAL_DIR / "govt_debt_levels.csv", index=False)
            log.info("govt_debt_levels.csv written (%s)", quarter)
        results["levels"] = df_levels

        # III.4 — creditor types
        df_types = _parse_cuadro_iii4(text_iii3, quarter)
        results["creditor_types"] = df_types

        # III.5 — multilateral creditors
        df_multi = _parse_cuadro_iii5(text_iii45, quarter)
        if df_multi is not None:
            df_multi.to_csv(EXTERNAL_DIR / "multilateral_creditors.csv", index=False)
            log.info("multilateral_creditors.csv written (%d rows)", len(df_multi))
        results["multilateral"] = df_multi

        # III.6 — bonds nominal vs market (current quarter)
        df_bonds = _parse_cuadro_iii6(text_iii45, quarter)
        results["bonds"] = df_bonds

        # III.7 — bond time series
        df_series = _parse_cuadro_iii7(text_iii45)
        if df_series is not None:
            # Merge III.6 market value into latest row
            if df_bonds is not None:
                df_series.loc[df_series["year_quarter"] == quarter, "bonds_market_usd_m"] = (
                    df_bonds["bonds_market_usd_m"].iloc[0]
                )
            df_series.to_csv(EXTERNAL_DIR / "bonds_nom_vs_market.csv", index=False)
            log.info("bonds_nom_vs_market.csv written (%d rows)", len(df_series))
        results["bond_series"] = df_series

        # III.8 — non-resident holdings
        df_nr = _parse_cuadro_iii8(text_iii8)
        if df_nr is not None and not df_nr.empty:
            df_nr.to_csv(EXTERNAL_DIR / "bond_nonresident_pct.csv", index=False)
            log.info("bond_nonresident_pct.csv written (%d rows)", len(df_nr))
        results["nonresident"] = df_nr

    return results
