from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

API_URL = "http://api:8000"  # Using docker service name

@app.route('/')
def index():
    # Get list of places from API
    try:
        response = requests.get(f"{API_URL}/places")
        places = response.json().get('places', [])
    except:
        places = []
    return render_template('index.html', places=places)

@app.route('/find_route', methods=['POST'])
def find_route():
    start = request.form.get('start')
    end = request.form.get('end')
    
    try:
        response = requests.get(f"{API_URL}/find_path_by_name/{start}/{end}")
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)