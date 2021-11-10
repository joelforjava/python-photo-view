import random
from pathlib import Path

from services import CategoryService


class PhotoFeed:
    def __init__(self, categories=None):
        if not categories:
            categories = 'all'
        self.temp_dir = Path('__photo_frame/photos')
        if not self.temp_dir.exists():
            print('Temp directory not found. Will attempt to create.')
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.current_image = None
        self.photo_list = []
        self.photo_count = 0
        self.categories = categories
        self.category_service = CategoryService(Path('configs/categories'))
        self.refresh()

    def refresh(self):
        self.photo_list = list(self.category_service.load_from_categories(self.categories))
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
