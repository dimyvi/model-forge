FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY local.requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt gunicorn==23.0.0

COPY . .
RUN mkdir -p /app/media /app/staticfiles

EXPOSE 8000

CMD ["gunicorn", "backend_config.wsgi:application", "--bind=0.0.0.0:8000", "--workers=2", "--timeout=60", "--access-logfile=-", "--error-logfile=-"]
