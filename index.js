const express = require('express');
const app = express();
const bodyParser = require('body-parser');
const axios = require('axios');

// Define threshold values
const humidityThreshold = 60;
const temperatureThreshold = 15;
const soilMoistureThreshold = 80; // 80% soil moisture threshold

// OpenWeatherMap API key
const apiKey = 'da2398eac5df1a035636082a740a1bbc';

// Arduino board IP address
const arduinoIpAddress = 'http://192.168.1.6'; // Update to Arduino's IP

// Middleware to parse JSON requests
app.use(bodyParser.json());

// API endpoint to receive sensor data from ESP32
app.post('/receive_data', async (req, res) => {
  try {
    const { soil_moisture, humidity, temperature } = req.body;

    // Validate input data
    if (
      soil_moisture === undefined ||
      humidity === undefined ||
      temperature === undefined
    ) {
      return res.status(400).send({ message: 'Invalid input data' });
    }

    console.log('Received data:', req.body);

    // Get weather data from OpenWeatherMap API
    const weatherResponse = await axios.get(
      `https://api.openweathermap.org/data/2.5/weather?q=Coimbatore&appid=${apiKey}`
    );

    const weatherData = weatherResponse.data;
    const clouds = weatherData.clouds.all;
    const weather = weatherData.weather[0].main;

    // Determine the type of rain
    let rainType;
    if (clouds > 80 && weather === 'Rain') {
      rainType = 'Heavy Rain';
    } else if (clouds > 50 && weather === 'Rain') {
      rainType = 'Moderate Rain';
    } else if (clouds > 20 && weather === 'Rain') {
      rainType = 'Light Rain';
    } else {
      rainType = 'No Rain';
    }

    console.log('Rain type:', rainType);

    // Determine whether to water the plants
    let waterPlants = 0; // Default is not watering
    if (rainType === 'No Rain') {
      if (
        soil_moisture < soilMoistureThreshold &&
        humidity < humidityThreshold &&
        temperature > temperatureThreshold
      ) {
        waterPlants = 1; // Water the plants
      }
    }

    console.log(`Water plants decision: ${waterPlants ? 'YES' : 'NO'}`);

    // Send decision to Arduino
    const arduinoResponse = await axios.post(
      `${arduinoIpAddress}/control_valve`,
      { water_plants: waterPlants }
    );

    console.log('Response from Arduino:', arduinoResponse.data);

    // Send the decision back to ESP32
    res.status(200).send({ water_plants: waterPlants });
  } catch (error) {
    console.error('Error processing sensor data:', error.message);
    res.status(500).send({ message: 'Error processing sensor data' });
  }
});

// Start the server
const port = 3000;
app.listen(port, () => {
  console.log(`Server listening on port ${port}`);
});
