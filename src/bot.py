import re, threading
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

        # Get last reminder ID so listener doesn't pull tweets already in db
        self.cur.execute("SELECT Max(id) FROM Tweets;")
        query_result = self.cur.fetchone()[0]

        if query_result:
            self.last_id = query_result + 1
        else:
            self.last_id = 1

        self.conn.commit()


    def analyze_tweet_data(self, tweet):
        remind_pattern = r'\[.+\]'
        time_pattern = r'\b(?:[01]{0,1}\d|2[0-4]):[0-5]\d\b'
        date_pattern = r'\b(?:[0-2]{0,1}\d|3[01])[-./](?:0{0,1}\d|1[0-2])(?:[-./]20[1-9]\d|)\b'

        tweet_id = tweet['id']
        tweet_text = tweet['text']

        # Find the username
        username = "@" + tweet['user']['screen_name']
        # username = re.findall(username_pattern, tweet_text)[0]

        # Find text enclosed in brackets
        # if tweet does not contain it an exception is thrown (indexing None)
        reminder = re.findall(remind_pattern, tweet_text)
        if reminder:
            reminder = reminder[0].strip("[").strip("]").strip() # Strip the brackets
            reminder = username + " " + reminder # Add the username to the reminder

        # Find the date
        due_date = re.findall(date_pattern, tweet_text)
        if not due_date: # If date was omitted
            due_date = str(datetime.utcnow().date()) # Use today's date
        else:
            due_date = utils.convert_date(due_date[0])

        # Find the time
        due_datetime = None # Remains none if a time wasn't passed
        due_time = re.findall(time_pattern, tweet_text)
        if due_time:
            due_time = due_time[0]
            if due_time.count(":") == 1: # if only one : in time, seconds were omitted
                due_time = due_time + ":00"
            # Convert to postgresql timestamp format
            due_datetime = "{} {}".format(due_date, due_time)



        # Get coordinates for the timezone offset
        has_coordinates = False
        coordinates = tweet['place']['bounding_box']['coordinates']
        if coordinates:
            print(due_datetime)
            due_datetime = self.utc_time(coordinates[0][0], due_datetime)
            has_coordinates = True

        return tweet_id, reminder, due_datetime, has_coordinates, username


    def utc_time(self, coord, time):
        timestamp = t.time()
        client = utils.oauth_client(*utils.get_credentials(self.conn))

        # Maps API timezone data request
        response, tz = client.request(
            "{}?location={},{}&timestamp={}&key={}".format(
                utils.TZ_URL, coord[1], coord[0], timestamp, utils.get_maps_key(self.conn)
            )
        )
        tz = utils.toJSON(tz)

        tz_offset = tz['dstOffset'] + tz['rawOffset']

        offset_time = datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
        offset_time -= timedelta(seconds=tz_offset)

        return str(offset_time)


    def reply_tweet(self, tweet_id, msg):
        post_url = "https://api.twitter.com/1.1/statuses/update.json"

        encoded_msg = urlencode({"status": msg})

        client = utils.oauth_client(*utils.get_credentials(self.conn))
        response, data = client.request("{}?{}&in_reply_to_status_id={}".format(
            post_url, encoded_msg, tweet_id
        ), method="POST")

        return response, data


    def listen(self):
        while True:
            mention_url = "https://api.twitter.com/1.1/statuses/mentions_timeline.json"
            client = utils.oauth_client(*utils.get_credentials(self.conn))
            # Get all new mentions
            response, tweets = client.request("{}?since_id={}".format(
                mention_url, self.last_id + 1
            ))
            tweets = utils.toJSON(tweets)

            for tweet in tweets:
                tweet_id, tweet_text, tweet_time, coordinates, username = self.analyze_tweet_data(tweet)
                if tweet_id > self.last_id:
                    self.last_id = tweet_id

                if not tweet_text or not tweet_time:
                    continue # Skip the tweet if text or time wasn't passed

                time_now = datetime.utcnow()
                # Convert to datetime format for comparison
                requested_time = datetime.strptime(tweet_time, "%Y-%m-%d %H:%M:%S")

                if requested_time > time_now: # Prevent reminders for the past
                    self.cur.execute("INSERT INTO Tweets VALUES (%s, %s, %s);",
                        (tweet_id, tweet_text, tweet_time))
                    self.conn.commit()

                    msg = ""
                    if coordinates:
                        msg = "{} Created reminder using geolocation for UTC {}, delete tweet to cancel."
                    else:
                        msg = "{} Created reminder for UTC {}, delete tweet to cancel. (Warning: Tweet location was off, time may be different from your timezone)"
                    formatted_msg = msg.format(username, tweet_time)
                    print(formatted_msg)
                    response, data = self.reply_tweet(tweet_id, formatted_msg)
                    # print(response, "\n\n", data)

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

                client = utils.oauth_client(*utils.get_credentials(self.conn))
                # Check if tweet still exists
                response, data = client.request("https://api.twitter.com/1.1/statuses/show.json?id=" + str(tweet_id))
                data = utils.toJSON(data)
                if "errors" in data: # if error in data tweet was deleted
                    print("Reminder {} was deleted".format(tweet_msg))
                    self.cur.execute("DELETE FROM Tweets WHERE id=(%s);", (tweet_id,))
                    self.conn.commit()
                else:
                    print("Sending reminder {}".format(tweet_msg))
                    msg = "Reminder: {}".format(tweet_msg)
                    response, data = self.reply_tweet(tweet_id, msg)
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
