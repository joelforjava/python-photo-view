import os
import random

from pathlib import Path

import requests


class SlideShowService:

    def __init__(self):
        self.temp_dir = Path('__photo_frame/photos')
        self.init_images()

    def init_images(self):
        self.photo_list = [entry for entry in self.temp_dir.iterdir() if is_image_file(str(entry))]
        self.photo_count = len(self.photo_list)

    def select_images(self, count=5):
        sample_size = count if count <= self.photo_count else self.photo_count
        return random.sample(self.photo_list, sample_size)

    def get_random_photo(self):
        print('Loading Random Photo from cache')
        if self.photo_count:
            return random.choice(self.photo_list)
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
        if not self.temp_dir.exists():
            print('Temp directory not found. Will attempt to create.')
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.refresh()

    def refresh(self):
        self.photo_list = [entry for entry in self.temp_dir.iterdir() if is_image_file(str(entry))]
        self.photo_count = len(self.photo_list)

    @property
    def has_photos(self):
        return self.photo_count > 0

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self):
        if self.has_photos:
            return random.choice(self.photo_list)
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
        yield random.choice(photo_list)
    else:
        raise StopIteration()


def photo_feed_alt():
    temp_dir = Path('__photo_frame/photos')
    image_files = (entry for entry in temp_dir.iterdir() if is_image_file(str(entry)))
    yield next(image_files)
    # for entry in image_files:
    #     yield entry


image_files = (entry for entry in Path('__photo_frame/photos').iterdir() if is_image_file(str(entry)))
