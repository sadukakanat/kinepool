# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Install system dependencies if required (e.g., build-essential, libpq-dev)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 1. Create a non-root user and group
RUN groupadd -r appuser && useradd -r -g appuser -d /home/appuser -m -s /bin/bash appuser

# Set environment variables for the non-root user
ENV HOME=/home/appuser
ENV PATH="/home/appuser/.local/bin:$PATH"

# Set the working directory inside the container
WORKDIR /app

# Copy requirements.txt first and ensure proper ownership for the non-root user
COPY --chown=appuser:appuser requirements.txt .

# 2. Switch to the non-root user
USER appuser

# 3. Install Python dependencies locally into the user directory
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code with proper ownership
COPY --chown=appuser:appuser . .

# Expose port (if applicable, e.g., for Flask/FastAPI)
# EXPOSE 8000

# Run the application
CMD ["python", "main.py"]
