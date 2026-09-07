"""
PaddleOCR Automatic Local Fallback Adapter (C1 per ADR-0004).

Runs the full (non-mobile) PaddleOCR pipeline for Hindi + English.
GPU-primary with bounded allocation (gpu_mem=2000); on any CUDA error/OOM,
transparently falls back to CPU (use_gpu=False) and retries without dropping
the request. GPU is re-attempted on the next request since VRAM pressure changes.
"""

import asyncio
from typing import Any, List, Optional
from lmpc_schema import ImageSlot, Line, PanelRole, Transform, Word

from app.preprocessing import CoordinateMapper
from .protocol import OcrEngineError

GPU_MEM_MB = 2000


class PaddleOcrAdapter:
    """Automatic local OCR fallback: GPU-first with bounded memory, CPU fallback on failure."""

    engine_name = "paddleocr"
    engine_version = "3.x"

    def __init__(self, lang: str = "hi", use_gpu: bool = True, gpu_mem: int = GPU_MEM_MB):
        self.lang = lang
        self._preferred_use_gpu = use_gpu
        self.gpu_mem = gpu_mem
        self._gpu_ocr_instance: Optional[Any] = None
        self._cpu_ocr_instance: Optional[Any] = None
        self._gpu_disabled_this_session = False

    def _build_instance(self, use_gpu: bool):
        try:
            from paddleocr import PaddleOCR
        except ImportError as e:
            raise OcrEngineError(
                "paddleocr is not installed in this environment. "
                "Install via `pip install paddlepaddle-gpu paddleocr` in a Python "
                "3.11/3.13 venv (paddlepaddle has no cp314 wheels as of 2026-09)."
            ) from e

        kwargs = {"lang": self.lang, "use_angle_cls": True}
        if use_gpu:
            kwargs["use_gpu"] = True
            kwargs["gpu_mem"] = self.gpu_mem
        else:
            kwargs["use_gpu"] = False

        return PaddleOCR(**kwargs)

    def _get_gpu_instance(self):
        if self._gpu_ocr_instance is None:
            self._gpu_ocr_instance = self._build_instance(use_gpu=True)
        return self._gpu_ocr_instance

    def _get_cpu_instance(self):
        if self._cpu_ocr_instance is None:
            self._cpu_ocr_instance = self._build_instance(use_gpu=False)
        return self._cpu_ocr_instance

    async def is_available(self) -> bool:
        try:
            import paddleocr  # noqa: F401
            return True
        except ImportError:
            return False

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
        Attempts GPU inference first (bounded gpu_mem); on CUDA OOM/error, falls
        back transparently to CPU for this request. GPU is retried on the next call.
        """
        loop = asyncio.get_running_loop()

        def _run_gpu():
            instance = self._get_gpu_instance()
            return instance.ocr(analysis_bytes, cls=True)

        def _run_cpu():
            instance = self._get_cpu_instance()
            return instance.ocr(analysis_bytes, cls=True)

        result = None
        if self._preferred_use_gpu and not self._gpu_disabled_this_session:
            try:
                result = await loop.run_in_executor(None, _run_gpu)
            except Exception as gpu_exc:
                # CUDA OOM / device error: fall back to CPU transparently for this call.
                # GPU will be retried on the next request per ADR-0004 (VRAM pressure can change).
                try:
                    result = await loop.run_in_executor(None, _run_cpu)
                except Exception as cpu_exc:
                    raise OcrEngineError(
                        f"PaddleOCR failed on both GPU ({gpu_exc}) and CPU ({cpu_exc})"
                    ) from cpu_exc
        else:
            try:
                result = await loop.run_in_executor(None, _run_cpu)
            except Exception as cpu_exc:
                raise OcrEngineError(f"PaddleOCR CPU inference failed: {cpu_exc}") from cpu_exc

        return self._parse_paddle_result(
            result=result,
            role=role,
            image_id=image_id,
            analysis_width=analysis_width,
            analysis_height=analysis_height,
            original_width=original_width,
            original_height=original_height,
            transform=transform,
        )

    def _parse_paddle_result(
        self,
        result: Any,
        role: PanelRole,
        image_id: str,
        analysis_width: int,
        analysis_height: int,
        original_width: int,
        original_height: int,
        transform: Transform,
    ) -> ImageSlot:
        """
        PaddleOCR .ocr() returns: List[List[ [ [4 pts], (text, confidence) ] ]] per image.
        """
        lines: List[Line] = []
        if not result or not result[0]:
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

        for idx, entry in enumerate(result[0]):
            poly_analysis = [[float(p[0]), float(p[1])] for p in entry[0]]
            text, confidence = entry[1][0], float(entry[1][1])

            poly_orig = CoordinateMapper.analysis_to_original(
                poly_analysis, transform, original_width, original_height
            )
            poly_norm = CoordinateMapper.original_to_normalized(
                poly_orig, original_width, original_height
            )

            lines.append(Line(
                line_id=f"{image_id}:l{idx + 1:03d}",
                raw_text=text,
                confidence=round(confidence, 3),
                polygon_analysis=poly_analysis,
                polygon_original=poly_orig,
                polygon_normalized=poly_norm,
                script="LATIN",
                words=[],
            ))

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
