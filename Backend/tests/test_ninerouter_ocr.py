"""Tests for 9Router's OpenAI-compatible Gemini OCR transport."""

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from lmpc_schema import PanelRole, Transform

from app.ocr.gemini_engine import STRUCTURED_RESPONSE_SCHEMA, SYSTEM_PROMPT
from app.ocr.ninerouter_engine import (
    NINEROUTER_EXTRACTION_INSTRUCTION,
    NINEROUTER_RESPONSE_SCHEMA,
    NineRouterOcrAdapter,
)
from app.ocr.protocol import OcrEngineError
from app.ocr.router import OcrRouter


PANEL_ARGS = {
    "analysis_bytes": b"fake_image_bytes",
    "role": PanelRole.PDP,
    "image_id": "img_9router",
    "analysis_width": 1000,
    "analysis_height": 1000,
    "original_width": 2000,
    "original_height": 2000,
    "transform": Transform(scale_x=0.5, scale_y=0.5),
}


def _structured_content():
    return json.dumps({
        "product_summary": {
            "brand": "Britannia",
            "product_name": "Good Day",
            "variant": "Butter",
            "category": "food",
        },
        "regions": [{
            "field_type": "net_quantity",
            "label": "Net Qty",
            "observed_text": "Net Qty: 1200 gms",
            "normalized_value": "1200 g",
            "source_image_index": 0,
            "bbox_2d": [100, 200, 150, 600],
            "legibility": "clear",
        }],
        "extraction_notes": [],
    })


def _assert_schema_preserved(gemini, standard):
    if isinstance(gemini, dict):
        assert set(gemini) - {"nullable"} == set(standard)
        for key, value in gemini.items():
            if key == "nullable":
                continue
            if key == "type":
                expected = value.lower()
                if gemini.get("nullable") is True:
                    assert standard[key] == [expected, "null"]
                else:
                    assert standard[key] == expected
            else:
                _assert_schema_preserved(value, standard[key])
    elif isinstance(gemini, list):
        assert len(gemini) == len(standard)
        for left, right in zip(gemini, standard):
            _assert_schema_preserved(left, right)
    else:
        assert standard == gemini


@pytest.mark.asyncio
async def test_ninerouter_sends_existing_prompt_image_and_schema():
    adapter = NineRouterOcrAdapter(
        base_url="http://localhost:20128",
        api_key="test-key",
        model="ag/gemini-3.8-flash",
    )
    response = httpx.Response(
        200,
        json={"choices": [{"message": {"content": _structured_content()}}]},
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as post:
        post.return_value = response
        await adapter.recognize_panel(**PANEL_ARGS)

    url = post.call_args.args[0]
    request = post.call_args.kwargs
    payload = request["json"]
    assert url == "http://localhost:20128/v1/chat/completions"
    assert request["headers"]["Authorization"] == "Bearer test-key"
    assert payload["model"] == "ag/gemini-3.8-flash"
    assert payload["messages"][0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert payload["messages"][1]["content"][0]["text"] == NINEROUTER_EXTRACTION_INSTRUCTION
    assert "top-level 'regions'" in NINEROUTER_EXTRACTION_INSTRUCTION
    assert payload["messages"][1]["content"][1]["image_url"]["url"].startswith(
        "data:image/jpeg;base64,"
    )
    assert payload["response_format"]["type"] == "json_object"
    _assert_schema_preserved(
        STRUCTURED_RESPONSE_SCHEMA,
        payload["response_format"]["schema"],
    )
    _assert_schema_preserved(STRUCTURED_RESPONSE_SCHEMA, NINEROUTER_RESPONSE_SCHEMA)


@pytest.mark.asyncio
async def test_ninerouter_parses_openai_response_with_gemini_mapper():
    adapter = NineRouterOcrAdapter(base_url="http://localhost:20128")
    response = httpx.Response(
        200,
        json={"choices": [{"message": {"content": _structured_content()}}]},
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as post:
        post.return_value = response
        slot = await adapter.recognize_panel(**PANEL_ARGS)

    assert slot.lines[0].raw_text == "Net Qty: 1200 gms"
    assert slot.lines[0].polygon_analysis == [
        [200.0, 100.0],
        [600.0, 100.0],
        [600.0, 150.0],
        [200.0, 150.0],
    ]
    assert slot.lines[0].polygon_original[2] == [1200.0, 300.0]
    assert [word.raw_text for word in slot.lines[0].words] == [
        "Net", "Qty:", "1200", "gms"
    ]


@pytest.mark.asyncio
async def test_ninerouter_normalizes_antigravity_aliases():
    adapter = NineRouterOcrAdapter(base_url="http://localhost:20128")
    antigravity_content = {
        "declarations": [{
            "field_type": "net_quantity",
            "label": "NET QTY",
            "observed_text": "NET QTY: 500 g",
            "normalized_value": {"value": 500.0, "unit": "g"},
            "source_image_index": 0,
            "bounding_box": [100, 200, 150, 600],
            "legibility": "clear",
        }]
    }
    response = httpx.Response(
        200,
        json={
            "choices": [{
                "message": {
                    "content": f"```json\n{json.dumps(antigravity_content)}\n```"
                }
            }]
        },
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as post:
        post.return_value = response
        slot = await adapter.recognize_panel(**PANEL_ARGS)

    assert [line.raw_text for line in slot.lines] == ["NET QTY: 500 g"]
    assert slot.lines[0].polygon_analysis == [
        [200.0, 100.0],
        [600.0, 100.0],
        [600.0, 150.0],
        [200.0, 150.0],
    ]


@pytest.mark.asyncio
async def test_ninerouter_rejects_non_json_content():
    adapter = NineRouterOcrAdapter(base_url="http://localhost:20128")
    response = httpx.Response(
        200,
        json={"choices": [{"message": {"content": "not structured json"}}]},
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as post:
        post.return_value = response
        with pytest.raises(OcrEngineError, match="invalid structured OCR JSON"):
            await adapter.recognize_panel(**PANEL_ARGS)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content",
    [
        {"product_summary": {}, "regions": [], "extraction_notes": []},
        {"product_summary": {}, "extraction_notes": []},
        {
            "product_summary": {},
            "regions": [{"observed_text": "", "bbox_2d": [0, 0, 100, 100]}],
            "extraction_notes": [],
        },
    ],
)
async def test_ninerouter_rejects_structured_output_without_usable_regions(content):
    adapter = NineRouterOcrAdapter(base_url="http://localhost:20128")
    response = httpx.Response(
        200,
        json={"choices": [{"message": {"content": json.dumps(content)}}]},
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as post:
        post.return_value = response
        with pytest.raises(OcrEngineError, match="no usable observed_text regions"):
            await adapter.recognize_panel(**PANEL_ARGS)


@pytest.mark.asyncio
async def test_ninerouter_empty_regions_fall_back_to_google_ai_studio():
    adapter = NineRouterOcrAdapter(base_url="http://localhost:20128")
    empty_response = httpx.Response(
        200,
        json={
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "product_summary": {},
                        "regions": [],
                        "extraction_notes": [],
                    })
                }
            }]
        },
    )
    google_ai_studio = AsyncMock()
    google_ai_studio.engine_name = "gemini-3.6-flash"
    google_ai_studio.is_available.return_value = True
    expected_slot = object()
    google_ai_studio.recognize_panel.return_value = expected_slot
    router = OcrRouter(engines=[adapter, google_ai_studio])

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as post:
        post.return_value = empty_response
        slot, engine = await router.recognize_panel(**PANEL_ARGS)

    assert slot is expected_slot
    assert engine == "gemini-3.6-flash"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [429, 503])
async def test_ninerouter_http_errors_are_actionable(status):
    adapter = NineRouterOcrAdapter(base_url="http://localhost:20128")
    response = httpx.Response(
        status,
        text="All accounts unavailable",
        headers={"retry-after": "30"},
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as post:
        post.return_value = response
        with pytest.raises(OcrEngineError, match=f"HTTP {status}.*Retry after 30s"):
            await adapter.recognize_panel(**PANEL_ARGS)


@pytest.mark.asyncio
async def test_ninerouter_failure_falls_back_to_google_ai_studio_engine():
    ninerouter = AsyncMock()
    ninerouter.engine_name = "9router-antigravity"
    ninerouter.is_available.return_value = True
    ninerouter.recognize_panel.side_effect = OcrEngineError("9Router returned HTTP 503")

    google_ai_studio = AsyncMock()
    google_ai_studio.engine_name = "gemini-3.6-flash"
    google_ai_studio.is_available.return_value = True
    expected_slot = object()
    google_ai_studio.recognize_panel.return_value = expected_slot

    slot, engine = await OcrRouter(engines=[ninerouter, google_ai_studio]).recognize_panel(
        **PANEL_ARGS
    )

    assert slot is expected_slot
    assert engine == "gemini-3.6-flash"
    google_ai_studio.recognize_panel.assert_awaited_once()


def test_router_prefers_configured_ninerouter_then_google_ai_studio():
    with patch.dict(
        "os.environ",
        {
            "NINEROUTER_URL": "http://localhost:20128",
            "GEMINI_API_KEY": "test-google-key",
        },
    ), patch("app.ocr.router.NineRouterOcrAdapter") as nine_cls, patch(
        "app.ocr.router.GeminiFlashOcrAdapter"
    ) as gemini_cls:
        nine_cls.return_value.base_url = "http://localhost:20128"
        nine_cls.return_value.engine_name = "9router-antigravity"
        gemini_cls.return_value.api_key = "test-google-key"
        gemini_cls.return_value.engine_name = "gemini-3.6-flash"

        router = OcrRouter()

    assert [engine.engine_name for engine in router.engines] == [
        "9router-antigravity",
        "gemini-3.6-flash",
    ]
