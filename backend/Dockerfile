FROM python:3.12-slim

# Keep Python output buffered and avoid writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies and build tools necessary for some Python packages.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first to leverage Docker layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy the Django project files and media directory definition.
COPY . .

# Ensure media directory exists so that uploads mount cleanly.
RUN mkdir -p /app/media

EXPOSE 8000

# Default command runs the Django app using gunicorn for compatibility with production environments.
CMD ["gunicorn", "backend.wsgi:application", "--bind", "0.0.0.0:8000"]
