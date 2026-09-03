from pydantic import BaseModel
from fastapi import UploadFile

class Image():
    
    def __init__(self, front, back, side):
        self.front = front
        self.back = back
        self.side = side
           