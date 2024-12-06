from fbprophet import Prophet
import pandas as pd
import sqlite3

db = sqlite3.connect("feeds.db")
cursor = db.cursor()

# Fetch publication dates and counts
cursor.execute("""
    SELECT published, COUNT(*) as article_count
    FROM feeds
    GROUP BY published
""")
data = cursor.fetchall()

# Prepare data for Prophet
df = pd.DataFrame(data, columns=['ds', 'y'])
df['ds'] = pd.to_datetime(df['ds'])

# Train Prophet model
model = Prophet()
model.fit(df)

# Predict future trends
future = model.make_future_dataframe(periods=30)
forecast = model.predict(future)

# Save predictions to database
forecast[['ds', 'yhat']].to_csv("predictions.csv")
db.close()
