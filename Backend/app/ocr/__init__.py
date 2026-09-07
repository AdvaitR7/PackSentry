"""
LMPC OCR Package (Track C1 per ADR-0001, ADR-0004).

Provides:
- OcrEngine protocol
- GoogleCloudVisionAdapter (primary, with circuit breaker & timeout)
- PaddleOcrAdapter (automatic local fallback, GPU bounded -> CPU fallback)
- OcrRouter (failover orchestration)
"""

from .cloud_vision import CircuitBreaker, CircuitState, GoogleCloudVisionAdapter
from .paddleocr_engine import PaddleOcrAdapter
from .protocol import CircuitBreakerOpenError, OcrEngine, OcrEngineError
from .router import OcrRouter
from .vlm_interpreter import QwenVlmInterpreter

__all__ = [
    "OcrEngine",
    "OcrEngineError",
    "CircuitBreakerOpenError",
    "CircuitBreaker",
    "CircuitState",
    "GoogleCloudVisionAdapter",
    "PaddleOcrAdapter",
    "OcrRouter",
    "QwenVlmInterpreter",
]
