import cv2 as cv
import numpy as np
import sys
import os

if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
    img = cv.imread(sys.argv[1])
else:
    img = np.zeros((400, 600, 3), dtype=np.uint8)
    cv.putText(img, "OpenCV Popup Test", (50, 200), cv.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)

window_name = "PackSentry - Received Product Images (Front | Back | Side)"
cv.namedWindow(window_name, cv.WINDOW_NORMAL)
cv.resizeWindow(window_name, 1000, 450)
cv.imshow(window_name, img)
cv.setWindowProperty(window_name, cv.WND_PROP_TOPMOST, 1)
print("Waiting for key press...", flush=True)
cv.waitKey(0)
cv.destroyAllWindows()
