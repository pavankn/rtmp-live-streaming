FROM ubuntu:22.04

# Install Python and FFmpeg
RUN apt-get update && apt-get install -y python3 python3-pip ffmpeg && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y iputils-ping dnsutils && rm -rf /var/lib/apt/lists/*

# Install Flask (and optionally requests if needed)
RUN pip install --no-cache-dir flask fastapi uvicorn[standard] python-multipart requests httpx

# Copy the script that generates nginx.conf
#COPY generate_nginx_conf.py /data/generate_nginx_conf.py

# Copy the Python relay script
COPY stream_relay.py /data/stream_relay.py

WORKDIR /app
COPY on_publish.py /app/on_publish.py

COPY entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/app/entrypoint.sh"]
