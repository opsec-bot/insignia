# config.py
import os
from dotenv import load_dotenv

load_dotenv()  # pip install python-dotenv

CLIENT_ID = os.environ["DISCORD_CLIENT_ID"]
CLIENT_SECRET = os.environ["DISCORD_CLIENT_SECRET"]
BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
REDIRECT_URI = os.environ["REDIRECT_URI"]
API_VERSION = os.getenv("API_VERSION", "v10")
