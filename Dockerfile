# Use an official Python runtime as a base image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY llm_service.py .

# Expose the port for the FastAPI app
EXPOSE 8000

# Command to run the FastAPI app
CMD ["uvicorn", "llm_service:app", "--host", "0.0.0.0", "--port", "8000"]
