FROM python:3.11.13-slim

LABEL authors="lasige-summer-researchers"
RUN apt-get update && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY blossom_public ./blossom_public
COPY open_hmi ./open_hmi


RUN pip install --no-cache-dir -r /app/open_hmi/requirements.txt

WORKDIR /app/open_hmi/robot_server

ENTRYPOINT ["python", "start.py"]
