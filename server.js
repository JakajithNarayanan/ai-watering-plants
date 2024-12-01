const express = require('express');
const app = express();
const bodyParser = require('body-parser');
const axios = require('axios');

// Middleware to parse JSON requests
app.use(bodyParser.json());

// API endpoint to receive sensor data
app.post('/receive_data', async (req, res) => {
  try {
    const { temperature, humidity, soil_moisture } = req.body;

    // Validate input data
    if (!temperature || !humidity || !soil_moisture) {
      return res.status(400).send({ message: 'Invalid input data' });
    }

    console.log(`Received sensor data: temperature=${temperature}, humidity=${humidity}, soil_moisture=${soil_moisture}`);

    // Process the sensor data and make a decision
    const decision = makeDecision(temperature, humidity, soil_moisture);
    console.log(`Decision: ${decision}`);

    // Send the decision to the Arduino board
    const arduinoIpAddress = '(link unavailable)';
    const response = await axios.post(`${arduinoIpAddress}/control_valve`, { status: decision });
    console.log(`Sent decision to Arduino board: ${response.data}`);

    // Send the decision back to the ESP32
    res.status(200).send({ water_plants: decision });
  } catch (error) {
    console.error(error);
    res.status(500).send({ message: 'Error processing sensor data' });
  }
});

// Function to make a decision based on the sensor data
function makeDecision(temperature, humidity, soilMoisture) {
  // Implement your decision-making logic here
  // For example, you can use a simple threshold-based approach
  if (soilMoisture < 500) {
    return 1; // Water the plants
  } else {
    return 0; // Don't water the plants
  }
}

// API endpoint to control the valve
app.post('/control_valve', async (req, res) => {
  try {
    const { status } = req.body;

    // Validate input data
    if (!status) {
      return res.status(400).send({ message: 'Invalid input data' });
    }

    console.log(`Valve status: ${status}`);
    res.status(200).send({ message: 'Valve controlled successfully' });
  } catch (error) {
    console.error(error);
    res.status(500).send({ message: 'Error controlling valve' });
  }
});

// Error handling middleware
app.use((error, req, res, next) => {
  console.error(error);
  res.status(500).send({ message: 'Internal Server Error' });
});

// Start the server
const port = 3000;
app.listen(port, () => {
  console.log(`Server listening on port ${port}`);
});

