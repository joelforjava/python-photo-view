import logging
import tkinter as tk

from common import CONFIG
from feeds import PhotoFeed, TitledPhotoFeed


class SlideShowFrame(tk.Tk):
    """Tk window/label adjusts to size of image"""
    def __init__(self, image_files, x, y, delay):
        tk.Tk.__init__(self)
        self.geometry(f'+{x}+{y}')
        self.delay = delay
        self.log = logging.getLogger('frame.SlideShowFrame')
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
        self.log.info('Displaying: %s', img_name)

    def run(self):
        self.mainloop()


if __name__ == '__main__':

    # Demo only the frame, assuming there are some existing images.

    frame_config = CONFIG['DEFAULT']
    _delay = frame_config.getint('delay_ms')

    _x = 0
    _y = 0

    show_titles = frame_config.getboolean('show_titles')
    categories = frame_config['categories']
    if show_titles:
        _feed = TitledPhotoFeed(categories=categories)
    else:
        _feed = PhotoFeed(categories=categories)

    app = SlideShowFrame(_feed, _x, _y, _delay)
    app.show_slides()
    app.run()
