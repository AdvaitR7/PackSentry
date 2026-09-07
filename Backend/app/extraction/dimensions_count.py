"""
Deterministic Dimensions and Count Parser (D5 per ADR-0001, Rules 14, 15, 16, 17).

Extracts:
- Commodity dimensions (e.g. '220 cm x 240 cm', 'Size: 5 m', 'Ø 75 mm')
- Piece count (e.g. '1 Piece', '20 pieces', '1 N', '2 U')
- Usable sheet count (e.g. '100 usable sheets', '100 sheets')
- Sheet dimensions (e.g. '20 cm x 20 cm')
- Multi-item / per-piece entries for sets (e.g. '1 Bed Sheet: 220 cm x 240 cm, 2 Pillow Covers: 45 cm x 70 cm')
"""

import re
from typing import List, Optional, Tuple

DIMENSION_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(cm|m|mm|inches|inch|\"|ft)?\s*[xX×]\s*(\d+(?:\.\d+)?)\s*(cm|m|mm|inches|inch|\"|ft)",
    re.IGNORECASE,
)

SHEET_COUNT_PATTERN = re.compile(
    r"\b(\d+)\s*(?:usable\s+)?sheets?\b",
    re.IGNORECASE,
)

PIECE_COUNT_PATTERN = re.compile(
    r"\b(\d+)\s*(?:pieces?|pcs?|units?|pairs?|sets?|n|u)\b",
    re.IGNORECASE,
)


def parse_commodity_dimensions(raw_line: str) -> Optional[Tuple[str, str]]:
    """
    Extracts finished commodity dimensions (e.g. '220 cm x 240 cm' or 'Size: 5 m').
    Returns (raw_value, canonical_dimension_string) if found, else None.
    """
    if not raw_line:
        return None

    m = DIMENSION_PATTERN.search(raw_line)
    if m:
        w = m.group(1)
        u1 = m.group(2) or m.group(4)
        h = m.group(3)
        u2 = m.group(4)
        raw_val = m.group(0).strip()
        formatted = f"{w} {u1} x {h} {u2}".strip()
        return raw_val, formatted

    # Check for single dimension with size keyword, e.g. "Size: 5 m"
    m_single = re.search(r"\b(?:size|length|width|height|diameter|ø)\s*[:.\-]?\s*(\d+(?:\.\d+)?\s*(?:cm|m|mm))\b", raw_line, re.IGNORECASE)
    if m_single:
        return m_single.group(0).strip(), m_single.group(1).strip()

    return None


def parse_usable_sheet_count(raw_line: str) -> Optional[Tuple[str, int]]:
    """Extracts usable sheet count (e.g. '100 sheets')."""
    if not raw_line:
        return None

    m = SHEET_COUNT_PATTERN.search(raw_line)
    if m:
        return m.group(0).strip(), int(m.group(1))

    return None


def parse_sheet_dimensions(raw_line: str) -> Optional[Tuple[str, str]]:
    """Extracts per-sheet dimensions (e.g. '20 cm x 20 cm')."""
    if not raw_line:
        return None

    # Usually appears near sheet keyword or on sheet products
    if re.search(r"sheet|tissue|napkin|wipe|foil", raw_line, re.IGNORECASE) or DIMENSION_PATTERN.search(raw_line):
        dim = parse_commodity_dimensions(raw_line)
        if dim:
            return dim

    return None


def parse_piece_count(raw_line: str) -> Optional[Tuple[str, int]]:
    """Extracts piece count (e.g. '20 pieces', '1 Piece', '2 N')."""
    if not raw_line:
        return None

    m = PIECE_COUNT_PATTERN.search(raw_line)
    if m:
        return m.group(0).strip(), int(m.group(1))

    return None


def parse_per_piece_entries(lines: List[str]) -> Optional[Tuple[str, List[str]]]:
    """
    Extracts multi-item per-piece entries for textile or set packs.
    e.g. '1 Bed Sheet: 220 cm x 240 cm, 2 Pillow Covers: 45 cm x 70 cm'
    """
    entries: List[str] = []
    for line in lines:
        has_dims = DIMENSION_PATTERN.search(line) is not None
        # Starts with a digit followed by an item name or contains count word
        has_count_or_item = (
            re.search(r"^\s*\d+\s+[a-zA-Z]+", line) is not None
            or PIECE_COUNT_PATTERN.search(line) is not None
        )
        if has_dims and has_count_or_item:
            entries.append(line.strip())

    if entries:
        return " | ".join(entries), entries

    return None
