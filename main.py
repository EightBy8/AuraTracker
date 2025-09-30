import os
from modules.bot_setup import bot
from modules.aura_manager import load_aura, load_history, ensure_today, save_json, load_aura_count, HISTORY_FILE
from modules.utils import log
from modules.daily_tasks import load_config, daily_aura_snapshot, post_daily_leaderboard

# Load data into memory before registering commands/events
load_config()
load_aura()
load_aura_count()
history = load_history()
ensure_today(history)
save_json(HISTORY_FILE, history)

# Import commands and events so they register with the bot
import modules.commands  # noqa: E402,F401
import modules.events    # noqa: E402,F401


async def setup_hook():
    """Called auto atically by discord.py when bot is ready to start background tasks."""
    bot.loop.create_task(daily_aura_snapshot())
    bot.loop.create_task(post_daily_leaderboard())
    log("Background tasks scheduled", "SUCCESS")


# Assign proper coroutine function
bot.setup_hook = setup_hook

# Run bot
log("Bot is starting...", "SUCCESS")
bot.run(os.getenv("DISCORD_TOKEN"))

