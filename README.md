# Twitter reminder bot

Code that powers the [@createreminder](https://twitter.com/createreminder) twitter bot.

To update the credentials use `python src\main.py --login`

## How to use the bot:
Turn tweet location on to use your local timezone, else UTC is assumed.

Tweet at the bot with any text that must at least contain a time (24h format). If the date (DD-MM-YYYY format, year is optional) is omitted, current day is used.

There is no other strict rules on structuring reminder text, where to put the time and/or date etc.

If the reminder was successfully created, the bot will notify you by replying to your tweet, and when the reminder is due it will reply to the same tweet again.

## Example tweets:
@createreminder Go shopping at 14:00

@createreminder 9:00 Walk the dogs

@createreminder Go to uni 13-07-2017 10:00

@createreminder Watch movies 20:00 17/09
