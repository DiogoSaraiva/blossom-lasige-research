FROM python:3.11.13-slim

LABEL authors="lasige-summer-researchers"

RUN apt-get update && apt-get install -y git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN git clone --single-branch --branch main https://github.com/DiogoSaraiva/blossom-lasige-research.git /app && \
    cd /app && \
    git submodule update --init --recursive

RUN pip install --no-cache-dir -r /app/requirements.txt

WORKDIR /app/open_hmi/robot_server



ENTRYPOINT ["python", "start.py"]
