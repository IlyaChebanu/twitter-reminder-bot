import os
import re
import httplib2
import json
import psycopg2
import oauth2
import time as t
from urllib.parse import urlparse, urlencode
from datetime import datetime, timedelta

TZ_URL = 'https://maps.googleapis.com/maps/api/timezone/json'


def establish_db_connection():
    url = urlparse(os.environ["DATABASE_URL"])

    conn = psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )
    return conn


def oauth_client(consumer_key, consumer_secret, access_token, access_secret):
    consumer = oauth2.Consumer(key=consumer_key, secret=consumer_secret)
    token = oauth2.Token(key=access_token, secret=access_secret)
    client = oauth2.Client(consumer, token)
    return client


def get_credentials():
    conn = establish_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Credentials;")
    query_result = cursor.fetchone()
    cursor.close()
    conn.close()
    return query_result


def toJSON(msg):
    return json.loads(msg.decode('latin-1'))


# converts day month (year) date to YYYY-MM-DD
def convert_date(date):
    date = re.split("[-./]", date)
    if len(date) < 3:  # If year wasn't passed
        date.append(str(datetime.utcnow().year))  # Add the year
    date = date[::-1]  # Reverse list so year is 1st
    return "-".join(date)


# returns offset from UTC in seconds
def get_tz_offset(coord):
    timestamp = t.time()
    client = httplib2.Http()

    # Maps API timezone data request
    params = "?" + urlencode({
        'location': "{},{}".format(coord[1], coord[0]),
        'timestamp': timestamp,
        'key': "AIzaSyC40RWwQJbqOt9UpfbzZsUW5GwyKChfv_I"
    })
    response, tz = client.request(TZ_URL + params, headers={'connection': 'close'})
    tz = toJSON(tz)

    return tz['dstOffset'] + tz['rawOffset']


# converts local time to utc time
def utc_time(coord, time):
    tz_offset = get_tz_offset(coord)

    offset_time = datetime.strptime(time, "%Y-%m-%d %H:%M")
    offset_time -= timedelta(seconds=tz_offset)

    return datetime.strftime(offset_time, "%Y-%m-%d %H:%M")


def get_local_date(coord):
    tz_offset = get_tz_offset(coord)

    time = datetime.utcnow()
    time += timedelta(seconds=tz_offset)

    return str(time.date())
