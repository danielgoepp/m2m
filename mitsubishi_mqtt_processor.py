#!/usr/bin/env python3

import json
import logging
import time
import paho.mqtt.client as mqtt
import config

logging.basicConfig(
    level=config.LOG_LEVEL, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MitsubishiMQTTProcessor:
    def __init__(self):
        self.mqtt_server = config.MQTT_SERVER
        self.mqtt_port = config.MQTT_PORT
        self.mqtt_username = config.MQTT_USERNAME
        self.mqtt_password = config.MQTT_PASSWORD

        # Configure devices
        self.devices = config.DEVICES
        
        # Initialize device states - all start as null (no desired state set)
        self.device_states = {}
        for device in self.devices:
            self.device_states[device] = {
                "temp": None,
                "fan": None, 
                "vane": None,
                "wideVane": None,
                "mode": None
            }
        
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            logger.info("Connected to MQTT broker")
            # Subscribe to both topic patterns
            client.subscribe("mitsubishi2mqtt/+/+/set")
            client.subscribe("mitsubishi2mqtt/+/state")
            logger.info("Subscribed to topics")
        else:
            logger.error(f"Failed to connect to MQTT broker: {reason_code}")

    def parse_topic(self, topic: str) -> dict:
        """Parse MQTT topic into components"""
        parts = topic.split("/")
        
        if len(parts) == 4 and parts[3] == "set":
            # mitsubishi2mqtt/device_name/attribute/set
            return {
                "device_name": parts[1],
                "attribute": parts[2],
                "message_type": "set",
            }
        elif len(parts) == 3 and parts[2] == "state":
            # mitsubishi2mqtt/device_name/state
            return {"device_name": parts[1], "message_type": "state"}
        else:
            return {}

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode("utf-8")

            logger.info(f"Received message on {topic}: {payload}")

            parsed_topic = self.parse_topic(topic)
            if not parsed_topic:
                logger.warning(f"Could not parse topic: {topic}")
                return

            if parsed_topic["message_type"] == "set":
                self.handle_set_message(parsed_topic, payload)
            elif parsed_topic["message_type"] == "state":
                self.handle_state_message(parsed_topic, payload)

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def handle_set_message(self, parsed_topic: dict, payload: str):
        """Handle set request messages - save as desired state"""
        device_name = parsed_topic["device_name"]
        attribute = parsed_topic["attribute"]
        
        # Only handle known devices and attributes
        if device_name not in self.devices:
            logger.warning(f"Unknown device: {device_name}")
            return
            
        if attribute not in ["temp", "fan", "vane", "wideVane", "mode"]:
            # Silently ignore unknown attributes (like remote_temp)
            return
        
        # Save the desired state
        self.device_states[device_name][attribute] = payload
        logger.info(f"Set desired state: {device_name}.{attribute} = {payload}")

    def handle_state_message(self, parsed_topic: dict, payload: str):
        """Handle state update messages - ignore if no desired state exists"""
        device_name = parsed_topic["device_name"]
        
        # Only handle known devices
        if device_name not in self.devices:
            logger.warning(f"Unknown device: {device_name}")
            return
        
        try:
            state_data = json.loads(payload)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in state message: {payload}")
            return
        
        # Check each attribute we care about (ignore remote_temp - it's just room sensor data)
        for attribute in ["temperature", "fan", "vane", "wideVane", "mode"]:
            if attribute not in state_data:
                continue
                
            # Map temperature to temp for consistency  
            set_attribute = "temp" if attribute == "temperature" else attribute
            
            current_value = str(state_data[attribute])
            desired_state = self.device_states[device_name][set_attribute]
            
            if desired_state is None:
                # No previous set value, use the current state as our baseline
                self.device_states[device_name][set_attribute] = current_value
                logger.info(f"Initial state recorded: {device_name}.{set_attribute} = {current_value}")
            else:
                # We have a previous set value, compare it
                # Special handling for temperature - compare as integers
                if set_attribute == "temp":
                    try:
                        desired_int = int(float(desired_state))
                        current_int = int(float(current_value))
                        values_match = desired_int == current_int
                    except ValueError:
                        values_match = desired_state == current_value
                else:
                    values_match = desired_state == current_value
                
                if not values_match:
                    logger.warning(f"State mismatch: {device_name}.{set_attribute} desired={desired_state} current={current_value}")
                    self.send_correction(device_name, set_attribute, desired_state)
                else:
                    logger.debug(f"State matches: {device_name}.{set_attribute} = {current_value}")

    def send_correction(self, device_name: str, attribute: str, value: str):
        """Send correction command to MQTT"""
        topic = f"mitsubishi2mqtt/{device_name}/{attribute}/set"
        
        logger.info(f"Sending correction to {topic}: {value}")
        
        result = self.client.publish(topic, value, qos=0, retain=False)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.error(f"Failed to send correction: {result.rc}")
        else:
            logger.info("Correction sent successfully")

    def run(self):
        """Start the MQTT processor"""
        try:
            logger.info("Starting Mitsubishi MQTT Processor")
            config.log_configuration()

            while True:
                try:
                    logger.info(f"Connecting to MQTT broker at {self.mqtt_server}:{self.mqtt_port}")
                    self.client.connect(self.mqtt_server, self.mqtt_port, 60)
                    self.client.loop_forever()
                except (ConnectionRefusedError, OSError) as e:
                    logger.error(f"Connection failed: {e}")
                    logger.info(f"Retrying in {config.RECONNECT_DELAY} seconds...")
                    time.sleep(config.RECONNECT_DELAY)
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                    logger.info(f"Retrying in {config.RECONNECT_DELAY} seconds...")
                    time.sleep(config.RECONNECT_DELAY)

        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            try:
                self.client.disconnect()
            except:
                pass


if __name__ == "__main__":
    processor = MitsubishiMQTTProcessor()
    processor.run()