from pathlib import Path

import inflection
from PIL import Image, ImageTk, ImageDraw, ImageFont


class Photo:
    def __init__(self, file_path: Path, title=None):
        self.file_path = file_path
        self.image = Image.open(self.file_path)
        self.title = title if title else create_title(file_path)

    def as_photo_image(self, with_title: bool = False):
        if with_title:
            return self.__as_photo_image_with_title()
        return ImageTk.PhotoImage(self.image)

    def __as_photo_image_with_title(self):
        im_x, im_y = self.image.size
        draw = ImageDraw.Draw(self.image)
        font = ImageFont.truetype('/Library/Fonts/Georgia.ttf', 48)  # TODO - will need a better way to look up a font!
        draw.text((5, im_y - 60), self.title, (255, 255, 255), font=font)
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