from configparser import ConfigParser
from pathlib import Path


CONFIGS_ROOT = Path(__file__).parent / 'configs'
""" The root Path containing all configuration files, etc. """

CONFIG_INI_PATH = CONFIGS_ROOT / 'config.ini'
""" The Path to the config.ini file used by the frame and services. """

CONFIG = ConfigParser()
""" The Config instance to contain all configuration details. """

CONFIG.read(CONFIG_INI_PATH)
