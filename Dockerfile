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

# Expose port 8080 required by Google Cloud Run
EXPOSE 8080

# Run FastAPI application via Uvicorn, dynamically using the PORT environment variable
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]

### What Changed?
1. **Port Changed to 8080**: Updated `EXPOSE` and the default port mapping to `8080` to align with Google Cloud Run standards.
2. **Dynamic Port Binding (`${PORT:-8080}`)**: Using a shell command (`sh -c`) allows Uvicorn to automatically pick up the dynamic `PORT` assigned by Google Cloud Run at runtime, while gracefully defaulting to `8080` during local testing.

### Next Steps:
1. Save this updated configuration into your `Dockerfile`.
2. Ensure your `DATABASE_URL` environment variable is added to your Cloud Run service configuration (*Variables & Secrets* tab).
3. Redeploy your service. It should now successfully pass the TCP startup health check and start up cleanly!
