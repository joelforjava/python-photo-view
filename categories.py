import json
import logging
import logging.config
import sqlite3
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Union

import boto3
import botocore.exceptions

from common import synchronized
from photo import Photo


class RekognitionService:
    def __init__(self, data_path: Path = None):
        if not data_path:
            # TODO - refactor default location to config file?
            data_path = Path('__photo_frame/rekognition')
            if not data_path.exists():
                data_path.mkdir(parents=True, exist_ok=True)
        self.data_path = data_path
        self.log = logging.getLogger('frame.RekognitionService')
        self.client = boto3.client('rekognition')

    def detect_labels(self, file_path: Path):
        photo_bytes = file_path.read_bytes()
        # TODO - ensure bytes < 5MB
        resp = None
        try:
            self.log.info('Calling Rekognition service to detect labels for %s', file_path)
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

    def load_categories_for_photo(self, photo: Photo, confidence=None):
        if not confidence:
            confidence = 70.0

        file_name = photo.file_path.name

        local_data = (self.data_path / file_name).with_suffix('.json')
        if local_data.exists():
            self.log.info('Retrieving labels for %s from local cache', photo.file_path)
            with local_data.open('r') as f:
                resp = json.load(f)
        else:
            resp = self.detect_labels(photo.file_path)
            if resp:
                with local_data.open('x') as f:
                    json.dump(resp, f)

        labels = []
        for label in resp['Labels']:
            svc_confidence = label.get('Confidence', 0.0)
            if svc_confidence >= confidence:
                labels.append(label['Name'].lower())

        return labels


class CategoryService(ABC):
    @abstractmethod
    def save_to_categories(self, file_path, tags: Union[str, list]):
        pass

    @abstractmethod
    def load_from_categories(self, categories: Union[str, list]):
        pass

    @abstractmethod
    def shutdown(self):
        pass

    @classmethod
    def load(cls, service_type, data_path: Path = None):
        if service_type.lower() == 'sql':
            return SqlDbCategoryService(data_path)
        elif service_type.lower() == 'json':
            return JsonCategoryService(data_path)
        else:
            raise ValueError(f'Unknown service type: {service_type}')


class SqlDbCategoryService(CategoryService):
    def __init__(self, data_path: Path = None):
        if not data_path:
            data_path = Path('__photo_frame/db/tags.db')
        self.data_path = data_path
        self.log = logging.getLogger('frame.SqlDbCategoryService')
        requires_setup = False
        if not self.data_path.exists():
            self.log.warning('Data directory "%s" does not exist. Attempting to create', data_path)
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            requires_setup = True
        self.db = sqlite3.connect(data_path, check_same_thread=False)
        self._lock = RLock()
        if requires_setup:
            self._setup()

    def _sync(self):
        """
        Sync data from the JSON Category Storage into the Database.
        """
        json_path = Path('configs/categories')
        for f in json_path.iterdir():
            if f.is_file() and f.suffix == '.json':
                cat_name = f.stem.lower()
                self.log.info(f'Syncing category: %s', cat_name)
                with f.open('r') as cf:
                    file_names = json.load(cf)
                for file_name in file_names:
                    self.save_to_categories(Path(file_name), cat_name)

    @synchronized
    def _setup(self):
        """
        Set up the tables necessary for this service
        """

        def tables():
            """
            Create the tables.
            :return: A set of table names that were created. If set is empty, then tables were already in place.
            """
            self.log.info("Checking tables")
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
                    self.log.info('Creating table: %s', table_name)
                    cur.execute(comm)
                except sqlite3.OperationalError as e:
                    if 'already exists' in str(e):
                        already_exists.add(table_name)
                        self.log.warning('Table %s already exists', table_name)
                    else:
                        raise e
            self.db.commit()

            self.log.info("Completed table creation")
            self.log.info(f'The following tables previously existed: {already_exists}')
            return set(table_mapping.keys()) - already_exists

        try:
            created = tables()
            if created:
                self._sync()
        finally:
            self.log.info('Setup complete')

    @synchronized
    def save_to_categories(self, file_path, tags: Union[str, list]):
        """
        Save a string representation of a Path to the category store using the provided tags.

        :param file_path: The Path we wish to save to the category store.
        :param tags: The tags used to represent this file.
        :return: None
        """

        def check_for_category(cat_name):
            cur = self.db.cursor()
            resp = cur.execute("SELECT id FROM categories WHERE tag = ?", [cat_name])
            return resp.fetchone()[0]

        def add_category(cat_name):
            cur = self.db.cursor()
            resp = cur.execute("INSERT INTO categories (tag) values (?)", [cat_name])
            self.db.commit()
            return resp.lastrowid

        def check_for_photo(photo_path):
            cur = self.db.cursor()
            resp = cur.execute("SELECT id FROM photos WHERE img_path = ?", [str(photo_path)])
            return resp.fetchone()[0]

        def add_photo(photo_path):
            photo = Photo(photo_path)
            im_w, im_h = photo.image.size
            dt_added = datetime.fromtimestamp(photo.file_path.stat().st_ctime).isoformat()
            values = [str(photo.file_path), im_w, im_h, dt_added, photo.title]
            cur = self.db.cursor()
            resp = cur.execute(
                'INSERT INTO photos (img_path, img_width, img_height, date_added, title) values (?,?,?,?,?)',
                values
            )
            self.db.commit()
            return resp.lastrowid

        def check_for_categories_photos(cat_id, photo_id):
            cur = self.db.cursor()
            resp = cur.execute(
                "SELECT category_id, photo_id from categories_photos WHERE category_id = ? and photo_id = ?",
                [cat_id, photo_id]
            )
            return resp.fetchone()[0]

        def add_category_photo_mapping(cat_id, photo_id):
            cur = self.db.cursor()
            resp = cur.execute("INSERT INTO categories_photos (category_id,photo_id) VALUES (?,?)",
                               [cat_id, photo_id])
            self.db.commit()
            return resp.lastrowid

        def update_category(f_path, cat_name):
            self.log.debug('update_category: Saving %s with category: %s', file_path, category)
            try:
                category_id = check_for_category(cat_name)
            except TypeError:
                category_id = add_category(cat_name)
                self.log.info('Category %s added to the database with id %d', cat_name, category_id)
            else:
                self.log.info('Category %s already exists with id %d', cat_name, category_id)

            self.log.debug('update_category: After checking category')
            try:
                photo_id = check_for_photo(f_path)
            except TypeError:
                photo_id = add_photo(f_path)
                self.log.info('Photo %s added to the database with id %d', f_path, photo_id)
            else:
                self.log.info('Photo %s is already in the database with id %d', f_path, photo_id)

            self.log.debug('update_category: After checking photo')
            try:
                check_for_categories_photos(category_id, photo_id)
            except TypeError:
                cat_photo_id = add_category_photo_mapping(category_id, photo_id)
                self.log.info(
                    'Category mapping added for category %s and photo %s at row: %d', cat_name, f_path, cat_photo_id)
            else:
                self.log.warning('Category mapping for category %s and photo %s already exists', cat_name, f_path)

            self.log.debug('update_category: After checking category/photo')

        if isinstance(tags, str):
            categories = [x.strip() for x in tags.split(',')]
        elif isinstance(tags, list):
            categories = tags.copy()
        else:
            categories = []

        self.log.info('Saving %s with categories: %s', file_path, categories)
        for category in categories:
            self.log.info('Saving %s with category: %s', file_path, category)
            update_category(file_path, category)
            self.log.debug('After update_category')
        self.log.debug('After loop')

    def load_from_categories(self, categories: Union[str, list]):
        """
        Load the images (as Photo objects) that represent the provided categories.

        If 'all' is provided in categories, then all images are returned.
        :param categories: A comma-separated list of categories we wish to retrieve.
        :return: a Generator containing all of the images matching the provided categories.
        """

        def load_all_photos():
            stmt = """SELECT * FROM photos p """
            cur = self.db.cursor()
            found = cur.execute(stmt)

            return (Photo(Path(p[1]), p[8]) for p in found.fetchall())

        def load_photos_with_categories(cat_names):
            qmarks = ','.join(['?'] * len(cat_names))
            stmt = f"""SELECT * 
                       FROM photos p WHERE p.id IN (
                         SELECT cp.photo_id FROM categories_photos cp
                         WHERE cp.category_id IN (
                           SELECT c.id
                           FROM categories c
                           WHERE c.tag in ({qmarks})
                         )
                       )"""
            cur = self.db.cursor()
            found = cur.execute(stmt, cat_names)

            # TODO - need to verify the photo exists!
            return (Photo(Path(p[1]), p[8]) for p in found.fetchall())

        if isinstance(categories, str):
            parsed = [x.strip() for x in categories.split(',')]
        elif isinstance(categories, list):
            parsed = [x.strip() for x in categories]
        else:
            parsed = []

        if 'all' in parsed or not parsed:
            # If any category is all, just return all
            return load_all_photos()
        else:
            return load_photos_with_categories(parsed)

    def shutdown(self):
        self.db.close()


class JsonCategoryService(CategoryService):
    def __init__(self, data_path: Path = None):
        if not data_path:
            data_path = Path('configs/categories')
        self.data_path = data_path
        if not self.data_path.exists():
            self.data_path.mkdir(parents=True, exist_ok=True)
        self.log = logging.getLogger('frame.JsonCategoryService')

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
                        self.log.info('Added image %s to category %s', f_path, category)
                    else:
                        self.log.info('Image %s is already saved in category %s.', f_path, category)
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
                self.log.error('Category "%s" not found.', category)
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

    def shutdown(self):
        """ Do Nothing. """
        pass


def gather_photos(from_dir=None):
    if not from_dir:
        from_dir = Path('__photo_frame/photos')
    return (Photo(entry) for entry in from_dir.iterdir() if is_image_file(entry))


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


if __name__ == '__main__':
    # Save previously downloaded images into category files.
    # Some files have extra details, such as usernames, which will result in some strange categories.
    def save_existing():
        category_service = JsonCategoryService(Path('configs/categories'))
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
        category_service = JsonCategoryService(Path('configs/categories'))
        trees = category_service.load_from_categories('trees,tulip,all')

        for item in trees:
            print(item)


    def setup_db_items():
        tag_service = SqlDbCategoryService()

    def test_rekog():
        rek = RekognitionService()
        all_photos = gather_photos()
        for ii in all_photos:
            rek.load_categories_for_photo(ii)
            time.sleep(1)
        # for ii in range(5):
        #     current = next(all_photos)
        #     categories = rek.load_categories_for_photo(current)
        #     print(f'{current} has labels: {categories}')
        #     time.sleep(1)

    def test_db_retrieval():
        tag_service = SqlDbCategoryService()
        photos = tag_service.load_from_categories(['armored', 'apple', 'beach', 'all'])
        for i, photo in enumerate(photos):
            # photo.image.show()
            print(f'{i} -- {photo}')

    def test_db_save_for_existing():
        tag_service = SqlDbCategoryService()
        photo_path = Path('__photo_frame/photos/wave-sea-blue-beach-foam-marina-4162734.jpg')
        categories = ['beach']
        tag_service.save_to_categories(photo_path, categories)

    def test_db_save_for_new():
        tag_service = SqlDbCategoryService()
        photo_path = Path('__photo_frame/photos/flowers-daisies-arrangement-garden-4126095.png')
        categories = ['testinsertphoto']  # to make it easier to remove later
        tag_service.save_to_categories(photo_path, categories)

    with Path('configs/logging.json').open('r') as lc:
        logging.config.dictConfig(json.load(lc))

    # test_categories()
    # setup_db_items()
    test_rekog()
    # test_db_retrieval()
    # test_db_save_for_existing()
    # test_db_save_for_new()
