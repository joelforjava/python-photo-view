import time

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from categories import JsonCategoryService


class PixabayPhotoFeedService:
    def __init__(self, args):
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

        print(f'Downloading feed from {self.base_url}')
        response = requests.get(self.base_url, params=data, headers=headers)
        if response.status_code == 200:
            self.current_feed = response.json()['hits']
        else:
            print(f'There was an error connecting to {self.base_url}: {response.status_code}')

        return self.current_feed


class PhotoDownloader:
    def __init__(self, service, download_path: Path, category_service: JsonCategoryService = None):
        if not category_service:
            category_service = JsonCategoryService(Path('configs/categories'))
        self.photo_service = service
        self.download_path = download_path
        self.category_service = category_service

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
                    new_file = self.download_path / file_name
                    with new_file.open('wb') as f:
                        f.write(data)
                    print(f'Saved {file_name}')
                    tags = item.get('tags', 'all')
                    print(f'Saving tags: {tags}')
                    self.category_service.save_to_categories(new_file, tags)
            else:
                print(f'File {file_name} was found in the cache. Skipping download.')

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
