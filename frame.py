import os
import random
import tkinter as tk
from itertools import cycle

import requests
from PIL import Image, ImageTk

from services import SlideShowService, PhotoFeed, PixabayPhotoFeedService


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

    _x = 100
    _y = 50

    app = SlideShowFrame(PhotoFeed(), _x, _y, _delay)
    app.show_slides()
    app.run()
