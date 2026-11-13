#!/usr/bin/env python3
"""
Configuration module for M2M Controller.
Loads environment variables and validates configuration.
"""

import logging
import os

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def load_env_file(env_file: str = ".env") -> None:
    """Load environment variables from .env file if it exists.

    Existing environment variables take precedence. Matching surrounding
    single or double quotes are stripped from values.
    """
    if not os.path.exists(env_file):
        return
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            if key and value:
                os.environ.setdefault(key, value)


def _get_int(name: str, default: str | None = None) -> int:
    raw = os.getenv(name, default)
    try:
        return int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be an integer, got: {raw!r}") from None


load_env_file()

# Required variables
_REQUIRED = ["MQTT_SERVER", "MQTT_PORT", "MQTT_USERNAME", "MQTT_PASSWORD", "DEVICES"]
_missing = [name for name in _REQUIRED if not os.getenv(name)]
if _missing:
    raise ValueError(
        f"Required environment variables missing: {', '.join(_missing)}. "
        "Please set these in your .env file or environment."
    )

# MQTT Configuration
MQTT_SERVER: str = os.environ["MQTT_SERVER"]
MQTT_PORT: int = _get_int("MQTT_PORT")
MQTT_USERNAME: str = os.environ["MQTT_USERNAME"]
MQTT_PASSWORD: str = os.environ["MQTT_PASSWORD"]

# Device Configuration
DEVICES: list[str] = [
    device.strip() for device in os.environ["DEVICES"].split(",") if device.strip()
]

# Application Configuration
_log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
if _log_level_str not in LOG_LEVELS:
    raise ValueError(
        f"LOG_LEVEL must be one of {', '.join(LOG_LEVELS)}, got: {_log_level_str!r}"
    )
LOG_LEVEL: int = LOG_LEVELS[_log_level_str]
RECONNECT_DELAY: int = _get_int("RECONNECT_DELAY", "5")

# Validation
if not DEVICES:
    raise ValueError(
        "No valid devices found in DEVICES environment variable. "
        "Please provide a comma-separated list of device names."
    )

if not 1 <= MQTT_PORT <= 65535:
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
