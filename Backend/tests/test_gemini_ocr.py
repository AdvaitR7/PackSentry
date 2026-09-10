"""
Unit tests for GeminiFlashOcrAdapter and router failover integration.
Verifies parsing of Gemini 2.5 Flash structured regions JSON responses, coordinate mapping,
verbatim text preservation, and ensuring Qwen/PaddleOCR are not called when Gemini is configured.
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, patch
import pytest
import httpx
from lmpc_schema import CaptureContext, CommodityCategory, DimensionKind, ExtractionStatus, Field, ImportStatus, OcrDocument, PackageType, PanelRole, Transform
from app.extraction.pipeline import extract_declarations
from app.normalise import build_normalised_document
from app.ocr.gemini_engine import GeminiFlashOcrAdapter, STRUCTURED_RESPONSE_SCHEMA
from app.ocr.protocol import OcrEngineError
from app.ocr.router import OcrRouter


@pytest.mark.asyncio
async def test_gemini_ocr_missing_api_key():
    adapter = GeminiFlashOcrAdapter(api_key="")
    assert await adapter.is_available() is False

    with pytest.raises(OcrEngineError, match="GEMINI_API_KEY environment variable is not configured"):
        await adapter.recognize_panel(
            analysis_bytes=b"fake_image_bytes",
            role=PanelRole.PDP,
            image_id="img_test_pdp",
            analysis_width=1000,
            analysis_height=1000,
            original_width=2000,
            original_height=2000,
            transform=Transform(),
        )


@pytest.mark.asyncio
async def test_gemini_ocr_success_regions_schema_parsing():
    adapter = GeminiFlashOcrAdapter(api_key="test_mock_key")
    assert await adapter.is_available() is True

    gemini_api_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "product_summary": {
                                    "brand": "Britannia",
                                    "product_name": "Good Day",
                                    "variant": "Butter",
                                    "category": "food",
                                },
                                "regions": [
                                    {
                                        "field_type": "net_quantity",
                                        "label": "Net Qty",
                                        "observed_text": "Net Qty: 1200 gms",
                                        "normalized_value": "1200 g",
                                        "source_image_index": 0,
                                        "bbox_2d": [100, 200, 150, 600],
                                        "legibility": "clear",
                                    },
                                    {
                                        "field_type": "mrp_price",
                                        "label": "MRP",
                                        "observed_text": "MRP Rs. 250.00 (incl. of all taxes)",
                                        "normalized_value": "250.00 INR",
                                        "source_image_index": 0,
                                        "bbox_2d": [200, 200, 250, 800],
                                        "legibility": "clear",
                                    },
                                    {
                                        "field_type": "manufacturer",
                                        "label": "Mfd By",
                                        "observed_text": "Mfd By: ABC Foods Ltd, Delhi - 110001",
                                        "normalized_value": None,
                                        "source_image_index": 0,
                                        "bbox_2d": [300, 200, 350, 850],
                                        "legibility": "clear",
                                    },
                                ],
                                "extraction_notes": ["Clear print on front panel"],
                            })
                        }
                    ],
                    "role": "model",
                },
                "finishReason": "STOP",
                "index": 0,
            }
        ]
    }

    mock_response = httpx.Response(status_code=200, json=gemini_api_response)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        slot = await adapter.recognize_panel(
            analysis_bytes=b"fake_image_bytes",
            role=PanelRole.PDP,
            image_id="img_test_pdp",
            analysis_width=1000,
            analysis_height=1000,
            original_width=2000,
            original_height=2000,
            transform=Transform(scale_x=0.5, scale_y=0.5),
        )

        assert slot.image_id == "img_test_pdp"
        assert len(slot.lines) == 3

        # Line 1 checks: Verbatim raw text preservation
        line1 = slot.lines[0]
        assert line1.raw_text == "Net Qty: 1200 gms"
        assert line1.confidence == 0.95

        # Spatial coordinate checks
        # box_2d: [100, 200, 150, 600] -> xmin=200, ymin=100, xmax=600, ymax=150
        assert line1.polygon_analysis == [
            [200.0, 100.0],
            [600.0, 100.0],
            [600.0, 150.0],
            [200.0, 150.0],
        ]
        # Normalized coordinates (0.0 to 1.0)
        assert line1.polygon_normalized[0] == [0.2, 0.1]
        assert line1.polygon_normalized[2] == [0.6, 0.15]

        # Original coordinates mapped with scale_x=0.5, scale_y=0.5 -> 2x pixels
        assert line1.polygon_original[0] == [400.0, 200.0]
        assert line1.polygon_original[2] == [1200.0, 300.0]

        # Word decomposition: 'Net', 'Qty:', '1200', 'gms'
        assert len(line1.words) == 4
        assert [w.raw_text for w in line1.words] == ["Net", "Qty:", "1200", "gms"]


def test_gemini_ocr_does_not_invent_missing_field_labels():
    adapter = GeminiFlashOcrAdapter(api_key="test_mock_key")
    response = json.dumps({
        "product_summary": {"brand": None, "product_name": None, "variant": None, "category": "unknown"},
        "regions": [
            {
                "field_type": "mrp_price",
                "label": None,
                "observed_text": "Rs. 99.00",
                "normalized_value": "99 INR",
                "source_image_index": 0,
                "bbox_2d": [0, 0, 100, 100],
                "legibility": "clear",
            },
            {
                "field_type": "net_quantity",
                "label": None,
                "observed_text": "1 U",
                "normalized_value": "1 unit",
                "source_image_index": 0,
                "bbox_2d": [100, 0, 200, 100],
                "legibility": "clear",
            },
        ],
        "extraction_notes": [],
    })

    slot = adapter._parse_response(
        response,
        PanelRole.PDP,
        "img_pdp",
        1000,
        1000,
        1000,
        1000,
        Transform(),
    )

    assert [line.raw_text for line in slot.lines] == ["Rs. 99.00", "1 U"]


def test_gemini_count_region_reaches_quantity_extraction_without_invented_label():
    adapter = GeminiFlashOcrAdapter(api_key="test_mock_key")
    response = json.dumps({
        "product_summary": {"brand": None, "product_name": "Towel", "variant": None, "category": "other"},
        "regions": [{
            "field_type": "net_quantity",
            "label": None,
            "observed_text": "1 U",
            "normalized_value": "1 unit",
            "source_image_index": 0,
            "bbox_2d": [0, 0, 100, 100],
            "legibility": "clear",
        }],
        "extraction_notes": [],
    })
    slot = adapter._parse_response(
        response,
        PanelRole.PDP,
        "img_pdp",
        1000,
        1000,
        1000,
        1000,
        Transform(),
    )

    ocr_doc = OcrDocument(ocr_engine="gemini-2.5-flash", ocr_version="2.5", images=[slot])
    declarations = extract_declarations(
        build_normalised_document(ocr_doc),
        ocr_doc,
        CaptureContext(
            package_type=PackageType.RETAIL,
            commodity_category=CommodityCategory.TEXTILE,
            import_status=ImportStatus.DOMESTIC,
            all_panels_captured=True,
            inspector_id="test",
            captured_at=datetime(2026, 9, 9),
        ),
    )
    quantity = next(d for d in declarations.declarations if d.field == Field.NET_QUANTITY)

    assert slot.lines[0].raw_text == "1 U"
    assert quantity.status == ExtractionStatus.FOUND
    assert quantity.raw_value == "1 U"
    assert quantity.parsed.dimension == DimensionKind.NUMBER


def test_gemini_ocr_summary_commercial_entities_and_rule_04():
    """Verify separate manufactured_by, marketed_by, and optional imported_by fields."""
    adapter = GeminiFlashOcrAdapter(api_key="test_mock_key")
    response = json.dumps({
        "product_summary": {
            "brand": "Marico",
            "product_name": "Parachute",
            "variant": "Coconut Oil",
            "category": "food",
            "manufactured_by": "Manufactured by: ABC Oils Pvt Ltd, SIPCOT, Perundurai 638052",
            "marketed_by": "Marketed by: Marico Ltd, Santacruz East, Mumbai 400098",
            "imported_by": None,  # optional for domestic package
        },
        "regions": [
            {
                "field_type": "net_quantity",
                "label": "Net Qty",
                "observed_text": "500 mL",
                "normalized_value": "500 ml",
                "source_image_index": 0,
                "bbox_2d": [0, 0, 100, 100],
                "legibility": "clear",
            },
            {
                "field_type": "mrp_price",
                "label": "M.R.P.",
                "observed_text": "M.R.P. Rs. 250.00",
                "normalized_value": "250 INR",
                "source_image_index": 0,
                "bbox_2d": [100, 0, 200, 100],
                "legibility": "clear",
            },
        ],
        "extraction_notes": [],
    })

    slot = adapter._parse_response(
        response,
        PanelRole.PDP,
        "img_pdp",
        1000,
        1000,
        1000,
        1000,
        Transform(),
    )
    ocr_doc = OcrDocument(ocr_engine="gemini-2.5-flash", ocr_version="2.5", images=[slot])
    ctx = CaptureContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.FOOD,
        import_status=ImportStatus.DOMESTIC,
        all_panels_captured=True,
        inspector_id="test",
        captured_at=datetime(2026, 9, 9),
    )
    declarations = extract_declarations(build_normalised_document(ocr_doc), ocr_doc, ctx)

    from app.rules import evaluate_single_rule, get_rule
    from lmpc_schema import InternalVerdict, ProductContext
    prod_ctx = ProductContext(
        package_type=ctx.package_type,
        commodity_category=ctx.commodity_category,
        import_status=ctx.import_status,
        scan_date=ctx.captured_at.date(),
        ruleset_as_of=ctx.captured_at.date(),
    )

    # Rule 4: Mandatory declarations (disabled -> COMPLIANT)
    r4_res = evaluate_single_rule(get_rule("R04_MANDATORY_LABEL"), declarations, prod_ctx)
    assert r4_res.verdict == InternalVerdict.COMPLIANT
    assert r4_res.reason_code == "RULE_4_DISABLED"

    # Rule 6(1)(e): MRP rule (disabled -> COMPLIANT)
    r6_price = evaluate_single_rule(get_rule("R6_1_E_RSP_FORM"), declarations, prod_ctx)
    assert r6_price.verdict == InternalVerdict.COMPLIANT
    assert r6_price.reason_code == "MRP_RULE_DISABLED"


def test_gemini_ocr_stamped_misaligned_info_parsing():
    """Verify stamped and chronologically reasoned dates and offset pricing."""
    adapter = GeminiFlashOcrAdapter(api_key="test_mock_key")
    response = json.dumps({
        "product_summary": {
            "brand": "NutriLife",
            "product_name": "Health Mix",
            "variant": "Standard",
            "category": "food",
            "manufactured_by": "NutriLife Foods Ltd, Plot 5, MIDC, Pune 411026",
            "marketed_by": None,
            "imported_by": None,
        },
        "regions": [
            {
                # Inkjet-stamped price offset from header
                "field_type": "mrp_price",
                "label": "M.R.P.",
                "observed_text": "Rs. 199.00",
                "normalized_value": "199 INR",
                "source_image_index": 0,
                "bbox_2d": [750, 100, 800, 300],
                "legibility": "clear",
            },
            {
                # Chronologically earlier date -> manufacture_date
                "field_type": "manufacture_date",
                "label": "MFD",
                "observed_text": "06/2025",
                "normalized_value": "2025-06",
                "source_image_index": 0,
                "bbox_2d": [810, 100, 850, 300],
                "legibility": "clear",
            },
            {
                # Chronologically later date -> expiry_date
                "field_type": "expiry_date",
                "label": "USE BY",
                "observed_text": "06/2026",
                "normalized_value": "2026-06",
                "source_image_index": 0,
                "bbox_2d": [860, 100, 900, 300],
                "legibility": "clear",
            },
        ],
        "extraction_notes": ["Stamped inkjet batch window identified on carton flap"],
    })

    slot = adapter._parse_response(
        response,
        PanelRole.PDP,
        "img_pdp",
        1000,
        1000,
        1000,
        1000,
        Transform(),
    )
    ocr_doc = OcrDocument(ocr_engine="gemini-2.5-flash", ocr_version="2.5", images=[slot])
    ctx = CaptureContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.FOOD,
        import_status=ImportStatus.DOMESTIC,
        all_panels_captured=True,
        inspector_id="test",
        captured_at=datetime(2026, 9, 9),
    )
    declarations = extract_declarations(build_normalised_document(ocr_doc), ocr_doc, ctx)

    price_decl = next(d for d in declarations.declarations if d.field == Field.RETAIL_SALE_PRICE)
    date_decl = next(d for d in declarations.declarations if d.field == Field.DATE_OF_MANUFACTURE_PACKING_IMPORT)

    assert price_decl.status == ExtractionStatus.FOUND
    assert price_decl.parsed.amount == 199.00
    assert date_decl.status == ExtractionStatus.FOUND
    assert date_decl.parsed.month == 6
    assert date_decl.parsed.year == 2025


def test_gemini_reported_fields_reach_rule_6_evaluation():
    from datetime import date
    from app.rules import evaluate_single_rule, get_rule
    from lmpc_schema import InternalVerdict, ProductContext

    field_types = STRUCTURED_RESPONSE_SCHEMA["properties"]["regions"]["items"]["properties"]["field_type"]["enum"]
    assert "manufacture_date" in field_types
    assert "mrp_price" in field_types

    response = json.dumps({
        "product_summary": {
            "brand": "GIZGA ESSENTIALS",
            "product_name": "3-IN-1 SCREEN CLEANING KIT",
            "variant": None,
            "category": "household_product",
        },
        "regions": [
            {
                "field_type": "importer",
                "label": "IMPORTED BY:",
                "observed_text": "IMPORTED BY: IRIS TECH. G-1, DHARAM COMPLEX, PHASE-1, ANJUR MANKOLI ROAD, BHIWANDI-421302.",
                "normalized_value": None,
                "source_image_index": 0,
                "bbox_2d": [160, 110, 205, 835],
                "legibility": "clear",
            },
            {
                "field_type": "manufacture_date",
                "label": "MONTH & YEAR OF MANUFACTURING:",
                "observed_text": "MONTH & YEAR OF MANUFACTURING: APRIL - 2026",
                "normalized_value": "April 2026",
                "source_image_index": 0,
                "bbox_2d": [345, 110, 365, 675],
                "legibility": "clear",
            },
            {
                "field_type": "mrp_price",
                "label": "MRP:",
                "observed_text": "MRP: RS. 199.00 (INCL. OF ALL TAXES)",
                "normalized_value": "199.00",
                "source_image_index": 0,
                "bbox_2d": [370, 110, 390, 560],
                "legibility": "clear",
            },
        ],
        "extraction_notes": [],
    })

    adapter = GeminiFlashOcrAdapter(api_key="test_mock_key")
    slot = adapter._parse_response(
        response, PanelRole.BACK, "img_back", 1000, 1000, 1000, 1000, Transform()
    )
    ocr_doc = OcrDocument(ocr_engine="gemini-2.5-flash", ocr_version="2.5", images=[slot])
    capture_ctx = CaptureContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.GENERAL,
        import_status=ImportStatus.IMPORTED,
        all_panels_captured=True,
        inspector_id="test",
        captured_at=datetime(2026, 9, 9),
    )
    declarations = extract_declarations(build_normalised_document(ocr_doc), ocr_doc, capture_ctx)

    importer = next(d for d in declarations.declarations if d.field == Field.IMPORTER_NAME_ADDRESS)
    manufacture_date = next(
        d for d in declarations.declarations if d.field == Field.DATE_OF_MANUFACTURE_PACKING_IMPORT
    )
    mrp = next(d for d in declarations.declarations if d.field == Field.RETAIL_SALE_PRICE)

    assert importer.status == ExtractionStatus.FOUND
    assert importer.parsed.pin_code == "421302"
    assert manufacture_date.status == ExtractionStatus.FOUND
    assert (manufacture_date.parsed.month, manufacture_date.parsed.year) == (4, 2026)
    assert mrp.status == ExtractionStatus.FOUND
    assert mrp.parsed.amount == 199.00

    product_ctx = ProductContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.GENERAL,
        import_status=ImportStatus.IMPORTED,
        scan_date=date(2026, 9, 9),
        ruleset_as_of=date(2026, 9, 9),
    )
    expected_outcomes = {
        "R6_1_A_IDENTITY": "IDENTITY_AND_ADDRESS_COMPLIANT",
        "R6_1_D_DATE": "MANUFACTURE_DATE_COMPLIANT",
        "R6_1_E_RSP_FORM": "MRP_RULE_DISABLED",
    }
    for rule_id, reason_code in expected_outcomes.items():
        outcome = evaluate_single_rule(get_rule(rule_id), declarations, product_ctx)
        assert outcome.verdict == InternalVerdict.COMPLIANT
        assert outcome.reason_code == reason_code


@pytest.mark.asyncio
async def test_gemini_ocr_api_http_error():
    adapter = GeminiFlashOcrAdapter(api_key="test_mock_key")

    mock_response = httpx.Response(
        status_code=429,
        text="Resource exhausted: Quota exceeded for quota metric 'Generate Content API requests'.",
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        with pytest.raises(OcrEngineError, match="Gemini API returned HTTP 429"):
            await adapter.recognize_panel(
                analysis_bytes=b"fake_image_bytes",
                role=PanelRole.PDP,
                image_id="img_test_pdp",
                analysis_width=1000,
                analysis_height=1000,
                original_width=2000,
                original_height=2000,
                transform=Transform(),
            )


@pytest.mark.asyncio
async def test_ocr_router_uses_only_gemini_when_key_set():
    """Verify router selects Gemini exclusively and does not initialize or run PaddleOCR/Qwen."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test_key_live"}):
        router = OcrRouter()
        assert len(router.engines) == 1
        assert router.engines[0].engine_name == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_ocr_router_gemini_primary_success():
    """Verify router selects Gemini when it succeeds."""
    gemini_engine = GeminiFlashOcrAdapter(api_key="test_mock_key")
    fallback_engine = AsyncMock()
    fallback_engine.engine_name = "mock_fallback"

    gemini_response = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": json.dumps({
                        "product_summary": {"brand": "Test", "product_name": "Item", "variant": None, "category": "food"},
                        "regions": [{"field_type": "other", "label": None, "observed_text": "Sample Text", "normalized_value": None, "source_image_index": 0, "bbox_2d": [0, 0, 100, 100], "legibility": "clear"}],
                        "extraction_notes": []
                    })}]
                }
            }
        ]
    }

    router = OcrRouter(primary=gemini_engine, fallback=fallback_engine)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(status_code=200, json=gemini_response)

        slot, engine_used = await router.recognize_panel(
            analysis_bytes=b"fake_image_bytes",
            role=PanelRole.PDP,
            image_id="img_pdp",
            analysis_width=800,
            analysis_height=1200,
            original_width=1600,
            original_height=2400,
            transform=Transform(),
        )

        assert engine_used == "gemini-2.5-flash"
        assert len(slot.lines) == 1
        assert slot.lines[0].raw_text == "Sample Text"
        fallback_engine.recognize_panel.assert_not_called()


def test_imported_product_address_compliant():
    """Verify that an imported product with foreign manufacturer + Indian importer evaluates as COMPLIANT."""
    from datetime import date
    from lmpc_schema import (
        CommodityCategory,
        Declaration,
        DeclarationSet,
        ExtractionMethod,
        ExtractionStatus,
        Field,
        ImportStatus,
        InternalVerdict,
        PackageType,
        PanelCoverage,
        ParsedAddress,
        ProductContext,
    )
    from app.rules.rule_06 import evaluate_r6_1_a

    # Foreign manufacturer without Indian PIN, but valid Indian importer with PIN
    decl_mfg = Declaration(
        field=Field.MANUFACTURER_NAME_ADDRESS,
        status=ExtractionStatus.FOUND,
        raw_value="Manufactured by: Global Electronics Corp, Suwon, South Korea",
        parsed=ParsedAddress(
            lines=["Manufactured by: Global Electronics Corp, Suwon, South Korea"],
            has_premises_number=False,
            has_street=False,
            has_city=True,
            has_state=False,
            pin_code=None,
        ),
        method=ExtractionMethod.ALIAS_ANCHOR,
    )

    decl_imp = Declaration(
        field=Field.IMPORTER_NAME_ADDRESS,
        status=ExtractionStatus.FOUND,
        raw_value="Imported by: India Imports Pvt Ltd, 12 Barakhamba Road, Connaught Place, New Delhi 110001",
        parsed=ParsedAddress(
            lines=["Imported by: India Imports Pvt Ltd, 12 Barakhamba Road, Connaught Place, New Delhi 110001"],
            has_premises_number=True,
            has_street=True,
            has_city=True,
            has_state=True,
            pin_code="110001",
        ),
        method=ExtractionMethod.ALIAS_ANCHOR,
    )

    decl_set = DeclarationSet(
        declarations=[decl_mfg, decl_imp],
        panel_coverage=PanelCoverage(roles_captured=[PanelRole.PDP, PanelRole.BACK], all_panels_confirmed=True),
    )

    ctx = ProductContext(
        package_type=PackageType.RETAIL,
        commodity_category=CommodityCategory.GENERAL,
        import_status=ImportStatus.IMPORTED,
        scan_date=date(2026, 9, 9),
        ruleset_as_of=date(2026, 9, 9),
    )

    outcome = evaluate_r6_1_a(decl_set, ctx)
    assert outcome.verdict == InternalVerdict.COMPLIANT
    assert outcome.reason_code == "IDENTITY_AND_ADDRESS_COMPLIANT"

