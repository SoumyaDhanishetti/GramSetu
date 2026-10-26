import io
import json
import os
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
import uuid

from flask import Flask, redirect, render_template, render_template_string, request, url_for
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Image uploads
UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB

PRODUCT_CATEGORIES = [
    "Food & Homemade Products",
    "Handicrafts & Handmade Items",
    "Clothing & Textiles",
    "Jewellery & Accessories",
    "Home Decor",
    "Beauty & Personal Care",
    "Agricultural Products",
    "Other",
]

PRICE_UNITS = [
    "per piece",
    "per pair",
    "per set",
    "per packet",
    "per jar",
    "per kg",
    "per 500 g",
    "per litre",
    "per metre",
    "per custom order",
]


def allowed_image(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS
    )


def save_uploaded_image(file):
    """Save an optional image and return its relative static path."""
    if not file or not file.filename:
        return ""

    if not allowed_image(file.filename):
        raise ValueError("Upload a PNG, JPG, JPEG, or WEBP image.")

    safe_name = secure_filename(file.filename)
    extension = safe_name.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{extension}"
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], unique_name))
    return f"uploads/{unique_name}"


def remove_uploaded_image(relative_path):
    """Remove only a file stored inside this app's upload directory."""
    if not relative_path:
        return
    filename = os.path.basename(relative_path)
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        app.logger.warning("Could not remove uploaded image: %s", filename)


def get_db():
    conn = sqlite3.connect(os.path.join(app.root_path, "gramsetu.db"))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables and safely add columns missing from older databases."""
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farmer TEXT NOT NULL,
                crop TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                location TEXT NOT NULL,
                contact TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller TEXT NOT NULL,
                product TEXT NOT NULL,
                price REAL NOT NULL,
                location TEXT NOT NULL,
                contact TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT ''
            )
            """
        )

        migrations = {
            "products": {
                "category": "TEXT NOT NULL DEFAULT 'Other'",
                "price_unit": "TEXT NOT NULL DEFAULT 'per piece'",
                "image": "TEXT NOT NULL DEFAULT ''",
                "owner_pin_hash": "TEXT NOT NULL DEFAULT ''",
            },
            "listings": {
                "quantity_unit": "TEXT NOT NULL DEFAULT 'kg'",
                "image": "TEXT NOT NULL DEFAULT ''",
                "price_unit": "TEXT NOT NULL DEFAULT 'per kg'",
                "description": "TEXT NOT NULL DEFAULT ''",
                "owner_pin_hash": "TEXT NOT NULL DEFAULT ''",
            },
        }

        for table, new_columns in migrations.items():
            existing = {
                row["name"]
                for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
            for column, definition in new_columns.items():
                if column not in existing:
                    conn.execute(
                        f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
                    )
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employer TEXT NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                location TEXT NOT NULL,
                wage REAL NOT NULL,
                wage_period TEXT NOT NULL DEFAULT 'per day',
                workers_needed INTEGER NOT NULL DEFAULT 1,
                contact TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'Open'
            )
        """)

        job_columns = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
        if "owner_pin_hash" not in job_columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN owner_pin_hash TEXT NOT NULL DEFAULT ''")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                applicant TEXT NOT NULL,
                skills TEXT NOT NULL DEFAULT '',
                village TEXT NOT NULL,
                contact TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        """)


init_db()

# Optional AI leaf-disease classifier; loaded only when requested.
DISEASE_MODEL_ID = "neghani/plantvillage-mobilenetv2"
_disease_classifier = None
_disease_model_error = None


def predict_leaf_disease(image_bytes):
    """Run a pretrained image classifier on an uploaded leaf image."""
    global _disease_classifier, _disease_model_error
    try:
        from PIL import Image, UnidentifiedImageError
        from transformers import pipeline
    except ImportError as exc:
        raise RuntimeError(
            "AI dependencies are not installed. Install requirements-ai.txt "
            "in the same Python environment used to run GramSetu."
        ) from exc

    if _disease_classifier is None:
        if _disease_model_error:
            raise RuntimeError(_disease_model_error)
        try:
            _disease_classifier = pipeline(
                "image-classification", model=DISEASE_MODEL_ID, device=-1
            )
        except Exception as exc:
            _disease_model_error = (
                "The AI model could not be downloaded or loaded. Check internet "
                "access, Python dependencies, and available memory, then restart GramSetu."
            )
            raise RuntimeError(_disease_model_error) from exc

    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.verify()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError(
            "This file is not a readable image. Upload a clear JPG, PNG or WEBP leaf photo."
        ) from exc

    if image.width < 80 or image.height < 80:
        raise ValueError("Image is too small. Upload a clearer leaf photo at least 80 x 80 pixels.")
    if image.width * image.height > 20_000_000:
        raise ValueError("Image dimensions are too large. Resize the photo and try again.")

    predictions = _disease_classifier(image, top_k=3)
    if not predictions:
        raise RuntimeError("The model returned no predictions. Please try another clear leaf photo.")

    best = predictions[0]
    label = str(best.get("label", "Unknown")).replace("___", " — ").replace("_", " ").strip()
    confidence = float(best.get("score", 0.0))
    alternatives = []
    for item in predictions[1:]:
        alt_label = str(item.get("label", "Unknown")).replace("___", " — ").replace("_", " ").strip()
        alternatives.append(f"{alt_label} ({float(item.get('score', 0.0)) * 100:.1f}%)")

    if confidence < 0.55:
        result = (
            f"AI screening is uncertain. The closest model category is: {label} "
            f"({confidence * 100:.1f}% model score). Do not treat this as a diagnosis."
        )
    else:
        result = f"Most likely model category: {label} ({confidence * 100:.1f}% model score)."

    if alternatives:
        result += " Other model predictions: " + "; ".join(alternatives) + "."
    result += (
        "\n\nNext steps: photograph several affected and healthy leaves in natural light; "
        "check whether symptoms are spreading; compare with local agriculture-department "
        "guidance or consult an agriculture officer before applying any treatment."
        "\n\nLimitations: this model was trained on PlantVillage-style images and may be less "
        "reliable on field photos, unfamiliar crops, mixed symptoms or poor lighting. The "
        "score is not a validated probability of disease. No pesticide or fertilizer prescription is provided."
    )
    return result


HOME = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GramSetu</title>
<style>body{font-family:Arial;background:#f4f7f0;color:#243526;margin:0}header{background:#245c3a;color:white;padding:24px 8%}main{padding:30px 8%}.card{background:white;padding:20px;border-radius:12px;margin:14px 0}a{color:#245c3a;font-weight:bold}</style></head>
<body><header><h1>🌱 GramSetu</h1><p>Connecting rural producers to better livelihoods</p></header><main><div class="card"><h2>Growing Together, Thriving Together</h2><p>Digital tools for rural producers, farming guidance and livelihoods.</p></div>
<div class="card"><h3>🌾 Farmer Marketplace</h3><a href="/marketplace">Explore marketplace</a></div><div class="card"><h3>🌿 Smart Agriculture</h3><a href="/farming">Open Smart Farming</a></div><div class="card"><h3>🧺 Rural Entrepreneurs</h3><a href="/products">Explore rural products</a></div><div class="card"><h3>👩‍🌾 Rural Employment</h3><p>Find local work, post job opportunities, and connect rural workers with employers.</p><a href="/employment">Explore Rural Employment</a></div></main></body></html>"""

@app.route("/employment", methods=["GET", "POST"])
def employment():
    if request.method == "POST":
        employer = request.form.get("employer", "").strip()
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        contact = request.form.get("contact", "").strip()
        owner_pin = request.form.get("owner_pin", "").strip()
        wage_period = request.form.get("wage_period", "per day").strip()

        try:
            wage = float(request.form.get("wage", "0"))
            workers_needed = int(request.form.get("workers_needed", "1"))
        except ValueError:
            return "Enter a valid wage and number of workers.", 400

        if not all([employer, title, category, location, contact, owner_pin]):
            return "Please complete all required fields, including your private PIN.", 400
        if not owner_pin.isdigit() or len(owner_pin) < 4 or len(owner_pin) > 12:
            return "PIN must contain 4 to 12 digits.", 400
        if wage <= 0 or workers_needed < 1:
            return "Wage and number of workers must be positive.", 400
        if wage_period not in ["per hour", "per day", "per week", "per month", "per task"]:
            return "Choose a valid wage period.", 400

        with get_db() as conn:
            conn.execute(
                """INSERT INTO jobs
                (employer, title, category, description, location,
                 wage, wage_period, workers_needed, contact, owner_pin_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (employer, title, category, description, location,
                 wage, wage_period, workers_needed, contact, generate_password_hash(owner_pin)),
            )
        return redirect(url_for("employment"))

    with get_db() as conn:
        jobs = conn.execute(
            "SELECT * FROM jobs ORDER BY id DESC"
        ).fetchall()

    return render_template("employment.html", jobs=jobs)


@app.route("/employment/apply/<int:job_id>", methods=["POST"])
def apply_for_job(job_id):
    applicant = request.form.get("applicant", "").strip()
    skills = request.form.get("skills", "").strip()
    village = request.form.get("village", "").strip()
    contact = request.form.get("contact", "").strip()

    if not all([applicant, village, contact]):
        return "Name, village and contact are required.", 400

    with get_db() as conn:
        job = conn.execute(
            "SELECT id FROM jobs WHERE id = ? AND status = 'Open'",
            (job_id,),
        ).fetchone()

        if job is None:
            return "This job is no longer available.", 404

        conn.execute(
            """INSERT INTO job_applications
            (job_id, applicant, skills, village, contact)
            VALUES (?, ?, ?, ?, ?)""",
            (job_id, applicant, skills, village, contact),
        )

    return redirect(url_for("employment"))


@app.route("/employment/status/<int:job_id>", methods=["POST"])
def update_job_status(job_id):
    action = request.form.get("action", "").strip()

    if action not in ["close", "reopen"]:
        return "Invalid job status action.", 400

    new_status = "Closed" if action == "close" else "Open"

    with get_db() as conn:
        job = conn.execute(
            "SELECT id, owner_pin_hash FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()

        if job is None:
            return "Job not found.", 404
        if not job["owner_pin_hash"]:
            return "This older job has no owner PIN. It cannot be managed with PIN verification.", 403
        if not check_password_hash(job["owner_pin_hash"], request.form.get("owner_pin", "").strip()):
            return "Incorrect owner PIN. No changes were made.", 403

        conn.execute(
            "UPDATE jobs SET status = ? WHERE id = ?",
            (new_status, job_id),
        )

    return redirect(url_for("employment"))



@app.route("/marketplace/delete/<int:item_id>", methods=["POST"])
def delete_listing(item_id):
    pin = request.form.get("owner_pin", "").strip()
    with get_db() as conn:
        item = conn.execute("SELECT owner_pin_hash, image FROM listings WHERE id = ?", (item_id,)).fetchone()
        if item is None:
            return "Listing not found.", 404
        if not item["owner_pin_hash"]:
            return "This older listing has no owner PIN and cannot be deleted through PIN verification.", 403
        if not check_password_hash(item["owner_pin_hash"], pin):
            return "Incorrect owner PIN. Listing was not deleted.", 403
        conn.execute("DELETE FROM listings WHERE id = ?", (item_id,))
        image_path = item["image"]
    remove_uploaded_image(image_path)
    return redirect(url_for("marketplace"))


@app.route("/products/delete/<int:item_id>", methods=["POST"])
def delete_product(item_id):
    pin = request.form.get("owner_pin", "").strip()
    with get_db() as conn:
        item = conn.execute("SELECT owner_pin_hash, image FROM products WHERE id = ?", (item_id,)).fetchone()
        if item is None:
            return "Product not found.", 404
        if not item["owner_pin_hash"]:
            return "This older product has no owner PIN and cannot be deleted through PIN verification.", 403
        if not check_password_hash(item["owner_pin_hash"], pin):
            return "Incorrect owner PIN. Product was not deleted.", 403
        conn.execute("DELETE FROM products WHERE id = ?", (item_id,))
        image_path = item["image"]
    remove_uploaded_image(image_path)
    return redirect(url_for("products"))


@app.route("/employment/delete/<int:job_id>", methods=["POST"])
def delete_job(job_id):
    pin = request.form.get("owner_pin", "").strip()
    with get_db() as conn:
        job = conn.execute("SELECT owner_pin_hash FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if job is None:
            return "Job not found.", 404
        if not job["owner_pin_hash"]:
            return "This older job has no owner PIN and cannot be deleted through PIN verification.", 403
        if not check_password_hash(job["owner_pin_hash"], pin):
            return "Incorrect owner PIN. Job was not deleted.", 403
        conn.execute("DELETE FROM job_applications WHERE job_id = ?", (job_id,))
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    return redirect(url_for("employment"))

@app.route("/")
def home():
    return render_template_string(HOME)


@app.route("/marketplace", methods=["GET", "POST"])
def marketplace():
    if request.method == "POST":
        try:
            farmer = request.form.get("farmer", "").strip()
            crop = request.form.get("crop", "").strip()
            quantity = float(request.form.get("quantity", "0"))
            quantity_unit = request.form.get("quantity_unit", "kg").strip()
            price = float(request.form.get("price", "0"))
            location = request.form.get("location", "").strip()
            contact = request.form.get("contact", "").strip()
            description = request.form.get("description", "").strip()
            owner_pin = request.form.get("owner_pin", "").strip()
            price_unit = request.form.get("price_unit", "per kg").strip()

            if not all([farmer, crop, location, contact, owner_pin]):
                return "Please complete all required fields, including your private PIN.", 400
            if not owner_pin.isdigit() or len(owner_pin) < 4 or len(owner_pin) > 12:
                return "PIN must contain 4 to 12 digits.", 400
            if quantity <= 0 or price <= 0:
                return "Quantity and price must be positive.", 400

            allowed_quantity_units = [
                "kg", "g", "pieces", "dozens", "bags", "quintals", "tonnes"
            ]
            if quantity_unit not in allowed_quantity_units:
                return "Please select a valid quantity unit.", 400

            allowed_units = [
                "per kg", "per quintal", "per tonne", "per bag", "per dozen", "per piece"
            ]
            if price_unit not in allowed_units:
                return "Please select a valid price unit.", 400

            image_path = save_uploaded_image(request.files.get("image"))
        except (ValueError, TypeError) as exc:
            return str(exc) or "Enter valid listing details.", 400

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO listings
                (farmer, crop, quantity, quantity_unit, price, location, contact, image, price_unit, description, owner_pin_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    farmer, crop, quantity, quantity_unit, price,
                    location, contact, image_path, price_unit, description, generate_password_hash(owner_pin)
                ),
            )
        return redirect(url_for("marketplace"))

    with get_db() as conn:
        listings = conn.execute("SELECT * FROM listings ORDER BY id DESC").fetchall()
    return render_template("marketplace.html", listings=listings)


CROPS = {
    "paddy": {"name": "Paddy (rice)", "ph": (5.5, 7.0), "water": "High", "yield": 1800, "price": 23, "cost": 18000, "soil": "Clay-loam/loamy soil may suit rice where water management is possible."},
    "cotton": {"name": "Cotton", "ph": (5.5, 8.0), "water": "Moderate", "yield": 700, "price": 70, "cost": 22000, "soil": "Well-drained loamy to black soils are often used; avoid waterlogging."},
    "maize": {"name": "Maize", "ph": (5.5, 7.5), "water": "Moderate", "yield": 1600, "price": 22, "cost": 14000, "soil": "Well-drained loamy soil is generally favourable."},
    "red_gram": {"name": "Red gram", "ph": (5.5, 7.5), "water": "Low-moderate", "yield": 450, "price": 75, "cost": 12000, "soil": "Well-drained soil is important; prolonged waterlogging is harmful."},
    "groundnut": {"name": "Groundnut", "ph": (5.5, 7.0), "water": "Moderate", "yield": 700, "price": 55, "cost": 16000, "soil": "Loose, well-drained sandy-loam soils are commonly preferred."},
    "soybean": {"name": "Soybean", "ph": (6.0, 7.5), "water": "Moderate", "yield": 650, "price": 46, "cost": 14000, "soil": "Well-drained loamy soils are commonly preferred."},
    "millets": {"name": "Millets", "ph": (5.5, 7.5), "water": "Low", "yield": 700, "price": 30, "cost": 9000, "soil": "Some millet varieties tolerate lower rainfall; local suitability varies."},
    "chickpea": {"name": "Chickpea", "ph": (6.0, 8.0), "water": "Low", "yield": 500, "price": 60, "cost": 11000, "soil": "Well-drained soils are important; avoid excess irrigation."},
}


def soil_advice(form):
    crop = form.get("crop", "")
    soil = form.get("soil", "")
    water = form.get("water", "")
    if crop not in CROPS or soil not in {"unknown", "sandy", "clay", "loamy"} or water not in {"limited", "moderate", "plenty"}:
        return ["Please choose valid crop, soil and water options."]

    crop_info = CROPS[crop]
    tips = [f"{crop_info['name']}: {crop_info['soil']}"]
    phraw = form.get("ph", "").strip()
    if phraw:
        try:
            ph = float(phraw)
        except ValueError:
            return ["Soil pH must be a number from 0 to 14."]
        if not 0 <= ph <= 14:
            return ["Soil pH must be a number from 0 to 14."]
        low, high = crop_info["ph"]
        tips.append(
            f"Entered pH {ph:g}; broad reference range for this crop is {low}–{high}. "
            "Confirm with a soil lab and local recommendations."
        )
    else:
        tips.append("Add measured soil pH from a soil test for a better assessment.")

    nutrient_labels = [("nitrogen", "N"), ("phosphorus", "P"), ("potassium", "K")]
    recorded = []
    for key, label in nutrient_labels:
        raw = form.get(key, "").strip()
        if raw:
            try:
                value = float(raw)
                if value < 0:
                    raise ValueError
                recorded.append(f"{label}={value:g}")
            except ValueError:
                return [f"{label} must be a non-negative number."]

    if recorded:
        tips.append(
            "Recorded lab values: " + ", ".join(recorded) + ". Interpret using the lab's units "
            "and crop-specific advice; this app does not prescribe fertilizer doses."
        )
    else:
        tips.append("NPK values are optional; enter them only from a soil-test report.")

    tips.append({
        "sandy": "Sandy soil drains quickly; monitor moisture and ask about organic matter.",
        "clay": "Clay soil may drain slowly; avoid waterlogging.",
        "loamy": "Loamy soil can suit many crops, but drainage and test results still matter.",
        "unknown": "Soil type is unknown; consider a soil test.",
    }[soil])
    tips.append({
        "limited": "Water is limited: compare locally suitable low-water crops and use water-saving practices.",
        "moderate": "Schedule irrigation using rainfall, crop stage and actual soil moisture.",
        "plenty": "Abundant water does not mean more irrigation is needed; prevent waterlogging.",
    }[water])
    tips.append("Use soil-test recommendations and state agriculture guidance before applying fertilizer or pesticides.")
    return tips


@app.route("/farming", methods=["GET", "POST"])
def farming():
    suggestions = []
    weather = None
    irrigation = None
    market = None
    disease = None
    active = ""

    if request.method == "POST":
        action = request.form.get("action", "soil")
        active = action

        if action == "soil":
            suggestions = soil_advice(request.form)

        elif action == "weather":
            location = request.form.get("weather_location", "").strip()
            crop = request.form.get("weather_crop", "paddy")
            try:
                if not location or crop not in CROPS:
                    raise ValueError
                query = urllib.parse.urlencode({"name": location, "count": 1, "language": "en", "format": "json"})
                req = urllib.request.Request(
                    "https://geocoding-api.open-meteo.com/v1/search?" + query,
                    headers={"User-Agent": "GramSetu/1.0"},
                )
                with urllib.request.urlopen(req, timeout=8) as response:
                    places = json.loads(response.read().decode()).get("results", [])

                if not places:
                    weather = {"error": "Location not found. Try a nearby town or district."}
                else:
                    place = places[0]
                    params = urllib.parse.urlencode({
                        "latitude": place["latitude"],
                        "longitude": place["longitude"],
                        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum",
                        "timezone": "auto",
                        "forecast_days": 5,
                    })
                    req = urllib.request.Request(
                        "https://api.open-meteo.com/v1/forecast?" + params,
                        headers={"User-Agent": "GramSetu/1.0"},
                    )
                    with urllib.request.urlopen(req, timeout=8) as response:
                        daily = json.loads(response.read().decode()).get("daily", {})
                    weather = {
                        "place": ", ".join(x for x in [place.get("name"), place.get("admin1"), place.get("country")] if x),
                        "crop": CROPS[crop]["name"],
                        "days": [],
                    }
                    for index, day in enumerate(daily.get("time", [])):
                        weather["days"].append([
                            day,
                            daily.get("temperature_2m_min", [None] * 5)[index],
                            daily.get("temperature_2m_max", [None] * 5)[index],
                            daily.get("precipitation_probability_max", [None] * 5)[index],
                            daily.get("precipitation_sum", [None] * 5)[index],
                        ])
            except (ValueError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError):
                weather = {"error": "Could not retrieve forecast. Check location and internet connection."}

        elif action == "irrigation":
            try:
                moisture = float(request.form.get("moisture", ""))
                threshold = float(request.form.get("threshold", "35"))
                if not (0 <= moisture <= 100 and 0 <= threshold <= 100):
                    raise ValueError
                irrigation = (
                    "Below chosen threshold: check crop needs and field before irrigating."
                    if moisture < threshold
                    else "At or above threshold: check crop stage and field before irrigating."
                )
            except ValueError:
                irrigation = "Enter valid moisture and threshold values from 0 to 100."

        elif action == "market":
            try:
                area = float(request.form.get("area", ""))
                water = request.form.get("plan_water", "moderate")
                soil = request.form.get("plan_soil", "loamy")
                if area <= 0 or area > 100000:
                    raise ValueError
                rows = []
                for key, crop_info in CROPS.items():
                    score = 50
                    if water == "limited":
                        score += 12 if key in {"millets", "red_gram", "chickpea"} else (-12 if key == "paddy" else 0)
                    if soil == "sandy":
                        score += 8 if key in {"groundnut", "millets"} else (-5 if key == "paddy" else 0)
                    elif soil == "clay" and key in {"paddy", "cotton"}:
                        score += 6
                    elif soil == "loamy" and key in {"maize", "soybean", "chickpea"}:
                        score += 5
                    revenue = area * crop_info["yield"] * crop_info["price"]
                    cost = area * crop_info["cost"]
                    rows.append({
                        "name": crop_info["name"],
                        "score": max(25, min(80, score)),
                        "price": crop_info["price"],
                        "yield": crop_info["yield"],
                        "revenue": round(revenue),
                        "cost": round(cost),
                        "profit": round(revenue - cost),
                        "water": crop_info["water"],
                    })
                rows.sort(key=lambda item: (item["score"], item["profit"]), reverse=True)
                market = {"area": area, "rows": rows}
            except ValueError:
                market = {"error": "Enter valid land area greater than zero."}

        elif action == "disease":
            file = request.files.get("leaf_image")
            extension = file.filename.rsplit(".", 1)[-1].lower() if file and "." in file.filename else ""
            if not file or not file.filename or extension not in ALLOWED_IMAGE_EXTENSIONS:
                disease = "Choose a PNG, JPG, JPEG or WEBP leaf image."
            else:
                try:
                    image_bytes = file.read()
                    if not image_bytes:
                        raise ValueError("The uploaded file is empty. Choose a leaf photo and try again.")
                    disease = predict_leaf_disease(image_bytes)
                except (ValueError, RuntimeError) as exc:
                    disease = str(exc)
                except Exception:
                    disease = "AI screening failed unexpectedly. Please try another image. No diagnosis was produced."

    return render_template(
        "farming.html",
        suggestions=suggestions,
        weather=weather,
        irrigation=irrigation,
        market=market,
        disease=disease,
        active=active,
        crops=CROPS,
    )


@app.route("/products", methods=["GET", "POST"])
def products():
    if request.method == "POST":
        try:
            seller = request.form.get("seller", "").strip()
            product = request.form.get("product", "").strip()
            category = request.form.get("category", "Other").strip()
            price = float(request.form.get("price", "0"))
            price_unit = request.form.get("price_unit", "per piece").strip()
            location = request.form.get("location", "").strip()
            contact = request.form.get("contact", "").strip()
            description = request.form.get("description", "").strip()
            owner_pin = request.form.get("owner_pin", "").strip()

            if not all([seller, product, location, contact, owner_pin]):
                raise ValueError("Please complete all required fields, including your private PIN.")
            if not owner_pin.isdigit() or len(owner_pin) < 4 or len(owner_pin) > 12:
                raise ValueError("PIN must contain 4 to 12 digits.")
            if price <= 0:
                raise ValueError("Price must be greater than zero.")
            if category not in PRODUCT_CATEGORIES:
                raise ValueError("Please choose a valid category.")
            if price_unit not in PRICE_UNITS:
                raise ValueError("Please choose a valid price unit.")
            image_path = save_uploaded_image(request.files.get("image"))
        except ValueError as exc:
            return str(exc), 400

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO products
                (seller, product, price, location, contact, description, category, price_unit, image, owner_pin_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (seller, product, price, location, contact, description, category, price_unit, image_path, generate_password_hash(owner_pin)),
            )
        return redirect(url_for("products"))

    with get_db() as conn:
        product_list = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    return render_template(
        "products.html",
        products=product_list,
        categories=PRODUCT_CATEGORIES,
        price_units=PRICE_UNITS,
    )


if __name__ == "__main__":
    app.run(debug=True)
