import os
import random

import requests


class SlideShowService:

    def __init__(self):
        self.temp_dir = '__photo_frame/photos'

    def init_images(self):
        pass

    def select_images(self, count=5):
        selected = []
        while len(selected) < count:
            curr_img = self.get_random_photo()
            if curr_img not in selected:
                selected.append(curr_img)
                print(f'Added: {curr_img}')
        # This could potentially cause an issue if the number of available files is < count
        return selected

    def get_random_photo(self):
        print('Loading Random Photo from cache')
        photo_list = []
        for filename in os.listdir(self.temp_dir):
            if is_image_file(filename):
                photo_list.append(filename)
        photo_count = len(photo_list)
        if photo_count:
            random_index = random.randint(0, photo_count-1)
            selected_filename = photo_list[random_index]
            return f'{self.temp_dir}/{selected_filename}'
        return None


def is_image_file(filename):
	if filename.endswith('.jpg') or filename.endswith('.gif') or filename.endswith('.png'):
		return True
	return False


class PixabayPhotoFeedService:
    def __init__(self, args):
	    self.base_url = args['request']['base_url']
	    self.api_token = args['request']['token']
	    self.image_key = args['request']['image_key']
	    self.current_feed = None

    def retrieve_feed(self):
        """ Get latest photo feed """
        data = { 
            'key': self.api_token, 
            'order': 'popular', 
            'editors_choice': 'false', 
            'image_type': 'photo', 
            'per_page': 28
        }
        headers = { 'Content-Type': 'application/json' }

        print(f'Downloading feed from {self.base_url}')
        response = requests.get(self.base_url, params=data, headers=headers)
        if (response.status_code == 200):
            self.current_feed = response.json()['hits']
        else:
            pass  # Do we just print an error? We probably shouldn't terminate the program!

