import feedparser
import sqlite3
from datetime import datetime

# Database setup
db = sqlite3.connect("feeds.db")
cursor = db.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS feeds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        link TEXT,
        published TEXT,
        source TEXT
    )
""")
db.commit()

# Fetch and store feeds
def fetch_feeds(feed_urls):
    for url in feed_urls:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            cursor.execute("""
                INSERT INTO feeds (title, link, published, source)
                VALUES (?, ?, ?, ?)
            """, (entry.title, entry.link, entry.published, feed.feed.title))
    db.commit()

feed_urls = [
    "https://example.com/rss", 
    "https://anotherexample.com/feed"
]
fetch_feeds(feed_urls)
db.close()
