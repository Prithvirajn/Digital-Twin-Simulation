<<<<<<< HEAD
from flask import Flask, request, jsonify, send_file
import csv, os, base64
from datetime import datetime

app = Flask(__name__)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, "data.html")
PHOTO_FOLDER = os.path.join(BASE_DIR, "photos")
os.makedirs(PHOTO_FOLDER, exist_ok=True)
CSV_FILE = os.path.join(BASE_DIR, "user_reports.csv")

# Serve HTML
@app.route("/", methods=["GET"])
@app.route("/data.html", methods=["GET"])
def serve_html():
    if os.path.exists(HTML_FILE):
        return send_file(HTML_FILE)
    return "HTML file not found", 404

# Handle report POST
@app.route("/report", methods=["POST"])
def report():
    data = request.get_json()
    if not data:
        return jsonify({"status":"error","message":"No data received"}),400

    # Save photo
    photo_filename = None
    if "photo" in data and data["photo"].startswith("data:image"):
        try:
            header, encoded = data["photo"].split(",",1)
            img_bytes = base64.b64decode(encoded)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = data.get("name","user").replace(" ","_")
            photo_filename = f"{safe_name}_{timestamp}.png"
            with open(os.path.join(PHOTO_FOLDER, photo_filename), "wb") as f:
                f.write(img_bytes)
        except Exception as e:
            print("Error saving photo:", e)

    # Save to CSV
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["name","email","lat","lon","timestamp","photo_file","status"])
        writer.writerow([
            data.get("name"),
            data.get("email"),
            data.get("lat"),
            data.get("lon"),
            data.get("timestamp"),
            photo_filename if photo_filename else "N/A",
            "unvisited"
        ])

    return jsonify({"status":"success","message":"Report saved!"})

# ---------------- ADD USER-REPORTED BINS ----------------
for b in all_bins:
    if b.get("is_user_report"):
        folium.Marker(
            location=[b["lat"], b["lon"]],
            popup=f"User Report from {b['report_source']}<br>{b['photo']}<br>{b['timestamp']}",
            icon=folium.Icon(color="red", icon="exclamation-triangle", prefix="fa")
        ).add_to(m)


if __name__ == "__main__":
    print(f"Serving HTML from: {HTML_FILE}")
    app.run(debug=True)
=======
from flask import Flask, request, jsonify, send_file
import csv, os, base64
from datetime import datetime

app = Flask(__name__)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, "data.html")
PHOTO_FOLDER = os.path.join(BASE_DIR, "photos")
os.makedirs(PHOTO_FOLDER, exist_ok=True)
CSV_FILE = os.path.join(BASE_DIR, "user_reports.csv")

# Serve HTML
@app.route("/", methods=["GET"])
@app.route("/data.html", methods=["GET"])
def serve_html():
    if os.path.exists(HTML_FILE):
        return send_file(HTML_FILE)
    return "HTML file not found", 404

# Handle report POST
@app.route("/report", methods=["POST"])
def report():
    data = request.get_json()
    if not data:
        return jsonify({"status":"error","message":"No data received"}),400

    # Save photo
    photo_filename = None
    if "photo" in data and data["photo"].startswith("data:image"):
        try:
            header, encoded = data["photo"].split(",",1)
            img_bytes = base64.b64decode(encoded)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = data.get("name","user").replace(" ","_")
            photo_filename = f"{safe_name}_{timestamp}.png"
            with open(os.path.join(PHOTO_FOLDER, photo_filename), "wb") as f:
                f.write(img_bytes)
        except Exception as e:
            print("Error saving photo:", e)

    # Save to CSV
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["name","email","lat","lon","timestamp","photo_file","status"])
        writer.writerow([
            data.get("name"),
            data.get("email"),
            data.get("lat"),
            data.get("lon"),
            data.get("timestamp"),
            photo_filename if photo_filename else "N/A",
            "unvisited"
        ])

    return jsonify({"status":"success","message":"Report saved!"})

# ---------------- ADD USER-REPORTED BINS ----------------
for b in all_bins:
    if b.get("is_user_report"):
        folium.Marker(
            location=[b["lat"], b["lon"]],
            popup=f"User Report from {b['report_source']}<br>{b['photo']}<br>{b['timestamp']}",
            icon=folium.Icon(color="red", icon="exclamation-triangle", prefix="fa")
        ).add_to(m)


if __name__ == "__main__":
    print(f"Serving HTML from: {HTML_FILE}")
    app.run(debug=True)
>>>>>>> a8ee72ade03890e0735d53aa3bfabf6944a8f04f
