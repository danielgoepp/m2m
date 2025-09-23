# M2M Controller

MQTT-based control system for Mitsubishi mini split air conditioners. Monitors and corrects AC settings to ensure they match intended configurations.

## Overview

The M2M Controller listens to MQTT messages for AC control commands and state updates, automatically correcting any settings that drift from their intended values. It provides real-time monitoring and correction of Mitsubishi AC units through the `mitsubishi2mqtt` integration.

## Features

- **Real-time Monitoring**: Continuously monitors AC state changes via MQTT
- **Auto-correction**: Immediately corrects settings that drift from desired values
- **Multi-device Support**: Handles multiple AC units simultaneously
- **Robust Configuration**: Type-safe configuration with comprehensive validation
- **Auto-reconnect**: Automatic MQTT broker reconnection with configurable delays
- **Comprehensive Logging**: Configurable log levels for debugging and monitoring

## Quick Start

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd m2m
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure**
   ```bash
   cp .env.example .env
   # Edit .env with your MQTT credentials and device list
   ```

3. **Run**
   ```bash
   python3 mitsubishi_mqtt_processor.py
   ```

## Configuration

### Required Environment Variables
- `MQTT_USERNAME` - MQTT broker authentication username
- `MQTT_PASSWORD` - MQTT broker authentication password
- `DEVICES` - Comma-separated list of AC device names

### Optional Environment Variables
- `MQTT_SERVER` - MQTT broker address (default: `mosquitto-prod.goepp.net.`)
- `MQTT_PORT` - MQTT broker port (default: `1883`)
- `LOG_LEVEL` - Logging level (default: `INFO`)
- `RECONNECT_DELAY` - Reconnection delay in seconds (default: `5`)

## Monitored Attributes

- `temp` - Temperature setting (compared as integers)
- `fan` - Fan speed setting
- `vane` - Air direction/vane position
- `wideVane` - Wide vane position
- `mode` - Operating mode (heat/cool/etc.)

*Note: `remote_temp` (room sensor data) is ignored*

## MQTT Topics

```
mitsubishi2mqtt/{device_name}/{attribute}/set  # Control commands & corrections
mitsubishi2mqtt/{device_name}/state           # Status updates
```

## Deployment

### Docker
```bash
docker build -t m2m-controller .
docker run --env-file .env m2m-controller
```

### Kubernetes
Deploy using the provided Kubernetes manifest in the `management` namespace.

## Dependencies

- Python 3.11+
- paho-mqtt >= 1.6.0

## License

[Add your license here]