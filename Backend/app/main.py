from fastapi import FastAPI, UploadFile, File
from typing import Optional
from schemas import ScanSession
from print import Printer

app = FastAPI()
printer = Printer()

@app.get("/")
def home():
    return {
        "message": "Mock API is running"
    }

# example data transaction
@app.get("/products/{product_id}")
def get_product(product_id: int, st = "heyhey"):
    return {
        "product_id": product_id,
        "name": "Sample Product",
        "price": 249.99,
        "unit": "kg",
        "status": "valid",
        "sjdhfsd" : st
    }
    
#session data transaction
@app.post("/transaction/session_details")
async def get_session(session : ScanSession):
    printer.print_session(session)

# Image analysis endpoint
@app.post("/api/analyze")
async def analyze_images(
    front_image: UploadFile = File(...),
    back_image: Optional[UploadFile] = File(None),
    side_image: Optional[UploadFile] = File(None),
):
    front_bytes = await front_image.read()
    back_bytes = await back_image.read() if back_image else None
    side_bytes = await side_image.read() if side_image else None

    print(f"\n--- [PackSentry API] Received Image Analysis Request ---")
    print(f"Front image: {front_image.filename} ({len(front_bytes):,} bytes)")
    if back_image and back_bytes:
        print(f"Back image:  {back_image.filename} ({len(back_bytes):,} bytes)")
    if side_image and side_bytes:
        print(f"Side image:  {side_image.filename} ({len(side_bytes):,} bytes)")
    print(f"-------------------------------------------------------\n")

    return {
        "status": "compliant",
        "message": "Images successfully received and processed",
        "received": {
            "front": {
                "filename": front_image.filename,
                "size_bytes": len(front_bytes),
            },
            "back": {
                "filename": back_image.filename if back_image else None,
                "size_bytes": len(back_bytes) if back_bytes else None,
            },
            "side": {
                "filename": side_image.filename if side_image else None,
                "size_bytes": len(side_bytes) if side_bytes else None,
            },
        },
    }


