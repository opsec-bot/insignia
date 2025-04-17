# Insignia OAuth & CLI

Insignia provides:

- **oauth_server.py**: A Flask OAuth server for Discord authentication and role assignment.
- **insignia.py**: A CLI for administrators to configure guilds, drag users, send verify prompts, and export users.

---
## Table of Contents
1. [Prerequisites](#1-prerequisites)
2. [Domain & DNS Setup](#2-domain--dns-setup)
3. [Server Setup](#3-server-setup)
4. [SSL with Let’s Encrypt](#4-ssl-with-lets-encrypt)
5. [Configure Environment](#5-configure-environment)
6. [Docker Compose Deployment](#6-docker-compose-deployment)
7. [Reverse Proxy with Nginx](#7-reverse-proxy-with-nginx)
8. [Auto-Start with Systemd](#8-auto-start-with-systemd)
9. [Admin CLI Usage](#9-admin-cli-usage)

---
## 1. Prerequisites

- A **Linux server** (e.g. Ubuntu 22.04) with **sudo** access.
- A **domain name** (e.g. `example.com`).
- Your server’s **public IP address** (e.g. `203.0.113.10`).
- A local machine with **Git** and **Docker** (for CLI use).

> **SSH into your server**:
```bash
ssh youruser@203.0.113.10
```

## 2. Domain & DNS Setup

1. Log in to your domain registrar’s dashboard (e.g. GoDaddy, Namecheap).
2. Locate **DNS Management** for `example.com`.
3. Create an **A Record**:
   - **Host**: `auth`
   - **Type**: A
   - **Value**: `203.0.113.10`
   - **TTL**: `600`

After saving, it may take a few minutes to propagate:
```bash
ping auth.example.com
# should resolve to 203.0.113.10
```

## 3. Server Setup

On your Linux server, install Docker and Docker Compose:
```bash
sudo apt update
sudo apt install -y docker.io docker-compose
sudo systemctl enable --now docker
```

Clone this repository:
```bash
cd ~
git clone https://github.com/youruser/insignia.git
cd insignia
```

## 4. SSL with Let’s Encrypt

Install Certbot and the Nginx plugin:
```bash
sudo apt install -y certbot python3-certbot-nginx
```

Obtain and install a certificate for `auth.example.com`:
```bash
sudo certbot --nginx -d auth.example.com
```
Follow prompts to agree to the TOS and enter your email.

Certbot will automatically configure Nginx for SSL and reload it.

## 5. Configure Environment

In the project root, create a file named **`.env`** with exactly these values:
```ini
DISCORD_CLIENT_ID=<your_client_id>
DISCORD_CLIENT_SECRET=<your_client_secret>
DISCORD_BOT_TOKEN=<your_bot_token>
REDIRECT_URI=https://auth.example.com/callback
API_VERSION=v10
API_URL=https://auth.example.com/api
API_SECRET=<your_api_secret>
DB_PATH=/app/insignia.db
```
> **Important:** Do **not** commit `.env` to Git. It contains secrets.

## 6. Docker Compose Deployment Docker Compose Deployment

Create **`docker-compose.yml`** in the same directory (if not present) with:
```yaml
services:
  web:
    build: .
    env_file: .env
    ports:
      - "5000:8000"
    volumes:
      - data:/data
    restart: unless-stopped

volumes:
  data:
```

Build and start the container:
```bash
docker-compose up -d --build
```
Verify it’s running:
```bash
docker-compose ps
```

## 7. Reverse Proxy with Nginx

Create an Nginx server block at `/etc/nginx/sites-available/insignia`:
```nginx
server {
    listen 80;
    server_name auth.example.com;
    return 301 https://$host$request_uri;
}
server {
    listen 443 ssl;
    server_name auth.example.com;

    ssl_certificate /etc/letsencrypt/live/auth.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/auth.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
Enable and reload Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/insignia /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## 8. Auto-Start with Systemd

(Optional) Have Docker Compose start on boot. Create `/etc/systemd/system/insignia.service`:
```ini
[Unit]
Description=Insignia OAuth Server
After=docker.service

[Service]
WorkingDirectory=/home/youruser/insignia
ExecStart=/usr/bin/docker-compose up
ExecStop=/usr/bin/docker-compose down
Restart=always

[Install]
WantedBy=multi-user.target
```
Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable insignia
sudo systemctl start insignia
```

## 9. Admin CLI Usage

On any machine (local or remote) with Python 3:
```bash
git clone https://github.com/youruser/insignia.git
cd insignia
cp .env.example .env        # or create .env with same variables
# adjust API_URL=https://auth.example.com/api, API_SECRET=
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt colorama requests
python insignia.py
```

Use the menu to:

1. Add new guilds & verify roles
2. Drag authenticated users into guilds
3. Send embedded "Verify 🔗" messages
4. Export users to a one-time CSV link
