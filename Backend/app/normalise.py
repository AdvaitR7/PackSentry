"""
Normalisation and Alias Matching Service (C3 per ADR-0001, ADR-0002).

Performs text normalisation strictly for finding and matching:
1. Unicode NFKC
2. Lowercase (Latin only; Devanagari unaffected)
3. Unify currency markers (₹, Rs., Rs, INR -> rs)
4. Unify multiplication signs (×, X, * -> x)
5. Strip trailing punctuation from tokens (Qty.: -> qty)
6. Collapse whitespace runs to a single space

CRITICAL ARCHITECTURAL INVARIANT (ADR-0002):
Normalised text is used ONLY by matchers and locators.
Raw text is preserved untouched for legal rule adjudication.
"""

from functools import lru_cache
from pathlib import Path
import re
import unicodedata
from typing import Dict, List, Optional, Tuple
import yaml

from lmpc_schema import NormalisedDocument, NormalisedLine, OcrDocument

DEFAULT_ALIAS_PATH = Path(__file__).resolve().parent / "data" / "aliases.yaml"
ALIAS_VERSION = "2026.09.01"


def normalise_text(raw_text: str) -> str:
    """
    Normalises raw text for anchor matching without altering statutory notations.
    Preserves units (e.g. 'gms' is NOT altered to 'g').
    """
    if not raw_text:
        return ""

    # 1. Unicode NFKC
    text = unicodedata.normalize("NFKC", raw_text)

    # 2. Lowercase Latin characters
    text = text.lower()

    # 3. Unify currency markers: ₹, Rs., Rs, INR -> rs (with token spacing)
    text = re.sub(r"(?:₹|\brs\.?|\binr\b)", " rs ", text, flags=re.IGNORECASE)

    # 4. Unify multiplication signs: ×, *, X between words/numbers -> x
    text = re.sub(r"(?<=\S)[×\*](?=\S)", " x ", text)
    text = re.sub(r"\s+[×\*]\s+", " x ", text)

    # 5. Tokenize and strip trailing punctuation from tokens (e.g. 'qty.:' -> 'qty')
    tokens = text.split()
    cleaned_tokens = []
    for tok in tokens:
        # Strip trailing colons, semicolons, commas, dots, dashes
        cleaned = re.sub(r"[:;,.\-_]+$", "", tok)
        # Strip leading colons, dashes
        cleaned = re.sub(r"^[:;\-_]+", "", cleaned)
        if cleaned:
            cleaned_tokens.append(cleaned)

    # 6. Collapse all whitespace runs
    return " ".join(cleaned_tokens)


@lru_cache(maxsize=1)
def load_alias_table(alias_path_str: Optional[str] = None) -> List[Tuple[str, str]]:
    """
    Loads and caches the alias table from YAML.
    Returns a list of (normalized_alias, field_name) sorted by alias length descending
    to ensure longest-alias-first matching.
    """
    path = Path(alias_path_str) if alias_path_str else DEFAULT_ALIAS_PATH
    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    flat_entries: List[Tuple[str, str]] = []
    for field_name, aliases in data.items():
        if not isinstance(aliases, list):
            continue
        for alias in aliases:
            norm_alias = normalise_text(str(alias))
            if norm_alias:
                flat_entries.append((norm_alias, field_name))

    # Longest alias first
    flat_entries.sort(key=lambda x: len(x[0]), reverse=True)
    return flat_entries


def match_aliases(normalized_text: str, alias_entries: Optional[List[Tuple[str, str]]] = None) -> List[str]:
    """
    Matches normalized text against alias entries (longest-alias first).
    Returns list of matched field names (deduplicated, order preserved).
    """
    if not normalized_text:
        return []

    entries = alias_entries if alias_entries is not None else load_alias_table()
    matched_fields: List[str] = []
    padded_text = f" {normalized_text} "

    for norm_alias, field_name in entries:
        pattern = rf"(?:\b|\s){re.escape(norm_alias)}(?:\b|\s)"
        if re.search(pattern, padded_text):
            if field_name not in matched_fields:
                matched_fields.append(field_name)

    return matched_fields


def build_normalised_document(
    ocr_doc: OcrDocument,
    alias_table_path: Optional[str] = None,
) -> NormalisedDocument:
    """
    Constructs a NormalisedDocument from an OcrDocument.
    Preserves raw_text on every line while generating normalized_text and matched_aliases.
    """
    alias_entries = load_alias_table(alias_table_path)
    normalised_lines: List[NormalisedLine] = []

    for img in ocr_doc.images:
        for line in img.lines:
            norm_text = normalise_text(line.raw_text)
            matched = match_aliases(norm_text, alias_entries)
            norm_line = NormalisedLine(
                line_id=line.line_id,
                raw_text=line.raw_text,
                normalized_text=norm_text,
                confidence=line.confidence,
                script=line.script,
                matched_aliases=matched,
                image_id=img.image_id,
                role=img.role,
            )
            normalised_lines.append(norm_line)

    return NormalisedDocument(
        lines=normalised_lines,
        alias_table_version=ALIAS_VERSION,
    )
