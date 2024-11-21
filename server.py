from flask import Flask, request
import joblib
import pandas as pd
import json
import requests

app = Flask(__name__)

# Load the machine learning model
model = joblib.load("watering_model.pkl")
API_KEY = 'b0b6fbb82e714fefa7c133211241711'
CITY = 'Coimbatore'
BASE_URL = 'http://api.weatherapi.com/v1/forecast.json'

# HTTP POST endpoint to receive data from the Arduino
@app.route('/receive_data', methods=['POST'])
def receive_data():
    try:
        # Receive JSON data from Arduino
        sensor_data = request.json
        print(f"Received sensor data: {sensor_data}")

        # Extract sensor values
        temperature = sensor_data.get("temperature")
        humidity = sensor_data.get("humidity")
        soil_moisture = sensor_data.get("soil_moisture")

        # If any data is missing, return an error response
        if None in [temperature, humidity, soil_moisture]:
            return json.dumps({"error": "Invalid data received"}), 400

        # Prepare data for prediction
        sensor_input = pd.DataFrame({
            "precip": [humidity],
            "temp_avg": [temperature],
            "temp_max": [temperature],
            "temp_min": [temperature]
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
            "ml_decision": "Water plants" if water_plants == 1 else "No watering needed"
        }

        print(f"Prediction: {response}")
        return json.dumps({"status": "success", "prediction": response}), 200

    except Exception as e:
        print(f"Error processing data: {e}")
        return json.dumps({"error": "Error processing data"}), 500


# Function to fetch weather data (optional, for added insights)
def get_weather_data():
    params = {'key': API_KEY, 'q': CITY, 'days': 1}
    try:
        response = requests.get(BASE_URL, params=params)
        data = response.json()
        temperature = data['current']['temp_c']
        humidity = data['current']['humidity']
        return temperature, humidity
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None, None


# Health check route (optional)
@app.route('/')
def index():
    return "Flask server is running!"

if __name__ == '__main__':
    # Set port dynamically for Render
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
