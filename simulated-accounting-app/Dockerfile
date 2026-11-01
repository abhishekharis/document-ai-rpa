FROM python:3.12-slim

RUN useradd --create-home --uid 10001 app \
    && mkdir -p /data && chown app /data

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py db.py ./
COPY templates ./templates

USER app
ENV ACCOUNTING_DB_PATH=/data/accounting.db
VOLUME /data

EXPOSE 3001
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3001/api/records')"
# One worker: SQLite has a single writer. Threads handle concurrent requests.
CMD ["gunicorn", "--bind", "0.0.0.0:3001", "--workers", "1", "--threads", "4", "app:app"]
