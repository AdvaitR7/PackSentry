"""
Deterministic Address and Consumer Care Extractor (D4 per ADR-0001, Rule 6(1)(a), Rule 6(2), Rule 10).

Evaluates Rule 10's statutory definition of 'complete address':
- Premises number (plot, flat, shop, door, unit, or initial digits)
- Street / Area / Sector / Estate name
- City and State OR 6-digit PIN code
- Role marker: MANUFACTURED BY, PACKED BY, MARKETED BY, IMPORTED BY

Consumer Care extraction:
- Telephone / Helpline number
- Email address
- Postal contact
"""

import re
from typing import List, Optional, Tuple
from lmpc_schema import AddressRoleMarker, ParsedAddress

PIN_CODE_PATTERN = re.compile(r"\b([1-9][0-9]{5})\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(r"(?:tel|phone|toll\s*free|call|contact|ph)?[:.\s\-]*(\+?91[\s\-]?)?(?:\d{3,5}[\s\-]?\d{6,8}|\d{10,11}|1800[\s\-]?\d{3}[\s\-]?\d{3,4})", re.IGNORECASE)

INDIAN_STATES = {
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
    "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka",
    "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram",
    "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu",
    "telangana", "tripura", "uttar pradesh", "uttarakhand", "west bengal",
    "delhi", "jammu & kashmir", "jammu and kashmir", "ladakh", "puducherry",
    "chandigarh", "daman & diu", "dadra & nagar haveli",
}

STREET_KEYWORDS = {
    "street", "road", "marg", "lane", "rasta", "sector", "nagar", "area",
    "estate", "industrial area", "midc", "gidc", "sidco", "riico", "phase",
    "highway", "avenue", "path", "gali", "bazaar", "colony", "enclave", "park",
}

PREMISES_PATTERNS = [
    re.compile(r"\b(?:plot|flat|shop|door|unit|block|shed|gala|survey|khasra)\s*(?:no\.?|number)?\s*[0-9A-Za-z\-/]+", re.IGNORECASE),
    re.compile(r"\bno\.?\s*[0-9A-Za-z\-/]+", re.IGNORECASE),
    re.compile(r"^[0-9A-Za-z\-/]+,\s+", re.IGNORECASE),
    re.compile(r"\b\d+[\s,]+(?:industrial|industrial\s+area|midc|gidc|street|road|nagar|sector)", re.IGNORECASE),
]

ROLE_MARKER_MAP = [
    (re.compile(r"\bmanufactured\s+by\b|\bmfd\.?\s+by\b", re.IGNORECASE), AddressRoleMarker.MANUFACTURED_BY),
    (re.compile(r"\bpacked\s+by\b|\bpkd\.?\s+by\b", re.IGNORECASE), AddressRoleMarker.PACKED_BY),
    (re.compile(r"\bmarketed\s+by\b|\bmkd\.?\s+by\b", re.IGNORECASE), AddressRoleMarker.MARKETED_BY),
    (re.compile(r"\bimported\s+by\b|\bimp\.?\s+by\b", re.IGNORECASE), AddressRoleMarker.IMPORTED_BY),
]


def detect_role_marker(text: str) -> Optional[AddressRoleMarker]:
    for pattern, marker in ROLE_MARKER_MAP:
        if pattern.search(text):
            return marker
    return None


def parse_address_block(lines: List[str]) -> Optional[Tuple[str, ParsedAddress]]:
    """
    Parses a block of text lines into a ParsedAddress checking Rule 10 complete address criteria.
    """
    if not lines:
        return None

    full_text = " ".join(lines).strip()
    if not full_text:
        return None

    role = detect_role_marker(full_text)

    # Detect PIN code
    pin_match = PIN_CODE_PATTERN.search(full_text)
    pin_code = pin_match.group(1) if pin_match else None

    # Detect premises number
    has_premises = False
    for p in PREMISES_PATTERNS:
        if p.search(full_text):
            has_premises = True
            break

    # Detect street / industrial area
    lower_text = full_text.lower()
    has_street = any(keyword in lower_text for keyword in STREET_KEYWORDS)

    # Detect State
    has_state = any(state in lower_text for state in INDIAN_STATES)

    # Detect City (look for common word preceding state or PIN code)
    has_city = False
    # If state or pin code is present and there are commas separating segments, city is likely present
    segments = [s.strip() for s in full_text.split(",") if s.strip()]
    if len(segments) >= 3:
        has_city = True
    elif has_state or pin_code:
        has_city = True

    parsed = ParsedAddress(
        kind="ADDRESS",
        lines=lines,
        has_premises_number=has_premises,
        has_street=has_street,
        has_city=has_city,
        has_state=has_state,
        pin_code=pin_code,
        role_marker=role,
    )
    return full_text, parsed


def parse_consumer_care(raw_line: str) -> Optional[Tuple[str, str]]:
    """
    Extracts consumer care details from a line (telephone, email, address).
    Returns (raw_value, description) if matched, else None.
    """
    if not raw_line:
        return None

    has_email = EMAIL_PATTERN.search(raw_line) is not None
    has_phone = PHONE_PATTERN.search(raw_line) is not None
    has_keyword = re.search(r"consumer\s+care|customer\s+care|helpline|care@", raw_line, re.IGNORECASE) is not None

    if has_keyword or (has_email and has_phone):
        return raw_line.strip(), raw_line.strip()

    return None
