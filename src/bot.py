import json
import re
import time as t
from datetime import datetime, timedelta
from urllib.parse import urlencode
import utils

class Bot:
    def __init__(self, conn=None):
        self.conn = conn
        self.cur = self.conn.cursor()

        self.cur.execute("CREATE TABLE IF NOT EXISTS \
                          Tweets(id BIGINT NOT NULL, \
                                 reminder VARCHAR NOT NULL, \
                                 due TIMESTAMP NOT NULL);")
        self.cur.execute("SELECT Max(id) FROM Tweets;")
        query_result = self.cur.fetchone()[0]
        print(query_result)
        if query_result:
            self.last_id = query_result + 1
        else:
            self.last_id = 1
        self.conn.commit()


    def analyze_tweet_data(self, tweet):
        remind_pattern = r'\[.+\]'
        time_pattern = r'\b(?:[01]\d|2[0-4]):[0-5]\d\b'
        date_pattern = r'\b(?:[0-2]\d|3[01])(?:-|.|\/)(?:0\d|1[0-2])(?:-|.|\/)20[1-9]\d\b'

        tweet_id = tweet['id']
        tweet_text = tweet['text']

        reminder = re.findall(remind_pattern, tweet_text)[0]
        reminder = reminder.strip("[").strip("]").strip() # Strip the brackets

        due_date = re.findall(date_pattern, tweet_text)[0]
        conv_date = utils.date_dmy_to_ymd(due_date) # Convert to YYYY-MM-DD

        due_time = re.findall(time_pattern, tweet_text)[0]

        due_datetime = "{} {}".format(conv_date, due_time)

        coordinates = tweet['place']['bounding_box']['coordinates'][0][0]
        if coordinates:
            due_datetime = self.utc_time(coordinates, due_datetime)

        return tweet_id, reminder, due_datetime


    def utc_time(self, coord, time):
        timestamp = t.time()
        client = utils.oauth_client(*utils.get_credentials(self.conn))

        response, tz = client.request(
            "{}?location={},{}&timestamp={}&key={}".format(
                utils.TZ_URL, coord[1], coord[0], timestamp, utils.get_maps_key(self.conn)
            )
        )
        tz = json.loads(tz.decode('latin-1'))

        tz_offset = tz['dstOffset'] + tz['rawOffset']

        offset_time = datetime.strptime(time, "%Y-%m-%d %H:%M")
        offset_time += timedelta(seconds=tz_offset)

        return str(offset_time)


    def reply_tweet(self, tweet_id, time):
        post_url = "https://api.twitter.com/1.1/statuses/update.json"

        msg = "Created reminder for UTC {}, delete tweet to cancel."
        formatted_msg = msg.format(tweet_time)
        encoded_msg = urlencode({"status": formatted_msg})

        response, data = client.request("{}?in_reply_to_status_id={}&{}".format(
            post_url, tweet_id, encoded_msg
        ), method="POST")

        return response, data


    def listen(self):
        while True:
            client = utils.oauth_client(*utils.get_credentials(self.conn))
            mention_url = "https://api.twitter.com/1.1/statuses/mentions_timeline.json"
            response, tweets = client.request("{}?since_id={}".format(
                mention_url, self.last_id + 1
            ))

            print(response, '\n\n')
            tweets = json.loads(tweets.decode("latin-1"))
            for i, tweet in enumerate(tweets):
                print(i, ": ", tweet, "\n\n")

                try:
                    tweet_id, tweet_text, tweet_time = self.analyze_tweet_data(tweet)
                    self.last_id = tweet_id

                    time_now = datetime.utcnow()
                    requested_time = datetime.strptime(tweet_time, "%Y-%m-%d %H:%M:%S")

                    if requested_time > time_now: # Prevent reminders for the past
                        self.cur.execute("INSERT INTO Tweets VALUES (%s, %s, %s);",
                            (tweet_id, tweet_text, tweet_time))
                        self.conn.commit()
                        reply_tweet(tweet_id, tweet_time)
                except:
                    pass # Invalid request syntax

            t.sleep(30)
