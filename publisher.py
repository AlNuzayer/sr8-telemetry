import json
import random
import ssl
import threading
import time

from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt


# AWS IoT Core connection details
ENDPOINT = "a2ty0w4pe6etk8-ats.iot.ap-southeast-2.amazonaws.com"
PORT = 8883
CLIENT_ID = "sr8-telemetry-simulator-01"
TOPIC = "sr8/telemetry/test"

# Keeps the certificate paths relative to this script.
BASE_DIR = Path(__file__).resolve().parent
CERT_DIR = BASE_DIR / "certs"

CA_CERT = CERT_DIR / "AmazonRootCA1.pem"
DEVICE_CERT = CERT_DIR / "device.pem.crt"
PRIVATE_KEY = CERT_DIR / "private.pem.key"

# Sends ten packets, one second apart, for the initial test.
PACKET_COUNT = 10
PUBLISH_INTERVAL = 1.0

# Used to wait until AWS has accepted the MQTT connection.
connected_event = threading.Event()
connection_successful = False


# Called when the broker responds to our connection request.
def on_connect(client, userdata, flags, reason_code, properties):
    global connection_successful

    connection_successful = not reason_code.is_failure

    if connection_successful:
        print("[MQTT] Connected to AWS IoT Core.")
    else:
        print(f"[MQTT] Connection failed: {reason_code}")

    connected_event.set()


# Generates some sample vehicle measurements to send as JSON.
def generate_packet(sequence):
    return {
        "source": CLIENT_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sequence": sequence,
        "speed_kmh": round(random.uniform(55, 85), 2),
        "motor_temperature_c": round(random.uniform(38, 55), 2),
        "battery_soc_pct": round(max(0, 90 - sequence * 0.05), 2),
        "battery_voltage_v": round(random.uniform(370, 405), 2),
    }


# Sets up the MQTT connection and publishes the simulated telemetry.
def main():
    # Checks the certificate files before attempting a connection.
    for path in (CA_CERT, DEVICE_CERT, PRIVATE_KEY):
        if not path.is_file():
            raise FileNotFoundError(f"Missing certificate file: {path}")

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=CLIENT_ID,
        protocol=mqtt.MQTTv311,
    )

    client.on_connect = on_connect

    # Uses TLS so the connection is encrypted and authenticated.
    # AWS checks our device certificate against its attached IoT policy.
    client.tls_set(
        ca_certs=str(CA_CERT),
        certfile=str(DEVICE_CERT),
        keyfile=str(PRIVATE_KEY),
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLS_CLIENT,
    )

    print(f"[MQTT] Connecting to {ENDPOINT}:{PORT}...")

    try:
        client.connect(ENDPOINT, PORT, keepalive=60)

        # Processes incoming MQTT messages and acknowledgements
        # in a separate network thread.
        client.loop_start()

        # Waits for the connection acknowledgement before publishing.
        if not connected_event.wait(timeout=15):
            raise TimeoutError("MQTT connection timed out.")

        if not connection_successful:
            raise ConnectionError("AWS IoT Core rejected the connection.")

        for sequence in range(1, PACKET_COUNT + 1):
            packet = generate_packet(sequence)
            payload = json.dumps(packet)

            # QoS 1 requests an acknowledgement from the broker.
            result = client.publish(
                topic=TOPIC,
                payload=payload,
                qos=1,
            )

            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(
                    f"Publish failed: {mqtt.error_string(result.rc)}"
                )

            # Waits for AWS to acknowledge this packet.
            result.wait_for_publish(timeout=10)

            if not result.is_published():
                raise TimeoutError(
                    f"No publish acknowledgement for packet {sequence}"
                )

            print(f"[PUBLISHED {sequence}/{PACKET_COUNT}] {payload}")

            time.sleep(PUBLISH_INTERVAL)

        print("\n[SUCCESS] Finished publishing telemetry.")

    finally:
        # Closes the MQTT connection whether publishing finishes successfully
        # or an error occurs during the process.
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()

