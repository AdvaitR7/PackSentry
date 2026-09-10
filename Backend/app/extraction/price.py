"""
Deterministic Price Parser (D2 per ADR-0001, Rule 6(1)(e)).

Extracts Retail Sale Price (MRP) declarations:
- Amount and currency (INR)
- Statutory prefix form: MRP vs MAXIMUM_RETAIL_PRICE vs OTHER
- Mandatory statutory inclusive phrase: 'incl. of all taxes' / 'inclusive of all taxes'
"""

import re
from typing import Optional, Tuple
from lmpc_schema import ParsedPrice, PricePrefixForm

PRICE_KEYWORD_PATTERN = re.compile(
    r"\b(?:m\.?\s*r\.?\s*p\.?|maximum\s+retail\s+price|max\.?\s+retail\s+price|retail\s+(?:sale\s+)?price|rsp)\b|अधिकतम\s+खुदरा\s+मूल्य|खुदरा\s+मूल्य|मूल्य",
    re.IGNORECASE,
)
CURRENCY_PATTERN = re.compile(r"(?:₹|\brs\.?|\binr\b|रु\.?|रुपये)", re.IGNORECASE)


def parse_price(raw_line: str) -> Optional[Tuple[str, ParsedPrice]]:
    """
    Parses a line containing Retail Sale Price (MRP).
    Requires the presence of either an explicit MRP/RSP keyword or an explicit currency marker (Rs, ₹).
    Returns (raw_value_substring, ParsedPrice) if matched, else None.
    """
    if not raw_line:
        return None

    has_mrp_kw = PRICE_KEYWORD_PATTERN.search(raw_line) is not None
    has_currency = CURRENCY_PATTERN.search(raw_line) is not None

    # Must have either price keyword or currency indicator to be a price declaration
    if not (has_mrp_kw or has_currency):
        return None

    # Ignore pure date or net quantity lines unless they explicitly carry MRP/price keyword
    lower = raw_line.lower()
    if not has_mrp_kw and any(w in lower for w in ["net qty", "net weight", "net quantity", "pkd:", "mfg:"]):
        return None

    # Check for inclusive phrase
    inclusive_present = False
    inclusive_raw = None
    incl_match = re.search(
        r"(?:[\(\[\{]?)?\s*(incl(?:usive|uding)?\.?\s*(?:of)?\s*(?:all)?\s*taxes?|all\s+taxes?\s*(?:incl(?:uded|usive|uding)?)?|taxes?\s+incl(?:uded|usive|uding)?|सभी\s+कर(?:ों)?\s*सहित)\s*(?:[\)\]\}]?)?",
        raw_line,
        re.IGNORECASE,
    )
    if incl_match:
        inclusive_present = True
        inclusive_raw = incl_match.group(1).strip()

    # Determine prefix form
    prefix_form = PricePrefixForm.OTHER
    prefix_raw = ""

    if re.search(r"\bmaximum\s+retail\s+price\b|\bmax\.?\s+retail\s+price\b|अधिकतम\s+खुदरा\s+मूल्य", raw_line, re.IGNORECASE):
        prefix_form = PricePrefixForm.MAXIMUM_RETAIL_PRICE
        p_match = re.search(r"\b(?:maximum|max\.?)\s+retail\s+price\b|अधिकतम\s+खुदरा\s+मूल्य", raw_line, re.IGNORECASE)
        prefix_raw = p_match.group(0) if p_match else "Maximum Retail Price"
    elif re.search(r"\bm\.?\s*r\.?\s*p\.?\b|खुदरा\s+मूल्य|\brsp\b", raw_line, re.IGNORECASE):
        prefix_form = PricePrefixForm.MRP
        p_match = re.search(r"\bm\.?\s*r\.?\s*p\.?(?:\s*(?:rs\.?|₹|inr|रु\.?))?|खुदरा\s+मूल्य|\brsp\b", raw_line, re.IGNORECASE)
        prefix_raw = p_match.group(0) if p_match else "MRP"
    elif re.search(r"\bprice\b|₹|\brs\.?|रु\.?", raw_line, re.IGNORECASE):
        prefix_form = PricePrefixForm.OTHER
        p_match = re.search(r"\bprice\b|₹|\brs\.?|रु\.?", raw_line, re.IGNORECASE)
        prefix_raw = p_match.group(0) if p_match else "Price"

    # Extract price amount adjacent to currency or price keyword
    # Matches: Rs. 185.00, ₹249, 185/-, Rs 1,250.00, MRP 185, M.R.P. 250
    price_pattern = re.compile(
        r"(?:(?:m\.?\s*r\.?\s*p\.?|(?:max(?:imum)?\s+)?retail\s+(?:sale\s+)?price|price)\s*[:.\-]?\s*)?"
        r"(?:(?:₹|\brs\.?|\binr\b|रु\.?)\s*)?"
        r"([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)\s*(?:/-)?",
        re.IGNORECASE,
    )

    amount: Optional[float] = None
    for m in price_pattern.finditer(raw_line):
        amt_str = m.group(1)
        if amt_str:
            clean_amt = amt_str.replace(",", "")
            try:
                val = float(clean_amt)
                # Ensure the matched amount is preceded by keyword or currency in the span
                span_text = m.group(0)
                if PRICE_KEYWORD_PATTERN.search(span_text) or CURRENCY_PATTERN.search(span_text) or has_mrp_kw:
                    if val > 0:
                        amount = val
                        break
            except ValueError:
                continue

    if amount is not None:
        raw_val = raw_line.strip()
        parsed = ParsedPrice(
            kind="PRICE",
            amount=amount,
            currency="INR",
            prefix_raw=prefix_raw if prefix_raw else "Price",
            prefix_form=prefix_form,
            inclusive_phrase_present=inclusive_present,
            inclusive_phrase_raw=inclusive_raw,
        )
        return raw_val, parsed

    return None
