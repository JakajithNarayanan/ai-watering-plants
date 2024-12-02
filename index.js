const express = require('express');
const app = express();
const bodyParser = require('body-parser');
const axios = require('axios');

// Environment variables
const apiKey = process.env.API_KEY;
const arduinoIpAddress = process.env.ARDUINO_IP;

// Threshold values
const humidityThreshold = 60;
const temperatureThreshold = 15;
const soilMoistureThreshold = 80;

// Middleware to parse JSON requests
app.use(bodyParser.json());

// API endpoint to receive sensor data
app.post('/receive_data', async (req, res) => {
  try {
    const { soil_moisture, humidity, temperature } = req.body;

    if (!soil_moisture || !humidity || !temperature) {
      return res.status(400).send({ message: 'Invalid input data' });
    }

    // Fetch weather data
    const weatherResponse = await axios.get(
      `http://api.openweathermap.org/data/2.5/weather?q=Coimbatore&appid=${apiKey}`
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

    // Determine whether to water the plants
    let waterPlants = 0; // Default to not watering
    if (rainType === 'No Rain' &&
      soil_moisture < soilMoistureThreshold &&
      humidity < humidityThreshold &&
      temperature < temperatureThreshold
    ) {
      waterPlants = 1; // Water the plants
    }

    // Send the decision to the Arduino
    await axios.post(`http://${arduinoIpAddress}/control_valve`, { water_plants: waterPlants });

    // Send the decision back to the ESP32
    res.status(200).send({ water_plants: waterPlants });
  } catch (error) {
    console.error(error.message);
    res.status(500).send({ message: 'Error processing sensor data' });
  }
});

// Start the server
const port = process.env.PORT || 3000;
app.listen(port, () => {
  console.log(`Server is running on port ${port}`);
});
