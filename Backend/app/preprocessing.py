from schemas import Image
import cv2 as cv
import numpy as np
import threading
import os

class ImagePreprocessor:

    @staticmethod
    def _prepare_panel(raw_bytes, label: str):
        if not raw_bytes:
            panel = np.zeros((450, 300, 3), dtype=np.uint8)
            cv.putText(panel, f"No {label}", (50, 225), cv.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            return panel

        img = cv.imdecode(np.frombuffer(raw_bytes, np.uint8), cv.IMREAD_COLOR)
        if img is None:
            panel = np.zeros((450, 300, 3), dtype=np.uint8)
            cv.putText(panel, f"Invalid {label}", (50, 225), cv.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            return panel

        h, w = img.shape[:2]
        target_h = 450
        new_w = max(int(w * (target_h / h)), 100)
        resized = cv.resize(img, (new_w, target_h))

        # Add label overlay banner
        cv.rectangle(resized, (0, 0), (new_w, 40), (20, 20, 20), -1)
        cv.putText(resized, label, (15, 28), cv.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        return resized

    @staticmethod
    def show(image: Image):
        try:
            front_panel = ImagePreprocessor._prepare_panel(image.front, "Front View")
            back_panel = ImagePreprocessor._prepare_panel(image.back, "Back View")
            side_panel = ImagePreprocessor._prepare_panel(image.side, "Side View")

            combined = np.hstack([front_panel, back_panel, side_panel])

            window_name = "PackSentry - Received Product Images (Front | Back | Side)"
            cv.namedWindow(window_name, cv.WINDOW_NORMAL)
            cv.resizeWindow(window_name, 1000, 450)
            cv.imshow(window_name, combined)
            cv.setWindowProperty(window_name, cv.WND_PROP_TOPMOST, 1)

            print(f"\n[ImagePreprocessor] >>> OpenCV Window '{window_name}' displayed on screen! <<<", flush=True)
            print("[ImagePreprocessor] Press any key on the image window to close it and return to Flutter.\n", flush=True)

            cv.waitKey(0)
            cv.destroyAllWindows()
        except Exception as e:
            print(f"[ImagePreprocessor] Error showing GUI: {e}", flush=True)


    
    