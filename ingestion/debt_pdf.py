"""
Parse INDEC quarterly EDE PDF (Balanza de pagos / Deuda Externa publication).

Scrapes https://www.indec.gob.ar/Institucional/Indec/InformesTecnicos/45 to find
all quarterly `bal_*.pdf` files, downloads each (with per-file caching), and
extracts government debt tables across the full history.

Tables extracted per PDF:
  Cuadro III.3  — Govt general: central vs subnational (current quarter)
  Cuadro III.4  — Central govt by creditor type: multilateral / bonds / other
  Cuadro III.5  — Multilateral breakdown: IMF, IDB, World Bank, CAF, etc.
  Cuadro III.6  — Central govt bonds: nominal residual vs market value
  Cuadro III.7  — Bond stock time series (from most-recent PDF only)
  Cuadro III.8  — Non-resident holdings % by bond ISIN (most-recent PDF only)

Output files (all in data/external/):
  govt_debt_levels.csv        — central vs subnational, one row per quarter
  govt_debt_creditor_types.csv — multilateral/bond/other shares, one row per quarter
  multilateral_creditors.csv  — IMF, IDB, World Bank, CAF, etc., one row per quarter per creditor
  bonds_nom_vs_market.csv     — bonds at nominal + market value (quarterly series)
  bond_nonresident_pct.csv    — % non-resident holdings per bond, quarterly
"""

import io
import re

import pandas as pd
import requests

from utils import EXTERNAL_DIR, get_logger, load_cache, save_cache

log = get_logger("fetch.debt_pdf")

INDEC_CONTENT_URL = "https://www.indec.gob.ar/Institucional/Indec/InformesTecnicos/45"
INDEC_BASE_URL    = "https://www.indec.gob.ar"
SCRAPE_CACHE_KEY  = "indec_ede_pdf_index_v2"

_QUARTER_PATTERNS = [
    (re.compile(r"Primer trimestre de (\d{4})"),  "Q1"),
    (re.compile(r"Segundo trimestre de (\d{4})"), "Q2"),
    (re.compile(r"Tercer trimestre de (\d{4})"),  "Q3"),
    (re.compile(r"Cuarto trimestre de (\d{4})"),  "Q4"),
]

_QUARTERS_2016_2026 = [
    f"{y}Q{q}" for y in range(2016, 2027) for q in range(1, 5)
]

# ---------------------------------------------------------------------------
# URL scraping
# ---------------------------------------------------------------------------

def _scrape_pdf_urls() -> list[str]:
    """
    Fetch the INDEC publications page and return full URLs for all bal_*.pdf files,
    most-recent first. Results are cached for 24h (the cache is a newline-joined string).
    """
    cached = load_cache(SCRAPE_CACHE_KEY)
    if cached and isinstance(cached, str) and cached.strip():
        urls = [u for u in cached.strip().split("\n") if u]
        if urls:
            return urls

    try:
        resp = requests.get(INDEC_CONTENT_URL, timeout=60)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        log.warning("Failed to fetch INDEC PDF index: %s", e)
        return []

    paths = re.findall(r'href=["\'](/uploads/[^"\']+\.pdf)["\']', html)
    seen, unique = set(), []
    for p in paths:
        if "bal_" in p and p not in seen:
            seen.add(p)
            unique.append(INDEC_BASE_URL + p)

    if unique:
        save_cache(SCRAPE_CACHE_KEY, "\n".join(unique))
        log.info("EDE PDF index: found %d bal_*.pdf URLs", len(unique))

    return unique


# ---------------------------------------------------------------------------
# Per-PDF download + cache
# ---------------------------------------------------------------------------

def _pdf_cache_key(url: str) -> str:
    # e.g. "indec_ede_pdf_bal_03_262210251315"
    filename = url.split("/")[-1].replace(".pdf", "")
    return f"indec_ede_pdf_{filename}"


def _load_pdf_bytes(url: str) -> bytes | None:
    key = _pdf_cache_key(url)
    cached = load_cache(key)
    if cached:
        try:
            return bytes.fromhex(cached)
        except Exception:
            pass

    try:
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        save_cache(key, resp.content.hex())
        return resp.content
    except Exception as e:
        log.warning("EDE PDF download failed (%s): %s", url, e)
        return None


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------

def _num(s: str) -> float | None:
    """Parse Spanish-format number: '174.999' → 174999.0, '2,1' → 2.1"""
    s = s.strip().replace("\xa0", "").replace(" ", "")
    if not s or s in ("-", ""):
        return None
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    elif "." in s:
        parts = s.split(".")
        if len(parts) == 2 and len(parts[1]) == 3:
            s = s.replace(".", "")
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


def _detect_quarter(text: str) -> str:
    for pat, suffix in _QUARTER_PATTERNS:
        m = pat.search(text)
        if m:
            return f"{m.group(1)}{suffix}"
    return "unknown"


# ---------------------------------------------------------------------------
# Cuadro III.3 — central vs subnational
# ---------------------------------------------------------------------------
_RE_III3 = re.compile(
    r"Deuda externa(?: bruta)? del gobierno general\s+([\d.,]+).*?"
    r"Gobierno central\s+([\d.,]+).*?"
    r"Gobiernos subnacionales\s+([\d.,]+)",
    re.DOTALL,
)

def _parse_cuadro_iii3(text: str, quarter: str) -> pd.DataFrame | None:
    m = _RE_III3.search(text)
    if not m:
        return None
    return pd.DataFrame([{
        "year_quarter":          quarter,
        "govt_total_nom_usd_m":  _num(m.group(1)),
        "central_nom_usd_m":     _num(m.group(2)),
        "subnational_nom_usd_m": _num(m.group(3)),
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
        "year_quarter":         quarter,
        "multilateral_usd_m":   _num(m.group(1)),
        "multilateral_pct":     _num(m.group(2)),
        "official_other_usd_m": _num(m.group(3)),
        "official_other_pct":   _num(m.group(4)),
        "bondholders_usd_m":    _num(m.group(5)),
        "bondholders_pct":      _num(m.group(6)),
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
                "year_quarter":  quarter,
                "creditor":      creditor,
                "current_usd_m": _num(m.group(1)),
                "prev_usd_m":    _num(m.group(2)),
            })
    m_other = re.search(r"Otros organismos.*?\s+([\d.,]+)\s+([\d.,]+)", text)
    if m_other:
        rows.append({
            "year_quarter":  quarter,
            "creditor":      "Otros (BEI/OFID/BCIE)",
            "current_usd_m": _num(m_other.group(1)),
            "prev_usd_m":    _num(m_other.group(2)),
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
    nom = _num(mn.group(1))
    mkt = _num(mm.group(1)) if mm else None
    return pd.DataFrame([{
        "year_quarter":        quarter,
        "bonds_nominal_usd_m": nom,
        "bonds_market_usd_m":  mkt,
        "discount_pct":        round((1 - mkt / nom) * 100, 1) if mkt and nom else None,
    }])


# ---------------------------------------------------------------------------
# Quarter range helper
# ---------------------------------------------------------------------------
_QWORDS = {"primer": 1, "segundo": 2, "tercer": 3, "cuarto": 4}
_RE_QRANGE = re.compile(
    r"(primer|segundo|tercer|cuarto)\s+trimestre\s+(?:de\s+)?(\d{4})",
    re.IGNORECASE,
)

def _quarter_range_from_header(text: str) -> list[str]:
    """
    Extract start/end quarter from a header like
    'Primer trimestre 2023-cuarto trimestre 2025' and return list of year_quarter strings.
    Falls back to _QUARTERS_2016_2026 if not detected.
    """
    matches = _RE_QRANGE.findall(text[:500])
    if len(matches) >= 2:
        try:
            sy, sq = int(matches[0][1]), _QWORDS[matches[0][0].lower()]
            ey, eq = int(matches[1][1]), _QWORDS[matches[1][0].lower()]
            quarters, y, q = [], sy, sq
            while (y, q) <= (ey, eq):
                quarters.append(f"{y}Q{q}")
                q += 1
                if q > 4:
                    q, y = 1, y + 1
            return quarters
        except (KeyError, ValueError):
            pass
    return _QUARTERS_2016_2026


# ---------------------------------------------------------------------------
# Cuadro III.7 — bond stock quarterly time series (most-recent PDF only)
# ---------------------------------------------------------------------------

# Layout A (older): "Títulos de deuda (a valor nominal residual) <numbers>"
_RE_III7_A = re.compile(
    r"T.tulos de deuda\s*\(a valor nominal residual\)\s*([\d.,\s]+)"
)
# Layout B (newer): "Títulos de deuda\n<numbers>\n(a valor nominal residual)"
_RE_III7_B = re.compile(
    r"T.tulos de deuda\s*\n([\d.,\s]+)\n\(a valor nominal residual\)"
)
_RE_III7_HEADER = re.compile(
    r"Cuadro III\.7[^\n]*\n([^\n]+trimestre[^\n]+)", re.IGNORECASE
)
_RE_III7_CANJE2020 = re.compile(r"Bonos canje 2020\s+([\d,.\s]+)")

def _parse_cuadro_iii7(text: str) -> pd.DataFrame | None:
    m = _RE_III7_B.search(text) or _RE_III7_A.search(text)
    if not m:
        return None

    raw = m.group(1).strip().split()
    vals = [_num(v) for v in raw if re.match(r"[\d.,]+$", v)]

    hm = _RE_III7_HEADER.search(text)
    quarters = _quarter_range_from_header(hm.group(1) if hm else "")[:len(vals)]

    rows = [{"year_quarter": q, "bonds_nominal_usd_m": v}
            for q, v in zip(quarters, vals)]

    mc = _RE_III7_CANJE2020.search(text)
    if mc:
        pcts = [_num(v) for v in mc.group(1).strip().split() if re.match(r"[\d,]+$", v)]
        for i, row in enumerate(rows):
            if i < len(pcts):
                row["canje2020_pct"] = pcts[i]

    return pd.DataFrame(rows) if rows else None


# ---------------------------------------------------------------------------
# Cuadro III.8 — non-resident holdings % by bond (most-recent PDF only)
# ---------------------------------------------------------------------------
_BONDS_III8 = [
    ("ARARGE3209S6", "AL30", "USD", "Interna"),
    ("ARARGE3209T4", "AL35", "USD", "Interna"),
    ("ARARGE3209U2", "AL38", "USD", "Interna"),
    ("US040114HS26", "GD30", "USD", "Extranjera"),
    ("US040114HT09", "GD35", "USD", "Extranjera"),
    ("US040114HU71", "GD38", "USD", "Extranjera"),
]
_RE_III8_HEADER = re.compile(
    r"Cuadro III\.8[^\n]*\n([^\n]+trimestre[^\n]+)", re.IGNORECASE
)

def _parse_cuadro_iii8(text: str) -> pd.DataFrame | None:
    hm = _RE_III8_HEADER.search(text)
    quarters = _quarter_range_from_header(hm.group(1) if hm else "")

    rows = []
    for isin, ticker, currency, law in _BONDS_III8:
        # Extract the full line containing this ISIN, then pull all decimal numbers from it
        line_pat = re.compile(rf".*{isin}.*")
        m = line_pat.search(text)
        if not m:
            continue
        vals = [_num(v) for v in re.findall(r"\d+[,.]\d+", m.group(0))]
        if not vals:
            continue
        for q, v in zip(quarters[:len(vals)], vals):
            rows.append({
                "year_quarter":    q,
                "isin":            isin,
                "ticker":          ticker,
                "law":             law,
                "nonresident_pct": v,
            })
    return pd.DataFrame(rows) if rows else None


# ---------------------------------------------------------------------------
# Parse one PDF
# ---------------------------------------------------------------------------

def _parse_one_pdf(pdf_bytes: bytes, url: str) -> dict:
    """
    Parse a single EDE PDF. Returns dict with keys:
      quarter, levels, creditor_types, multilateral, bonds, bond_series, nonresident
    All values are DataFrames or None.
    """
    import pdfplumber

    result: dict = {k: None for k in
                    ("quarter", "levels", "creditor_types", "multilateral",
                     "bonds", "bond_series", "nonresident")}

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            p_iii3 = _find_page(pdf, "Cuadro III.3")
            p_iii5 = _find_page(pdf, "Cuadro III.5")
            p_iii8 = _find_page(pdf, "Cuadro III.8")

            if p_iii3 is None:
                log.debug("Cuadro III.3 not found in %s", url.split("/")[-1])
                return result

            text_iii3  = _page_text(pdf, p_iii3)
            text_iii45 = (_page_text(pdf, p_iii5)
                          if p_iii5 is not None
                          else _page_text(pdf, p_iii3 + 1))
            text_iii8  = _page_text(pdf, p_iii8) if p_iii8 is not None else ""

            quarter = _detect_quarter(text_iii3) or _detect_quarter(text_iii45)
            result["quarter"] = quarter

            result["levels"]        = _parse_cuadro_iii3(text_iii3, quarter)
            result["creditor_types"] = _parse_cuadro_iii4(text_iii3, quarter)
            result["multilateral"]  = _parse_cuadro_iii5(text_iii45, quarter)
            result["bonds"]         = _parse_cuadro_iii6(text_iii45, quarter)
            result["bond_series"]   = _parse_cuadro_iii7(text_iii45)
            result["nonresident"]   = _parse_cuadro_iii8(text_iii8)

    except Exception as e:
        log.warning("Failed to parse PDF %s: %s", url.split("/")[-1], e)

    return result


# ---------------------------------------------------------------------------
# Main entry point — all PDFs
# ---------------------------------------------------------------------------

def fetch_all_ede_pdfs() -> dict[str, pd.DataFrame | None]:
    """
    Scrape the INDEC page for all bal_*.pdf URLs, download and parse each one,
    and return concatenated multi-quarter DataFrames.

    Returns dict with keys:
      levels, creditor_types, multilateral, bonds, bond_series, nonresident

    Writes CSVs to data/external/:
      govt_debt_levels.csv, govt_debt_creditor_types.csv,
      multilateral_creditors.csv, bonds_nom_vs_market.csv,
      bond_nonresident_pct.csv
    """
    try:
        import pdfplumber  # noqa: F401
    except ImportError:
        log.error("pdfplumber not installed — run: uv add pdfplumber")
        return {}

    urls = _scrape_pdf_urls()
    if not urls:
        log.warning("No EDE PDF URLs found")
        return {}

    log.info("Processing %d EDE PDFs...", len(urls))

    levels_list, types_list, multi_list, bonds_list = [], [], [], []
    bond_series_df = None
    nonresident_df = None

    for i, url in enumerate(urls):
        fname = url.split("/")[-1]
        pdf_bytes = _load_pdf_bytes(url)
        if not pdf_bytes:
            continue

        parsed = _parse_one_pdf(pdf_bytes, url)
        quarter = parsed.get("quarter") or "unknown"
        log.info("  [%d/%d] %s → %s", i + 1, len(urls), fname, quarter)

        if parsed["levels"] is not None:
            levels_list.append(parsed["levels"])
        if parsed["creditor_types"] is not None:
            types_list.append(parsed["creditor_types"])
        if parsed["multilateral"] is not None:
            multi_list.append(parsed["multilateral"])
        if parsed["bonds"] is not None:
            bonds_list.append(parsed["bonds"])

        # Use time-series tables from the most recent PDF that has them
        if bond_series_df is None and parsed["bond_series"] is not None:
            bond_series_df = parsed["bond_series"]
            # Merge market value from III.6 into latest row
            if parsed["bonds"] is not None and quarter != "unknown":
                bond_series_df.loc[
                    bond_series_df["year_quarter"] == quarter, "bonds_market_usd_m"
                ] = parsed["bonds"]["bonds_market_usd_m"].iloc[0]

        if nonresident_df is None and parsed["nonresident"] is not None and not parsed["nonresident"].empty:
            nonresident_df = parsed["nonresident"]

    def _concat_dedup(frames: list, quarter_col: str = "year_quarter") -> pd.DataFrame | None:
        if not frames:
            return None
        df = pd.concat(frames, ignore_index=True)
        df = df.drop_duplicates(subset=[quarter_col], keep="first")
        df = df.sort_values(quarter_col).reset_index(drop=True)
        return df

    df_levels = _concat_dedup(levels_list)
    df_types  = _concat_dedup(types_list)
    df_multi  = (pd.concat(multi_list, ignore_index=True)
                 .drop_duplicates(subset=["year_quarter", "creditor"], keep="first")
                 .sort_values(["year_quarter", "creditor"])
                 .reset_index(drop=True)) if multi_list else None
    df_bonds  = _concat_dedup(bonds_list)

    if df_levels is not None:
        df_levels.to_csv(EXTERNAL_DIR / "govt_debt_levels.csv", index=False)
        log.info("govt_debt_levels.csv written (%d rows)", len(df_levels))

    if df_types is not None:
        df_types.to_csv(EXTERNAL_DIR / "govt_debt_creditor_types.csv", index=False)
        log.info("govt_debt_creditor_types.csv written (%d rows)", len(df_types))

    if df_multi is not None:
        df_multi.to_csv(EXTERNAL_DIR / "multilateral_creditors.csv", index=False)
        log.info("multilateral_creditors.csv written (%d rows)", len(df_multi))

    if bond_series_df is not None:
        bond_series_df.to_csv(EXTERNAL_DIR / "bonds_nom_vs_market.csv", index=False)
        log.info("bonds_nom_vs_market.csv written (%d rows)", len(bond_series_df))

    if nonresident_df is not None:
        nonresident_df.to_csv(EXTERNAL_DIR / "bond_nonresident_pct.csv", index=False)
        log.info("bond_nonresident_pct.csv written (%d rows)", len(nonresident_df))

    return {
        "levels":        df_levels,
        "creditor_types": df_types,
        "multilateral":  df_multi,
        "bonds":         df_bonds,
        "bond_series":   bond_series_df,
        "nonresident":   nonresident_df,
    }


# ---------------------------------------------------------------------------
# Legacy single-PDF entry point (kept for direct testing)
# ---------------------------------------------------------------------------

def fetch_govt_debt_pdf() -> dict[str, pd.DataFrame | None]:
    """Fetch and parse only the most-recent EDE PDF."""
    urls = _scrape_pdf_urls()
    if not urls:
        return {}
    pdf_bytes = _load_pdf_bytes(urls[0])
    if not pdf_bytes:
        return {}
    return _parse_one_pdf(pdf_bytes, urls[0])
