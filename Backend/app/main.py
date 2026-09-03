from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from schemas import Image
from preprocessing import ImagePreprocessor

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
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

    image = Image(front_bytes, back_bytes, side_bytes)
    ImagePreprocessor.show(image)
    
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