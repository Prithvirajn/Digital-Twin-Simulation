<<<<<<< HEAD
from flask import Flask, request, jsonify
import pandas as pd
import os

app = Flask(__name__)

CSV_FILE = "user_reports.csv"

# Ensure CSV exists
if not os.path.exists(CSV_FILE):
    df = pd.DataFrame(columns=["name","email","lat","lon","timestamp","photo","status"])
    df.to_csv(CSV_FILE, index=False)

@app.route("/report", methods=["POST"])
def report():
    data = request.json
    if not data:
        return jsonify({"error": "No data received"}), 400

    df = pd.read_csv(CSV_FILE)
    df = df.append({
        "name": data.get("name"),
        "email": data.get("email"),
        "lat": data.get("lat"),
        "lon": data.get("lon"),
        "timestamp": data.get("timestamp"),
        "photo": data.get("photo"),
        "status": "unvisited"
    }, ignore_index=True)
    df.to_csv(CSV_FILE, index=False)

    return jsonify({"message": "Report saved successfully"}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
=======
from flask import Flask, request, jsonify
import pandas as pd
import os

app = Flask(__name__)

CSV_FILE = "user_reports.csv"

# Ensure CSV exists
if not os.path.exists(CSV_FILE):
    df = pd.DataFrame(columns=["name","email","lat","lon","timestamp","photo","status"])
    df.to_csv(CSV_FILE, index=False)

@app.route("/report", methods=["POST"])
def report():
    data = request.json
    if not data:
        return jsonify({"error": "No data received"}), 400

    df = pd.read_csv(CSV_FILE)
    df = df.append({
        "name": data.get("name"),
        "email": data.get("email"),
        "lat": data.get("lat"),
        "lon": data.get("lon"),
        "timestamp": data.get("timestamp"),
        "photo": data.get("photo"),
        "status": "unvisited"
    }, ignore_index=True)
    df.to_csv(CSV_FILE, index=False)

    return jsonify({"message": "Report saved successfully"}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
>>>>>>> a8ee72ade03890e0735d53aa3bfabf6944a8f04f
