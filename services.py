import os
import random

from pathlib import Path

import inflection
import requests
from PIL import Image, ImageDraw, ImageFont, ImageTk


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
    if isinstance(filename, Path):
        return filename.suffix in ['.jpg', '.gif']
    # SEE: https://stackoverflow.com/questions/27599311/tkinter-photoimage-doesnt-not-support-png-image
    return filename.endswith('.jpg') or filename.endswith('.gif')  # cannot easily handle png with tkinter 8.5 -- or filename.endswith('.png')


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
        self.current_image = None
        self.refresh()

    def refresh(self):
        self.photo_list = list(gather_photos())
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
            selected = random.choice(self.photo_list)
            return selected.as_photo_image(), selected.title
        else:
            raise StopIteration()


class TitledPhotoFeed(PhotoFeed):
    def next(self):
        if self.has_photos:
            selected = random.choice(self.photo_list)
            return selected.as_photo_image(with_title=True), selected.title
        else:
            raise StopIteration()


class Photo:
    def __init__(self, file_path: Path, title=None):
        self.file_path = file_path
        self.image = Image.open(self.file_path)
        self.title = title if title else create_title(file_path)

    def as_photo_image(self, with_title: bool=False):
        if with_title:
            return self.__as_photo_image_with_title()
        return ImageTk.PhotoImage(self.image)

    def __as_photo_image_with_title(self):
        im_x, im_y = self.image.size
        draw = ImageDraw.Draw(self.image)
        font = ImageFont.truetype('/Library/Fonts/Georgia.ttf', 48)  # TODO - will need a better way to look up a font!
        draw.text((5,im_y-60), self.title, (255,255,255), font=font)
        return ImageTk.PhotoImage(self.image)

    def __repr__(self):
        return f'{self.title} at {self.file_path}'


def create_title(image_file: Path):
    file_name = image_file.name
    suffix = image_file.suffix
    # Drop the file extension
    minus_ext = file_name.replace(suffix, '')
    # Intended to remove the trailing digits
    minus_ext = ''.join(s for s in minus_ext if not s.isdigit())
    return inflection.titleize(minus_ext).strip()


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
