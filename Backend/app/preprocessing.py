from schemas import Image
import cv2 as cv
from typing import Optional
import numpy as np

class ImagePreprocessor:
    
    blank = np.zeros((500,500,3), dtype = np.uint8)
    
    def _showblank():
        
        cv.putText(ImagePreprocessor.blank, "No Image", (255,255), cv.FONT_HERSHEY_DUPLEX, 1, (0, 0, 255), 2  )
        cv.imshow('no image', ImagePreprocessor.blank)
    
    def show(image : Image):
        
        
        
        front = cv.imdecode(np.frombuffer(image.front, np.uint8), cv.IMREAD_COLOR)
        cv.imshow("front", front)
        back = cv.imdecode(np.frombuffer(image.back, np.uint8) , cv.IMREAD_COLOR) if image.back != None else ImagePreprocessor._showblank()
        side = cv.imdecode(np.frombuffer(image.side, np.uint8), cv.IMREAD_COLOR) if image.back != None else ImagePreprocessor._showblank()
        cv.imshow("back", back)
        cv.imshow("side", side)
        cv.waitKey(0)
    
    