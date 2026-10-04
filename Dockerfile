FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Automatically fix Windows line endings (CRLF -> LF) if the file was edited on Windows
RUN sed -i 's/\r$//' requirements.txt

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Flat layout: app code and HTML pages live side by side in /app
COPY *.py ./
COPY index.html register.html asset-register.html explorer.html ./

RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8000
# Render supplies $PORT; --proxy-headers makes request.client.host the real client IP
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
