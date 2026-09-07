"""
Panel Coverage Resolver (D6 per ADR-0001, ADR-0005).

Sets not_found_reason on every NOT_FOUND declaration using roles_captured and
all_panels_confirmed. This is what makes the MISSING_DECLARATION / NOT_CAPTURED
distinction real rather than aspirational (ADR-0005 absence-evidence gate).

Priority order for a NOT_FOUND field:
1. If not all_panels_confirmed -> PANEL_NOT_CAPTURED (inspector has not confirmed
   full coverage, so absence cannot be trusted as a real violation).
2. If OCR confidence across captured panels was below the legibility threshold ->
   BELOW_OCR_THRESHOLD (the panel was photographed but text was not legible).
3. Otherwise -> NO_MATCH_IN_CAPTURED_PANELS (a genuine absence; the rule engine's
   own absence-evidence gate still requires all_panels_confirmed=True to accuse).
"""

from typing import List
from lmpc_schema import (
    Declaration,
    ExtractionStatus,
    NotFoundReason,
    OcrDocument,
    PanelCoverage,
    PanelRole,
)

# Below this average OCR confidence, an absence is presumed to be a legibility
# problem rather than a genuine absence of the declaration.
OCR_LEGIBILITY_THRESHOLD = 0.5


def resolve_panel_coverage(ocr_doc: OcrDocument, all_panels_captured: bool) -> PanelCoverage:
    """Builds PanelCoverage from the roles actually present in the OcrDocument."""
    seen_roles: List[PanelRole] = []
    for img in ocr_doc.images:
        if img.role not in seen_roles:
            seen_roles.append(img.role)

    return PanelCoverage(
        roles_captured=seen_roles,
        all_panels_confirmed=all_panels_captured,
    )


def average_ocr_confidence(ocr_doc: OcrDocument) -> float:
    """Computes the mean line confidence across all captured panels."""
    confidences = [line.confidence for img in ocr_doc.images for line in img.lines]
    if not confidences:
        return 0.0
    return sum(confidences) / len(confidences)


def assign_not_found_reasons(
    declarations: List[Declaration],
    panel_coverage: PanelCoverage,
    avg_confidence: float,
) -> List[Declaration]:
    """
    Assigns not_found_reason to every NOT_FOUND declaration in-place (returns the
    same list for convenience). FOUND declarations are untouched.
    """
    for decl in declarations:
        if decl.status != ExtractionStatus.NOT_FOUND:
            continue

        if not panel_coverage.all_panels_confirmed:
            decl.not_found_reason = NotFoundReason.PANEL_NOT_CAPTURED
        elif avg_confidence < OCR_LEGIBILITY_THRESHOLD:
            decl.not_found_reason = NotFoundReason.BELOW_OCR_THRESHOLD
        else:
            decl.not_found_reason = NotFoundReason.NO_MATCH_IN_CAPTURED_PANELS

    return declarations
