"""
Local Scratch Disk Management for Uploaded Evidence Images (ADR-0009, ADR-0013).

Handles:
- Streaming incoming multipart file uploads to a per-inspection scratch directory.
- Calculating SHA-256 digests in-flight during streaming.
- Sniffing decoded image dimensions via OpenCV.
- Enforcing the 12 MiB per-image cap.
- Securely purging scratch directories upon terminal completion.
"""

import hashlib
import logging
import os
import shutil
from pathlib import Path
from typing import Tuple
import cv2
from fastapi import HTTPException, UploadFile
import numpy as np

logger = logging.getLogger("packsentry.db.scratch")

DEFAULT_SCRATCH_ROOT = Path(os.environ.get("PACKSENTRY_SCRATCH_DIR", Path(__file__).resolve().parent.parent.parent / "scratch"))
MAX_IMAGE_BYTES = 12 * 1024 * 1024  # 12 MiB per ADR-0009
CHUNK_SIZE = 64 * 1024  # 64 KiB chunks for in-flight hashing and streaming


def get_scratch_dir(inspection_id: str) -> Path:
    """Returns the absolute scratch directory path for an inspection, creating it if needed."""
    scratch_dir = DEFAULT_SCRATCH_ROOT / inspection_id
    scratch_dir.mkdir(parents=True, exist_ok=True)
    return scratch_dir


async def stream_upload_to_scratch(
    upload_file: UploadFile,
    target_path: Path,
    max_bytes: int = MAX_IMAGE_BYTES,
) -> Tuple[str, int, int]:
    """
    Streams bytes from an UploadFile to target_path on scratch disk.
    Computes SHA-256 in-flight, verifies image content, and determines dimensions.

    Returns:
        (sha256_hex, width, height)

    Raises:
        HTTPException(422): If file exceeds size cap or is not a valid decodeable image.
    """
    hasher = hashlib.sha256()
    total_bytes = 0

    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "wb") as f_out:
        while True:
            chunk = await upload_file.read(CHUNK_SIZE)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                target_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=422,
                    detail=f"Image exceeds maximum allowable size of {max_bytes // (1024*1024)} MiB.",
                )
            hasher.update(chunk)
            f_out.write(chunk)

    if total_bytes == 0:
        target_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="Uploaded image file is empty.")

    # Validate image content by decoding the raw bytes
    with open(target_path, "rb") as f_in:
        raw_bytes = f_in.read()

    np_arr = np.frombuffer(raw_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img is None:
        target_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=422,
            detail="File content is not a valid JPEG, PNG, or WebP image.",
        )

    height, width = img.shape[:2]
    return hasher.hexdigest(), width, height


def cleanup_scratch_dir(inspection_id: str) -> None:
    """Removes the local scratch directory and all transient files for an inspection."""
    scratch_dir = DEFAULT_SCRATCH_ROOT / inspection_id
    if scratch_dir.exists():
        try:
            shutil.rmtree(scratch_dir)
            logger.debug("Cleaned up scratch directory for %s", inspection_id)
        except Exception as exc:
            logger.warning("Failed to clean up scratch dir %s: %s", scratch_dir, exc)
