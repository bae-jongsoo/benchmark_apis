FROM python:3.12-slim

WORKDIR /app

COPY fastapi_app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared_schemas /app/shared_schemas
COPY fastapi_app/ /app/

CMD uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers ${WORKERS:-4}
