import cv2
import logging
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


class Camera:
    def __init__(self, index: int = 0, width: int = 1280, height: int = 720):
        self.index = index
        self.width = width
        self.height = height
        self._cap: Optional[cv2.VideoCapture] = None

    def open(self) -> bool:
        self._cap = cv2.VideoCapture(self.index)
        if not self._cap.isOpened():
            logger.error(f"Cannot open camera {self.index}")
            return False

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._cap.set(cv2.CAP_PROP_FPS, 30)

        logger.info(f"Camera {self.index} opened: {self.width}x{self.height}")
        return True

    def read(self) -> Optional[np.ndarray]:
        if self._cap is None or not self._cap.isOpened():
            return None

        ret, frame = self._cap.read()
        if not ret:
            return None

        # Flip horizontally for natural mirror effect
        return cv2.flip(frame, 1)

    def release(self):
        if self._cap:
            self._cap.release()
            logger.info("Camera released")
