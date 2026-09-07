"""
Shared Rule Evaluation Helpers.

Enforces ADR-0002 (raw_text only, never normalized_text) and ADR-0012
(no geometry) by construction: these helpers never read normalized_text
or polygon coordinates, so individual rule modules never need to.
"""

from typing import List, Optional
from lmpc_schema import (
    Declaration,
    DeclarationSet,
    ExtractionMethod,
    ExtractionStatus,
    Field,
    NotFoundReason,
)


def find_declaration(declarations: DeclarationSet, field: Field) -> Optional[Declaration]:
    """Locates the Declaration entry for the given Field. Per §2.4, one entry per field always exists."""
    for d in declarations.declarations:
        if d.field == field:
            return d
    return None


def declaration_found(declaration: Optional[Declaration]) -> bool:
    return declaration is not None and declaration.status == ExtractionStatus.FOUND


def methods_used_for(declarations: List[Optional[Declaration]]) -> List[ExtractionMethod]:
    """Collects the extraction methods of every declaration a rule consulted, for
    the engine's provenance-taint neutralization gate (ADR-0004/0005)."""
    methods = []
    for d in declarations:
        if d is not None and d.method is not None:
            methods.append(d.method)
    return methods


def raw_text_of(declaration: Optional[Declaration]) -> Optional[str]:
    """Returns the untouched raw_value of a declaration. NEVER normalized_text (ADR-0002)."""
    if declaration is None:
        return None
    return declaration.raw_value
