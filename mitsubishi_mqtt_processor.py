#!/usr/bin/env python3

import json
import logging
import signal
import threading

import paho.mqtt.client as mqtt

import config

logging.basicConfig(
    level=config.LOG_LEVEL, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Attributes we enforce. Keys are the names used in /set topics; values are the
# corresponding keys in the device's JSON state payload. remote_temp is ignored.
MONITORED_ATTRIBUTES = {
    "temp": "temperature",
    "fan": "fan",
    "vane": "vane",
    "wideVane": "wideVane",
    "mode": "mode",
}

# Stop correcting an attribute after this many consecutive failed corrections,
# so a value the unit rejects doesn't get republished forever. The counter
# resets on a new set command or when the state matches.
MAX_CONSECUTIVE_CORRECTIONS = 5


class MitsubishiMQTTProcessor:
    def __init__(self) -> None:
        self.devices = config.DEVICES

        # Desired state per device/attribute; None until a set or first state arrives
        self.device_states: dict[str, dict[str, str | None]] = {
            device: dict.fromkeys(MONITORED_ATTRIBUTES) for device in self.devices
        }
        self.correction_counts: dict[str, dict[str, int]] = {
            device: dict.fromkeys(MONITORED_ATTRIBUTES, 0) for device in self.devices
        }

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self._stop = threading.Event()

    def on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code == 0:
            logger.info("Connected to MQTT broker")
            client.subscribe("mitsubishi2mqtt/+/+/set")
            client.subscribe("mitsubishi2mqtt/+/state")
            logger.info("Subscribed to topics")
        else:
            logger.error(f"Failed to connect to MQTT broker: {reason_code}")

    @staticmethod
    def parse_topic(topic: str) -> dict:
        """Parse MQTT topic into components."""
        parts = topic.split("/")

        if len(parts) == 4 and parts[3] == "set":
            # mitsubishi2mqtt/device_name/attribute/set
            return {
                "device_name": parts[1],
                "attribute": parts[2],
                "message_type": "set",
            }
        if len(parts) == 3 and parts[2] == "state":
            # mitsubishi2mqtt/device_name/state
            return {"device_name": parts[1], "message_type": "state"}
        return {}

    def on_message(self, client, userdata, msg) -> None:
        try:
            topic = msg.topic
            payload = msg.payload.decode("utf-8")

            logger.debug(f"Received message on {topic}: {payload}")

            parsed_topic = self.parse_topic(topic)
            if not parsed_topic:
                logger.warning(f"Could not parse topic: {topic}")
                return

            if parsed_topic["message_type"] == "set":
                self.handle_set_message(parsed_topic, payload)
            elif parsed_topic["message_type"] == "state":
                self.handle_state_message(parsed_topic, payload)

        except Exception:
            logger.exception("Error processing message")

    def handle_set_message(self, parsed_topic: dict, payload: str) -> None:
        """Handle set request messages - save as desired state."""
        device_name = parsed_topic["device_name"]
        attribute = parsed_topic["attribute"]

        if device_name not in self.devices:
            logger.debug(f"Ignoring set for unmonitored device: {device_name}")
            return

        if attribute not in MONITORED_ATTRIBUTES:
            return

        # Our own corrections echo back on this topic with the same value, so
        # only a changed value counts as a new command (and resets the limit).
        if self.device_states[device_name][attribute] == payload:
            return

        self.device_states[device_name][attribute] = payload
        self.correction_counts[device_name][attribute] = 0
        logger.info(f"Set desired state: {device_name}.{attribute} = {payload}")

    def handle_state_message(self, parsed_topic: dict, payload: str) -> None:
        """Handle state update messages - compare against desired state."""
        device_name = parsed_topic["device_name"]

        if device_name not in self.devices:
            logger.debug(f"Ignoring state for unmonitored device: {device_name}")
            return

        try:
            state_data = json.loads(payload)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in state message: {payload}")
            return

        for attribute, state_key in MONITORED_ATTRIBUTES.items():
            if state_key not in state_data:
                continue

            current_value = str(state_data[state_key])
            desired_value = self.device_states[device_name][attribute]

            if desired_value is None:
                # No set seen yet; adopt the current state as the baseline
                self.device_states[device_name][attribute] = current_value
                logger.info(
                    f"Initial state recorded: {device_name}.{attribute} = "
                    f"{current_value}"
                )
                continue

            if self.values_match(attribute, desired_value, current_value):
                self.correction_counts[device_name][attribute] = 0
                logger.debug(
                    f"State matches: {device_name}.{attribute} = {current_value}"
                )
                continue

            count = self.correction_counts[device_name][attribute]
            if count >= MAX_CONSECUTIVE_CORRECTIONS:
                if count == MAX_CONSECUTIVE_CORRECTIONS:
                    logger.error(
                        f"Giving up on {device_name}.{attribute}: "
                        f"{count} corrections to {desired_value} did not take "
                        f"(current={current_value}). Waiting for a new set command."
                    )
                    self.correction_counts[device_name][attribute] = count + 1
                continue

            logger.warning(
                f"State mismatch: {device_name}.{attribute} "
                f"desired={desired_value} current={current_value}"
            )
            self.correction_counts[device_name][attribute] = count + 1
            self.send_correction(device_name, attribute, desired_value)

    @staticmethod
    def values_match(attribute: str, desired: str, current: str) -> bool:
        """Compare values; temperature is compared as rounded integers."""
        if attribute == "temp":
            try:
                return round(float(desired)) == round(float(current))
            except ValueError:
                pass
        return desired == current

    def send_correction(self, device_name: str, attribute: str, value: str) -> None:
        """Publish a correction command (non-retained)."""
        topic = f"mitsubishi2mqtt/{device_name}/{attribute}/set"

        logger.info(f"Sending correction to {topic}: {value}")

        result = self.client.publish(topic, value, qos=0, retain=False)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.error(f"Failed to send correction: {result.rc}")

    def stop(self, signum: int | None = None, frame=None) -> None:
        """Request a clean shutdown; safe to call from a signal handler."""
        if signum is not None:
            logger.info(f"Received {signal.Signals(signum).name}, shutting down...")
        self._stop.set()
        # Makes loop_forever() return after sending DISCONNECT to the broker
        self.client.disconnect()

    def run(self) -> None:
        """Start the MQTT processor; returns after SIGTERM/SIGINT."""
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)

        logger.info("Starting Mitsubishi MQTT Processor")
        config.log_configuration()

        while not self._stop.is_set():
            try:
                logger.info(
                    f"Connecting to MQTT broker at "
                    f"{config.MQTT_SERVER}:{config.MQTT_PORT}"
                )
                self.client.connect(config.MQTT_SERVER, config.MQTT_PORT, 60)
                self.client.loop_forever()
            except Exception:
                if self._stop.is_set():
                    break
                logger.exception("Connection error")
                logger.info(f"Retrying in {config.RECONNECT_DELAY} seconds...")
                self._stop.wait(config.RECONNECT_DELAY)

        logger.info("Stopped")


if __name__ == "__main__":
    MitsubishiMQTTProcessor().run()
