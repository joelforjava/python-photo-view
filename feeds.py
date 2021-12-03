import logging
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from categories import JsonCategoryService
from photo import update_photo_metrics


class PhotoFeed:
    def __init__(self, categories=None, category_service=None):
        if not categories:
            categories = 'all'
        if not category_service:
            category_service = JsonCategoryService(Path('configs/categories'))
        self.log = logging.getLogger('frame.PhotoFeed')
        self.log.info('Using category service of type %s', type(category_service))
        self.temp_dir = Path('__photo_frame/photos')
        if not self.temp_dir.exists():
            self.log.debug('Temp directory not found. Will attempt to create.')
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.current_image = None
        self.photo_list = []
        self.photo_count = 0
        self.categories = categories
        self.category_service = category_service
        self.refresh()

    def refresh(self):
        old_size = self.photo_count
        self.photo_list = list(self.category_service.load_from_categories(self.categories))
        self.photo_count = len(self.photo_list)
        self.log.info('Feed photo count: %d -> %d', old_size, self.photo_count)

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
            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(update_photo_metrics, Path('__photo_frame/db/tags.db'), selected)
            return selected.as_photo_image(), selected.title
        else:
            raise StopIteration()

    def next_x(self, count=5):
        sample_size = count if count <= self.photo_count else self.photo_count
        sample = random.sample(self.photo_list, sample_size)
        return [(s.as_photo_image(), s.title) for s in sample]


class TitledPhotoFeed(PhotoFeed):
    def next(self):
        if self.has_photos:
            selected = random.choice(self.photo_list)
            return selected.as_photo_image(with_title=True), selected.title
        else:
            raise StopIteration()
