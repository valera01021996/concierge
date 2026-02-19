FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ bot/

CMD uvicorn bot.main:app --host 0.0.0.0 --port ${BOT_PORT:-8080}
