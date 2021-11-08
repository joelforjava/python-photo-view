import random
import time

from pathlib import Path
from typing import Union

import requests

from photo import Photo


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
            'per_page': 3
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


class PhotoDownloader:
    def __init__(self, service, download_path: Path):
        self.photo_service = service
        self.download_path = download_path

    def download_feed(self):
        def has_file(file_name):
            f = Path(f'{self.download_path}/{file_name}')
            return f.exists()

        def create_file_name(image_url, page_url):
            """
            create a file name for use by the system for saving and
            loading pictures to and from the cache
            """
            file_name = determine_file_name_from_url(page_url)
            file_extension = determine_file_extension(image_url)
            return file_name + file_extension

        def download_photo(item):
            image_url = item['largeImageURL']
            page_url = item['pageURL']
            file_name = create_file_name(image_url, page_url)
            if not has_file(file_name):
                print(f'Caching: {image_url} as \n\t{file_name}')
                resp = requests.get(image_url)
                data = resp.content if resp.status_code == 200 else None
                if data:
                    with (self.download_path / file_name).open('wb') as f:
                        f.write(data)
                    print(f'Saved {file_name}')
            else:
                print(f'File {file_name} was found in the cache. Skipping download.')

        feed = self.photo_service.retrieve_feed()
        for img in feed:
            download_photo(img)


def gather_photos(from_dir=None):
    if not from_dir:
        from_dir = Path('__photo_frame/photos')
    return (Photo(entry) for entry in from_dir.iterdir() if is_image_file(entry))


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
