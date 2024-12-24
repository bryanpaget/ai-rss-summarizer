from transformers import pipeline
import sqlite3
import json

# Load NLP pipelines
summarizer = pipeline('summarization')
sentiment_analyzer = pipeline('sentiment-analysis')

def summarize_articles():
    # Connect to both databases
    conn = sqlite3.connect('articles.db')
    metadata_conn = sqlite3.connect('metadata.db')
    cursor = conn.cursor()
    metadata_cursor = metadata_conn.cursor()

    # Create the metadata table if it doesn't exist
    metadata_cursor.execute('''
    CREATE TABLE IF NOT EXISTS metadata (
        id TEXT PRIMARY KEY,
        title TEXT,
        summary TEXT,
        sentiment_emotions JSON,
        mental_health_score INTEGER
    )''')

    # Fetch unsummarized articles
    cursor.execute('SELECT id, title, content FROM articles')
    articles = cursor.fetchall()

    for article_id, title, content in articles:
        try:
            # Generate a summary
            summary = summarizer(content, max_length=130, min_length=30, do_sample=False)[0]['summary_text']
        except:
            summary = content[:200] + "..."  # Fallback to a snippet if summarization fails

        # Perform sentiment analysis
        sentiment = sentiment_analyzer(content)[0]
        sentiment_emotions = json.dumps(sentiment)  # Convert dict to JSON string
        mental_health_score = calculate_mental_health_score(sentiment)

        # Store metadata
        metadata_cursor.execute('''
        INSERT INTO metadata (id, title, summary, sentiment_emotions, mental_health_score) 
        VALUES (?, ?, ?, ?, ?)
        ''', (article_id, title, summary, sentiment_emotions, mental_health_score))
    
    metadata_conn.commit()
    conn.close()
    metadata_conn.close()

def calculate_mental_health_score(sentiment):
    # Example scoring logic: Positive sentiment = higher score
    score_map = {'POSITIVE': 8, 'NEGATIVE': 2, 'NEUTRAL': 5}
    return score_map.get(sentiment['label'], 5)

if __name__ == "__main__":
    summarize_articles()
