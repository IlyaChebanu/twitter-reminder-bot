import unittest
import utils
from bot import Bot

class KnownValues(unittest.TestCase):
    def test_utils_convert_date(self):
        result = utils.convert_date("02/07/2018")
        expected = "2018-07-02"
        self.assertEqual(expected, result)

    def test_utils_toJSON(self):
        result = utils.toJSON(b'{"test": 1094, "another_test": {"another": "value"}}')
        expected = {"test": 1094, "another_test": {"another": "value"}}
        self.assertEqual(expected, result)

    def test_utils_get_tz_offset(self):
        result = utils.get_tz_offset([28.108222, 53.623710])
        expected = 10800
        self.assertEqual(expected, result)

    def test_utils_utc_time(self):
        result = utils.utc_time([28.108222, 53.623710], "2017-06-07 02:40")
        expected = "2017-06-06 23:40"
        self.assertEqual(expected, result)

    def test_bot_analyze_tweet_data(self):
        # Real but edited tweet
        tweet_data = {'coordinates': None, 'truncated': False, 'place': {'full_name': 'Fingal, Ireland', 'id': '73a5d83329504007', 'attributes': {}, 'contained_within': [], 'url': 'https://api.twitter.com/1.1/geo/id/73a5d83329504007.json', 'country': 'Ireland', 'place_type': 'city', 'name': 'Fingal', 'bounding_box': {'coordinates': [[[-6.4757083, 53.3508617], [-5.9957316, 53.3508617], [-5.9957316, 53.6383337], [-6.4757083, 53.6383337]]], 'type': 'Polygon'}, 'country_code': 'IE'}, 'geo': None, 'source': '<a href="http://twitter.com" rel="nofollow">Twitter Web Client</a>', 'is_quote_status': False, 'favorite_count': 0, 'in_reply_to_status_id_str': None, 'id_str': '872232821007540231', 'in_reply_to_status_id': None, 'in_reply_to_user_id': 869715461130399744, 'in_reply_to_user_id_str': '869715461130399744', 'lang': 'en', 'in_reply_to_screen_name': 'createreminder', 'contributors': None, 'retweet_count': 0, 'user': {'contributors_enabled': False, 'is_translator': False, 'screen_name': '_dirtyBit', 'geo_enabled': True, 'profile_background_color': 'F5F8FA', 'profile_use_background_image': True, 'profile_background_image_url': None, 'listed_count': 6, 'profile_image_url_https': 'https://pbs.twimg.com/profile_images/859900439554404352/EQd9D6lX_normal.jpg', 'has_extended_profile': True, 'id_str': '4795555284', 'friends_count': 86, 'time_zone': 'Dublin', 'profile_sidebar_border_color': 'C0DEED', 'following': False, 'url': None, 'profile_image_url': 'http://pbs.twimg.com/profile_images/859900439554404352/EQd9D6lX_normal.jpg', 'lang': 'en', 'follow_request_sent': False, 'verified': False, 'default_profile': True, 'profile_banner_url': 'https://pbs.twimg.com/profile_banners/4795555284/1493851522', 'profile_sidebar_fill_color': 'DDEEF6', 'notifications': False, 'profile_text_color': '333333', 'created_at': 'Thu Jan 21 23:27:34 +0000 2016', 'is_translation_enabled': False, 'followers_count': 78, 'default_profile_image': False, 'protected': False, 'profile_link_color': '1DA1F2', 'favourites_count': 58, 'location': 'Your cache', 'profile_background_tile': False, 'id': 4795555284, 'utc_offset': 3600, 'translator_type': 'none', 'entities': {'description': {'urls': []}}, 'profile_background_image_url_https': None, 'statuses_count': 17234, 'description': 'Pineapple does NOT belong on pizza; Creator of @historyiguess and @createreminder; Pronouns: He/Him/Daddy;', 'name': 'Ilya'}, 'created_at': 'Tue Jun 06 23:24:44 +0000 2017', 'favorited': False, 'text': '@createreminder test 01:50 07/06/2017', 'retweeted': False, 'id': 872232821007540231, 'entities': {'urls': [], 'user_mentions': [{'id_str': '869715461130399744', 'indices': [0, 15], 'id': 869715461130399744, 'screen_name': 'createreminder', 'name': 'Reminders'}], 'symbols': [], 'hashtags': []}}

        result = Bot.analyze_tweet_data(tweet_data)
        expected = (872232821007540231, '@_dirtyBit Reminder: test 01:50 07/06/2017', '2017-06-07 00:50', True, '@_dirtyBit')
        self.assertEqual(expected, result)


if __name__ == '__main__':
    unittest.main()
