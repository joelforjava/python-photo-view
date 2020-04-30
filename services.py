import os
import random

from pathlib import Path

import requests


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


class PhotoFeed:
    def __init__(self):
        self.temp_dir = Path('__photo_frame/photos')
        self.setup()

    def setup(self):
        self.photo_list = [entry for entry in self.temp_dir.iterdir() if is_image_file(str(entry))]
        self.photo_count = len(self.photo_list)

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self):
        if self.photo_count:
            random_index = random.randint(0, self.photo_count-1)
            selected = self.photo_list[random_index]
            # yield f'{self.temp_dir}/{selected_filename}'
            return str(selected)
        else:
            raise StopIteration()


def gather_photos():
    temp_dir = Path('__photo_frame/photos')
    return [entry for entry in temp_dir.iterdir() if is_image_file(str(entry))]


def photo_feed():
    temp_dir = Path('__photo_frame/photos')
    photo_list = [entry for entry in temp_dir.iterdir() if is_image_file(str(entry))]
    photo_count = len(photo_list)
    if photo_count:
        selected = random.choice(photo_list)
        yield str(selected)
    else:
        raise StopIteration()


def photo_feed_alt():
    temp_dir = Path('__photo_frame/photos')
    image_files = (entry for entry in temp_dir.iterdir() if is_image_file(str(entry)))
    yield next(image_files)
    # for entry in image_files:
    #     yield entry


image_files = (entry for entry in Path('__photo_frame/photos').iterdir() if is_image_file(str(entry)))
