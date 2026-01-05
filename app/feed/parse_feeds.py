import feedparser

def parse_feeds():
    url = "http://newsfeed.zeit.de/all"
    feed = feedparser.parse(url)
    print(feed)
