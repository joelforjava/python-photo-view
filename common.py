import logging
import tkinter as tk
from configparser import ConfigParser
from functools import wraps
from pathlib import Path
from typing import Optional

CONFIGS_ROOT = Path(__file__).parent / 'configs'
""" The root Path containing all configuration files, etc. """

CONFIG_INI_PATH = CONFIGS_ROOT / 'config.ini'
""" The Path to the config.ini file used by the frame and services. """

CONFIG = ConfigParser()
""" The Config instance to contain all configuration details. """

CONFIG.read(CONFIG_INI_PATH)

PHOTO_DIRECTORY_NAME = CONFIG['DEFAULT'].get('download_directory', '__photo_frame/photos')
""" The name of the directory which contains the photos we want to display. """

PHOTO_PATH = Path(PHOTO_DIRECTORY_NAME)
""" The path pointing to the photo directory. """

print(f'Using photo directory of: {PHOTO_PATH}')

JSON_STORAGE_DIRECTORY_NAME = CONFIG['storage.json'].get('data_directory', 'configs/categories')
""" The name of the directory which contains the data used by the JSON version of the storage service. """

JSON_STORAGE_PATH = Path(JSON_STORAGE_DIRECTORY_NAME)
""" The path pointing to the JSON storage directory. """

DB_STORAGE_DIRECTORY_NAME = CONFIG['storage.db'].get('data_directory', '__photo_frame/db')
""" The name of the directory which contains the data used by the DB-backed version of the storage service. """

DB_STORAGE_PATH = Path(DB_STORAGE_DIRECTORY_NAME)
""" The path pointing to the DB storage directory. """

DB_STORAGE_FILE_NAME = CONFIG['storage.db'].get('db_file_name', 'tags.db')
""" The name of the database file. """

DB_FILE_PATH = DB_STORAGE_PATH / DB_STORAGE_FILE_NAME
""" The path pointing to the DB file. """

REKOGNITION_STORAGE_DIRECTORY_NAME = CONFIG['service.rekognition'].get('data_directory', '__photo_frame/rekognition')
""" The name of the directory which contains the cached data from the AWS Rekognition service. """

REKOGNITION_DATA_PATH = Path(REKOGNITION_STORAGE_DIRECTORY_NAME)
""" The path pointing to the Rekognition data directory. """

LOGGING_FILE_NAME = CONFIG['logging'].get('data_file', 'configs/logging.json')
""" The name of the file that contains logging configurations. """

LOGGING_FILE_PATH = Path(LOGGING_FILE_NAME)
""" The path pointing to the logging configuration file. """

USE_REKOGNITION_SERVICE = CONFIG['service.rekognition'].getboolean('use_service')
""" Should we use the AWS Rekognition service to collect additional tags/labels. """

# Yet another courtesy of Stack Overflow
# https://stackoverflow.com/questions/3129322/how-do-i-get-monitor-resolution-in-python/56913005#56913005
# Needs testing. it reported my resolution as 1680x1050 and none of my displays have that.
# Will probably move it elsewhere at some point.
def show_current_screen_geometry():
    root = tk.Tk()
    root.update_idletasks()
    root.attributes('-fullscreen', True)
    root.state('iconic')
    geo = root.winfo_geometry()
    root.destroy()
    print(f'Screen details: {geo}')


class Configuration:

    def __init__(self, config_dir: Optional[Path] = None, config_file_name: Optional[str] = None):
        self.log = logging.getLogger('frame.Configuration')
        self.cfg = ConfigParser()
        if config_dir:
            self.config_dir = config_dir
        else:
            self.config_dir = (Path(__file__).parent.absolute() / 'configs').resolve()

        self.log.info('Configuration using directory: %s', self.config_dir)
        if config_file_name:
            self.config_file_name = config_file_name
        else:
            self.config_file_name = 'config.ini'

        self.config_file = self.config_dir / self.config_file_name
        self.log.info('Configuration using configuration file: %s', self.config_file)
        # Initialized indicates whether or not the config data has been loaded
        # The config data is not loaded until load() is called.
        self.initialized = False

    def load(self, reload=False):
        if not self.initialized or reload:
            self.log.info('Loading configuration')
            with self.config_file.open('r') as cf:
                self.cfg.read(cf)
            self.initialized = True

    def add(self, section: str, name: str, value: str):
        if section not in self.cfg:
            self.cfg.add_section(section)
        self.log.info('Adding CFG[%s][%s] = %s', section, name, value)
        self.cfg.set(section, name, value)

    def add_and_save(self, section: str, name: str, value: str):
        self.add(section, name, value)
        self.persist()

    def get(self, section: str, name: str, default: Optional[str] = None):
        return self.cfg.get(section, name, fallback=default)

    def has_section(self, section: str) -> bool:
        return section in self.cfg

    def section(self, section_name: str):
        return self.cfg[section_name]

    def __getitem__(self, section_name):
        return self.cfg[section_name]

    def persist(self):
        self.log.info('Updating %s', self.config_file_name)
        with self.config_file.open('w') as cf:
            self.cfg.write(cf)


def synchronized(item):
    @wraps(item)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return item(self, *args, **kwargs)
    return wrapper
