FROM python:3.13.13-slim-trixie

ENV PATH=/usr/local/bin:$PATH
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
COPY . .
CMD ["python", "-u", "main.py"]