import json
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


class CategoryService:
    def __init__(self, data_path: Path):
        self.data_path = data_path
        if not self.data_path.exists():
            self.data_path.mkdir(parents=True, exist_ok=True)

    def save_to_categories(self, file_path, tags: Union[str, list]):

        def update_category(f_path, cat_name):
            cat_path = self.data_path / f'{cat_name}.json'
            if cat_path.exists():
                updated = False
                with cat_path.open('r') as f:
                    existing = json.load(f)
                    if str(f_path) not in existing:
                        existing.append(str(f_path))
                        updated = True
                    else:
                        print(f'Image {f_path} is already saved in category {category}.')
                if updated:
                    with cat_path.open('w') as f:
                        json.dump(existing, f)
            else:
                with cat_path.open('x') as f:
                    json.dump([str(f_path)], f)

        if isinstance(tags, str):
            categories = [x.strip() for x in tags.split(',')]
        elif isinstance(tags, list):
            categories = tags.copy()
        else:
            categories = []
        for category in categories:
            update_category(file_path, category)


class PixabayPhotoFeedService:
    def __init__(self, args):
        self.base_url = args['request']['base_url']
        self.api_token = args['request']['token']
        self.image_key = args['request']['image_key']
        self.max_photos = args.get('max_photos', 3)
        self.current_feed = None

    def retrieve_feed(self):
        """ Get latest photo feed """
        data = {
            'key': self.api_token,
            'order': 'popular',
            'editors_choice': 'false',
            'image_type': 'photo',
            'per_page': self.max_photos,
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
        self.category_service = CategoryService(Path('configs/categories'))

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


if __name__ == '__main__':
    # Save previously downloaded images into category files.
    # Some files have extra details, such as usernames, which will result in some strange categories.
    def save_existing():
        category_service = CategoryService(Path('configs/categories'))
        existing_images = [entry for entry in Path('__photo_frame/photos').iterdir() if is_image_file(entry)]
        for img in existing_images:
            n = img.name
            print(f'Processing: {img}')
            tags = n.split('-')
            print(f'Found tags: {tags[:-1]}')
            # The last tag is actually in the form "123456.jpg" and includes the file extension
            # which we don't want. Could have alternatively used 'stem' instead of 'name' above,
            # but we'd still want to skip the id at the end.
            category_service.save_to_categories(img, tags[:-1])
            time.sleep(1)

    save_existing()
