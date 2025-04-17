# Dockerfile
FROM python:3.11-slim-bullseye

WORKDIR /app

# 1) Get security updates + deps
RUN apt-get update \
 && apt-get upgrade -y \
 && apt-get install -y --no-install-recommends \
      build-essential \
      libsqlite3-dev \
 && rm -rf /var/lib/apt/lists/*

# 2) Install Python requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 3) Copy your app
COPY oauth_server.py db.py config.py ./

# 4) Prepare persistent data folder
RUN mkdir -p /data

# 5) Run under Gunicorn
EXPOSE 8000
CMD ["gunicorn","--bind","0.0.0.0:8000","oauth_server:app","-w","2"]