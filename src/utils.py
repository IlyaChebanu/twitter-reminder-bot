import os, re
import psycopg2, oauth2, json
from urllib.parse import urlparse
from datetime import datetime

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
    cursor.execute("SELECT ConsumerKey, ConsumerSecret, AccessToken, AccessSecret FROM Credentials;")
    query_result = cursor.fetchone()
    cursor.close()
    conn.close()
    return query_result

def get_maps_key():
    conn = establish_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MapsKey FROM Credentials;")
    query_result = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return query_result

# converts day month (year) date to YYYY-MM-DD
def convert_date(date):
    date = re.split("[-./]", date)
    if len(date) < 3: # If year wasn't passed
        date.append(str(datetime.utcnow().year)) # Add the year
    date = date[::-1] # Reverse list so year is 1st
    return "-".join(date)

def toJSON(msg):
    return json.loads(msg.decode('latin-1'))
