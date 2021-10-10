""" Module containing configurable variables """
import os
import logging
from typing import Any
from dataclasses import dataclass

LOGGER = logging.getLogger(__name__)

TRUE_CONVERSIONS = ['true', 't', '1']

def override_value(key: str, default: Any, secret: bool = False) -> Any:
    """Helper function used to override local configuration
    settings with values set in environment variables

    Arguments:
        key: str name of environment variable to override
        default: Any default value to use if not set
        secret: bool hide value from logs if True
    Returns:
        default value if not set in environs, else value from
            environment variables
    """

    value = os.environ.get(key.upper(), None)

    if value is not None:
        LOGGER.info('overriding variable %s with value %s', key, value if not secret else '*' * len(value))

        # cast to boolean if default is of instance boolean
        if isinstance(default, bool):
            LOGGER.info('default value for %s is boolean. casting to boolean', key)
            value = value.lower() in TRUE_CONVERSIONS
    else:
        value = default
    return type(default)(value)

LOG_LEVELS = {'DEBUG': logging.DEBUG,
              'INFO': logging.INFO,
              'WARNING': logging.WARN,
              'ERROR': logging.ERROR,
              'CRITICAL': logging.CRITICAL}

LOG_LEVEL = LOG_LEVELS.get(override_value('LOG_LEVEL', 'DEBUG'), logging.DEBUG)
logging.basicConfig(level=LOG_LEVEL)

AUTHENTICATION_SECRET_KEY = override_value('AUTHENTICATION_SECRET_KEY', '', True)
FRONT_END_BASE_URL = override_value('FRONT_END_BASE_URL', '')
MAIL_FROM_ADDRESS = override_value('MAIL_FROM_ADDRESS', 'no-reply@prescriptionmanagementsystem.com')
SENDGRID_HOST = override_value('SENDGRID_HOST', 'https://api.sendgrid.com')
SENDGRID_API_KEY = override_value('SENDGRID_API_KEY', '', secret=True)
NOTIFICATION_CHECK_DURATION = int(override_value('NOTIFICATION_CHECK_DURATION', 1440))

@dataclass
class DBConfig:
    USERNAME = override_value("DB_USERNAME", "")
    PASSWORD = override_value("DB_PASSWORD", "", secret=True)
    ADDRESS = override_value("DB_ADDRESS", "")
    NAME = override_value("DB_NAME", "")
