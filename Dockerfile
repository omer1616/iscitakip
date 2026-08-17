FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# psycopg[binary] derleme gerektirmez; yalnızca sağlık kontrolü için curl kuruluyor.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x /app/docker/entrypoint.sh

# Statikler imaj içinde toplanır; çalışma anında yazma izni gerekmez.
RUN DJANGO_DEBUG=0 \
    DJANGO_SECRET_KEY=build-time-only \
    DJANGO_SECURE_SSL_REDIRECT=0 \
    python manage.py collectstatic --noinput

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/media /app/data \
    && chown -R app:app /app
USER app

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]