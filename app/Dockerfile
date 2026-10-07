FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py seed.py ./
EXPOSE 8000
# 2 worker processes x 4 threads each. Deliberately modest: the legacy box is small.
CMD ["gunicorn", "-w", "2", "--threads", "4", "-b", "0.0.0.0:8000", "app:app"]
