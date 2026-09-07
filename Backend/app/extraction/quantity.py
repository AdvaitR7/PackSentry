"""
Deterministic Quantity Parser (D1 per ADR-0001, ADR-0002).

Extracts Net Quantity declarations:
- Magnitude, raw unit, canonical unit, dimension (MASS, VOLUME, LENGTH, AREA, NUMBER)
- Prescribed SI symbol verification (preserves raw 'gms', 'oz', 'Ltr' for Rule 13(5)(i) check)
- Multi-unit packs (e.g. '4 x 100 g = 400 g')
- Statutory qualifiers (e.g. 'when packed')
"""

import re
from typing import Optional, Tuple
from lmpc_schema import DimensionKind, MultiUnitInfo, MultiUnitItem, ParsedQuantity

# Statutory prescribed SI symbols under Rule 13(5)(i) and 2021 G.S.R. 779(E) count units
PRESCRIBED_SYMBOLS = {
    # Mass
    "g", "kg", "mg",
    # Volume
    "l", "ml", "kl",
    # Length
    "m", "cm", "mm", "km",
    # Area
    "m2", "cm2", "mm2", "km2",
    # Number (2021 amendment includes piece, pair, set, unit, number)
    "u", "n", "piece", "pieces", "pair", "pairs", "set", "sets", "unit", "units", "number", "numbers",
}

UNIT_CANONICAL_MAP = {
    # Mass
    "g": ("g", DimensionKind.MASS, True, True),
    "gm": ("g", DimensionKind.MASS, True, False),
    "gms": ("g", DimensionKind.MASS, True, False),
    "gram": ("g", DimensionKind.MASS, True, False),
    "grams": ("g", DimensionKind.MASS, True, False),
    "kg": ("kg", DimensionKind.MASS, True, True),
    "kgs": ("kg", DimensionKind.MASS, True, False),
    "kilo": ("kg", DimensionKind.MASS, True, False),
    "kilogram": ("kg", DimensionKind.MASS, True, False),
    "kilograms": ("kg", DimensionKind.MASS, True, False),
    "mg": ("mg", DimensionKind.MASS, True, True),
    "mgs": ("mg", DimensionKind.MASS, True, False),
    "oz": ("g", DimensionKind.MASS, False, False),
    "lb": ("kg", DimensionKind.MASS, False, False),
    "lbs": ("kg", DimensionKind.MASS, False, False),

    # Volume
    "l": ("l", DimensionKind.VOLUME, True, True),
    "litre": ("l", DimensionKind.VOLUME, True, False),
    "litres": ("l", DimensionKind.VOLUME, True, False),
    "liter": ("l", DimensionKind.VOLUME, True, False),
    "liters": ("l", DimensionKind.VOLUME, True, False),
    "ltr": ("l", DimensionKind.VOLUME, True, False),
    "ltrs": ("l", DimensionKind.VOLUME, True, False),
    "ml": ("ml", DimensionKind.VOLUME, True, True),
    "mls": ("ml", DimensionKind.VOLUME, True, False),
    "milli litre": ("ml", DimensionKind.VOLUME, True, False),
    "millilitre": ("ml", DimensionKind.VOLUME, True, False),
    "millilitres": ("ml", DimensionKind.VOLUME, True, False),
    "kl": ("kl", DimensionKind.VOLUME, True, True),

    # Length
    "m": ("m", DimensionKind.LENGTH, True, True),
    "metre": ("m", DimensionKind.LENGTH, True, False),
    "metres": ("m", DimensionKind.LENGTH, True, False),
    "meter": ("m", DimensionKind.LENGTH, True, False),
    "meters": ("m", DimensionKind.LENGTH, True, False),
    "cm": ("cm", DimensionKind.LENGTH, True, True),
    "cms": ("cm", DimensionKind.LENGTH, True, False),
    "mm": ("mm", DimensionKind.LENGTH, True, True),
    "km": ("km", DimensionKind.LENGTH, True, True),

    # Area
    "m2": ("m2", DimensionKind.AREA, True, True),
    "sq m": ("m2", DimensionKind.AREA, True, False),
    "sq. m": ("m2", DimensionKind.AREA, True, False),
    "sq.m": ("m2", DimensionKind.AREA, True, False),
    "cm2": ("cm2", DimensionKind.AREA, True, True),
    "sq cm": ("cm2", DimensionKind.AREA, True, False),
    "sq. cm": ("cm2", DimensionKind.AREA, True, False),
    "sq.cm": ("cm2", DimensionKind.AREA, True, False),

    # Number (Amended Rule 13(5)(ii))
    "u": ("u", DimensionKind.NUMBER, True, True),
    "n": ("n", DimensionKind.NUMBER, True, True),
    "piece": ("piece", DimensionKind.NUMBER, True, True),
    "pieces": ("piece", DimensionKind.NUMBER, True, True),
    "pc": ("piece", DimensionKind.NUMBER, True, False),
    "pcs": ("piece", DimensionKind.NUMBER, True, False),
    "unit": ("unit", DimensionKind.NUMBER, True, True),
    "units": ("unit", DimensionKind.NUMBER, True, True),
    "pair": ("pair", DimensionKind.NUMBER, True, True),
    "pairs": ("pair", DimensionKind.NUMBER, True, True),
    "set": ("set", DimensionKind.NUMBER, True, True),
    "sets": ("set", DimensionKind.NUMBER, True, True),
    "number": ("number", DimensionKind.NUMBER, True, True),
    "numbers": ("number", DimensionKind.NUMBER, True, True),
}


def parse_quantity(raw_line: str) -> Optional[Tuple[str, ParsedQuantity]]:
    """
    Parses a line containing net quantity.
    Returns (raw_value_substring, ParsedQuantity) if matched, else None.
    """
    if not raw_line:
        return None

    # Check for statutory qualifier
    qualifier = None
    if re.search(r"\bwhen\s+packed\b", raw_line, re.IGNORECASE):
        qualifier = "when packed"

    # 1. Try multi-unit pattern: "4 x 100 g = 400 g" or "4 x 100g"
    multi_pattern = re.compile(
        r"(\d+)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]+)(?:\s*=\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]+))?",
        re.IGNORECASE,
    )
    multi_match = multi_pattern.search(raw_line)
    if multi_match:
        count = int(multi_match.group(1))
        each_mag = float(multi_match.group(2))
        each_raw_unit = multi_match.group(3)
        unit_info = UNIT_CANONICAL_MAP.get(each_raw_unit.lower())
        if unit_info:
            each_canon, dimension, is_si, prescribed = unit_info
            tot_declared = None
            if multi_match.group(4) and multi_match.group(5):
                tot_declared = MultiUnitItem(
                    magnitude=float(multi_match.group(4)),
                    unit_canonical=UNIT_CANONICAL_MAP.get(multi_match.group(5).lower(), (multi_match.group(5).lower(), dimension, True, False))[0]
                )

            multi_info = MultiUnitInfo(
                count=count,
                each=MultiUnitItem(magnitude=each_mag, unit_canonical=each_canon),
                total_declared=tot_declared,
            )

            total_mag = tot_declared.magnitude if tot_declared else (count * each_mag)
            raw_val = multi_match.group(0).strip()
            parsed = ParsedQuantity(
                kind="QUANTITY",
                magnitude=total_mag,
                unit_raw=each_raw_unit,
                unit_canonical=each_canon,
                dimension=dimension,
                is_si=is_si,
                symbol_is_prescribed=prescribed,
                qualifier=qualifier,
                multi_unit=multi_info,
            )
            return raw_val, parsed

    # 2. Standard single-unit pattern
    # Looks for: (optional Net Qty header) (digits) (units)
    # e.g. "Net Qty: 1200 gms", "500 g", "1.2 kg", "20 pieces"
    qty_pattern = re.compile(
        r"(?:(?:net\s+(?:qty|quantity|wt|weight|vol|contents?)|contents?|qty)\s*[:.\-]?\s*)?"
        r"(\d+(?:\.\d+)?)\s*([a-zA-Z²]+)",
        re.IGNORECASE,
    )

    for m in qty_pattern.finditer(raw_line):
        mag_str = m.group(1)
        raw_unit = m.group(2)
        unit_key = raw_unit.lower()

        # Check if unit is recognized
        if unit_key in UNIT_CANONICAL_MAP:
            canon, dimension, is_si, prescribed = UNIT_CANONICAL_MAP[unit_key]
            raw_val = f"{mag_str} {raw_unit}".strip()
            parsed = ParsedQuantity(
                kind="QUANTITY",
                magnitude=float(mag_str),
                unit_raw=raw_unit,
                unit_canonical=canon,
                dimension=dimension,
                is_si=is_si,
                symbol_is_prescribed=prescribed,
                qualifier=qualifier,
                multi_unit=None,
            )
            return raw_val, parsed

    return None
