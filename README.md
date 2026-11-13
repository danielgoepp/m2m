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
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure**

   Copy the example config and edit it with your MQTT credentials and device list:
   ```bash
   cp .env.example .env
   ```

3. **Run**
   ```bash
   python3 mitsubishi_mqtt_processor.py
   ```

## Configuration

### Required Environment Variables
- `MQTT_SERVER` - MQTT broker address
- `MQTT_PORT` - MQTT broker port (e.g. `1883`)
- `MQTT_USERNAME` - MQTT broker authentication username
- `MQTT_PASSWORD` - MQTT broker authentication password
- `DEVICES` - Comma-separated list of AC device names

### Optional Environment Variables
- `LOG_LEVEL` - Logging level (default: `INFO`; one of DEBUG/INFO/WARNING/ERROR/CRITICAL)
- `RECONNECT_DELAY` - Reconnection delay in seconds (default: `5`)

## Monitored Attributes

- `temp` - Temperature setting (compared as rounded integers)
- `fan` - Fan speed setting
- `vane` - Air direction/vane position
- `wideVane` - Wide vane position
- `mode` - Operating mode (heat/cool/etc.)

*Note: `remote_temp` (room sensor data) is ignored*

## Behavior

- A `/set` command on a monitored attribute becomes that attribute's desired value.
- Before any `/set` is seen, the first reported state is adopted as the desired value.
- When a state update differs from the desired value, a correction is republished to the `/set` topic (non-retained).
- After 5 consecutive corrections that don't take effect, the controller stops correcting that attribute and logs an error until a `/set` with a different value arrives (protects against values the unit rejects; the controller's own corrections echo back on `/set` and are ignored).

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

Published images live on GitHub Container Registry at `ghcr.io/danielgoepp/m2m-controller` (`:latest` and `:<git-short-sha>`). To build and push:
```bash
# one-time: echo "$GHCR_TOKEN" | docker login ghcr.io -u danielgoepp --password-stdin
./build-and-push.sh
```

### Kubernetes
Runs in the `management` namespace of the k3s cluster. The manifest is not in this repo; it is managed in the cluster's GitOps config. MQTT server, port and devices come from a ConfigMap; credentials from a Secret.

## Dependencies

- Python 3.11+
- paho-mqtt >= 2.0

## License

[Add your license here]