FROM python:3.10

COPY . /app/
RUN pip install -r /app/requirements.txt
WORKDIR /app

ENTRYPOINT watchmedo auto-restart --directory=/app --pattern=*.py --recursive -- celery -A config.celery worker --loglevel=INFO