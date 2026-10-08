# Use official lightweight Python image
FROM python:3.10-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend source files into the container
COPY . .

# Expose port for Render
EXPOSE 5000

# Run FastAPI application via Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
