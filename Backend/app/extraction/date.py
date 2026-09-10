"""
Deterministic Date Parser (D3 per ADR-0001, Rule 6(1)(d)).

Extracts manufacture/packing/import date declarations:
- Month (1-12), Year (4-digit)
- Form: NUMERIC ('07/2026'), WORDS ('July 2026'), MIXED
- Label: MFG, PKD, IMPORTED, UNLABELLED
- Supports Devanagari month names.
"""

import re
from typing import Optional, Tuple
from lmpc_schema import DateForm, DateLabel, ParsedDate

MONTH_WORDS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

DEVANAGARI_MONTHS = {
    "जनवरी": 1, "फरवरी": 2, "मार्च": 3, "अप्रैल": 4,
    "मई": 5, "जून": 6, "जुलाई": 7, "अगस्त": 8,
    "सितंबर": 9, "अक्टूबर": 10, "नवंबर": 11, "दिसंबर": 12,
}

LABEL_PATTERNS = [
    (re.compile(r"\bmf[gd]\b|\bmanufactur|उत्पादक?|निर्माण", re.IGNORECASE), DateLabel.MFG),
    (re.compile(r"\bpkd\b|\bpack(?:ed|ing)?\b|पैकिंग", re.IGNORECASE), DateLabel.PKD),
    (re.compile(r"\bimport(?:ed)?\b|आयात", re.IGNORECASE), DateLabel.IMPORTED),
]


def _detect_label(raw_line: str) -> DateLabel:
    for pattern, label in LABEL_PATTERNS:
        if pattern.search(raw_line):
            return label
    return DateLabel.UNLABELLED


def _normalize_year(year_val: int) -> int:
    if year_val < 100:
        return 2000 + year_val
    return year_val


def parse_date(raw_line: str) -> Optional[Tuple[str, ParsedDate]]:
    """
    Parses a line containing a manufacture/packing/import date.
    Returns (raw_value_substring, ParsedDate) if matched, else None.
    """
    if not raw_line:
        return None

    # Exclude standalone expiry / best before / use by declarations that lack manufacture or packing indicators
    if (
        re.search(r"\b(?:exp(?:iry)?|use\s+by|use\s+before|best\s+before)\b", raw_line, re.IGNORECASE)
        and not re.search(r"\bmf[gd]\b|\bmanufactur|\bpkd\b|\bpack(?:ed|ing)?\b|उत्पाद|पैकिंग", raw_line, re.IGNORECASE)
    ):
        return None

    label = _detect_label(raw_line)

    # 0. Numeric DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    dd_mm_yyyy_pattern = re.compile(
        r"\b(?:0?[1-9]|[12][0-9]|3[01])\s*[/.\-]\s*(0?[1-9]|1[0-2])\s*[/.\-]\s*((?:19|20)\d{2}|\d{2})\b"
    )
    m0 = dd_mm_yyyy_pattern.search(raw_line)
    if m0:
        month = int(m0.group(1))
        year = _normalize_year(int(m0.group(2)))
        return m0.group(0).strip(), ParsedDate(
            kind="DATE", month=month, year=year, form=DateForm.NUMERIC, label=label
        )

    # 1. Numeric MM/YYYY or MM.YYYY or MM-YYYY
    numeric_pattern = re.compile(r"\b(0?[1-9]|1[0-2])\s*[/.\-]\s*((?:19|20)\d{2}|\d{2})\b")
    m = numeric_pattern.search(raw_line)
    if m:
        month = int(m.group(1))
        year = _normalize_year(int(m.group(2)))
        return m.group(0).strip(), ParsedDate(
            kind="DATE", month=month, year=year, form=DateForm.NUMERIC, label=label
        )

    # 2. English word month + year: "July 2026", "Jul-2026", "July, 2026"
    word_pattern = re.compile(
        r"\b(" + "|".join(sorted(MONTH_WORDS.keys(), key=len, reverse=True)) + r")\.?,?\s*((?:19|20)\d{2})\b",
        re.IGNORECASE,
    )
    m2 = word_pattern.search(raw_line)
    if m2:
        month = MONTH_WORDS[m2.group(1).lower()]
        year = int(m2.group(2))
        return m2.group(0).strip(), ParsedDate(
            kind="DATE", month=month, year=year, form=DateForm.WORDS, label=label
        )

    # 3. Devanagari month + year
    devanagari_pattern = re.compile(
        r"(" + "|".join(DEVANAGARI_MONTHS.keys()) + r")\s*((?:19|20)\d{2})"
    )
    m3 = devanagari_pattern.search(raw_line)
    if m3:
        month = DEVANAGARI_MONTHS[m3.group(1)]
        year = int(m3.group(2))
        return m3.group(0).strip(), ParsedDate(
            kind="DATE", month=month, year=year, form=DateForm.WORDS, label=label
        )

    # 4. Mixed: numeric month + word-ish context, or DD Month YYYY
    mixed_pattern = re.compile(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+("
        + "|".join(sorted(MONTH_WORDS.keys(), key=len, reverse=True))
        + r")\.?,?\s*((?:19|20)\d{2})\b",
        re.IGNORECASE,
    )
    m4 = mixed_pattern.search(raw_line)
    if m4:
        month = MONTH_WORDS[m4.group(2).lower()]
        year = int(m4.group(3))
        return m4.group(0).strip(), ParsedDate(
            kind="DATE", month=month, year=year, form=DateForm.MIXED, label=label
        )

    return None
