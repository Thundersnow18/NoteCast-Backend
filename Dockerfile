FROM python:3.11-slim

ENV PYTHONUNBUFFERED 1
ENV PATH="/usr/bin:${PATH}" 

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    libsndfile1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY . .

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080"]
