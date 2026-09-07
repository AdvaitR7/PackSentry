"""
Authoritative Statutory Citations Repository (ADR-0008).
Every rule evaluation is anchored to an immutable Citation instance containing
the provision, legal instrument, gazette notification (G.S.R.), gazette date,
and primary source URL.
"""

from datetime import date
from lmpc_schema import Citation

LMPC_2011_SOURCE_URL = (
    "https://upload.indiacode.nic.in/showfile?actid=AC_CEN_21_44_00007_201001_1517807327712&filename=lm_packaged_commodities_rules_2011.pdf&type=rule"
)

# Rule 3: Chapter II Scope and exclusions
CIT_RULE_03 = Citation(
    provision="Rule 3(a), 3(b)",
    instrument="Legal Metrology (Packaged Commodities) Rules, 2011",
    gsr="G.S.R. 202(E)",
    gazette_date=date(2011, 3, 7),
    source_url=LMPC_2011_SOURCE_URL,
)

# Rule 4: Root obligation to declare
CIT_RULE_04_BASE = Citation(
    provision="Rule 4",
    instrument="Legal Metrology (Packaged Commodities) Rules, 2011",
    gsr="G.S.R. 202(E)",
    gazette_date=date(2011, 3, 7),
    source_url=LMPC_2011_SOURCE_URL,
)

# Rule 4: Explanation-2 (Bonded warehouses for AEO Tier-2/Tier-3)
CIT_RULE_04_EXPLANATION_2_2026 = Citation(
    provision="Rule 4 Explanation-2",
    instrument="Legal Metrology (Packaged Commodities) Third Amendment Rules, 2026",
    gsr="G.S.R. 418(E)",
    gazette_date=date(2026, 5, 29),
    effective_from=date(2026, 6, 1),
    source_url="https://consumeraffairs.gov.in/sites/default/files/PCR_3rd_29May2026.pdf",
)

# Rule 6(1)(a): Manufacturer, packer or importer identity and complete address
CIT_RULE_06_1_A = Citation(
    provision="Rule 6(1)(a) read with Rule 10",
    instrument="Legal Metrology (Packaged Commodities) Rules, 2011",
    gsr="G.S.R. 202(E)",
    gazette_date=date(2011, 3, 7),
    source_url=LMPC_2011_SOURCE_URL,
)

# Rule 6(1)(b): Common or generic name
CIT_RULE_06_1_B = Citation(
    provision="Rule 6(1)(b)",
    instrument="Legal Metrology (Packaged Commodities) Rules, 2011",
    gsr="G.S.R. 202(E)",
    gazette_date=date(2011, 3, 7),
    source_url=LMPC_2011_SOURCE_URL,
)

# Rule 6(1)(c): Net quantity declaration
CIT_RULE_06_1_C = Citation(
    provision="Rule 6(1)(c)",
    instrument="Legal Metrology (Packaged Commodities) Rules, 2011",
    gsr="G.S.R. 202(E)",
    gazette_date=date(2011, 3, 7),
    source_url=LMPC_2011_SOURCE_URL,
)

# Rule 6(1)(d): Month and year of manufacture, packing or import
CIT_RULE_06_1_D = Citation(
    provision="Rule 6(1)(d)",
    instrument="Legal Metrology (Packaged Commodities) Rules, 2011",
    gsr="G.S.R. 202(E)",
    gazette_date=date(2011, 3, 7),
    source_url=LMPC_2011_SOURCE_URL,
)

# Rule 6(1)(e): Retail sale price (MRP) form
CIT_RULE_06_1_E = Citation(
    provision="Rule 6(1)(e) read with Rule 2(m)",
    instrument="Legal Metrology (Packaged Commodities) Rules, 2011",
    gsr="G.S.R. 202(E)",
    gazette_date=date(2011, 3, 7),
    source_url=LMPC_2011_SOURCE_URL,
)

# Rule 6(1)(f): Commodity dimensions where applicable
CIT_RULE_06_1_F = Citation(
    provision="Rule 6(1)(f)",
    instrument="Legal Metrology (Packaged Commodities) Rules, 2011",
    gsr="G.S.R. 202(E)",
    gazette_date=date(2011, 3, 7),
    source_url=LMPC_2011_SOURCE_URL,
)

# Rule 6(2): Consumer care details
CIT_RULE_06_2 = Citation(
    provision="Rule 6(2)",
    instrument="Legal Metrology (Packaged Commodities) Rules, 2011",
    gsr="G.S.R. 202(E)",
    gazette_date=date(2011, 3, 7),
    source_url=LMPC_2011_SOURCE_URL,
)

# Rule 6 Country of origin (imported goods)
CIT_RULE_06_COUNTRY_OF_ORIGIN = Citation(
    provision="Rule 6(1)(a) import proviso & Rule 6(10)",
    instrument="Legal Metrology (Packaged Commodities) Rules, 2011",
    gsr="G.S.R. 202(E)",
    gazette_date=date(2011, 3, 7),
    source_url=LMPC_2011_SOURCE_URL,
)

# Rule 7: Character height (Deferred)
CIT_RULE_07 = Citation(
    provision="Rule 7",
    instrument="Legal Metrology (Packaged Commodities) Rules, 2011",
    gsr="G.S.R. 202(E)",
    gazette_date=date(2011, 3, 7),
    source_url=LMPC_2011_SOURCE_URL,
)

# Rule 8: Clear space (Deferred)
CIT_RULE_08 = Citation(
    provision="Rule 8",
    instrument="Legal Metrology (Packaged Commodities) Rules, 2011",
    gsr="G.S.R. 202(E)",
    gazette_date=date(2011, 3, 7),
    source_url=LMPC_2011_SOURCE_URL,
)

# Rule 12: Basis of quantity & Fourth Schedule
CIT_RULE_12_BASE = Citation(
    provision="Rule 12(1), 12(2) & Fourth Schedule",
    instrument="Legal Metrology (Packaged Commodities) Rules, 2011",
    gsr="G.S.R. 202(E)",
    gazette_date=date(2011, 3, 7),
    source_url=LMPC_2011_SOURCE_URL,
)

# Rule 12(6): Misleading quantity expressions
CIT_RULE_12_6 = Citation(
    provision="Rule 12(6)",
    instrument="Legal Metrology (Packaged Commodities) Rules, 2011",
    gsr="G.S.R. 202(E)",
    gazette_date=date(2011, 3, 7),
    source_url=LMPC_2011_SOURCE_URL,
)

# Rule 13(2), 13(3): Unit threshold (g vs kg, ml vs l)
CIT_RULE_13_UNIT_THRESHOLD = Citation(
    provision="Rule 13(2), 13(3)",
    instrument="Legal Metrology (Packaged Commodities) Rules, 2011",
    gsr="G.S.R. 202(E)",
    gazette_date=date(2011, 3, 7),
    source_url=LMPC_2011_SOURCE_URL,
)

# Rule 13(4): Prohibition of archaic count units
CIT_RULE_13_NO_ARCHAIC_COUNT = Citation(
    provision="Rule 13(4)",
    instrument="Legal Metrology (Packaged Commodities) Rules, 2011",
    gsr="G.S.R. 202(E)",
    gazette_date=date(2011, 3, 7),
    source_url=LMPC_2011_SOURCE_URL,
)

# Rule 13(5)(i): Mandatory use of SI symbols
CIT_RULE_13_SI_ONLY = Citation(
    provision="Rule 13(5)(i)",
    instrument="Legal Metrology (Packaged Commodities) Rules, 2011",
    gsr="G.S.R. 202(E)",
    gazette_date=date(2011, 3, 7),
    source_url=LMPC_2011_SOURCE_URL,
)

# Rule 13(5)(ii): Number symbol amended in 2021 by G.S.R. 779(E)
CIT_RULE_13_NUMBER_SYMBOL_2021 = Citation(
    provision="Rule 13(5)(ii)",
    instrument="Legal Metrology (Packaged Commodities) Amendment Rules, 2021",
    gsr="G.S.R. 779(E)",
    gazette_date=date(2021, 11, 2),
    effective_from=date(2022, 4, 1),
    source_url="https://egazette.gov.in/WriteReadData/2021/230946.pdf",
)

# Rule 14: Textile and household commodities
CIT_RULE_14 = Citation(
    provision="Rule 14",
    instrument="Legal Metrology (Packaged Commodities) Rules, 2011",
    gsr="G.S.R. 202(E)",
    gazette_date=date(2011, 3, 7),
    source_url=LMPC_2011_SOURCE_URL,
)

# Rule 15: Commodities where price depends on size/weight
CIT_RULE_15 = Citation(
    provision="Rule 15",
    instrument="Legal Metrology (Packaged Commodities) Rules, 2011",
    gsr="G.S.R. 202(E)",
    gazette_date=date(2011, 3, 7),
    source_url=LMPC_2011_SOURCE_URL,
)

# Rule 16: Usable sheets and per-sheet dimensions
CIT_RULE_16 = Citation(
    provision="Rule 16",
    instrument="Legal Metrology (Packaged Commodities) Rules, 2011",
    gsr="G.S.R. 202(E)",
    gazette_date=date(2011, 3, 7),
    source_url=LMPC_2011_SOURCE_URL,
)

# Rule 17: Container-type commodities sold as containers
CIT_RULE_17 = Citation(
    provision="Rule 17",
    instrument="Legal Metrology (Packaged Commodities) Rules, 2011",
    gsr="G.S.R. 202(E)",
    gazette_date=date(2011, 3, 7),
    source_url=LMPC_2011_SOURCE_URL,
)
