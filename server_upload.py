<<<<<<< HEAD
from flask import Flask, render_template_string, request
import os
import pandas as pd
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = "photos"
DATA_FILE = "user_reports.csv"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Upload Bin Report</title>
<style>
body { font-family: Arial, sans-serif; margin: 40px; }
input, button { margin: 8px 0; padding: 6px; font-size: 16px; }
</style>
</head>
<body>
<h2>Garbage Bin Report</h2>
<form id="reportForm" method="POST" enctype="multipart/form-data">
  <label>Name/ID: <input type="text" name="name" required></label><br>
  <label>Photo: <input type="file" name="photo" accept="image/*" capture="environment" required></label><br>
  
  <label>Latitude: <input type="text" name="lat" id="lat" readonly required></label><br>
  <label>Longitude: <input type="text" name="lon" id="lon" readonly required></label><br>
  
  <button type="button" onclick="getLocation()">Get My Location</button><br>
  <button type="submit">Submit Report</button>
</form>

<script>
function getLocation(){
    if (!navigator.geolocation) {
        alert("Geolocation is not supported by your browser.");
        return;
    }
    navigator.geolocation.getCurrentPosition(function(position){
        document.getElementById("lat").value = position.coords.latitude;
        document.getElementById("lon").value = position.coords.longitude;
        alert("Location captured! You can now submit the form.");
    }, function(error){
        alert("Location access denied or unavailable.");
    });
}
</script>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def upload_report():
    if request.method == "POST":
        name = request.form.get("name", "anon")
        lat = request.form.get("lat")
        lon = request.form.get("lon")
        photo = request.files.get("photo")

        if not lat or not lon or not photo:
            return "Missing data. Please allow location and upload a photo."

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.jpg"
        photo_path = os.path.join(UPLOAD_FOLDER, filename)
        photo.save(photo_path)

        # Append to CSV
        if not os.path.exists(DATA_FILE):
            df = pd.DataFrame(columns=["name","lat","lon","photo","timestamp","status"])
        else:
            df = pd.read_csv(DATA_FILE)
        df = pd.concat([df, pd.DataFrame([{
            "name": name,
            "lat": float(lat),
            "lon": float(lon),
            "photo": filename,
            "timestamp": timestamp,
            "status": "unvisited"
        }])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        return f"✅ Report submitted successfully for {name}. <a href='/'>Submit another</a>"

    return render_template_string(HTML_PAGE)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
=======
from flask import Flask, render_template_string, request
import os
import pandas as pd
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = "photos"
DATA_FILE = "user_reports.csv"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Upload Bin Report</title>
<style>
body { font-family: Arial, sans-serif; margin: 40px; }
input, button { margin: 8px 0; padding: 6px; font-size: 16px; }
</style>
</head>
<body>
<h2>Garbage Bin Report</h2>
<form id="reportForm" method="POST" enctype="multipart/form-data">
  <label>Name/ID: <input type="text" name="name" required></label><br>
  <label>Photo: <input type="file" name="photo" accept="image/*" capture="environment" required></label><br>
  
  <label>Latitude: <input type="text" name="lat" id="lat" readonly required></label><br>
  <label>Longitude: <input type="text" name="lon" id="lon" readonly required></label><br>
  
  <button type="button" onclick="getLocation()">Get My Location</button><br>
  <button type="submit">Submit Report</button>
</form>

<script>
function getLocation(){
    if (!navigator.geolocation) {
        alert("Geolocation is not supported by your browser.");
        return;
    }
    navigator.geolocation.getCurrentPosition(function(position){
        document.getElementById("lat").value = position.coords.latitude;
        document.getElementById("lon").value = position.coords.longitude;
        alert("Location captured! You can now submit the form.");
    }, function(error){
        alert("Location access denied or unavailable.");
    });
}
</script>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def upload_report():
    if request.method == "POST":
        name = request.form.get("name", "anon")
        lat = request.form.get("lat")
        lon = request.form.get("lon")
        photo = request.files.get("photo")

        if not lat or not lon or not photo:
            return "Missing data. Please allow location and upload a photo."

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.jpg"
        photo_path = os.path.join(UPLOAD_FOLDER, filename)
        photo.save(photo_path)

        # Append to CSV
        if not os.path.exists(DATA_FILE):
            df = pd.DataFrame(columns=["name","lat","lon","photo","timestamp","status"])
        else:
            df = pd.read_csv(DATA_FILE)
        df = pd.concat([df, pd.DataFrame([{
            "name": name,
            "lat": float(lat),
            "lon": float(lon),
            "photo": filename,
            "timestamp": timestamp,
            "status": "unvisited"
        }])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        return f"✅ Report submitted successfully for {name}. <a href='/'>Submit another</a>"

    return render_template_string(HTML_PAGE)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
>>>>>>> a8ee72ade03890e0735d53aa3bfabf6944a8f04f
