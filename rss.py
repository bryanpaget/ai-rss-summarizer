import feedparser
import sqlite3
import uuid

def fetch_articles(feed_urls):
    # Connect to the SQLite database
    conn = sqlite3.connect('articles.db')
    cursor = conn.cursor()
    
    # Create the articles table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS articles (
        id TEXT PRIMARY KEY,
        title TEXT,
        date TEXT,
        content TEXT,
        url TEXT
    )''')

    # Iterate through RSS feeds and fetch articles
    for feed_url in feed_urls:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            # Generate a unique ID for each article
            unique_id = str(uuid.uuid4())
            title = entry.get('title', 'No Title')
            date = entry.get('published', 'No Date')
            # Prefer content, fallback to summary, then title
            content = entry.get('content', [{'value': entry.get('summary', title)}])[0]['value']
            url = entry.get('link', '')

            # Insert the article into the database
            cursor.execute('''
            INSERT OR IGNORE INTO articles (id, title, date, content, url) 
            VALUES (?, ?, ?, ?, ?)
            ''', (unique_id, title, date, content, url))
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    # Read the RSS feed URLs from feeds.txt
    with open('feeds.txt', 'r') as f:
        feed_urls = [line.strip() for line in f.readlines()]
    fetch_articles(feed_urls)
