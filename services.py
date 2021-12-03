import logging
import time

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from categories import CategoryService, JsonCategoryService


class PixabayPhotoFeedService:
    def __init__(self, args):
        self.log = logging.getLogger('frame.PixabayPhotoFeedService')
        self.base_url = args['base_url']
        self.api_token = args['token']
        self.image_key = args['image_key']
        self.max_photos = args.getint('max_photos', 3)
        self.order = args.get('order', 'popular')
        self.image_type = args.get('image_type', 'photo')
        self.category = args.get('category', None)
        self.editors_choice = args.get('editors_choice', 'false')
        self.current_feed = None

    def retrieve_feed(self):
        """ Get latest photo feed """
        data = {
            'key': self.api_token,
            'order': self.order,
            'editors_choice': self.editors_choice,
            'image_type': self.image_type,
            'per_page': self.max_photos,
        }
        if self.category and self.category != 'all':
            data['category'] = self.category

        headers = {'Content-Type': 'application/json'}

        self.log.info('Downloading feed from %s', self.base_url)
        response = requests.get(self.base_url, params=data, headers=headers)
        if response.status_code == 200:
            self.current_feed = response.json()['hits']
        else:
            self.log.error('There was an error connecting to %s: %d', self.base_url, response.status_code)

        return self.current_feed


class PhotoDownloader:
    def __init__(self, service, download_path: Path, category_service: CategoryService = None):
        if not category_service:
            category_service = JsonCategoryService(Path('configs/categories'))
        self.log = logging.getLogger('frame.PhotoDownloader')
        self.photo_service = service
        self.download_path = download_path
        self.category_service = category_service
        self.log.info('Using category service of type %s', type(category_service))

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
                self.log.info('Caching: %s as %s', image_url, file_name)
                resp = requests.get(image_url)
                data = resp.content if resp.status_code == 200 else None
                if data:
                    new_file = self.download_path / file_name
                    with new_file.open('wb') as f:
                        f.write(data)
                    self.log.info('Saved %s', file_name)
                    tags = item.get('tags', 'all')
                    # TODO - get additional tags from Rekognition
                    self.log.info('Saving tags: %s', tags)
                    self.category_service.save_to_categories(new_file, tags)
            else:
                self.log.info('File %s was found in the cache. Skipping download.', file_name)

        feed = self.photo_service.retrieve_feed()
        if feed:
            with ThreadPoolExecutor(max_workers=4) as executor:
                executor.map(download_photo, feed)


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
