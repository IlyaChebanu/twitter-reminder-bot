import os, re
import psycopg2, oauth2
from urllib.parse import urlparse

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

def get_credentials(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT ConsumerKey, ConsumerSecret, AccessToken, AccessSecret FROM Credentials;")
    query_result = cursor.fetchone()
    return query_result

def get_maps_key(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT MapsKey FROM Credentials;")
    query_result = cursor.fetchone()[0]
    return query_result

def date_dmy_to_ymd(date):
    split_date = re.split("[.-/]", date)
    ymd_date = "-".join(split_date[::-1])
    return ymd_date
