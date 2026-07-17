# Base image: minimal Python 3.11 on Debian slim
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements first for better layer caching
# This layer is only rebuilt when requirements.txt changes
COPY requirements.txt .

# Install dependencies (no pip cache to keep image size small)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project into /app
COPY . .

# Document that the app listens on port 7860 (required by Hugging Face Spaces)
EXPOSE 7860

# Start the FastAPI server
# --host 0.0.0.0 makes it reachable from outside the container
# --port 7860 is required by Hugging Face Spaces
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
