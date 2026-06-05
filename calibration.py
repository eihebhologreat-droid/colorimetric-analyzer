"""
calibration.py
--------------
Reads every image in the `samples/` folder, extracts its average colour
(both RGB and HSV), and writes them to `calibrationdb.json`.

Sample filename convention:
    sample_<concentration><unit>.<ext>
Examples:
    sample_0.0ppm.jpg
    sample_0.5ppm.jpg
    sample_2.0ppm.png

The number directly after `sample_` and before the unit is parsed
as the concentration value.

Run it from the project folder:
    python calibration.py
"""

import os
import re
import json
import cv2
import numpy as np

SAMPLES_DIR = "samples"
DB_FILE = "calibrationdb.json"

# Regex: capture a number (int or float) right after "sample_"
FILENAME_RE = re.compile(r"sample_([0-9]*\.?[0-9]+)", re.IGNORECASE)


def get_average_color(image_path: str):
    """Return the average BGR, RGB and HSV colour of the centre region of an image."""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")

    # Use the centre 50% of the image to avoid background/edges
    h, w = img.shape[:2]
    cx0, cy0 = int(w * 0.25), int(h * 0.25)
    cx1, cy1 = int(w * 0.75), int(h * 0.75)
    roi = img[cy0:cy1, cx0:cx1]

    # OpenCV uses BGR
    avg_bgr = roi.mean(axis=(0, 1))           # [B, G, R]
    avg_rgb = avg_bgr[::-1]                   # [R, G, B]

    # Convert ROI to HSV and average
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    avg_hsv = hsv.mean(axis=(0, 1))           # [H, S, V]

    return avg_rgb.tolist(), avg_hsv.tolist()


def build_calibration_db():
    if not os.path.isdir(SAMPLES_DIR):
        raise SystemExit(
            f"❌ Folder '{SAMPLES_DIR}/' not found. "
            f"Create it and add your sample images first."
        )

    entries = []
    files = sorted(os.listdir(SAMPLES_DIR))
    if not files:
        raise SystemExit(f"❌ No files in '{SAMPLES_DIR}/'.")

    print(f"📂 Scanning {len(files)} file(s) in '{SAMPLES_DIR}/'...\n")

    for fname in files:
        path = os.path.join(SAMPLES_DIR, fname)
        if not os.path.isfile(path):
            continue

        match = FILENAME_RE.search(fname)
        if not match:
            print(f"  ⚠️  Skipping '{fname}' (no concentration in filename)")
            continue

        concentration = float(match.group(1))

        try:
            rgb, hsv = get_average_color(path)
        except Exception as e:
            print(f"  ❌ {fname}: {e}")
            continue

        entries.append({
            "filename": fname,
            "concentration": concentration,
            "rgb": [round(v, 3) for v in rgb],
            "hsv": [round(v, 3) for v in hsv],
        })

        print(f"  ✅ {fname:30s}  conc={concentration:<6}  "
              f"RGB=({rgb[0]:6.1f},{rgb[1]:6.1f},{rgb[2]:6.1f})  "
              f"HSV=({hsv[0]:6.1f},{hsv[1]:6.1f},{hsv[2]:6.1f})")

    if not entries:
        raise SystemExit("\n❌ No valid samples processed.")

    # Sort by concentration so the DB is easy to read
    entries.sort(key=lambda e: e["concentration"])

    with open(DB_FILE, "w") as f:
        json.dump({"entries": entries}, f, indent=2)

    print(f"\n💾 Wrote {len(entries)} entries to '{DB_FILE}'")


if __name__ == "__main__":
    build_calibration_db()
