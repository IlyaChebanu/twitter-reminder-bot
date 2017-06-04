import re, threading
import time as t
from datetime import datetime, timedelta, tzinfo
from urllib.parse import urlencode
import utils

MENTION_URL = "https://api.twitter.com/1.1/statuses/mentions_timeline.json"
POST_URL = "https://api.twitter.com/1.1/statuses/update.json"
TZ_URL = 'https://maps.googleapis.com/maps/api/timezone/json'

class Bot:
    def __init__(self):
        self.conn = utils.establish_db_connection()
        self.cur = self.conn.cursor()

        self.cur.execute("CREATE TABLE IF NOT EXISTS \
                          Tweets(id BIGINT NOT NULL, \
                                 reminder VARCHAR NOT NULL, \
                                 due TIMESTAMP NOT NULL); \
                          CREATE TABLE IF NOT EXISTS \
                          TweetIDs(id BIGINT NOT NULL);")

        # Get last reminder ID so listener doesn't pull tweets already in db
        self.cur.execute("SELECT Max(id) FROM TweetIDs;")
        query_result = self.cur.fetchone()

        if query_result:
            self.last_id = query_result[0] + 1
        else:
            self.last_id = 1

        self.conn.commit()


    @staticmethod
    def reply_tweet(tweet_id, msg):
        client = utils.oauth_client(*utils.get_credentials())

        params = "?" + urlencode({
            "in_reply_to_status_id": tweet_id,
            "status": msg
        })
        response, data = client.request(POST_URL + params, method="POST")
        return response, data


    @staticmethod
    def get_tz_offset(coord):
        timestamp = t.time()
        client = utils.oauth_client(*utils.get_credentials())

        # Maps API timezone data request
        params = "?" + urlencode({
            'location': "{},{}".format(coord[1], coord[0]),
            'timestamp': timestamp,
            'key': utils.get_maps_key()
        })
        response, tz = client.request(TZ_URL + params)
        tz = utils.toJSON(tz)

        return tz['dstOffset'] + tz['rawOffset']


    def utc_time(self, coord, time):
        tz_offset = self.get_tz_offset(coord)

        offset_time = datetime.strptime(time, "%Y-%m-%d %H:%M")
        offset_time -= timedelta(seconds=tz_offset)

        return datetime.strftime(offset_time, "%Y-%m-%d %H:%M")


    def get_local_date(self, coord):
        tz_offset = self.get_tz_offset(coord)

        time = datetime.utcnow()
        time += timedelta(seconds=tz_offset)

        return str(time.date())


    def analyze_tweet_data(self, tweet):
        username_pattern = r'@[-_a-zA-Z0-9]+\b\s'
        time_pattern = r'\b(?:[01]{0,1}\d|2[0-4]):[0-5]\d\b'
        date_pattern = r'\b(?:[0-2]{0,1}\d|3[01])[-./](?:0{0,1}\d|1[0-2])(?:[-./]20[1-9]\d|)\b'

        tweet_id = tweet['id']
        tweet_text = tweet['text']
        tweet_text = re.sub(username_pattern, '', tweet_text) # Delete bot username

        # Find the username of person who requested a reminder
        username = "@" + tweet['user']['screen_name']
        tweet_text = username + ' Reminder: ' + tweet_text
        due_datetime = None # Remains none if a time wasn't passed

        # Find the date
        due_date = re.findall(date_pattern, tweet_text)
        if due_date:
            due_date = utils.convert_date(due_date[0]) # convert to timestamp format

        # Find the time
        due_time = re.findall(time_pattern, tweet_text)
        if due_time:
            due_time = due_time[0]

        # Get coordinates for the timezone offset
        has_coordinates = False
        try: # Fails if geolocation was off
            coordinates = tweet['place']['bounding_box']['coordinates']
            if not due_date: # If date was omitted use local date
                due_date = self.get_local_date(coordinates[0][0])
            if due_time:
                due_datetime = "{} {}".format(due_date, due_time)
                due_datetime = self.utc_time(coordinates[0][0], due_datetime)
            has_coordinates = True
        except:
            # If a time was passed, but date wasn't, and coordinates are off:
            if not due_date and due_time:
                # use current UTC date
                due_date = str(datetime.utcnow().date())
                due_datetime = "{} {}".format(due_date, due_time)

        return tweet_id, tweet_text, due_datetime, has_coordinates, username


    def listen(self):
        while True:
            client = utils.oauth_client(*utils.get_credentials())
            # Get all new mentions
            params = "?" + urlencode({"since_id": self.last_id + 1})
            response, tweets = client.request(MENTION_URL + params)
            tweets = utils.toJSON(tweets)

            for tweet in tweets:
                tweet_id, reminder_text, reminder_time, coordinates, username = self.analyze_tweet_data(tweet)
                if tweet_id > self.last_id:
                    self.last_id = tweet_id

                if not reminder_time:
                    continue # Skip the tweet if time wasn't passed

                time_now = datetime.utcnow()
                # Convert to datetime format for comparison
                requested_time = datetime.strptime(reminder_time, "%Y-%m-%d %H:%M")

                if requested_time > time_now: # Prevent reminders for the past
                    self.cur.execute("INSERT INTO Tweets VALUES (%s, %s, %s);",
                        (tweet_id, reminder_text, reminder_time))
                    self.cur.execute("INSERT INTO TweetIDs VALUES (%s);", (tweet_id,))
                    self.conn.commit()

                    msg = ""
                    if coordinates:
                        msg = "{} Created reminder using geolocation for UTC {}, delete tweet to cancel."
                    else:
                        msg = "{} Created reminder for UTC {}, delete tweet to cancel. (Warning: Tweet location was off, time may be different from your timezone)"
                    formatted_msg = msg.format(username, reminder_time)
                    print(formatted_msg)
                    self.reply_tweet(tweet_id, formatted_msg)

            t.sleep(15)


    def remind(self):
        while True:
            # Select due reminders
            self.cur.execute("SELECT id, reminder FROM Tweets WHERE current_timestamp > due;")
            due_tweets = self.cur.fetchall()
            self.conn.commit()

            for tweet in due_tweets:
                tweet_id = tweet[0]
                tweet_msg = tweet[1]

                # Check if tweet still exists
                client = utils.oauth_client(*utils.get_credentials())
                response, data = client.request("https://api.twitter.com/1.1/statuses/show.json?id=" + str(tweet_id))
                data = utils.toJSON(data)

                if "errors" in data: # if error in data tweet was deleted
                    print("Reminder \"{}\" was deleted".format(tweet_msg).encode('utf-8'))
                    self.cur.execute("DELETE FROM Tweets WHERE id=(%s);", (tweet_id,))
                    self.conn.commit()
                else:
                    print("Sending reminder: {}".format(tweet_msg).encode('utf-8'))
                    response, data = self.reply_tweet(tweet_id, tweet_msg)
                    if response.status == 200:
                        self.cur.execute("DELETE FROM Tweets WHERE id=(%s);", (tweet_id,))
                        self.conn.commit()
            t.sleep(30)


    def run(self):
        # Thread the two functions to concurrently
        listen_thread = threading.Thread(target=self.listen)
        listen_thread.daemon = True
        listen_thread.start()

        remind_thread = threading.Thread(target=self.remind)
        remind_thread.daemon = True
        remind_thread.start()

        while True:
            pass # Prevent the program from closing itself immediately
