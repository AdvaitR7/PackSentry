"""
Test Suite: Schema Validation and Fixture Verification
Validates that all LMPC domain models serialize/deserialize cleanly (ADR-0003),
and that all six permanent OCR fixtures parse into OcrDocument (ADR-0010).
"""

import json
from datetime import date, datetime
from pathlib import Path
import pytest

from lmpc_schema import (
    ApplicabilityGate,
    ApplicabilityResult,
    ApplicabilityStatus,
    CaptureContext,
    Citation,
    CommodityCategory,
    ConfidenceSet,
    DateForm,
    DateLabel,
    Declaration,
    DeclarationSet,
    DimensionKind,
    EngineMetadata,
    EvidenceSpan,
    ExtractionMethod,
    ExtractionStatus,
    Field,
    GeoLocation,
    ImportStatus,
    InspectionImageInfo,
    InspectionResponse,
    InspectionStatus,
    InternalVerdict,
    Line,
    NormalisedDocument,
    NormalisedLine,
    NotFoundReason,
    OcrDocument,
    PackageType,
    PanelCoverage,
    PanelRole,
    ParsedAddress,
    ParsedDate,
    ParsedPrice,
    ParsedQuantity,
    PricePrefixForm,
    ProductContext,
    RuleResult,
    SummaryCounts,
    Transform,
    UiBucket,
    Word,
)


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "ocr"


def test_six_ocr_fixtures_exist_and_validate():
    """ADR-0010: Six permanent OCR JSON fixtures must exist and validate into OcrDocument."""
    expected_files = [
        "clean_compliant_pack.json",
        "missing_mrp.json",
        "sheet_product.json",
        "symbol_violation_250gms.json",
        "textile_per_piece.json",
        "unit_violation_1200g.json",
    ]
    for filename in expected_files:
        fixture_path = FIXTURES_DIR / filename
        assert fixture_path.exists(), f"Missing required fixture: {filename}"

        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        doc = OcrDocument.model_validate(data)

        assert doc.ocr_engine == "paddleocr"
        assert len(doc.images) >= 2  # PDP and BACK
        for img in doc.images:
            assert img.role in [PanelRole.PDP, PanelRole.BACK, PanelRole.SIDE]
            assert img.analysis_width > 0
            assert img.original_width > 0
            assert len(img.lines) > 0
            for line in img.lines:
                assert line.raw_text
                assert 0.0 <= line.confidence <= 1.0
                assert len(line.polygon_normalized) == 4


def test_capture_context_roundtrip():
    """Verify CaptureContext serialization and deserialization."""
    ctx = CaptureContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.TEXTILE,
        fourth_schedule_key="READY_MADE_GARMENTS",
        import_status=ImportStatus.DOMESTIC,
        package_capacity_le_5cm3=False,
        all_panels_captured=True,
        inspector_id="lmo_0042",
        captured_at=datetime.fromisoformat("2026-09-04T11:22:03+05:30"),
        geo=GeoLocation(lat=18.5204, lon=73.8567, accuracy_m=12.0),
    )
    raw_json = ctx.model_dump_json()
    ctx2 = CaptureContext.model_validate_json(raw_json)

    assert ctx2.package_type == PackageType.RETAIL
    assert ctx2.commodity_category == CommodityCategory.TEXTILE
    assert ctx2.all_panels_captured is True
    assert ctx2.geo is not None
    assert ctx2.geo.lat == 18.5204


def test_declaration_discriminated_union_roundtrip():
    """Verify parsed union kinds (QUANTITY, PRICE, DATE, ADDRESS) deserialize correctly."""
    # 1. Quantity
    q = ParsedQuantity(
        magnitude=500.0,
        unit_raw="g",
        unit_canonical="g",
        dimension=DimensionKind.MASS,
        is_si=True,
        symbol_is_prescribed=True,
    )
    d_qty = Declaration(
        field=Field.NET_QUANTITY,
        status=ExtractionStatus.FOUND,
        raw_value="500 g",
        parsed=q,
        method=ExtractionMethod.ALIAS_ANCHOR,
        ocr_confidence=0.98,
        extraction_confidence=0.99,
    )
    dumped = d_qty.model_dump_json()
    loaded = Declaration.model_validate_json(dumped)
    assert isinstance(loaded.parsed, ParsedQuantity)
    assert loaded.parsed.magnitude == 500.0
    assert loaded.parsed.is_si is True

    # 2. Price
    p = ParsedPrice(
        amount=249.0,
        currency="INR",
        prefix_raw="MRP Rs.",
        prefix_form=PricePrefixForm.MRP,
        inclusive_phrase_present=True,
        inclusive_phrase_raw="incl. of all taxes",
    )
    d_price = Declaration(
        field=Field.RETAIL_SALE_PRICE,
        status=ExtractionStatus.FOUND,
        raw_value="MRP Rs. 249.00 incl. of all taxes",
        parsed=p,
        method=ExtractionMethod.ALIAS_ANCHOR,
    )
    loaded_price = Declaration.model_validate_json(d_price.model_dump_json())
    assert isinstance(loaded_price.parsed, ParsedPrice)
    assert loaded_price.parsed.amount == 249.0

    # 3. Date
    dt = ParsedDate(
        month=7,
        year=2026,
        form=DateForm.NUMERIC,
        label=DateLabel.MFG,
    )
    d_date = Declaration(
        field=Field.DATE_OF_MANUFACTURE_PACKING_IMPORT,
        status=ExtractionStatus.FOUND,
        raw_value="MFG 07/2026",
        parsed=dt,
        method=ExtractionMethod.ALIAS_ANCHOR,
    )
    loaded_date = Declaration.model_validate_json(d_date.model_dump_json())
    assert isinstance(loaded_date.parsed, ParsedDate)
    assert loaded_date.parsed.month == 7

    # 4. Address
    addr = ParsedAddress(
        lines=["Plot 14, MIDC Bhosari", "Pune, Maharashtra 411026"],
        has_premises_number=True,
        has_street=True,
        has_city=True,
        has_state=True,
        pin_code="411026",
    )
    d_addr = Declaration(
        field=Field.MANUFACTURER_NAME_ADDRESS,
        status=ExtractionStatus.FOUND,
        raw_value="Plot 14, MIDC Bhosari, Pune, Maharashtra 411026",
        parsed=addr,
        method=ExtractionMethod.ALIAS_ANCHOR,
    )
    loaded_addr = Declaration.model_validate_json(d_addr.model_dump_json())
    assert isinstance(loaded_addr.parsed, ParsedAddress)
    assert loaded_addr.parsed.pin_code == "411026"


def test_inspection_response_envelope_roundtrip():
    """Verify full InspectionResponse serialization with rule results and citations."""
    citation = Citation(
        provision="Rule 13(2), 13(3)",
        instrument="Legal Metrology (Packaged Commodities) Rules, 2011",
        gsr="G.S.R. 202(E)",
        gazette_date=date(2011, 3, 7),
        source_url="https://egazette.gov.in/sample",
    )
    rule_res = RuleResult(
        rule_id="R13_UNIT_THRESHOLD",
        provision="Rule 13(2), 13(3)",
        title="Correct unit for declared magnitude",
        verdict=InternalVerdict.NON_COMPLIANT,
        ui_bucket=UiBucket.POTENTIAL_NON_COMPLIANCE,
        reason_code="MAGNITUDE_AT_OR_ABOVE_THRESHOLD_IN_SUBMULTIPLE",
        message="Net quantity declared as 1200 g.",
        observed="1200 g",
        expected="1.2 kg",
        confidence=ConfidenceSet(ocr=0.95, extraction=0.98, rule=1.0),
        applicability=ApplicabilityResult(status=ApplicabilityStatus.APPLICABLE),
        citation=citation,
    )
    resp = InspectionResponse(
        inspection_id="insp_test_001",
        status=InspectionStatus.COMPLETE,
        created_at=datetime.fromisoformat("2026-09-04T11:22:03+05:30"),
        completed_at=datetime.fromisoformat("2026-09-04T11:22:08+05:30"),
        overall=InternalVerdict.NON_COMPLIANT,
        overall_ui_bucket=UiBucket.POTENTIAL_NON_COMPLIANCE,
        summary=SummaryCounts(compliant=5, potential_non_compliance=1),
        context=ProductContext(
            package_type=PackageType.RETAIL,
            commodity_category=CommodityCategory.GENERAL,
            scan_date=date(2026, 9, 4),
            ruleset_as_of=date(2026, 9, 4),
        ),
        rule_results=[rule_res],
        engine=EngineMetadata(
            rule_engine_version="2026.09.01",
            ruleset_as_of=date(2026, 9, 4),
            ocr_engine="paddleocr 2.8.0",
            alias_table_version="2026.09.01",
        ),
    )

    dumped = resp.model_dump_json()
    loaded = InspectionResponse.model_validate_json(dumped)

    assert loaded.inspection_id == "insp_test_001"
    assert loaded.overall == InternalVerdict.NON_COMPLIANT
    assert len(loaded.rule_results) == 1
    assert loaded.rule_results[0].citation.provision == "Rule 13(2), 13(3)"
    assert loaded.rule_results[0].citation.gazette_date == date(2011, 3, 7)
