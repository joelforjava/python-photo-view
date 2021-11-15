import json
import logging
import logging.config
from pathlib import Path

from common import CONFIG
from feeds import PhotoFeed, TitledPhotoFeed
from frame import SlideShowFrame
from timers import RepeatedTimer
from services import PixabayPhotoFeedService, PhotoDownloader


def update(downloader, feed):
    print('Updating...')
    downloader.download_feed()
    feed.refresh()


def run():
    with Path('configs/logging.json').open('r') as lc:
        logging.config.dictConfig(json.load(lc))
    feed_service = PixabayPhotoFeedService(CONFIG['service.pixabay'])
    downloader = PhotoDownloader(feed_service, Path('__photo_frame/photos'))
    downloader.download_feed()

    frame_config = CONFIG['DEFAULT']
    _delay = frame_config.getint('delay_ms')

    _x = 0
    _y = 0

    show_titles = frame_config.getboolean('show_titles')
    categories = frame_config.get('categories', 'all')
    if show_titles:
        _feed = TitledPhotoFeed(categories=categories)
    else:
        _feed = PhotoFeed(categories=categories)

    update_interval = frame_config.getint('update_interval', 300)
    thread = RepeatedTimer(update_interval, update, downloader, _feed)
    try:
        app = SlideShowFrame(_feed, _x, _y, _delay)
        app.show_slides()
        app.run()
    finally:
        thread.stop()


if __name__ == '__main__':
    run()
