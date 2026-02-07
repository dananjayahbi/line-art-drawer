"""
Zone-Based Progressive Engine - Portrait Focal Detector
========================================================
Enhanced focal point detection for portraits using
Haar cascade face and eye detection.
Eyes and faces get highest priority as focal points.
"""

import cv2
import numpy as np
from typing import List, Dict, Any

from ..config import FocalDetectionConfig


class PortraitFocalDetector:
    """
    Enhanced focal point detection for portraits.
    Uses OpenCV Haar cascades for face and eye detection.
    Falls back gracefully if no faces found.
    """
    
    def __init__(self, config: FocalDetectionConfig = None):
        self.config = config or FocalDetectionConfig()
        self._face_cascade = None
        self._eye_cascade = None
        self._initialized = False
        self._init_cascades()
    
    def _init_cascades(self):
        """Initialize Haar cascade classifiers."""
        try:
            face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            eye_cascade_path = cv2.data.haarcascades + 'haarcascade_eye.xml'
            
            self._face_cascade = cv2.CascadeClassifier(face_cascade_path)
            self._eye_cascade = cv2.CascadeClassifier(eye_cascade_path)
            
            # Verify they loaded
            if self._face_cascade.empty() or self._eye_cascade.empty():
                print("    ⚠️  Haar cascade files not found, portrait detection disabled")
                self._initialized = False
            else:
                self._initialized = True
        except Exception as e:
            print(f"    ⚠️  Portrait detector init failed: {e}")
            self._initialized = False
    
    @property
    def available(self) -> bool:
        """Whether portrait detection is available."""
        return self._initialized and self.config.enable_portrait_detection
    
    def detect_portrait_focals(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect portrait-based focal points.
        
        Priority order:
        1. Eyes (highest priority) 
        2. Face center (secondary)
        
        Args:
            image: Input image (RGB, uint8)
            
        Returns:
            List of focal point dicts. Empty list if no faces found.
        """
        if not self.available:
            return []
        
        # Convert to grayscale for detection
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        
        # Histogram equalization to improve detection
        gray = cv2.equalizeHist(gray)
        
        focal_points = []
        
        # Detect faces
        faces = self._face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=4,
            minSize=(30, 30)
        )
        
        if len(faces) == 0:
            return []
        
        for (x, y, w, h) in faces:
            face_region = gray[y:y + h, x:x + w]
            
            # Detect eyes within the face region
            eyes = self._eye_cascade.detectMultiScale(
                face_region,
                scaleFactor=1.1,
                minNeighbors=3,
                minSize=(15, 15)
            )
            
            for (ex, ey, ew, eh) in eyes:
                # Eye center in image coordinates
                eye_cx = x + ex + ew // 2
                eye_cy = y + ey + eh // 2
                focal_points.append({
                    'point': (eye_cx, eye_cy),
                    'priority': self.config.eye_priority,
                    'type': 'eye',
                    'saliency': 1.0
                })
            
            # Face center as secondary focal
            face_cx = x + w // 2
            face_cy = y + h // 2
            focal_points.append({
                'point': (face_cx, face_cy),
                'priority': self.config.face_priority,
                'type': 'face',
                'saliency': 0.8
            })
        
        return focal_points
