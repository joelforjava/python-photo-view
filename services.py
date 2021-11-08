import random
import time

from pathlib import Path
from typing import Union

import requests

from photo import Photo


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


def is_image_file(filename: Union[Path, str]) -> bool:
    if isinstance(filename, Path):
        return filename.suffix in ['.jpg', '.gif']
    # SEE: https://stackoverflow.com/questions/27599311/tkinter-photoimage-doesnt-not-support-png-image
    return filename.endswith('.jpg') or filename.endswith(
        '.gif')  # cannot easily handle png with tkinter 8.5 -- or filename.endswith('.png')


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
        headers = {'Content-Type': 'application/json'}

        print(f'Downloading feed from {self.base_url}')
        response = requests.get(self.base_url, params=data, headers=headers)
        if response.status_code == 200:
            # TODO - check to see if we can use any metadata for categorization
            self.current_feed = response.json()['hits']
        else:
            pass  # Do we just print an error? We probably shouldn't terminate the program!

        return self.current_feed


def gather_photos(from_dir=None):
    if not from_dir:
        from_dir = Path('__photo_frame/photos')
    return (Photo(entry) for entry in from_dir.iterdir() if is_image_file(entry))


def photo_feed():
    temp_dir = Path('__photo_frame/photos')
    photo_list = list(gather_photos(temp_dir))
    photo_count = len(photo_list)
    if photo_count:
        selected = random.choice(photo_list)
        yield selected
    else:
        raise StopIteration()


def determine_file_name_from_url(url):
    if url.find('/'):
        max_splits = 1
        if url.endswith('/'):
            max_splits = 2
        return url.rsplit('/', max_splits)[1]
    else:
        return str(int(time.time() * 1000))


def determine_file_extension(filename):
    return '.{}'.format(filename.rsplit('.', 1)[1])
