import asyncio
import datetime
import os
import random
import json
from discord import Embed, Color, TextChannel
from modules.bot_setup import bot
from modules import aura_manager
from modules.utils import log, seconds_until
from modules.ui import leaderboardEmbed

CONFIG_FILE: str = os.path.join("data", "config.json")
LINES_FILE: str = os.path.join("data", "dailyLines.json")


def load_config() -> None:
    """Load channel config from JSON file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                aura_manager.CHANNEL_ID = data.get("channel_id")
                aura_manager.OWNER_IDS = [int(x) for x in data.get("owner_id", [])]
                log(f"Loaded CHANNEL_ID = {aura_manager.CHANNEL_ID}", 
                    "SUCCESS" if aura_manager.CHANNEL_ID else "WARNING")
                log(f"Loaded OWNER_IDS = {aura_manager.OWNER_IDS}", 
                    "SUCCESS" if aura_manager.OWNER_IDS else "WARNING")
        except Exception as e:
            log(f"Failed to load config.json: {e}", "ERROR")

def save_config() -> None:
    """Save channel config to JSON file."""
    data = {"channel_id": aura_manager.CHANNEL_ID,
            "owner_id": list(aura_manager.OWNER_IDS)}
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    log(f"Saved CHANNEL_ID = {aura_manager.CHANNEL_ID} and OWNER_IDs = {aura_manager.OWNER_IDS}", "SUCCESS")


async def daily_aura_snapshot() -> None:
    """Take a daily snapshot of aura_data at ~09:29 local time and persist to history file."""
    await bot.wait_until_ready()

    # Takes daily snapshot everytime the bot starts (UNCOMMENT FOR DEBUG)
    # log("Running first daily_aura_snapshot immediately (debug)", "INFO")
    # await take_snapshot()

    while not bot.is_closed():
        wait_seconds: float = seconds_until(9, 29)
        hours, minutes, seconds = int(wait_seconds // 3600), int((wait_seconds % 3600) // 60), int(wait_seconds % 60)
        log(f"[Snapshot] Waiting {hours}h {minutes}m {seconds}s until next run", "WARNING")
        await asyncio.sleep(wait_seconds)

        await take_snapshot()


async def take_snapshot() -> None:
    """Helper function to take a snapshot immediately."""
    log("Taking daily snapshot...", "INFO")
    history: dict =  aura_manager.load_history()
    aura_manager.ensure_today(history)
    today: str = datetime.date.today().strftime("%Y-%m-%d")
    timestamp: str = datetime.datetime.now().strftime("%H-%M-%S")
    history[today] = {"time": timestamp, "aura": aura_manager.aura_data.copy()}
    aura_manager.save_json(aura_manager.HISTORY_FILE, history)
    log("Daily snapshot saved", "SUCCESS")


async def daily_leaderboard_data() -> list[str] | str:
    """
    Build the daily leaderboard comparing yesterday -> today.
    Returns a list of formatted strings for the paginator.
    """
    history: dict = aura_manager.load_history()
    dates: list[str] = sorted(history.keys())
    
    if len(dates) < 2:
        return "Not enough data for daily leaderboard!"

    yesterday: dict[str, int] = history[dates[-2]]["aura"]
    today: dict[str, int] = history[dates[-1]]["aura"]

    yesterday_sorted = sorted(yesterday.items(), key=lambda x: x[1], reverse=True)
    yesterday_ranks: dict[str, int] = {user_id: rank for rank, (user_id, _) in enumerate(yesterday_sorted, start=1)}
    
    today_sorted = sorted(today.items(), key=lambda x: x[1], reverse=True)

    formatted_lines = []
    for rank, (user_id, score) in enumerate(today_sorted, start=1):
        # --- SAFE USER LOOKUP ---
        # 1. Start with a fallback name so the variable ALWAYS exists
        user_name = f"User({user_id})" 
        
        # 2. Try to get the name from cache
        user = bot.get_user(int(user_id))
        if user:
            user_name = user.name.capitalize()
        else:
            # 3. If not in cache, try one quick fetch (this can be slow in large loops)
            try:
                user = await bot.fetch_user(int(user_id))
                user_name = user.name.capitalize()
            except:
                pass # user_name stays as "User(id)" if this fails

        # --- CALCULATE DIFFERENCE AND STATUS ---
        old_rank = yesterday_ranks.get(user_id)
        old_score = yesterday.get(user_id, 0)
        diff = score - old_score
        diff_text = f"(+{diff})" if diff > 0 else f"({diff})" if diff < 0 else ""

        if old_rank is None:
            status = "NEW✚"
        elif old_rank > rank:
            status = "AURA▲"
        elif old_rank < rank:
            status = "AURA▼"
        else:
            status = "AURA━"

        # --- FORMAT THE STRING ---
        prefix = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"**#{rank}**")
        line = f"{prefix} **{user_name}** {status}\n\u2003Aura: `{score}` {diff_text}\n"
        formatted_lines.append(line) 

    log("Daily leaderboard data processed", "INFO")
    return formatted_lines

async def post_daily_leaderboard() -> None:
    """Post the daily leaderboard to the configured channel at ~09:30 local time."""
    await bot.wait_until_ready()

    # Posts daily_leaderboard everytime bot starts (UNCOMMENT FOR DEBUGGING)
    # log("Running first post_daily_leaderboard immediately (debug)", "INFO")
    # await send_leaderboard()

    while not bot.is_closed():
        wait_seconds: float = seconds_until(9, 30)
        # wait_seconds: float = 10
        hours, minutes, seconds = int(wait_seconds // 3600), int((wait_seconds % 3600) // 60), int(wait_seconds % 60)
        log(f"[Leaderboard] Waiting {hours}h {minutes}m {seconds}s until next post", "WARNING")
        await asyncio.sleep(wait_seconds)

        await send_leaderboard()


def get_random_aura_message() -> str:
    """Loads the list of aura messages and then picks one at random"""
    with open(LINES_FILE, "r", encoding="utf-8") as f:
        messages = json.load(f)
    return random.choice(messages)

    channel = bot.get_channel(aura_manager.CHANNEL_ID)

async def send_leaderboard() -> None:
    """Helper function to send the leaderboard once."""
    if aura_manager.CHANNEL_ID is None:
        log("CHANNEL_ID not set. Skipping daily leaderboard post.", "WARNING")
        return

    channel = bot.get_channel(aura_manager.CHANNEL_ID)
    
    if channel is None:
        log(f"Channel {aura_manager.CHANNEL_ID} not found. Cannot post.", "ERROR")
        return

    data = await daily_leaderboard_data()
    
    if isinstance(data, str): 
        await channel.send(data)
        return

    #Create the view
    view = leaderboardEmbed(data, title="Daily Aura Standings", color=0x6dab18)
    random_message = get_random_aura_message()
    embed = view.createEmbed()
    
    botText=f"||@here||**{random_message}**"
    await channel.send(content=botText, embed=embed, view=view)

    log("Daily Leaderboard Posted", "SUCCESS")