import tkinter as tk
from configparser import ConfigParser
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
        self.cfg = ConfigParser()
        if config_dir:
            self.config_dir = config_dir
        else:
            self.config_dir = (Path(__file__).parent.absolute() / 'configs').resolve()

        print(f'Configuration using directory: {self.config_dir}')
        if config_file_name:
            self.config_file_name = config_file_name
        else:
            self.config_file_name = 'config.ini'

        self.config_file = self.config_dir / self.config_file_name
        print(f'Configuration using configuration file: {self.config_file}')
        # Initialized indicates whether or not the config data has been loaded
        # The config data is not loaded until load() is called.
        self.initialized = False

    def load(self):
        if not self.initialized:
            print('Loading configuration')
            with self.config_file.open('r') as cf:
                self.cfg.read(cf)
            self.initialized = True

    def add(self, section: str, name: str, value: str):
        if section not in self.cfg:
            self.cfg.add_section(section)
        print(f'Adding CFG[{section}][{name}] = {value}')
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
        print(f'Updating {self.config_file_name}')
        with self.config_file.open('w') as cf:
            self.cfg.write(cf)
