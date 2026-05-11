"""
Argentina External Debt Parser — INDEC
Parses Cuadro III.1 (deuda externa bruta by sector and instrument)
directly from the INDEC quarterly PDF report.

Usage:
    python argentina_external_debt.py path/to/bal_report.pdf

The PDF is published quarterly at:
    https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-35-45
"""

import sys
import pdfplumber
import pandas as pd


# Column order matches the INDEC table header (Cuadro III.1)
SECTOR_COLS = [
    "S121_banco_central",
    "S122_bancos",
    "S13_gobierno_general",
    "S12R_otras_financieras",
    "S1V_no_financieras_hogares",
    "total",
]

# Instrument rows and their clean names
ROW_MAP = {
    "Moneda y depósitos": "moneda_depositos",
    "Préstamos": "prestamos",
    "Créditos y anticipos comerciales": "creditos_anticipos",
    "Otros pasivos de deuda": "otros_pasivos",
    "Asignaciones de DEG": "deg_asignaciones",
    "Inversión directa: crédito entre empresas": "inversion_directa_deuda",
}


def parse_number(s: str) -> float | None:
    """Convert INDEC number string to float. INDEC uses '.' as thousands sep."""
    if s is None or s.strip() in ("-", "", "///", "..."):
        return None
    cleaned = s.strip().replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def find_debt_table_page(pdf: pdfplumber.PDF) -> int | None:
    """Find page containing Cuadro III.1."""
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if "Stock de deuda externa bruta" in text and "Banco" in text and "Gobierno" in text:
            return i
    return None


def parse_debt_table(pdf_path: str) -> dict:
    """
    Opens the INDEC PDF and extracts Cuadro III.1.
    Returns structured dict with sector totals and instrument breakdown.
    """
    with pdfplumber.open(pdf_path) as pdf:
        page_idx = find_debt_table_page(pdf)
        if page_idx is None:
            raise ValueError("Could not find Cuadro III.1 in this PDF.")
        raw = pdf.pages[page_idx].extract_tables()[0]

    result = {
        "instruments_vm_vn": {},
        "bonds_market_value": {},
        "bonds_nominal_value": {},
        "stock_market_value": {},
        "stock_nominal_value": {},
    }

    current_block = None
    bond_vm_done = False
    bond_vn_done = False

    for row in raw:
        label = row[0].strip() if row[0] else ""
        values = row[1:]

        # Detect block headers
        if "Valor de mercado/valor nominal" in label:
            current_block = "vm_vn"
            continue
        elif "Valor de mercado al final del período" in label:
            current_block = "vm_titles"
            continue
        elif "Valor nominal residual al final del período" in label:
            current_block = "vn_titles"
            continue
        elif label == "Valor de mercado":
            current_block = "vm_stock"
            continue
        elif "Valor nominal residual" in label and "Stock" not in label:
            current_block = "vn_stock"
            continue

        if not label:
            continue

        nums = {col: parse_number(v) for col, v in zip(SECTOR_COLS, values)}

        if current_block == "vm_vn" and label in ROW_MAP:
            result["instruments_vm_vn"][ROW_MAP[label]] = nums

        elif current_block == "vm_titles" and "Títulos de deuda" in label and not bond_vm_done:
            result["bonds_market_value"] = nums
            bond_vm_done = True

        elif current_block == "vn_titles" and "Títulos de deuda" in label and not bond_vn_done:
            result["bonds_nominal_value"] = nums
            bond_vn_done = True

        elif current_block == "vm_stock":
            if "al final del período" in label:
                result["stock_market_value"]["end"] = nums
            elif "al inicio del período" in label:
                result["stock_market_value"]["start"] = nums
            elif "Variación" in label:
                result["stock_market_value"]["change"] = nums

        elif current_block == "vn_stock":
            if "al final del período" in label:
                result["stock_nominal_value"]["end"] = nums
            elif "al inicio del período" in label:
                result["stock_nominal_value"]["start"] = nums
            elif "Variación" in label:
                result["stock_nominal_value"]["change"] = nums

    return result


def to_sector_df(parsed: dict) -> pd.DataFrame:
    """Sector totals as a tidy DataFrame."""
    end = parsed["stock_nominal_value"]["end"]
    start = parsed["stock_nominal_value"]["start"]
    change = parsed["stock_nominal_value"]["change"]
    total = end.get("total")

    labels = {
        "S121_banco_central": "Banco central",
        "S122_bancos": "Bancos (excl. BCRA)",
        "S13_gobierno_general": "Gobierno general",
        "S12R_otras_financieras": "Otras soc. financieras",
        "S1V_no_financieras_hogares": "Soc. no financieras / Hogares",
        "total": "TOTAL",
    }
    rows = []
    for col, label in labels.items():
        val = end.get(col)
        rows.append({
            "sector": label,
            "end_mn_usd": val,
            "start_mn_usd": start.get(col),
            "change_mn_usd": change.get(col),
            "share_pct": round(val / total * 100, 1) if val and total else None,
        })
    return pd.DataFrame(rows)


def main(pdf_path: str):
    print(f"Parsing: {pdf_path}\n")
    parsed = parse_debt_table(pdf_path)

    print("=" * 65)
    print("DEUDA EXTERNA BRUTA — SECTOR TOTALS (valor nominal, mn USD)")
    print("=" * 65)
    print(to_sector_df(parsed).to_string(index=False))

    print("\n" + "=" * 65)
    print("INSTRUMENT BREAKDOWN BY SECTOR (mn USD)")
    print("=" * 65)
    instruments = {**parsed["instruments_vm_vn"]}
    instruments["titulos_deuda_VN"] = parsed["bonds_nominal_value"]
    instruments["titulos_deuda_VM"] = parsed["bonds_market_value"]
    rows = [{"instrument": k, **v} for k, v in instruments.items()]
    print(pd.DataFrame(rows).set_index("instrument").to_string())

    print("\n" + "=" * 65)
    print("GRAND TOTALS")
    print("=" * 65)
    vn = parsed["stock_nominal_value"]["end"]["total"]
    vm = parsed["stock_market_value"]["end"]["total"]
    ch = parsed["stock_nominal_value"]["change"]["total"]
    print(f"  Nominal value (VN):  {vn:>10,.0f} mn USD")
    print(f"  Market value  (VM):  {vm:>10,.0f} mn USD")
    print(f"  VM discount:         {vn - vm:>10,.0f} mn USD  ({(1 - vm/vn)*100:.1f}%)")
    print(f"  QoQ change (VN):     {ch:>+10,.0f} mn USD")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python argentina_external_debt.py <path_to_indec_pdf>")
        sys.exit(1)
    main(sys.argv[1])
