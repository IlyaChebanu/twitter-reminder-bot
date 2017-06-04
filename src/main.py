import argparse
from bot import Bot
from utils import *

def input_credentials():
    username = input("Bot username: ").strip()
    consumer_key = input("Consumer key: ").strip()
    consumer_secret = input("Consumer secret: ").strip()
    access_token = input("Access token: ").strip()
    access_secret = input("Access secret: ").strip()
    maps_key = input("Google Maps API key: ").strip()
    return username, consumer_key, consumer_secret, access_token, access_secret, maps_key

def initial_setup():
    conn = establish_db_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS \
        Credentials(Name VARCHAR NOT NULL, \
        ConsumerKey VARCHAR NOT NULL, ConsumerSecret VARCHAR NOT NULL, \
        AccessToken VARCHAR NOT NULL, AccessSecret VARCHAR NOT NULL, \
        MapsKey VARCHAR NOT NULL);")
    cursor.execute("TRUNCATE TABLE Credentials;")
    cursor.execute("INSERT INTO Credentials VALUES (%s, %s, %s, %s, %s, %s);", input_credentials())
    conn.commit()
    cursor.close()
    conn.close()
    start_bot()

def start_bot():
    print("Starting bot")
    bot = Bot()
    bot.run()

def main():
    parser = argparse.ArgumentParser(description='Twitter reminder bot.')
    parser.add_argument('--login', action='store_true')
    args = parser.parse_args()

    conn = establish_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT EXISTS (\
        SELECT 1 FROM information_schema.tables \
        WHERE table_name = 'credentials' \
    );")
    num_tables = cursor.fetchone()[0]
    cursor.close()
    conn.close()

    if not num_tables or args.login:
        initial_setup()
    else:
        start_bot()


if __name__ == '__main__':
    main()
