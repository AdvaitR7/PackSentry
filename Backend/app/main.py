from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from preprocessing import ImagePreprocessor

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:8080",
        "http://127.0.0.1",
        "http://10.0.2.2",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

@app.post("/api/analyze")
async def analyze_product(
    front_image: UploadFile = File(...),
    back_image: Optional[UploadFile] = File(None),
    side_image: Optional[UploadFile] = File(None),
):
    # Read bytes or save to disk for ML/OCR processing:
    front_bytes = await front_image.read()
    back_bytes = await back_image.read() if back_image else None
    side_bytes = await side_image.read() if side_image else None

    front_img, front_matrix = ImagePreprocessor.process(front_bytes)
    back_img, back_matrix = (
        ImagePreprocessor.process(back_bytes) if back_bytes else (None, None)
    )
    side_img, side_matrix = (
        ImagePreprocessor.process(side_bytes) if side_bytes else (None, None)
    )

    # Run compliance / OCR checks here...
    return {
        "status": "compliant",
        "message": "Analysis completed successfully",
        "details": {
            "front_filename": front_image.filename,
            "has_back": back_image is not None,
            "has_side": side_image is not None,
        }
    }
