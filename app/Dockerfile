FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py seed.py gunicorn.conf.py ./
ENV PROMETHEUS_MULTIPROC_DIR=/tmp/prom
EXPOSE 8000
# 2 worker processes x 4 threads. Deliberately modest, like a small legacy server.
CMD ["sh", "-c", "rm -rf /tmp/prom && mkdir -p /tmp/prom && exec gunicorn -c gunicorn.conf.py -w 2 --threads 4 -b 0.0.0.0:8000 app:app"]
