# Colorimetric Concentration Prototype

A minimal Flask + HTML/JS web prototype that:
1. Builds a calibration database from sample images of known concentrations.
2. Lets a user upload a new image.
3. Returns the closest-matching concentration using Euclidean distance in HSV colour space.

---

## 📁 Project structure

```
colorimetric_prototype/
├── app.py                # Flask web server
├── calibration.py        # Builds calibrationdb.json from samples/
├── processor.py          # Loads DB and matches uploaded images
├── requirements.txt      # Python dependencies
├── samples/              # ⬅️ PUT YOUR REFERENCE IMAGES HERE
├── uploads/              # Temporarily holds user-uploaded files
├── templates/
│   └── index.html        # The web page
└── static/
    ├── style.css
    └── app.js
```

---

## 🪜 Step-by-step setup (complete beginner)

### 1. Install Python 3.10 or newer
Download from <https://www.python.org/downloads/>.
On Windows: tick **"Add Python to PATH"** during install.

Verify:
```bash
python --version
```

### 2. Open a terminal in this folder
- **Windows**: open the folder in File Explorer → click the address bar → type `cmd` → Enter.
- **Mac/Linux**: open Terminal → `cd /path/to/colorimetric_prototype`.

### 3. Create a virtual environment (keeps deps isolated)
```bash
python -m venv venv
```
Activate it:
- **Windows**: `venv\Scripts\activate`
- **Mac/Linux**: `source venv/bin/activate`

You should see `(venv)` at the start of your prompt.

### 4. Install the libraries
```bash
pip install -r requirements.txt
```

### 5. Add your reference samples
Put your photos into the `samples/` folder.
**Filename must contain the concentration**, like:

```
sample_0.0ppm.jpg
sample_0.5ppm.jpg
sample_1.0ppm.jpg
sample_2.0ppm.jpg
sample_5.0ppm.jpg
```

Tips for good samples:
- Same lighting for every photo.
- Same distance / camera angle.
- Fill the frame with the colour (the script analyses the centre 50%).
- White background helps consistency.

### 6. Build the calibration database
```bash
python calibration.py
```

This creates **`calibrationdb.json`**. You should see a table of RGB/HSV values per sample. Re-run any time you add or change samples.

### 7. Start the web app
```bash
python app.py
```

Open <http://127.0.0.1:5000> in your browser.

### 8. Use it
1. Click the upload box → choose a photo of an unknown sample.
2. Click **Analyze Sample**.
3. Read the predicted concentration.

---

## 🧠 How it works (in plain English)

- **calibration.py** opens each sample image, crops the centre 50%, computes the average RGB and HSV colour, and saves it next to the concentration parsed from the filename.
- **processor.py** does the same on an uploaded image, then computes the **Euclidean distance** in HSV space between the new colour and each calibration entry. Smallest distance wins.
- **HSV** is used (not raw RGB) because **Hue** is more stable when lighting changes brightness.
- **app.py** is the glue: Flask serves the HTML page and exposes `/analyze` which takes the file, runs `processor.analyze_image()`, and returns JSON.

---

## 🧪 Quick test without real samples
You can test the pipeline using solid-colour images:
1. Open Paint/Preview/any editor.
2. Save 3–4 plain-colour squares as `sample_1.0ppm.png`, `sample_2.0ppm.png`, etc.
3. Run `python calibration.py` then `python app.py`.
4. Upload another colour square and watch the match.

---

## 🚧 Next steps (after the prototype works)

- **Save results to a database** (SQLite is built into Python — perfect first step).
- **Date-stamped history page** with search + printable PDF report.
- **Camera capture** in the browser via `getUserMedia`.
- **Interpolation** between calibration points instead of nearest-neighbour, for continuous values.
- **Reference card** in the photo (e.g. a white square) for automatic white-balance correction.

---

## ❓ Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: cv2` | Run `pip install -r requirements.txt` inside the active venv. |
| `calibrationdb.json not found` | Run `python calibration.py` first. |
| `No valid samples processed` | Check that filenames contain a number, e.g. `sample_1.5ppm.jpg`. |
| Browser shows "Connection refused" | Make sure `python app.py` is still running in the terminal. |
| Predictions feel wrong | Take new photos under consistent lighting; HSV helps but isn't magic. |
