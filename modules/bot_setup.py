# modules/bot_setup.py
import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
from modules.utils import log

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("[ERROR] DISCORD_TOKEN not set in environment.")

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix="?", intents=intents, help_command=None)
log("Bot setup complete", "SUCCESS")
