import sqlite3

# Predefined trends
TRENDS = {
    "Conflict and War": ["war", "conflict", "military", "terrorism"],
    "Political Developments": ["election", "policy", "protest", "government"],
    "Economic and Financial Issues": ["market", "inflation", "recession", "finance"],
    "Natural Disasters": ["earthquake", "flood", "wildfire", "hurricane"],
    "Environmental and Climate Concerns": ["climate", "pollution", "conservation", "biodiversity"],
    "Public Health and Medicine": ["pandemic", "disease", "vaccine", "healthcare"],
    "Science and Technology Advancements": ["space", "AI", "research", "cybersecurity"],
    "Social and Cultural Movements": ["rights", "equality", "LGBTQ", "culture"],
    "Crime and Justice": ["crime", "justice", "trial", "corruption"],
    "Entertainment and Pop Culture": ["celebrity", "movie", "music", "sports"],
    "Humanitarian Crises": ["refugee", "poverty", "hunger", "human rights"],
    "Innovations and Solutions": ["innovation", "solution", "progress", "cooperation"]
}

def categorize_articles():
    conn = sqlite3.connect('articles.db')
    trends_conn = sqlite3.connect('trends.db')
    cursor = conn.cursor()
    trends_cursor = trends_conn.cursor()

    # Create the trends table if it doesn't exist
    trends_cursor.execute('''
    CREATE TABLE IF NOT EXISTS trends (
        id TEXT PRIMARY KEY,
        title TEXT,
        trend_tag TEXT
    )''')

    cursor.execute('SELECT id, title, content FROM articles')
    articles = cursor.fetchall()

    for article_id, title, content in articles:
        trend_tag = assign_trend(content)
        trends_cursor.execute('''
        INSERT INTO trends (id, title, trend_tag) 
        VALUES (?, ?, ?)
        ''', (article_id, title, trend_tag))
    
    trends_conn.commit()
    conn.close()
    trends_conn.close()

def assign_trend(content):
    for trend, keywords in TRENDS.items():
        if any(keyword.lower() in content.lower() for keyword in keywords):
            return trend
    return "Uncategorized"

if __name__ == "__main__":
    categorize_articles()
