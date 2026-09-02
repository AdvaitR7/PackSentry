from fastapi import FastAPI
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


