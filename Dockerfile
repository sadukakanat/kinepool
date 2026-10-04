FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Flat layout: app code and HTML pages live side by side in /app
COPY *.py ./
COPY index.html register.html asset-register.html explorer.html ./

RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8000
# Render supplies $PORT; --proxy-headers makes request.client.host the real client IP
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]

### Deployment on Render Checklist:
1. **Repository Structure**: Push all your files (`main.py`, `database.py`, `models.py`, engines, `.html` files, `requirements.txt`, and this `Dockerfile`) to your GitHub repository.
2. **Create Web Service on Render**: Connect your repository and select **Docker** as the environment.
3. **Environment Variables**: Configure the required environment variables in your Render dashboard:
   * `DATABASE_URL`: Your PostgreSQL connection string (Render automatically provides this if you attach a PostgreSQL database).
   * `RVE_SIGNING_KEY`: A long, secure random secret string to sign telemetry packets.
   * `ADMIN_API_KEY`: *(Optional)* A secure key if you want to enable anchor node registrations via `POST /api/v8/nodes/register`.
