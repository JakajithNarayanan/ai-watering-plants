from flask import Flask, request, jsonify
import joblib
import pandas as pd
import requests
import os

app = Flask(__name__)

# Load the machine learning model
model = joblib.load("watering_model.pkl")

# OpenWeatherMap API configurations
API_KEY = '702e1d129531c4da1cef6f9e3b26260d'
CITY = 'Coimbatore'
BASE_URL = 'https://api.openweathermap.org/data/2.5/weather'

# ESP32 control URL
ESP32_URL = 'http://192.168.1.6/control_valve'


# Function to fetch weather data from OpenWeatherMap
def fetch_weather_data():
    params = {'q': CITY, 'appid': API_KEY, 'units': 'metric'}
    try:
        response = requests.get(BASE_URL, params=params)
        data = response.json()

        # Ensure required keys exist in the response
        if 'main' not in data or 'rain' not in data:
            print("Weather API response is missing some required data.")
            return None

        # Extract temperature and precipitation
        current_temp = data['main']['temp']  # Temperature in Celsius
        precip_mm = data.get('rain', {}).get('1h', 0.0)  # Precipitation in mm (last 1 hour)

        # Use the same temperature for min, max, and avg
        return {
            "precip_mm": precip_mm,
            "temp_avg": current_temp,
            "temp_max": current_temp,
            "temp_min": current_temp
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None


# Function to process data from Arduino
def process_arduino_data(sensor_data):
    try:
        # Extract sensor values
        temperature = sensor_data.get("temperature")
        humidity = sensor_data.get("humidity")
        soil_moisture = sensor_data.get("soil_moisture")

        # Log if any value is missing
        if None in [temperature, humidity, soil_moisture]:
            print("Missing data:", sensor_data)
            return {"error": "Invalid data received"}

        return {
            "temperature": temperature,
            "humidity": humidity,
            "soil_moisture": soil_moisture
        }
    except Exception as e:
        print(f"Error processing Arduino data: {e}")
        return {"error": "Error processing Arduino data"}


# HTTP POST endpoint to receive data from Arduino
@app.route('/receive_data', methods=['POST'])
def receive_data():
    try:
        # Receive JSON data from Arduino
        sensor_data = request.json
        print(f"Received sensor data: {sensor_data}")  # Log the incoming data

        # Process Arduino data
        arduino_data = process_arduino_data(sensor_data)
        if "error" in arduino_data:
            return jsonify({"error": arduino_data["error"]}), 400

        # Fetch weather data
        weather_data = fetch_weather_data()
        if not weather_data:
            print("Error fetching weather data.")
            return jsonify({"error": "Failed to fetch weather data"}), 500

        # Prepare data for prediction
        sensor_input = pd.DataFrame({
            "precip": [weather_data["precip_mm"]],
            "temp_avg": [weather_data["temp_avg"]],
            "temp_max": [weather_data["temp_max"]],
            "temp_min": [weather_data["temp_min"]],
            "humidity": [arduino_data["humidity"]],
            "soil_moisture": [arduino_data["soil_moisture"]],
            "temperature": [arduino_data["temperature"]]
        })

        # Make prediction
        prediction = model.predict(sensor_input)
        water_plants = int(prediction[0])
        confidence = model.predict_proba(sensor_input).max()  # Get the highest probability

        # Construct prediction response
        response = {
            "water_plants": water_plants,
            "temperature": arduino_data["temperature"],
            "humidity": arduino_data["humidity"],
            "soil_moisture": arduino_data["soil_moisture"],
            "confidence": confidence,
            "ml_decision": "Water plants" if water_plants == 1 else "No watering needed",
            "weather_data": weather_data
        }

        print(f"Prediction: {response}")
        return jsonify({"status": "success", "prediction": response}), 200

    except Exception as e:
        print(f"Error processing data: {e}")  # Log the exception
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
