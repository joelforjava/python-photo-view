import json
import logging
import logging.config
import sqlite3
import time

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Union

import boto3
import botocore.exceptions
import requests

from photo import Photo


def is_image_file(file_path: Path) -> bool:
    """
    Determines whether or not the provided Path object represents a valid image file.

    :param file_path: The Path representing the file we wish to verify as a valid file.
    :return: True if the Path represents a valid image file. False otherwise.
    """
    # SEE: https://stackoverflow.com/questions/27599311/tkinter-photoimage-doesnt-not-support-png-image
    # cannot easily handle png with tkinter 8.5 -- or filename.endswith('.png')
    has_valid_suffix = file_path.suffix in ['.jpg', '.gif']
    if not has_valid_suffix:
        return has_valid_suffix

    return file_path.exists()


class RekognitionTaggingService:
    def __init__(self, data_path: Path = None):
        if not data_path:
            data_path = Path('__photo_frame/rekognition')
            if not data_path.exists():
                data_path.mkdir(parents=True, exist_ok=True)
        self.data_path = data_path
        self.log = logging.getLogger('frame.RekognitionTaggingService')
        self.client = boto3.client('rekognition')

    def detect_labels(self, file_path: Path):
        photo_bytes = file_path.read_bytes()
        # TODO - ensure bytes < 5MB
        resp = None
        try:
            self.log.info('Calling Rekogntion service to detect labels for %s', file_path)
            resp = self.client.detect_labels(Image={'Bytes': photo_bytes})
        except botocore.exceptions.ClientError as error:
            err = error.response['Error']
            if err['Code'] == 'InvalidImageException':
                self.log.error('Could not detect labels via service: %s', err['Message'])
            elif err['Code'] == 'ImageTooLargeException':
                self.log.error('Could not process image "%s" due to size limits', file_path.name)
                # TODO - upload to S3
            else:
                raise error

        return resp

    def load_categories_for_photo(self, photo: Photo):
        file_name = photo.file_path.name

        local_data = (self.data_path / file_name).with_suffix('.json')
        if local_data.exists():
            self.log.info('Retrieving labels for %s from local cache', photo.file_path)
            with local_data.open('r') as f:
                return json.load(f)
        else:
            resp = self.detect_labels(photo.file_path)
            if resp:
                with local_data.open('x') as f:
                    json.dump(resp, f)
            return resp


class TaggingService:
    def __init__(self, data_path: Path = None):
        if not data_path:
            data_path = Path('__photo_frame/db/tags.db')
        self.data_path = data_path
        self.log = logging.getLogger('frame.TaggingService')
        requires_setup = False
        if not self.data_path.exists():
            self.log.warning('Data directory "%s" does not exist. Attempting to create', data_path)
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            requires_setup = True
        self.db = sqlite3.connect(data_path)
        if requires_setup:
            self._setup()

    def _setup(self):

        def tables():
            self.log.info("Creating tables")
            create_photo_table = """CREATE TABLE photos
                                    (id integer primary key autoincrement, img_path text, img_width integer, 
                                    img_height integer, date_added text, date_last_displayed text, 
                                    times_displayed integer, disabled text, title text, subtitle text, 
                                    score integer)"""

            create_category_table = """CREATE TABLE categories (id integer primary key autoincrement, 
                                       tag text unique)"""

            create_join_table = """CREATE TABLE categories_photos (category_id integer, photo_id integer,
                                   constraint `fk_category_id` foreign key (category_id) references categories(id),
                                   constraint `fk_photo_id` foreign key (photo_id) references photos(id))"""

            table_mapping = {
                'photos': create_photo_table,
                'categories': create_category_table,
                'categories_photos': create_join_table,
            }

            already_exists = set()
            cur = self.db.cursor()
            for table_name, comm in table_mapping.items():
                try:
                    cur.execute(comm)
                except sqlite3.OperationalError as e:
                    if 'already exists' in str(e):
                        already_exists.add(table_name)
                    else:
                        raise e
            self.db.commit()

            self.log.info("Completed table creation")
            self.log.info(f'The following tables previously existed: {already_exists}')
            return set(table_mapping.keys()) - already_exists

        def check_table(table_name):
            self.log.info('Checking table: %s', table_name)
            cur = self.db.cursor()
            resp = cur.execute(f"SELECT count(*) FROM {table_name}",)
            return resp.fetchone()[0] > 0

        def populate_categories():
            self.log.info('Populating Category table with existing data from previous JSON data')
            json_path = Path('configs/categories')
            cur = self.db.cursor()
            cat_names = []
            for f in json_path.iterdir():
                if f.is_file() and f.suffix == '.json':
                    cat_name = f.stem.lower()
                    self.log.debug(f'Found category: %s', cat_name)
                    cat_names.append([cat_name])

            try:
                cur.executemany('INSERT INTO categories (tag) values (?)', cat_names)
            except sqlite3.DatabaseError as de:
                self.log.exception(f' -- {de}')
                raise
            finally:
                self.db.commit()
            self.log.info('Completed category table population')

        def populate_photos():
            cur = self.db.cursor()
            all_photos = gather_photos()
            items = []
            for photo in all_photos:
                im_w, im_h = photo.image.size
                dt_added = datetime.fromtimestamp(photo.file_path.stat().st_ctime).isoformat()
                items.append([str(photo.file_path), im_w, im_h, dt_added, photo.title])
            try:
                cur.executemany(
                    'INSERT INTO photos (img_path, img_width, img_height, date_added, title) values (?,?,?,?,?)',
                    items
                )
            except sqlite3.DatabaseError as de:
                print(f' -- {de}')
                raise
            finally:
                self.db.commit()

        def populate_join_table():
            json_path = Path('configs/categories')
            cur = self.db.cursor()
            temp_mapping = {}
            for f in json_path.iterdir():
                if f.is_file() and f.suffix == '.json':
                    cat_name = f.stem
                    with f.open('r') as cat_file:
                        temp_mapping[cat_name] = json.load(cat_file)

            # print(temp_mapping)
            for k, v in temp_mapping.items():
                q_items = [k] + v
                print(f'Adding category mappings for: {k}')
                try:
                    qmarks = ','.join(['?'] * len(v))
                    cur.execute(
                        f'''INSERT INTO categories_photos (category_id,photo_id)
                            SELECT c.id as category_id, p.id as photo_id
                            FROM categories c JOIN photos p
                            WHERE c.tag = ?
                            AND p.img_path in ({qmarks}) 
                        ''',
                        q_items
                    )
                    time.sleep(.25)
                except sqlite3.DatabaseError as de:
                    print(f' -- {de}')
                    raise

            self.db.commit()

        try:
            created = tables()
            if 'categories' in created or check_table('categories'):
                populate_categories()
            if 'photos' in created or check_table('photos'):
                populate_photos()
            if 'categories_photos' in created or check_table('categories_photos'):
                populate_join_table()
        finally:
            # As it currently stands, _setup is being called
            # without actually running the whole system, so
            # closing the db after running installs is fine
            # at this point. However, will want to update this
            # once new deployments are planned.
            self.db.close()

    # TODO - add load/save methods


class CategoryService:
    def __init__(self, data_path: Path = None):
        if not data_path:
            data_path = Path('configs/categories')
        self.data_path = data_path
        if not self.data_path.exists():
            self.data_path.mkdir(parents=True, exist_ok=True)

    def save_to_categories(self, file_path, tags: Union[str, list]):
        """
        Save a string representation of a Path to the category store using the provided tags.

        :param file_path: The Path we wish to save to the category store.
        :param tags: The tags used to represent this file.
        :return: None
        """

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

    def load_from_categories(self, categories):
        """
        Load the images (as Photo objects) that represent the provided categories.

        If 'all' is provided in categories, then all images are returned.
        :param categories: A comma-separated list of categories we wish to retrieve.
        :return: a Generator containing all of the images matching the provided categories.
        """

        def load_category(category):
            cat_path = self.data_path / f'{category}.json'

            if not cat_path.exists():
                print(f'Category "{category}" not found.')
                return []

            with cat_path.open('r') as f:
                existing = json.load(f)

            # This assumes the entry actually exists on the filesystem.
            # Need to check that the file exists!
            return [Path(entry) for entry in existing]

        parsed = [x.strip() for x in categories.split(',')]
        if 'all' in parsed:
            # If any category is all, just return all
            return gather_photos()

        all_paths = set()  # Prevent images from being listed multiple times
        for c in parsed:
            all_paths.update(load_category(c))

        return (Photo(p) for p in all_paths)


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
            # TODO - check to see if we can use any metadata for categorization
            self.current_feed = response.json()['hits']
        else:
            print(f'There was an error connecting to {self.base_url}: {response.status_code}')

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
        if feed:
            with ThreadPoolExecutor(max_workers=4) as executor:
                executor.map(download_photo, feed)


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
            n = img.stem
            print(f'Processing: {img}')
            tags = n.split('-')
            print(f'Found tags: {tags[:-1]}')
            # The last tag is actually in the form "123456.jpg" and includes the file extension
            # which we don't want. Could have alternatively used 'stem' instead of 'name' above,
            # but we'd still want to skip the id at the end.
            category_service.save_to_categories(img, tags[:-1])
            time.sleep(1)


    def test_categories():
        category_service = CategoryService(Path('configs/categories'))
        trees = category_service.load_from_categories('trees,tulip,all')

        for item in trees:
            print(item)


    def setup_db_items():
        tag_service = TaggingService()

    def test_rekog():
        rek = RekognitionTaggingService()
        all_photos = gather_photos()
        for ii in all_photos:
            rek.load_categories_for_photo(ii)
            time.sleep(1)
        # for ii in range(5):
        #     current = next(all_photos)
        #     rek.load_categories_for_photo(current)
        #     time.sleep(1)

    with Path('configs/logging.json').open('r') as lc:
        logging.config.dictConfig(json.load(lc))

    # test_categories()
    # setup_db_items()
    test_rekog()
