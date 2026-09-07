"""
Google Cloud Vision Primary OCR Adapter (C1 per ADR-0004).

Calls DOCUMENT_TEXT_DETECTION with:
- 3.5s hard per-request timeout
- Single retry on retryable transport error
- Circuit breaker: 3 consecutive failures -> OPEN (60s cooldown) -> HALF_OPEN (1 canary)
- Produces ImageSlot with Lines, Words, and mapped Polygons.
"""

import asyncio
import os
import time
from enum import Enum
from typing import Any, List, Optional
from lmpc_schema import ImageSlot, Line, PanelRole, Transform, Word

from app.preprocessing import CoordinateMapper
from .protocol import CircuitBreakerOpenError, OcrEngineError


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Manages consecutive failure counting, open cooldown, and canary recovery."""

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 60.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_state_change = time.monotonic()

    def record_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_state_change = time.monotonic()

    def record_failure(self):
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.last_state_change = time.monotonic()

    def can_attempt(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        now = time.monotonic()
        if self.state == CircuitState.OPEN:
            if now - self.last_state_change >= self.cooldown_seconds:
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = now
                return True
            return False
        if self.state == CircuitState.HALF_OPEN:
            # Allow canary request
            return True
        return False


class GoogleCloudVisionAdapter:
    """Google Cloud Vision primary OCR adapter with circuit breaker and bounded timeout."""

    engine_name = "google_cloud_vision"
    engine_version = "v1"

    def __init__(
        self,
        timeout_seconds: float = 3.5,
        circuit_breaker: Optional[CircuitBreaker] = None,
        client: Optional[Any] = None,
    ):
        self.timeout_seconds = timeout_seconds
        self.breaker = circuit_breaker or CircuitBreaker()
        self._client = client

    def _get_client(self):
        if self._client is not None:
            return self._client
        # Check credentials
        creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if not creds_path or not os.path.exists(creds_path):
            raise OcrEngineError("GOOGLE_APPLICATION_CREDENTIALS not configured or file missing.")

        try:
            from google.cloud import vision
            self._client = vision.ImageAnnotatorClient()
            return self._client
        except Exception as e:
            raise OcrEngineError(f"Failed to initialize Google Cloud Vision client: {e}") from e

    async def is_available(self) -> bool:
        """Returns True if client can be initialized and circuit breaker is not OPEN."""
        if not self.breaker.can_attempt():
            return False
        creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        return bool(creds and os.path.exists(creds))

    async def recognize_panel(
        self,
        analysis_bytes: bytes,
        role: PanelRole,
        image_id: str,
        analysis_width: int,
        analysis_height: int,
        original_width: int,
        original_height: int,
        transform: Transform,
    ) -> ImageSlot:
        """
        Executes DOCUMENT_TEXT_DETECTION with 3.5s timeout, circuit breaker, and 1 retry.
        """
        if not self.breaker.can_attempt():
            raise CircuitBreakerOpenError(
                f"Cloud Vision circuit breaker is {self.breaker.state.value}. Cooling down."
            )

        # Retry loop: attempt at most 2 times (1 initial + 1 retry)
        last_exception: Optional[Exception] = None
        for attempt in range(2):
            try:
                slot = await asyncio.wait_for(
                    self._call_vision_api(
                        analysis_bytes=analysis_bytes,
                        role=role,
                        image_id=image_id,
                        analysis_width=analysis_width,
                        analysis_height=analysis_height,
                        original_width=original_width,
                        original_height=original_height,
                        transform=transform,
                    ),
                    timeout=self.timeout_seconds,
                )
                self.breaker.record_success()
                return slot
            except (asyncio.TimeoutError, Exception) as exc:
                last_exception = exc
                if attempt == 0:
                    # Quick yield before single retry
                    await asyncio.sleep(0.1)

        # Both attempts failed
        self.breaker.record_failure()
        raise OcrEngineError(f"Cloud Vision request failed after retry: {last_exception}") from last_exception

    async def _call_vision_api(
        self,
        analysis_bytes: bytes,
        role: PanelRole,
        image_id: str,
        analysis_width: int,
        analysis_height: int,
        original_width: int,
        original_height: int,
        transform: Transform,
    ) -> ImageSlot:
        """Runs the synchronous Vision SDK call in an executor thread."""
        client = self._get_client()

        def _sync_call():
            from google.cloud import vision
            image = vision.Image(content=analysis_bytes)
            # DOCUMENT_TEXT_DETECTION gives full text annotation with word/symbol hierarchy
            response = client.document_text_detection(image=image)
            if response.error and response.error.message:
                raise OcrEngineError(f"Cloud Vision API returned error: {response.error.message}")
            return response

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, _sync_call)

        return self._parse_vision_response(
            response=response,
            role=role,
            image_id=image_id,
            analysis_width=analysis_width,
            analysis_height=analysis_height,
            original_width=original_width,
            original_height=original_height,
            transform=transform,
        )

    def _parse_vision_response(
        self,
        response: Any,
        role: PanelRole,
        image_id: str,
        analysis_width: int,
        analysis_height: int,
        original_width: int,
        original_height: int,
        transform: Transform,
    ) -> ImageSlot:
        lines: List[Line] = []
        annotation = getattr(response, "full_text_annotation", None)
        if not annotation:
            return ImageSlot(
                image_id=image_id,
                role=role,
                analysis_width=analysis_width,
                analysis_height=analysis_height,
                original_width=original_width,
                original_height=original_height,
                transform=transform,
                lines=[],
            )

        line_counter = 1
        for page in annotation.pages:
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    # Construct line from paragraph or line breaks
                    para_words: List[Word] = []
                    word_texts: List[str] = []
                    conf_sum = 0.0
                    word_count = 0

                    for w in paragraph.words:
                        w_text = "".join(s.text for s in w.symbols)
                        w_conf = float(getattr(w, "confidence", 0.95) or 0.95)
                        # Extract normalized polygon for word
                        w_poly_analysis = self._extract_poly(w.bounding_box, analysis_width, analysis_height)
                        w_poly_norm = CoordinateMapper.analysis_to_normalized(
                            w_poly_analysis, transform, original_width, original_height
                        )
                        para_words.append(Word(
                            raw_text=w_text,
                            confidence=round(w_conf, 3),
                            polygon_normalized=w_poly_norm,
                        ))
                        word_texts.append(w_text)
                        conf_sum += w_conf
                        word_count += 1

                    if not word_texts:
                        continue

                    raw_text = " ".join(word_texts)
                    para_conf = conf_sum / word_count if word_count > 0 else 0.95
                    poly_analysis = self._extract_poly(paragraph.bounding_box, analysis_width, analysis_height)
                    poly_orig = CoordinateMapper.analysis_to_original(
                        poly_analysis, transform, original_width, original_height
                    )
                    poly_norm = CoordinateMapper.original_to_normalized(
                        poly_orig, original_width, original_height
                    )

                    line_obj = Line(
                        line_id=f"{image_id}:l{line_counter:03d}",
                        raw_text=raw_text,
                        confidence=round(para_conf, 3),
                        polygon_analysis=poly_analysis,
                        polygon_original=poly_orig,
                        polygon_normalized=poly_norm,
                        script="LATIN",
                        words=para_words,
                    )
                    lines.append(line_obj)
                    line_counter += 1

        return ImageSlot(
            image_id=image_id,
            role=role,
            analysis_width=analysis_width,
            analysis_height=analysis_height,
            original_width=original_width,
            original_height=original_height,
            transform=transform,
            lines=lines,
        )

    def _extract_poly(self, bounding_box: Any, width: int, height: int) -> List[List[float]]:
        """Converts bounding_box vertices into 4-point [[x, y], ...] list."""
        if not bounding_box:
            return [[0.0, 0.0], [float(width), 0.0], [float(width), float(height)], [0.0, float(height)]]

        pts = []
        for v in bounding_box.vertices:
            x = float(getattr(v, "x", 0.0) or 0.0)
            y = float(getattr(v, "y", 0.0) or 0.0)
            pts.append([x, y])

        while len(pts) < 4:
            pts.append(pts[-1] if pts else [0.0, 0.0])

        return pts[:4]
