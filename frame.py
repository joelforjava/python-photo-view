import os
import random
import tkinter as tk

import requests

from services import PhotoFeed, PixabayPhotoFeedService, TitledPhotoFeed


class SlideShowFrame(tk.Tk):
    '''Tk window/label adjusts to size of image'''
    def __init__(self, image_files, x, y, delay):
        tk.Tk.__init__(self)
        self.geometry(f'+{x}+{y}')
        self.delay = delay
        self.pictures = image_files
        self.picture_display = tk.Label(self)
        self.picture_display.pack()

    def show_slides(self):
        '''cycle through the images and show them'''
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
    _delay = 6000

    _x = 0
    _y = 0

    show_titles = True  # TODO - put in settings/config file
    if show_titles:
        _feed = TitledPhotoFeed()
    else:
        _feed = PhotoFeed()

    app = SlideShowFrame(_feed, _x, _y, _delay)
    app.show_slides()
    app.run()
