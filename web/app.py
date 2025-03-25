import re
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

API_URL = "http://api:8000"  # Using docker service name


@app.route("/")
def index():
    # Get list of places from API
    try:
        response = requests.get(f"{API_URL}/places")
        places = response.json().get("places", [])
    except:
        places = []
    return render_template("index.html", places=places)


@app.route("/find_route", methods=["POST"])
def find_route():
    start = request.form.get("start")
    end = request.form.get("end")
    date_time = request.form.get("date_time")

    # parse start and end if they are coordinates
    if re.match(r"\d+\.\d+,\s?\d+\.\d+", start) and re.match(r"\d+\.\d+,\s?\d+\.\d+", end):
        try:
            start_lat, start_lon = start.split(", ")
            end_lat, end_lon = end.split(", ")
            response = requests.get(
                f"{API_URL}/find_path_by_coordinates/{start_lon}/{start_lat}/{end_lon}/{end_lat}?date_time={date_time}"
            )
            return jsonify(response.json())
        except Exception as e:
            return jsonify({"error": str(e)})
    else:
        try:
            response = requests.get(
                f"{API_URL}/find_path_by_name/{start}/{end}?date_time={date_time}"
            )
            return jsonify(response.json())
        except Exception as e:
            return jsonify({"error": str(e)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
