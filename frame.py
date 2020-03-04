import os
import random
import tkinter as tk
from itertools import cycle

import requests
from PIL import Image, ImageTk


class SlideShowFrame(tk.Tk):
    '''Tk window/label adjusts to size of image'''
    def __init__(self, image_files, x, y, delay):
        tk.Tk.__init__(self)
        self.geometry(f'+{x}+{y}')
        self.delay = delay
        self.pictures = self.load_pictures(image_files)
        self.picture_display = tk.Label(self)
        self.picture_display.pack()

    def show_slides(self):
        '''cycle through the images and show them'''
        img_object, img_name = next(self.pictures)
        self.picture_display.config(image=img_object)
        # shows the image filename, but could be expanded
        # to show an associated description of the image
        self.title(img_name)
        self.after(self.delay, self.show_slides)

    @staticmethod
    def load_pictures(image_files):
        return cycle((ImageTk.PhotoImage(Image.open(image)), image) for image in image_files)

    def run(self):
        self.mainloop()


class SlideShowService:

    def __init__(self):
        self.temp_dir = '__photo_frame/photos'

    def init_images(self):
        pass

    def select_images(self, count=5):
        selected = []
        while len(selected) < count:
            curr_img = self.get_random_photo()
            if curr_img not in selected:
                selected.append(curr_img)
                print(f'Added: {curr_img}')
        # This could potentially cause an issue if the number of available files is < count
        return selected

    def get_random_photo(self):
        print('Loading Random Photo from cache')
        photo_list = []
        for filename in os.listdir(self.temp_dir):
            if is_image_file(filename):
                photo_list.append(filename)
        photo_count = len(photo_list)
        if photo_count:
            random_index = random.randint(0, photo_count-1)
            selected_filename = photo_list[random_index]
            return f'{self.temp_dir}/{selected_filename}'
        return None


def is_image_file(filename):
	if filename.endswith('.jpg') or filename.endswith('.gif') or filename.endswith('.png'):
		return True
	return False


class PixabayPhotoFeedService:
    def __init__(self, args):
	    self.base_url = args['request']['base_url']
	    self.api_token = args['request']['token']
	    self.image_key = args['request']['image_key']
	    self.current_feed = None

    def retrieve_feed(self):
        """ Get latest photo feed """
        data = { 
            'key': self.api_token, 
            'order': 'popular', 
            'editors_choice': 'false', 
            'image_type': 'photo', 
            'per_page': 28
        }
        headers = { 'Content-Type': 'application/json' }

        print(f'Downloading feed from {self.base_url}')
        response = requests.get(self.base_url, params=data, headers=headers)
        if (response.status_code == 200):
            self.current_feed = response.json()['hits']
        else:
            pass  # Do we just print an error? We probably shouldn't terminate the program!


if __name__ == '__main__':
    _delay = 6000

    _x = 100
    _y = 50

    app = SlideShowFrame(SlideShowService().select_images(), _x, _y, _delay)
    app.show_slides()
    app.run()
