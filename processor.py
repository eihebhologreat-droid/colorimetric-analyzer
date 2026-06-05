"""
processor.py
------------
Loads `calibrationdb.json` once, and exposes:

    analyze_image(image_path) -> dict

which extracts the colour of an uploaded image and finds the
closest calibration entry using Euclidean distance in HSV space
(HSV is more robust to lighting changes than raw RGB).
"""

import json
import os
import cv2
import numpy as np

DB_FILE = "calibrationdb.json"


def _load_db():
    if not os.path.exists(DB_FILE):
        raise FileNotFoundError(
            f"'{DB_FILE}' not found. Run `python calibration.py` first."
        )
    with open(DB_FILE) as f:
        data = json.load(f)
    entries = data.get("entries", [])
    if not entries:
        raise ValueError("Calibration DB is empty.")
    return entries


def _average_color(image_path: str):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Could not read uploaded image.")

    h, w = img.shape[:2]
    cx0, cy0 = int(w * 0.25), int(h * 0.25)
    cx1, cy1 = int(w * 0.75), int(h * 0.75)
    roi = img[cy0:cy1, cx0:cx1]

    avg_bgr = roi.mean(axis=(0, 1))
    avg_rgb = avg_bgr[::-1]

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    avg_hsv = hsv.mean(axis=(0, 1))

    return avg_rgb.tolist(), avg_hsv.tolist()


def _euclidean(a, b):
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)
    return float(np.linalg.norm(a - b))


def analyze_image(image_path: str) -> dict:
    entries = _load_db()
    rgb, hsv = _average_color(image_path)

    # Compare in HSV — better for colour matching under varying brightness
    scored = []
    for e in entries:
        dist = _euclidean(hsv, e["hsv"])
        scored.append((dist, e))

    scored.sort(key=lambda x: x[0])
    best_dist, best = scored[0]

    # Confidence: closer = higher confidence (simple inverse mapping, capped)
    # 0 distance = 100%, 100 distance ≈ ~0%
    confidence = max(0.0, min(100.0, 100.0 * (1.0 - best_dist / 100.0)))

    # Top-3 nearest neighbours (useful for debugging)
    top3 = [{
        "filename": e["filename"],
        "concentration": e["concentration"],
        "distance": round(d, 3),
    } for d, e in scored[:3]]

    return {
        "concentration": best["concentration"],
        "matched_sample": best["filename"],
        "distance": round(best_dist, 3),
        "confidence_percent": round(confidence, 1),
        "measured_rgb": [round(v, 1) for v in rgb],
        "measured_hsv": [round(v, 1) for v in hsv],
        "top_matches": top3,
    }
