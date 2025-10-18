# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# M2M (Mitsubishi MQTT) Project Memory

## Project Overview
MQTT-based control system for Mitsubishi mini split air conditioners. Monitors and corrects AC settings to ensure they match intended configurations.

## Core Components

### Main Application: `mitsubishi_mqtt_processor.py`
- **Purpose**: Monitors MQTT messages for AC control commands and state updates
- **Functionality**: 
  - Listens for "set" commands (`mitsubishi2mqtt/+/+/set`)
  - Monitors state updates (`mitsubishi2mqtt/+/state`) 
  - Auto-corrects settings that drift from intended values immediately
  - Ignores state updates until desired state is set

### Controlled Devices
Configurable via `DEVICES` environment variable (comma-separated, required)

### Monitored Attributes
- `temp` - Temperature setting (compared as integers)
- `fan` - Fan speed setting
- `vane` - Air direction/vane position
- `wideVane` - Wide vane position
- `mode` - Operating mode (heat/cool/etc.)
- Ignores: `remote_temp` (room sensor data)

## MQTT Topic Structure
```
mitsubishi2mqtt/{device_name}/{attribute}/set  # Control commands & corrections
mitsubishi2mqtt/{device_name}/state           # Status updates
```

## Configuration
Uses enhanced `config.py` with type hints, validation, and comprehensive error handling.

### Environment Variables
**Required:**
- `MQTT_USERNAME` - MQTT authentication username
- `MQTT_PASSWORD` - MQTT authentication password
- `DEVICES` - Comma-separated device list (e.g., `BlueroomAir,GreatroomAir`)

**Optional (with defaults):**
- `MQTT_SERVER` - MQTT broker address (default: `mosquitto-prod.goepp.net.`)
- `MQTT_PORT` - MQTT broker port (default: `1883`)
- `LOG_LEVEL` - Logging level (default: `INFO`, options: DEBUG/INFO/WARNING/ERROR/CRITICAL)
- `RECONNECT_DELAY` - Seconds between reconnection attempts (default: `5`)

### Setup
1. Copy `.env.example` to `.env`
2. Update required credentials and device list in `.env`
3. Optionally adjust log level and reconnect delay
4. Run application - config validation occurs at startup with detailed error messages

### Configuration Features
- **Type Safety**: Full type hints throughout config module
- **Validation**: Comprehensive validation with helpful error messages
- **Logging**: Configuration summary logged at startup (secrets excluded)
- **Auto-reconnect**: Configurable reconnection delay for MQTT failures
- **Code Quality**: Consistent formatting with black/ruff style guidelines

## Deployment Options

### 1. Kubernetes (m2m-controller-deployment-prod.yaml)
- Containerized deployment in `management` namespace
- Uses ConfigMap for non-sensitive config (MQTT_SERVER, MQTT_PORT, DEVICES)
- Uses Secret for credentials (MQTT_USERNAME, MQTT_PASSWORD)
- Resource limits: 128Mi memory, 100m CPU
- No health checks for simplified deployment
- Auto-restart on failure

### 2. Docker Container (Dockerfile)
- Python 3.11 slim base image
- Non-root user for security
- No health checks for simplified operation
- Minimal dependencies
- Available at: `danielgoepp/m2m-controller:latest`

## Development & Testing

### Development Commands
```bash
# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with actual credentials

# Run the main application locally
python3 mitsubishi_mqtt_processor.py

# Build Docker image
docker build -t m2m-controller .

# Run with Docker
docker run --env-file .env m2m-controller
```

### Dependencies
- `paho-mqtt>=1.6.0` - MQTT client library

## Architecture Overview

### Core Architecture
- **Single-threaded event loop**: Uses `paho-mqtt` client with callback-based processing
- **State management**: In-memory tracking of desired vs actual device states per attribute
- **Configuration-driven**: Environment variables control MQTT connection and device list

### Key Components
- `mitsubishi_mqtt_processor.py:15` - Main `MitsubishiMQTTProcessor` class
- `config.py` - Environment variable loading with validation and `.env` file support
- State tracking in `device_states` dictionary - initialized to `None` for all attributes

### Message Flow
1. **Set commands** (`mitsubishi2mqtt/{device}/attribute/set`) → Update desired state
2. **State updates** (`mitsubishi2mqtt/{device}/state`) → Compare with desired state
3. **Auto-correction** → Publish correction commands when mismatch detected

## Key Behaviors
1. **Initial State Learning**: Records current states when no desired state exists
2. **Immediate Correction**: Auto-corrects mismatches without delay
3. **Integer Temperature Comparison**: Treats 72.0 and 72 as equal
4. **Non-Retained Messages**: Corrections published without retain flag
5. **State Tracking**: Maintains desired vs actual states per device/attribute
6. **Robust Error Handling**: Automatic reconnection with configurable delays
7. **Configuration Logging**: Startup summary excludes sensitive credentials

## Deployment Status
- **Currently deployed** to k3s cluster in `management` namespace
- **Pod name**: `m2m-controller-*` 
- **Status**: Running and processing MQTT messages
- **Monitoring**: `kubectl logs -n management deployment/m2m-controller -f`

## Project Structure
```
m2m/
├── README.md                    # Project documentation
├── CLAUDE.md                   # AI assistant memory/instructions
├── requirements.txt            # Python dependencies
├── .env.example               # Configuration template
├── .env                       # Local configuration (gitignored)
├── .gitignore                 # Git ignore patterns
├── .venv/                     # Virtual environment (gitignored)
├── config.py                  # Configuration module with validation
├── mitsubishi_mqtt_processor.py # Main application
└── Dockerfile                 # Container build instructions
```

## Security Notes
- Never commit actual MQTT credentials (`.env` is gitignored)
- Use environment variables or Kubernetes secrets for production
- Service runs as non-root user in container
- Configuration validation prevents common mistakes
- Sensitive data excluded from startup logging