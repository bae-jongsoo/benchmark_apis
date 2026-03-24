FROM python:3.12-slim

WORKDIR /app

COPY django_app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared_schemas /app/shared_schemas
COPY django_app/ /app/

ENTRYPOINT ["bash", "entrypoint.sh"]
CMD gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers ${WORKERS:-4} \
    --keep-alive 30 \
    --timeout 120
