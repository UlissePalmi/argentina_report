### Primary sources (always use these first)

**INDEC — National Statistics Institute**
- Base URL: `https://apis.datos.gob.ar/series/api/series/`
- FTP for Excel files: `https://www.indec.gob.ar/ftp/cuadros/economia/`
- Key series:
```python
INDEC_SERIES = {
    # Wages
    "nominal_wage_private": "149.1_SOR_PRIADO_OCTU_0_25",
    
    # CPI
    "cpi_national": "148.3_INIVELNAL_DICI_M_26",
    
    # EMAE (monthly activity)
    "emae_total": "143.3_NO_PR_2004_A_21",
    "emae_agriculture": "143.3_AGR_PR_2004_A_21",
    "emae_mining": "143.3_MIN_PR_2004_A_21", 
    "emae_manufacturing": "143.3_IND_PR_2004_A_21",
    "emae_construction": "143.3_CON_PR_2004_A_21",
    "emae_commerce": "143.3_COM_PR_2004_A_21",
    "emae_finance": "143.3_INT_PR_2004_A_21",
    
    # GDP (quarterly) — fetch from FTP Excel
    "gdp_excel": "sh_oferta_demanda_03_26.xls",
    
    # IPI Manufacturing
    "ipi_total": "309.1_PRODUCCIONNAL_0_M_30",
    
    # ISAC Construction proxy
    "isac_cement": "33.4_ISAC_CEMENAND_0_0_21_24",
    
    # Trade
    "exports_monthly": "trade_exports",
    "imports_monthly": "trade_imports",
}
```

**BCRA — Central Bank**
- Base URL: `https://api.bcra.gob.ar/estadisticas/v2.0/`
- Key series:
```python
BCRA_SERIES = {
    # Credit by type
    "consumer_credit": "91.1_PEFPGR_0_0_60",
    "personal_loans": "91.1_DETALLE_PRLES_0_0_52",
    "credit_cards": "91.1_DETALLE_PRTAS_0_0_60",
    "mortgages": "91.1_DETALLE_PRPOT_0_0_53",
    "auto_loans": "91.1_DETALLE_PREND_0_0_53",
    "overdrafts": "91.1_DETALLE_PRTOS_0_0_55",
    "commercial_paper": "91.1_DETALLE_PRTOS_0_0_56",
    "total_credit": "174.1_PTAMOS_O_0_0_29",
    
    # Deposits
    "fixed_term_deposits": "334.2_SIST_FINANIJO__54",
    
    # Reserves (gross — net requires calculation)
    "gross_reserves": "bcra_reservas",
}
```

**Secretaría de Energía**
- Oil production: `363.3_PRODUCCIONUDO__28`
- Gas production: `364.3_PRODUCCIoNRAL__25`

**Ministry of Labor (SIPA)**
- Formal private employment by sector
- Search: `apis.datos.gob.ar/series/api/series/search/?q=empleo+registrado+privado`

**IMF API**
- Base URL: `http://dataservices.imf.org/REST/SDMX_JSON.svc/`
- Current account, net reserves definition, debt

### GDP data — special handling
GDP quarterly data comes from INDEC FTP Excel files, not the API.
Always download from:
https://www.indec.gob.ar/ftp/cuadros/economia/sh_oferta_demanda_03_26.xls

This file contains:
- Cuadro 1: Constant price levels
- Cuadro 2: Real YoY growth rates ← PRIMARY for growth analysis
- Cuadro 3: Constant price shares ← SECONDARY, label clearly
- Cuadro 6: FBCF sub-components constant prices
- Cuadro 7: FBCF sub-component growth rates
- Cuadro 8: Nominal (current price) levels ← PRIMARY for structure
- Cuadro 11: Nominal shares ← PRIMARY for composition
- Cuadro 12: Production side by sector
- Cuadro 14: FBCF nominal current prices

**When the file URL changes** (INDEC updates it each quarter),
search for the latest at:
`https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-9-47`

---