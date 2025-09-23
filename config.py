#!/usr/bin/env python3
"""
Configuration module for M2M Controller.
Loads environment variables and validates configuration.
"""

import os
import logging
from typing import List, Optional


def load_env_file(env_file: str = ".env") -> None:
    """Load environment variables from .env file if it exists."""
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    if key and value:
                        os.environ.setdefault(key.strip(), value.strip())


def get_log_level(level_str: str) -> int:
    """Convert log level string to logging constant."""
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map.get(level_str.upper(), logging.INFO)


# Load environment file
load_env_file()

# MQTT Configuration
MQTT_SERVER: str = os.getenv("MQTT_SERVER")
MQTT_PORT: int = int(os.getenv("MQTT_PORT"))
MQTT_USERNAME: Optional[str] = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD: Optional[str] = os.getenv("MQTT_PASSWORD")

# Application Configuration
LOG_LEVEL: int = get_log_level(os.getenv("LOG_LEVEL", "INFO"))
RECONNECT_DELAY: int = int(os.getenv("RECONNECT_DELAY", "5"))

# Device Configuration
DEVICES_ENV: Optional[str] = os.getenv("DEVICES")
if not DEVICES_ENV:
    raise ValueError(
        "DEVICES environment variable must be set. "
        "Provide a comma-separated list of device names (e.g., 'BlueroomAir,GreatroomAir')"
    )

DEVICES: List[str] = [
    device.strip() for device in DEVICES_ENV.split(",") if device.strip()
]

# Validation
missing_vars = []
if not MQTT_USERNAME:
    missing_vars.append("MQTT_USERNAME")
if not MQTT_PASSWORD:
    missing_vars.append("MQTT_PASSWORD")

if missing_vars:
    raise ValueError(
        f"Required environment variables missing: {', '.join(missing_vars)}. "
        "Please set these in your .env file or environment."
    )

if not DEVICES:
    raise ValueError(
        "No valid devices found in DEVICES environment variable. "
        "Please provide a comma-separated list of device names."
    )

# Configuration validation
if MQTT_PORT < 1 or MQTT_PORT > 65535:
    raise ValueError(f"MQTT_PORT must be between 1 and 65535, got: {MQTT_PORT}")

if RECONNECT_DELAY < 1:
    raise ValueError(f"RECONNECT_DELAY must be positive, got: {RECONNECT_DELAY}")


def log_configuration() -> None:
    """Log current configuration (without sensitive data)."""
    logger = logging.getLogger(__name__)
    logger.info("=== M2M Controller Configuration ===")
    logger.info(f"MQTT Server: {MQTT_SERVER}:{MQTT_PORT}")
    logger.info(f"MQTT Username: {MQTT_USERNAME}")
    logger.info(f"Devices: {', '.join(DEVICES)} ({len(DEVICES)} total)")
    logger.info(f"Log Level: {logging.getLevelName(LOG_LEVEL)}")
    logger.info(f"Reconnect Delay: {RECONNECT_DELAY}s")
    logger.info("=====================================")


# Export all configuration variables
__all__ = [
    "MQTT_SERVER",
    "MQTT_PORT",
    "MQTT_USERNAME",
    "MQTT_PASSWORD",
    "DEVICES",
    "LOG_LEVEL",
    "RECONNECT_DELAY",
    "log_configuration",
]
