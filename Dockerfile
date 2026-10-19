FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN useradd --create-home --uid 1000 bot && mkdir -p /app/data && chown bot:bot /app/data
COPY --chown=bot:bot *.py ./

USER bot
VOLUME ["/app/data"]

CMD ["python", "main.py"]
