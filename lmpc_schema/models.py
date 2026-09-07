"""
LMPC Domain Models
Single-source-of-truth Pydantic v2 schemas for all pipeline stages.
Generates JSON Schema for quicktype Dart code generation and runtime validation.
"""

from datetime import date, datetime
from typing import Annotated, Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field as PydanticField

from .enums import (
    AddressRoleMarker,
    ApplicabilityGate,
    ApplicabilityStatus,
    CommodityCategory,
    DateForm,
    DateLabel,
    DimensionKind,
    ExtractionMethod,
    ExtractionStatus,
    Field as LmpcField,
    ImportStatus,
    InspectionStatus,
    InternalVerdict,
    NotFoundReason,
    PackageType,
    PanelRole,
    PricePrefixForm,
    UiBucket,
)


class BaseSchema(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class GeoLocation(BaseSchema):
    lat: float
    lon: float
    accuracy_m: Optional[float] = None


class CaptureContext(BaseSchema):
    package_type: PackageType = PackageType.UNKNOWN
    commodity_category: CommodityCategory = CommodityCategory.UNKNOWN
    fourth_schedule_key: Optional[str] = None
    import_status: ImportStatus = ImportStatus.UNKNOWN
    package_capacity_le_5cm3: bool = False
    all_panels_captured: bool = False
    inspector_id: str
    captured_at: datetime
    geo: Optional[GeoLocation] = None


class Transform(BaseSchema):
    rotation_deg: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0


class Word(BaseSchema):
    raw_text: str
    confidence: float
    polygon_normalized: List[List[float]]


class Line(BaseSchema):
    line_id: str
    raw_text: str
    confidence: float
    polygon_analysis: Optional[List[List[float]]] = None
    polygon_original: Optional[List[List[float]]] = None
    polygon_normalized: List[List[float]]
    script: str = "LATIN"
    words: List[Word] = PydanticField(default_factory=list)


class ImageSlot(BaseSchema):
    image_id: str
    role: PanelRole
    analysis_width: int
    analysis_height: int
    original_width: int
    original_height: int
    transform: Transform
    lines: List[Line] = PydanticField(default_factory=list)


class OcrDocument(BaseSchema):
    ocr_engine: str
    ocr_version: str
    images: List[ImageSlot]


class NormalisedLine(BaseSchema):
    line_id: str
    raw_text: str
    normalized_text: str
    confidence: float
    script: str = "LATIN"
    matched_aliases: List[str] = PydanticField(default_factory=list)
    image_id: str
    role: PanelRole


class NormalisedDocument(BaseSchema):
    lines: List[NormalisedLine]
    alias_table_version: str


class MultiUnitItem(BaseSchema):
    magnitude: float
    unit_canonical: str


class MultiUnitInfo(BaseSchema):
    count: int
    each: Optional[MultiUnitItem] = None
    total_declared: Optional[MultiUnitItem] = None


class ParsedQuantity(BaseSchema):
    kind: Literal["QUANTITY"] = "QUANTITY"
    magnitude: float
    unit_raw: str
    unit_canonical: str
    dimension: DimensionKind
    is_si: bool
    symbol_is_prescribed: bool
    qualifier: Optional[str] = None
    multi_unit: Optional[MultiUnitInfo] = None


class ParsedPrice(BaseSchema):
    kind: Literal["PRICE"] = "PRICE"
    amount: float
    currency: str = "INR"
    prefix_raw: str
    prefix_form: PricePrefixForm
    inclusive_phrase_present: bool
    inclusive_phrase_raw: Optional[str] = None


class ParsedDate(BaseSchema):
    kind: Literal["DATE"] = "DATE"
    month: int
    year: int
    form: DateForm
    label: DateLabel


class ParsedAddress(BaseSchema):
    kind: Literal["ADDRESS"] = "ADDRESS"
    lines: List[str]
    has_premises_number: bool
    has_street: bool
    has_city: bool
    has_state: bool
    pin_code: Optional[str] = None
    role_marker: Optional[AddressRoleMarker] = None


ParsedUnion = Annotated[
    Union[ParsedQuantity, ParsedPrice, ParsedDate, ParsedAddress],
    PydanticField(discriminator="kind"),
]


class EvidenceSpan(BaseSchema):
    image_id: str
    line_id: str
    polygon_normalized: List[List[float]]
    raw_text: str


class Declaration(BaseSchema):
    field: LmpcField
    status: ExtractionStatus
    raw_value: Optional[str] = None
    parsed: Optional[ParsedUnion] = None
    evidence: List[EvidenceSpan] = PydanticField(default_factory=list)
    ocr_confidence: Optional[float] = None
    extraction_confidence: Optional[float] = None
    method: Optional[ExtractionMethod] = None
    not_found_reason: Optional[NotFoundReason] = None


class PanelCoverage(BaseSchema):
    roles_captured: List[PanelRole]
    all_panels_confirmed: bool


class DeclarationSet(BaseSchema):
    declarations: List[Declaration]
    panel_coverage: PanelCoverage


class NetQuantityInfo(BaseSchema):
    magnitude: float
    unit_canonical: str
    dimension: Optional[DimensionKind] = None


class BaseUnitsInfo(BaseSchema):
    value: float
    unit: str


class AiSuggestion(BaseSchema):
    field: str
    value: str
    confidence: float


class ProductContext(BaseSchema):
    package_type: PackageType
    package_type_source: str = "INSPECTOR"
    commodity_category: CommodityCategory
    commodity_category_source: str = "INSPECTOR"
    commodity_category_confidence: float = 1.0
    fourth_schedule_key: Optional[str] = None
    import_status: ImportStatus = ImportStatus.DOMESTIC
    net_quantity: Optional[NetQuantityInfo] = None
    net_quantity_in_base_units: Optional[BaseUnitsInfo] = None
    is_food_article: bool = False
    is_cosmetic: bool = False
    is_alcoholic: bool = False
    is_certified_seed: bool = False
    package_capacity_le_5cm3: bool = False
    declaration_required_by_other_law: bool = False
    scan_date: date
    ruleset_as_of: date
    ai_suggestions: List[AiSuggestion] = PydanticField(default_factory=list)


class Citation(BaseSchema):
    provision: str
    instrument: str
    gsr: str
    gazette_date: date
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    source_url: str
    source_sha256: str = ""


class ApplicabilityResult(BaseSchema):
    status: ApplicabilityStatus
    gate: Optional[ApplicabilityGate] = None
    reason_code: Optional[str] = None
    message: Optional[str] = None


class ConfidenceSet(BaseSchema):
    ocr: float
    extraction: float
    rule: float = 1.0


class RuleResult(BaseSchema):
    rule_id: str
    provision: str
    title: str
    verdict: InternalVerdict
    ui_bucket: UiBucket
    reason_code: str
    message: str
    observed: Optional[str] = None
    expected: Optional[str] = None
    evidence: List[EvidenceSpan] = PydanticField(default_factory=list)
    confidence: ConfidenceSet
    applicability: ApplicabilityResult
    citation: Citation


class SummaryCounts(BaseSchema):
    compliant: int = 0
    potential_non_compliance: int = 0
    manual_review: int = 0
    insufficient_evidence: int = 0
    not_applicable: int = 0
    not_evaluated: int = 0


class InspectionImageInfo(BaseSchema):
    image_id: str
    role: PanelRole
    original_url: str
    analysis_url: Optional[str] = None
    original_width: int
    original_height: int


class EngineMetadata(BaseSchema):
    rule_engine_version: str
    ruleset_as_of: date
    ocr_engine: str
    alias_table_version: str


class ExcludedRuleEntry(BaseSchema):
    rule_id: str
    reason_code: str


class InspectionResponse(BaseSchema):
    inspection_id: str
    status: InspectionStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    overall: InternalVerdict
    overall_ui_bucket: UiBucket
    summary: SummaryCounts
    context: ProductContext
    images: List[InspectionImageInfo] = PydanticField(default_factory=list)
    declarations: List[Declaration] = PydanticField(default_factory=list)
    rule_results: List[RuleResult] = PydanticField(default_factory=list)
    configured_rule_ids: List[str] = PydanticField(default_factory=list)
    evaluated_rule_ids: List[str] = PydanticField(default_factory=list)
    excluded_rule_ids: List[ExcludedRuleEntry] = PydanticField(default_factory=list)
    engine: EngineMetadata
