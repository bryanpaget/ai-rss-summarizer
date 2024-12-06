from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import pipeline

# Load the LLM model
print("Loading LLM model...")
generator = pipeline("text-generation", model="EleutherAI/gpt-neo-2.7B")  # Replace with your desired model
print("Model loaded successfully!")

# Initialize FastAPI
app = FastAPI()

# Request schema
class PredictionRequest(BaseModel):
    historical_data: str
    timeframe: str  # e.g., "daily", "weekly", "monthly"

# Route to handle predictions
@app.post("/predict")
async def predict_trends(request: PredictionRequest):
    try:
        # Prepare prompt for the LLM
        prompt = (
            f"Analyze the following historical RSS feed data for the {request.timeframe} timeframe and predict "
            f"emerging trends or important topics:\n\n{request.historical_data}\n\nPredictions:"
        )

        # Generate predictions
        response = generator(prompt, max_length=200, num_return_sequences=1)

        # Return the generated text
        return {"predictions": response[0]["generated_text"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
