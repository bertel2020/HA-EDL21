"""Constants for the EDL21 component."""

import logging

LOGGER = logging.getLogger(__package__)

DOMAIN = "edl21"

CONF_SERIAL_PORT = "serial_port"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_MIN_CHANGE = "min_change"

DEFAULT_UPDATE_INTERVAL = 15  # seconds
DEFAULT_MIN_CHANGE = 0  # watts, 0 = off

# Sensors become unavailable after this long without a telegram.
AVAILABILITY_TIMEOUT = 180  # seconds
# A repair issue is raised after this long without a telegram.
NO_DATA_ISSUE_AFTER = 600  # seconds
CHECK_INTERVAL = 30  # seconds
LAST_TELEGRAM_MIN_INTERVAL = 60  # seconds

SIGNAL_EDL21_TELEGRAM = "edl21_telegram"
SIGNAL_EDL21_AVAILABILITY = "edl21_availability"
SIGNAL_EDL21_ALIVE = "edl21_alive"

DEFAULT_TITLE = "Smart Meter"

DEFAULT_DEVICE_NAME = "Smart Meter"
