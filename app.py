import io
import os
import re
import json
import uuid
from datetime import datetime

from flask import (
    Flask, request, jsonify, send_from_directory, send_file
)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# local modules
from processor import analyze_image
from db import init_db, save_measurement, get_measurements

# ---------- Config ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
CALIBRATION_DB = os.path.join(BASE_DIR, "calibrationdb.json")
ALLOWED_EXT = {"png", "jpg", "jpeg", "webp", "bmp"}
MAX_MB = 10

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, static_folder="static", template_folder=".")
app.config["MAX_CONTENT_LENGTH"] = MAX_MB * 1024 * 1024

init_db()

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

def load_calibration_entries():
    """Load calibration entries from JSON file."""
    if not os.path.exists(CALIBRATION_DB):
        return []
    with open(CALIBRATION_DB, "r") as f:
        data = json.load(f)
    return data.get("entries", [])

def save_calibration_entries(entries):
    """Save calibration entries to JSON file."""
    entries.sort(key=lambda e: e["concentration"])
    with open(CALIBRATION_DB, "w") as f:
        json.dump({"entries": entries}, f, indent=2)

def compute_average_color(image_path: str):
    """Compute average RGB and HSV of centre 50% of image."""
    import cv2
    import numpy as np
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Could not read image")
    h, w = img.shape[:2]
    cx0, cy0 = int(w * 0.25), int(h * 0.25)
    cx1, cy1 = int(w * 0.75), int(h * 0.75)
    roi = img[cy0:cy1, cx0:cx1]
    avg_bgr = roi.mean(axis=(0, 1))
    avg_rgb = avg_bgr[::-1].tolist()
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    avg_hsv = hsv.mean(axis=(0, 1)).tolist()
    return avg_rgb, avg_hsv

# ---------- Routes ----------
@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

# ---------- Calibration API ----------
@app.route("/api/calibration", methods=["GET"])
def api_get_calibration():
    entries = load_calibration_entries()
    return jsonify({"entries": entries})

@app.route("/api/calibration", methods=["POST"])
def api_add_calibration():
    if "image" not in request.files:
        return jsonify({"error": "No image file"}), 400
    file = request.files["image"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file"}), 400

    # Parse concentration from filename: sample_<number>...
    name = file.filename
    match = re.search(r"sample_([0-9]*\.?[0-9]+)", name, re.IGNORECASE)
    if not match:
        return jsonify({"error": "Filename must contain concentration, e.g. sample_0.5ppm.jpg"}), 400
    concentration = float(match.group(1))

    # Save temporarily to compute colors
    ext = name.rsplit(".", 1)[1].lower()
    temp_path = os.path.join(UPLOAD_DIR, f"_temp_{uuid.uuid4().hex}.{ext}")
    file.save(temp_path)
    try:
        rgb, hsv = compute_average_color(temp_path)
    finally:
        os.remove(temp_path)

    # Round values
    rgb = [round(v, 3) for v in rgb]
    hsv = [round(v, 3) for v in hsv]

    entries = load_calibration_entries()
    # Avoid duplicate by filename
    entries = [e for e in entries if e["filename"] != name]
    entries.append({
        "filename": name,
        "concentration": concentration,
        "rgb": rgb,
        "hsv": hsv
    })
    save_calibration_entries(entries)
    return jsonify({"success": True, "entry": entries[-1]}), 201

@app.route("/api/calibration/<path:filename>", methods=["DELETE"])
def api_delete_calibration(filename):
    entries = load_calibration_entries()
    new_entries = [e for e in entries if e["filename"] != filename]
    if len(new_entries) == len(entries):
        return jsonify({"error": "Entry not found"}), 404
    save_calibration_entries(new_entries)
    return jsonify({"success": True})

# ---------- Analysis API ----------
@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    file = request.files.get("image") or request.files.get("file")
    if not file or file.filename == "":
        return jsonify({"error": "No image uploaded"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type"}), 400

    ext = file.filename.rsplit(".", 1)[1].lower()
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(UPLOAD_DIR, safe_name)
    file.save(save_path)

    try:
        result = analyze_image(save_path)   # uses calibrationdb.json
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {e}"}), 500

    try:
        save_measurement(result, safe_name)
    except Exception as e:
        app.logger.warning(f"Could not save measurement: {e}")

    result["image_filename"] = safe_name
    return jsonify(result)

# ---------- History API ----------
@app.route("/api/history", methods=["GET"])
def api_history():
    start = request.args.get("start") or None
    end = request.args.get("end") or None
    if end and len(end) == 10:
        end = end + "T23:59:59"
    rows = get_measurements(start, end)
    return jsonify({"measurements": rows})

@app.route("/api/history/chart", methods=["GET"])
def api_history_chart():
    start = request.args.get("start") or None
    end = request.args.get("end") or None
    if end and len(end) == 10:
        end = end + "T23:59:59"

    rows = get_measurements(start, end)

    fig, ax = plt.subplots(figsize=(8, 3.6), dpi=120)
    if not rows:
        ax.text(0.5, 0.5, "No measurements in this range",
                ha="center", va="center", fontsize=12, color="#666")
        ax.set_axis_off()
    else:
        times, values = [], []
        for r in rows:
            try:
                times.append(datetime.fromisoformat(r["timestamp"]))
                values.append(r["concentration"])
            except Exception:
                continue
        ax.plot(times, values, marker="o", linewidth=2, color="#3b82f6")
        ax.set_title("Concentration over time", fontsize=12, fontweight="bold")
        ax.set_ylabel("Concentration (ppm)")
        ax.grid(True, linestyle="--", alpha=0.4)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
        fig.autofmt_xdate()

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    resp = send_file(buf, mimetype="image/png")
    resp.headers["Cache-Control"] = "no-store, max-age=0"
    return resp

# ---------- Error handlers ----------
@app.errorhandler(413)
def too_large(_e):
    return jsonify({"error": f"File too large (max {MAX_MB} MB)."}), 413

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
