
from flask import Flask, request, jsonify, render_template_string
from pathlib import Path
from datetime import datetime, timezone
import json
import csv

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
LOCATION_FILE = BASE_DIR / "location.json"
CSV_FILE = BASE_DIR / "location.csv"

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>DriveSafe AI - Live Location</title>
    <link rel="stylesheet"
          href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
    <style>
        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f5f5f0;
            color: #242820;
        }
        header {
            padding: 20px;
            background: #202820;
            color: white;
        }
        main { padding: 20px; }
        button {
            padding: 12px 18px;
            background: #d97736;
            color: white;
            border: 0;
            border-radius: 8px;
            cursor: pointer;
            font-size: 15px;
        }
        #status { margin: 16px 0; }
        #coordinates {
            padding: 14px;
            background: white;
            border-radius: 8px;
            margin-bottom: 16px;
            line-height: 1.8;
        }
        #map {
            height: 430px;
            width: 100%;
            border-radius: 10px;
        }
    </style>
</head>
<body>
<header>
    <h2>DriveSafe AI</h2>
    <div>Actual Laptop Location Tracking</div>
</header>
<main>
    <h3>Live GPS Location</h3>
    <button onclick="startTracking()">Start Tracking</button>
    <button onclick="stopTracking()">Stop Tracking</button>
    <div id="status">Tracking has not started.</div>
    <div id="coordinates">
        Latitude: --<br>
        Longitude: --<br>
        Accuracy: --<br>
        Last update: --
    </div>
    <div id="map"></div>
</main>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
    const map = L.map('map').setView([19.0760, 72.8777], 10);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    let marker = null;
    let accuracyCircle = null;
    let watchId = null;

    function startTracking() {
        if (!navigator.geolocation) {
            document.getElementById('status').textContent =
                'This browser does not support location services.';
            return;
        }

        if (watchId !== null) {
            document.getElementById('status').textContent =
                'Location tracking is already running.';
            return;
        }

        document.getElementById('status').textContent =
            'Requesting location permission...';

        watchId = navigator.geolocation.watchPosition(
            async function(position) {
                const latitude = position.coords.latitude;
                const longitude = position.coords.longitude;
                const accuracy = position.coords.accuracy;

                const now = new Date().toLocaleString();

                document.getElementById('status').textContent =
                    'Location received successfully.';

                document.getElementById('coordinates').innerHTML =
                    'Latitude: ' + latitude + '<br>' +
                    'Longitude: ' + longitude + '<br>' +
                    'Accuracy: ' + Math.round(accuracy) + ' metres<br>' +
                    'Last update: ' + now;

                const point = [latitude, longitude];

                if (!marker) {
                    marker = L.marker(point).addTo(map);
                    accuracyCircle = L.circle(point, {
                        radius: accuracy
                    }).addTo(map);
                    map.setView(point, 16);
                } else {
                    marker.setLatLng(point);
                    accuracyCircle.setLatLng(point);
                    accuracyCircle.setRadius(accuracy);
                }

                marker.bindPopup('Actual reported laptop location').openPopup();

                try {
                    const response = await fetch('/save_location', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            latitude: latitude,
                            longitude: longitude,
                            accuracy: accuracy
                        })
                    });

                    if (!response.ok) {
                        throw new Error('Server could not save location');
                    }
                } catch (error) {
                    document.getElementById('status').textContent =
                        'Location received, but saving failed: ' + error.message;
                }
            },
            function(error) {
                const messages = {
                    1: 'Location permission denied. Allow location access in browser settings.',
                    2: 'Location unavailable. Check macOS Location Services and Wi-Fi.',
                    3: 'Location request timed out. Try again.'
                };

                document.getElementById('status').textContent =
                    messages[error.code] || error.message;

                watchId = null;
            },
            {
                enableHighAccuracy: true,
                maximumAge: 0,
                timeout: 20000
            }
        );
    }

    function stopTracking() {
        if (watchId !== null) {
            navigator.geolocation.clearWatch(watchId);
            watchId = null;
        }
        document.getElementById('status').textContent =
            'Location tracking stopped.';
    }
</script>
</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(HTML_PAGE)


@app.route("/save_location", methods=["POST"])
def save_location():
    data = request.get_json(silent=True) or {}

    latitude = data.get("latitude")
    longitude = data.get("longitude")
    accuracy = data.get("accuracy")

    if latitude is None or longitude is None:
        return jsonify({"error": "Latitude and longitude are required"}), 400

    try:
        latitude = float(latitude)
        longitude = float(longitude)
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError("Coordinates are outside valid ranges")
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid coordinates"}), 400

    updated_at = datetime.now(timezone.utc).isoformat()

    location = {
        "latitude": latitude,
        "longitude": longitude,
        "accuracy": accuracy,
        "updated_at": updated_at
    }

    # Save the latest location to JSON.
    LOCATION_FILE.write_text(json.dumps(location, indent=4))

    # Update the CSV used by Tableau.
    with CSV_FILE.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Latitude", "Longitude", "Accuracy", "UpdatedAt"])
        writer.writerow([latitude, longitude, accuracy, updated_at])

    print(
        f"Location updated: {latitude}, {longitude} "
        f"(accuracy: {accuracy} m, time: {updated_at})"
    )

    return jsonify({"status": "success", "location": location}), 200


@app.route("/location")
def latest_location():
    if not LOCATION_FILE.exists():
        return jsonify({"error": "No location received yet"}), 404

    return app.response_class(
        LOCATION_FILE.read_text(),
        mimetype="application/json"
    )


if __name__ == "__main__":
    print("DriveSafe AI GPS server starting...")
    print("Open http://127.0.0.1:5000 in your browser.")
    app.run(host="127.0.0.1", port=5000, debug=False)
