import random
from pathlib import Path

from services import gather_photos


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
