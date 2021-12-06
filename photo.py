import sqlite3
from datetime import datetime
from pathlib import Path

import inflection
from PIL import Image, ImageTk, ImageDraw, ImageFont


class Photo:
    def __init__(self, file_path: Path, title=None, photo_id=None):
        self.file_path = file_path
        self.image = Image.open(self.file_path)
        self.title = title if title else create_title(file_path)
        self.id = photo_id

    def as_photo_image(self, with_title: bool = False):

        def image_with_title():
            im_x, im_y = self.image.size
            draw = ImageDraw.Draw(self.image)
            font = ImageFont.truetype('/Library/Fonts/Georgia.ttf',
                                      48)  # TODO - will need a better way to look up a font!
            draw.text((5, im_y - 60), self.title, (255, 255, 255), font=font)
            return ImageTk.PhotoImage(self.image)

        if with_title:
            return image_with_title()
        return ImageTk.PhotoImage(self.image)

    def __repr__(self):
        return f'{self.id}: {self.title} at {self.file_path}'


def create_title(image_file: Path):
    file_name = image_file.stem
    # Intended to remove the trailing digits
    minus_ext = ''.join(s for s in file_name if not s.isdigit())
    return inflection.titleize(minus_ext).strip()


def update_photo_metrics(data_path: Path, photo: Photo):

    def increment_times_displayed(entry):
        if not entry:
            return 1
        else:
            return entry + 1

    with sqlite3.connect(data_path) as con:
        con.create_function('incr_times_displayed', 1, increment_times_displayed)
        cur = con.cursor()
        cur.execute("""UPDATE photos 
                       SET times_displayed = incr.new_val,
                           date_last_displayed = ?
                       FROM (
                        SELECT incr_times_displayed(p1.times_displayed) as new_val
                        FROM photos p1
                        WHERE p1.id = ?
                        ) as incr
                        WHERE photos.id = ?""",
                    (datetime.now().isoformat(), photo.id, photo.id,))
        con.commit()
        con.close()


def update_photo_score(data_path: Path, photo: Photo, new_score):
    with sqlite3.connect(data_path) as con:
        cur = con.cursor()
        cur.execute("""UPDATE photos 
                       SET score = ?
                        WHERE photos.id = ?""",
                    (new_score, photo.id,))
        con.commit()
        con.close()
