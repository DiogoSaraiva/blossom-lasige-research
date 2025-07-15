FROM python:3.11.13-slim

LABEL authors="lasige-summer-researchers"

RUN apt-get update && \
    apt-get install -y libgl1 libglib2.0-0 ffmpeg libsm6 libxext6 && \
    pip install --no-cache-dir mediapipe opencv-python numpy requests

WORKDIR /app
COPY blossom_public ./blossom_public
COPY congruent ./congruent

RUN pip install --no-cache-dir -r /app/congruent/requirements.txt

WORKDIR /app/congruent

ENTRYPOINT ["python", "pose_bridge.py"]