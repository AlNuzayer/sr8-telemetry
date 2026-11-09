# SR8 Telemetry Simulator

A Python-based telemetry simulator that publishes JSON vehicle
measurements to AWS IoT Core using MQTT. An AWS IoT Rule forwards
the received messages to Amazon DynamoDB for storage.

## Architecture

Python simulator -> AWS IoT Core -> IoT Rule -> DynamoDB

## Simulated measurements

Each packet includes:
- Device identifier
- UTC timestamp
- Sequence number
- Vehicle speed (km/h)
- Motor temperature (C)
- Battery state of charge (%)
- Battery voltage (V)

All measurements are simulated and are not actual SR8 sensor data.

## Technologies

- Python 3
- Paho MQTT
- MQTT over TLS (port 8883)
- AWS IoT Core
- AWS IoT Rules Engine
- Amazon DynamoDB

## Running the publisher

1. Create a Python virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Create a `certs/` directory containing:
   - `AmazonRootCA1.pem`
   - `device.pem.crt`
   - `private.pem.key`
4. Configure AWS IoT Core with a matching device certificate
   and a policy allowing connection and publication.
5. Run `python publisher.py`.

The publisher sends 10 simulated JSON packets to the MQTT topic
`sr8/telemetry/test`, one packet per second.

## AWS configuration

Region: ap-southeast-2 (Sydney)

MQTT topic: sr8/telemetry/test

IoT Rule: sr8_telemetry_to_dynamodb

Rule SQL:
SELECT * FROM 'sr8/telemetry/test'

DynamoDB table: sr8-telemetry-records

Partition key: source (String)
Sort key: timestamp (String)

## Security

Device certificates and private keys are excluded from Git using
`.gitignore`. Each user must provision their own AWS IoT device
credentials to run the simulator.
