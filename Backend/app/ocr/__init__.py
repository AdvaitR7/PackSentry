"""
LMPC OCR Package (Track C1 per ADR-0001, ADR-0004).

Provides:
- OcrEngine protocol
- QwenOcrAdapter (primary local vision OCR)
- PaddleOcrAdapter and GoogleCloudVisionAdapter fallbacks
- OcrRouter (sequential failover orchestration)
"""

from .cloud_vision import CircuitBreaker, CircuitState, GoogleCloudVisionAdapter
from .gemini_engine import GeminiFlashOcrAdapter
from .ninerouter_engine import NineRouterOcrAdapter
from .paddleocr_engine import PaddleOcrAdapter
from .protocol import CircuitBreakerOpenError, OcrEngine, OcrEngineError
from .qwen_engine import QwenOcrAdapter
from .router import OcrRouter
from .vlm_interpreter import QwenVlmInterpreter

__all__ = [
    "OcrEngine",
    "OcrEngineError",
    "CircuitBreakerOpenError",
    "CircuitBreaker",
    "CircuitState",
    "GoogleCloudVisionAdapter",
    "GeminiFlashOcrAdapter",
    "NineRouterOcrAdapter",
    "PaddleOcrAdapter",
    "QwenOcrAdapter",
    "OcrRouter",
    "QwenVlmInterpreter",
]
