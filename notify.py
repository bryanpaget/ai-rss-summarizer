import sqlite3
import json
from scipy.spatial.distance import cosine

def notify_user():
    metadata_conn = sqlite3.connect('metadata.db')
    cursor = metadata_conn.cursor()

    cursor.execute('SELECT id, title, summary, sentiment_emotions FROM metadata')
    articles = cursor.fetchall()

    # Example user sentiment vector (this could be dynamically calculated)
    user_sentiment_vector = [0.2, 0.5, 0.3]  # Example: sadness, joy, anger

    for article_id, title, summary, sentiment_emotions in articles:
        sentiment_vepctor = json.loads(sentiment_emotions)["score"]
        similarity = 1 - cosine(user_sentiment_vector, sentiment_vector)

        if similarity > 0.8:  # Threshold for "interesting" articles
            print(f"Interesting Article Found:\nTitle: {title}\nSummary: {summary}\n")

    metadata_conn.close()

if __name__ == "__main__":
    notify_user()
