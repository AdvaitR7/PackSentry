"""
Schema Exporter for lmpc_schema
Emits JSON Schema from Pydantic models for Dart code generation via quicktype (ADR-0003).
"""

import json
from pathlib import Path
from pydantic import BaseModel, Field as PydanticField
from typing import Optional, List, Dict

from .models import (
    CaptureContext,
    DeclarationSet,
    InspectionResponse,
    NormalisedDocument,
    OcrDocument,
    ProductContext,
    RuleResult,
    Declaration,
    Line,
    Word,
    EvidenceSpan,
    Citation,
    ApplicabilityResult,
    ConfidenceSet,
    ImageSlot,
    SummaryCounts,
    InspectionImageInfo,
    EngineMetadata,
    GeoLocation,
    Transform,
    ParsedQuantity,
    ParsedPrice,
    ParsedDate,
    ParsedAddress,
    PanelCoverage,
    NormalisedLine,
)
from .enums import (
    PackageType,
    CommodityCategory,
    ImportStatus,
    PanelRole,
    Field as LmpcField,
    ExtractionStatus,
    ExtractionMethod,
    NotFoundReason,
    DimensionKind,
    DateForm,
    DateLabel,
    PricePrefixForm,
    AddressRoleMarker,
    ApplicabilityStatus,
    ApplicabilityGate,
    InternalVerdict,
    UiBucket,
    InspectionStatus,
)


class UnifiedLmpcBundle(BaseModel):
    """
    Top-level bundle referencing all LMPC domain contracts so that
    code generators (e.g. quicktype) discover every model and enum.
    """
    inspection_response: InspectionResponse
    capture_context: CaptureContext
    ocr_document: OcrDocument
    normalised_document: NormalisedDocument
    declaration_set: DeclarationSet
    product_context: ProductContext
    rule_result: RuleResult


def export_schemas(output_dir: Path | None = None) -> Path:
    if output_dir is None:
        output_dir = Path(__file__).resolve().parent / "dist"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate unified schema with top-level properties referencing all models
    unified_schema = UnifiedLmpcBundle.model_json_schema()

    unified_path = output_dir / "lmpc_schema.json"
    with open(unified_path, "w", encoding="utf-8") as f:
        json.dump(unified_schema, f, indent=2)

    # Also emit specific schemas
    with open(output_dir / "inspection_response.json", "w", encoding="utf-8") as f:
        json.dump(InspectionResponse.model_json_schema(), f, indent=2)

    with open(output_dir / "capture_context.json", "w", encoding="utf-8") as f:
        json.dump(CaptureContext.model_json_schema(), f, indent=2)

    with open(output_dir / "ocr_document.json", "w", encoding="utf-8") as f:
        json.dump(OcrDocument.model_json_schema(), f, indent=2)

    print(f"[lmpc_schema] Schemas successfully exported to {output_dir}")
    return output_dir


if __name__ == "__main__":
    export_schemas()
