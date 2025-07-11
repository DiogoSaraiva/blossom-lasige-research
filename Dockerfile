FROM python:3.12-slim

LABEL authors="lasige-summer-researchers"

RUN apt-get update && apt-get install -y git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN git clone --recurse-submodules --single-branch --branch testing https://github.com/DiogoSaraiva/blossom-lasige-research.git /app

WORKDIR /app/open_hmi/blossom_public/

RUN pip install --no-cache-dir -r requirements.txt || true

ENTRYPOINT ["python", "start.py"]
