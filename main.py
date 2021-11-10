from pathlib import Path

from common import CONFIG
from feeds import PhotoFeed, TitledPhotoFeed
from frame import SlideShowFrame
from services import PixabayPhotoFeedService, PhotoDownloader

if __name__ == '__main__':

    feed_service = PixabayPhotoFeedService(CONFIG['service.pixabay'])
    downloader = PhotoDownloader(feed_service, Path('__photo_frame/photos'))
    downloader.download_feed()

    frame_config = CONFIG['DEFAULT']
    _delay = frame_config.getint('delay_ms')

    _x = 0
    _y = 0

    show_titles = frame_config.getboolean('show_titles')
    categories = frame_config['categories']
    if show_titles:
        _feed = TitledPhotoFeed(categories=categories)
    else:
        _feed = PhotoFeed(categories=categories)

    app = SlideShowFrame(_feed, _x, _y, _delay)
    app.show_slides()
    app.run()
