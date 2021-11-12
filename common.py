from configparser import ConfigParser
from pathlib import Path
import tkinter as tk


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
