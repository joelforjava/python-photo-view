import tkinter as tk
from configparser import ConfigParser
from pathlib import Path

from constants import TOKEN
from services import PixabayPhotoFeedService
from feeds import PhotoFeed, TitledPhotoFeed


class SlideShowFrame(tk.Tk):
    """Tk window/label adjusts to size of image"""
    def __init__(self, image_files, x, y, delay):
        tk.Tk.__init__(self)
        self.geometry(f'+{x}+{y}')
        self.delay = delay
        self.pictures = image_files
        self.picture_display = tk.Label(self)
        self.picture_display.pack()

    def show_slides(self):
        """cycle through the images and show them"""
        img_object, img_name = next(self.pictures)
        self.picture_display.config(image=img_object)
        self.picture_display.image = img_object
        # shows the image filename, but could be expanded
        # to show an associated description of the image
        self.title(img_name)
        self.after(self.delay, self.show_slides)

    def run(self):
        self.mainloop()


if __name__ == '__main__':
    # defaults = {
    #     'request': {
    #         'token': TOKEN,
    #         'base_url': 'https://pixabay.com/api',
    #         'image_key': 'largeImageURL'
    #     },
    #     'update_interval': 20
    # }
    #
    # feed_service = PixabayPhotoFeedService(defaults)

    configs_root = Path(__file__).parent / 'configs'
    config_file_path = configs_root / 'config.ini'
    config = ConfigParser()
    config.read(config_file_path)

    _delay = config['default'].getint('delay_ms')

    _x = 0
    _y = 0

    show_titles = config['default'].getboolean('show_titles')
    if show_titles:
        _feed = TitledPhotoFeed()
    else:
        _feed = PhotoFeed()

    app = SlideShowFrame(_feed, _x, _y, _delay)
    app.show_slides()
    app.run()
