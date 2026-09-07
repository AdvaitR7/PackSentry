"""
LMPC Extraction Package (Track D per ADR-0001, ADR-0002, ADR-0005).

Deterministic extraction parsers and DeclarationSet builder:
- D1: parse_quantity
- D2: parse_price
- D3: parse_date
- D4: parse_address_block, parse_consumer_care
- D5: parse_commodity_dimensions, parse_piece_count, parse_usable_sheet_count, parse_sheet_dimensions, parse_per_piece_entries
- D6: resolve_panel_coverage, assign_not_found_reasons
- Pipeline: extract_declarations
"""

from .address import parse_address_block, parse_consumer_care
from .coverage import assign_not_found_reasons, average_ocr_confidence, resolve_panel_coverage
from .date import parse_date
from .dimensions_count import (
    parse_commodity_dimensions,
    parse_per_piece_entries,
    parse_piece_count,
    parse_sheet_dimensions,
    parse_usable_sheet_count,
)
from .pipeline import extract_declarations
from .price import parse_price
from .quantity import parse_quantity

__all__ = [
    "extract_declarations",
    "parse_quantity",
    "parse_price",
    "parse_date",
    "parse_address_block",
    "parse_consumer_care",
    "parse_commodity_dimensions",
    "parse_piece_count",
    "parse_usable_sheet_count",
    "parse_sheet_dimensions",
    "parse_per_piece_entries",
    "resolve_panel_coverage",
    "assign_not_found_reasons",
    "average_ocr_confidence",
]
