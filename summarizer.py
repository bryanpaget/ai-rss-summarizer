from transformers import pipeline
import sqlite3

# Load summarization pipeline
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

db = sqlite3.connect("feeds.db")
cursor = db.cursor()

# Fetch articles to summarize
cursor.execute("SELECT id, content FROM feeds WHERE summary IS NULL")
articles = cursor.fetchall()

# Generate and store summaries
for article_id, content in articles:
    summary = summarizer(content[:1024], max_length=100, min_length=25, do_sample=False)[0]['summary_text']
    cursor.execute("""
        UPDATE feeds
        SET summary = ?
        WHERE id = ?
    """, (summary, article_id))

db.commit()
db.close()
