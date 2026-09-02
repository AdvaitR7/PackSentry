from pydantic import BaseModel

class ScanSession(BaseModel):
    scan_id : str
    capture_time : str
    scan_mode : str