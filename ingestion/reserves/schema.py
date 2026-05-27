"""BCRA balance sheet schema: known sections, translation tables, normalisation."""

_SECTION_PARENTS = ['ASSETS', 'LIABILITIES', 'NET_EQUITY']

_SECTION_EN = {
    "RESERVAS INTERNACIONALES":                                                    "INTERNATIONAL RESERVES",
    "TITULOS PUBLICOS":                                                            "GOVERNMENT SECURITIES",
    "ADELANTOS TRANSITORIOS AL GOBIERNO NACIONAL":                                 "TRANSITORY ADVANCES TO NATIONAL GOVERNMENT",
    "CREDITOS AL SISTEMA FINANCIERO DEL PAIS":                                     "LOANS TO DOMESTIC FINANCIAL SYSTEM",
    "APORTES A ORGANISMOS INTERNACIONALES POR CUENTA DEL GOBIERNO NACIONAL Y OTROS": "CONTRIBUTIONS TO INTERNATIONAL ORGANIZATIONS (GOVT ACCOUNT)",
    "DERECHOS PROVENIENTES DE OTROS INSTRUMENTOS FINANCIEROS DERIVADOS":           "RIGHTS FROM FINANCIAL DERIVATIVE INSTRUMENTS",
    "DERECHOS POR OPERACIONES DE PASES":                                           "RIGHTS FROM REPO OPERATIONS",
    "OTROS ACTIVOS":                                                               "OTHER ASSETS",
    "BASE MONETARIA":                                                              "MONETARY BASE",
    "MEDIOS DE PAGO EN OTRAS MONEDAS":                                             "MEANS OF PAYMENT IN OTHER CURRENCIES",
    "CUENTAS CORRIENTES EN OTRAS MONEDAS":                                         "CURRENT ACCOUNTS IN OTHER CURRENCIES",
    "DEPOSITOS DEL GOBIERNO NACIONAL Y OTROS":                                     "NATIONAL GOVERNMENT AND OTHER DEPOSITS",
    "OTROS DEPOSITOS":                                                             "OTHER DEPOSITS",
    "ASIGNACIONES DE DEG":                                                         "SDR ALLOCATIONS",
    "OBLIGACIONES CON ORGANISMOS INTERNACIONALES":                                 "OBLIGATIONS WITH INTERNATIONAL ORGANIZATIONS",
    "TITULOS EMITIDOS POR EL B.C.R.A.":                                            "SECURITIES ISSUED BY THE BCRA",
    "CONTRAPARTIDA DE APORTES DEL GOBIERNO NACIONAL A ORGANISMOS INTERNACIONALES": "COUNTERPART OF GOVT CONTRIBUTIONS TO INTL ORGANIZATIONS",
    "OBLIGACIONES PROVENIENTES DE OTROS INSTRUMENTOS FINANCIEROS DERIVADOS":       "OBLIGATIONS FROM FINANCIAL DERIVATIVE INSTRUMENTS",
    "OBLIGACIONES POR OPERACIONES DE PASE":                                        "REPO OBLIGATIONS",
    "DEUDAS POR CONVENIOS MULTILATERALES DE CREDITO":                              "MULTILATERAL CREDIT AGREEMENT DEBTS",
    "OTROS PASIVOS":                                                               "OTHER LIABILITIES",
    "PREVISIONES":                                                                 "PROVISIONS",
}

_ITEM_EN = {
    # International reserves sub-items
    "Oro (Neto de Previsiones)":                               "Gold (Net of Provisions)",
    "Divisas":                                                 "Foreign Currency Deposits",
    "Colocaciones realizables en divisas":                     "Investable Foreign Currency Placements",
    "Convenios Multilaterales de Crédito":               "Multilateral Credit Agreements",
    "Convenios Multilaterales de Cr�ito":                "Multilateral Credit Agreements",
    "Instrumentos Derivados sobre Reservas Internacionales":   "Derivative Instruments on International Reserves",
    # Government securities
    "Títulos Públicos bajo Ley Extranjera":         "Government Securities under Foreign Law",
    "Títulos Públicos bajo Ley Nacional":           "Government Securities under Domestic Law",
    "T�tulos P�blicos bajo Ley Extranjera":         "Government Securities under Foreign Law",
    "T�tulos P�blicos bajo Ley Nacional":           "Government Securities under Domestic Law",
    "Títulos obtenidos por operaciones de pases activos": "Securities from Active Repo Operations",
    "T�tulos obtenidos por operaciones de pases activos": "Securities from Active Repo Operations",
    "PREVISION DESVALORIZACION DE TITULOS PUBLICOS":           "Provision for Devaluation of Govt Securities",
    # Financial system loans
    "Entidades financieras":                                   "Financial Institutions",
    "Previsión por incobrabilidad":                      "Provision for Bad Debts",
    "Previsi�dn por incobrabilidad":                     "Provision for Bad Debts",
    # Monetary base
    "Billetes y Monedas en Circulación":                 "Notes and Coins in Circulation",
    "Billetes y Monedas en Circulaci�n":                 "Notes and Coins in Circulation",
    "Cheques Cancelatorios en pesos en Circulación":     "Peso Cancellation Checks in Circulation",
    "Cheques Cancelatorios en pesos en Circulaci�n":     "Peso Cancellation Checks in Circulation",
    "Cuentas Corrientes en Pesos":                             "Peso Current Accounts",
    # Other currencies
    "Cheques Cancelatorios en otras monedas en Circulación": "Foreign Currency Cancellation Checks in Circulation",
    "Cheques Cancelatorios en otras monedas en Circulaci�n": "Foreign Currency Cancellation Checks in Circulation",
    "Certificados de Depósito para la Inversión":   "Investment Deposit Certificates",
    "Certificados de Dep�ito para la Inversi�n":    "Investment Deposit Certificates",
    # Deposits
    "Otros Depositos":                                         "Other Deposits",
    # SDR allocations
    "Asignaciones de DEG":                                     "SDR Allocations",
    "Contrapartida de Asignaciones de DEG":                    "Counterpart of SDR Allocations",
    # International obligations
    "Obligaciones":                                            "Obligations",
    "Contrapartida del Uso del Tramo de Reservas":             "Counterpart of Reserve Tranche Usage",
    # BCRA securities
    "Letras y Notas emitidas en Moneda Extranjera":            "Notes and Bonds in Foreign Currency",
    "Letras y Notas emitidas en Moneda Nacional":              "Notes and Bonds in Domestic Currency",
}

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


def en(spanish: str) -> str:
    """Return the English label for a Spanish section or item name, or the original if not mapped."""
    return _SECTION_EN.get(spanish) or _ITEM_EN.get(spanish) or spanish
