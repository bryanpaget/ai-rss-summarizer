import requests
from bs4 import BeautifulSoup
import sqlite3

db = sqlite3.connect("feeds.db")
cursor = db.cursor()

# Fetch articles from database
cursor.execute("SELECT id, link FROM feeds WHERE content IS NULL")
articles = cursor.fetchall()

# Scrape content
def scrape_article(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup.find('article').get_text()  # Adjust selector as needed.

# Store scraped content
for article_id, link in articles:
    try:
        content = scrape_article(link)
        cursor.execute("""
            UPDATE feeds
            SET content = ?
            WHERE id = ?
        """, (content, article_id))
    except Exception as e:
        print(f"Failed to scrape {link}: {e}")

db.commit()
db.close()
