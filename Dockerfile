FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

# libmagic1 is required by python-magic (file-type detection) on Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies before copying source (layer-cache friendly)
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/production.txt

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY . .

# Non-root user for security
RUN groupadd --system app && useradd --system --group app app \
    && mkdir -p staticfiles media \
    && chown -R app:app /app /entrypoint.sh

USER app

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
