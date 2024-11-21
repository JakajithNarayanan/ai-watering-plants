from flask import Flask, request, jsonify
import joblib
import pandas as pd
import json
import requests
import os

app = Flask(__name__)

# Load the machine learning model
model = joblib.load("watering_model.pkl")

API_KEY = 'b0b6fbb82e714fefa7c133211241711'
CITY = 'Coimbatore'
BASE_URL = 'http://api.weatherapi.com/v1/forecast.json'

# ESP32 control URL
ESP32_URL = 'http://192.168.1.6/control_valve'


# Function to fetch weather data
def get_weather_data():
    params = {'key': API_KEY, 'q': CITY, 'days': 1}
    try:
        response = requests.get(BASE_URL, params=params)
        data = response.json()

        # Extract required weather data
        precip_mm = data['forecast']['forecastday'][0]['day']['totalprecip_mm']
        temp_avg = data['forecast']['forecastday'][0]['day']['avgtemp_c']
        temp_max = data['forecast']['forecastday'][0]['day']['maxtemp_c']
        temp_min = data['forecast']['forecastday'][0]['day']['mintemp_c']

        return {
            "precip_mm": precip_mm,
            "temp_avg": temp_avg,
            "temp_max": temp_max,
            "temp_min": temp_min
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None


# HTTP POST endpoint to receive data from the ESP32
@app.route('/receive_data', methods=['POST'])
def receive_data():
    try:
        # Receive JSON data from the ESP32
        sensor_data = request.json
        print(f"Received sensor data: {sensor_data}")

        # Extract sensor values
        temperature = sensor_data.get("temperature")
        humidity = sensor_data.get("humidity")
        soil_moisture = sensor_data.get("soil_moisture")

        # If any data is missing, return an error response
        if None in [temperature, humidity, soil_moisture]:
            return jsonify({"error": "Invalid data received"}), 400

        # Fetch weather data from WeatherAPI
        weather_data = get_weather_data()
        if not weather_data:
            return jsonify({"error": "Failed to fetch weather data"}), 500

        # Prepare data for prediction (combine sensor and weather data)
        sensor_input = pd.DataFrame({
            "precip": [weather_data["precip_mm"]],
            "temp_avg": [weather_data["temp_avg"]],
            "temp_max": [weather_data["temp_max"]],
            "temp_min": [weather_data["temp_min"]],
            "humidity": [humidity],
            "soil_moisture": [soil_moisture],
            "temperature": [temperature]
        })

        # Make prediction
        prediction = model.predict(sensor_input)
        water_plants = int(prediction[0])
        confidence = model.predict_proba(sensor_input).max()  # Get the highest probability

        # Construct prediction response
        response = {
            "water_plants": water_plants,
            "temperature": temperature,
            "humidity": humidity,
            "soil_moisture": soil_moisture,
            "confidence": confidence,
            "ml_decision": "Water plants" if water_plants == 1 else "No watering needed",
            "weather_data": weather_data
        }

        print(f"Prediction: {response}")
        return jsonify({"status": "success", "prediction": response}), 200

    except Exception as e:
        print(f"Error processing data: {e}")
        return jsonify({"error": "Error processing data"}), 500


# Control valve route (to send HTTP request to ESP32 to control the valve)
@app.route('/control_valve', methods=['POST'])
def control_valve():
    try:
        # Receive the valve status from the request
        data = request.json
        valve_status = data.get("status")  # Expected to be 'open' or 'close'

        if valve_status not in ['open', 'close']:
            return jsonify({"error": "Invalid valve status"}), 400

        # Send the corresponding command to ESP32 via HTTP request
        response = requests.post(ESP32_URL, json={'status': valve_status})

        # Check if the response from ESP32 is successful
        if response.status_code == 200:
            return jsonify({"status": "success", "message": f"Valve {valve_status}ed"}), 200
        else:
            return jsonify({"error": "Failed to communicate with ESP32"}), 500

    except requests.exceptions.RequestException as e:
        print(f"Error communicating with ESP32: {e}")
        return jsonify({"error": "Error controlling valve"}), 500


# Health check route (optional)
@app.route('/')
def index():
    return "Flask server is running!"

if __name__ == '__main__':
    # Set port dynamically for deployment
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
