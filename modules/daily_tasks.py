import asyncio
import datetime
import os
import json
from discord import Embed, Color, TextChannel
from modules.bot_setup import bot
from modules.aura_manager import aura_data, load_history, ensure_today, save_json, HISTORY_FILE
from modules.utils import log, seconds_until

CONFIG_FILE: str = os.path.join("data", "config.json")

# Channel ID is loaded from config file or None by default
CHANNEL_ID: int | None = 622609287914717231


def load_config() -> None:
    """Load channel config from JSON file."""
    global CHANNEL_ID
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                CHANNEL_ID = data.get("channel_id")
                log(f"Loaded CHANNEL_ID = {CHANNEL_ID}", "SUCCESS" if CHANNEL_ID else "WARNING")
        except Exception as e:
            log(f"Failed to load config.json: {e}", "ERROR")


def save_config() -> None:
    """Save channel config to JSON file."""
    data = {"channel_id": CHANNEL_ID}
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    log(f"Saved CHANNEL_ID = {CHANNEL_ID}", "SUCCESS")


async def daily_aura_snapshot() -> None:
    """Take a daily snapshot of aura_data at ~09:29 local time and persist to history file."""
    await bot.wait_until_ready()

    # Run once immediately for debugging
    log("Running first daily_aura_snapshot immediately (debug)", "INFO")
    await take_snapshot()

    while not bot.is_closed():
        wait_seconds: float = seconds_until(9, 29)
        hours, minutes, seconds = int(wait_seconds // 3600), int((wait_seconds % 3600) // 60), int(wait_seconds % 60)
        log(f"[Snapshot] Waiting {hours}h {minutes}m {seconds}s until next run", "WARNING")
        await asyncio.sleep(wait_seconds)

        await take_snapshot()


async def take_snapshot() -> None:
    """Helper function to take a snapshot immediately."""
    log("Taking daily snapshot...", "INFO")
    history: dict = load_history()
    ensure_today(history)
    today: str = datetime.date.today().strftime("%Y-%m-%d")
    timestamp: str = datetime.datetime.now().strftime("%H-%M-%S")
    history[today] = {"time": timestamp, "aura": aura_data.copy()}
    save_json(HISTORY_FILE, history)
    log("Daily snapshot saved", "SUCCESS")


async def daily_leaderboard_embed() -> Embed | str:
    """
    Build the daily leaderboard embed comparing yesterday -> today.
    Returns Embed or a string message if not enough data.
    """
    history: dict = load_history()
    dates: list[str] = sorted(history.keys())
    if len(dates) < 2:
        return "Not enough data for daily leaderboard!"

    yesterday: dict[str, int] = history[dates[-2]]["aura"]
    today: dict[str, int] = history[dates[-1]]["aura"]

    yesterday_sorted = sorted(yesterday.items(), key=lambda x: x[1], reverse=True)
    yesterday_ranks: dict[str, int] = {user_id: rank for rank, (user_id, _) in enumerate(yesterday_sorted, start=1)}
    today_sorted = sorted(today.items(), key=lambda x: x[1], reverse=True)

    embed = Embed(title="Daily Aura Ranking", description="--------------------------------------", color=Color(0x32CD32))
    embed.set_footer(text=f"Updated: {dates[-1]}")

    for rank, (user_id, score) in enumerate(today_sorted, start=1):
        user = await bot.fetch_user(int(user_id))
        user_name: str = str(user.name).capitalize()
        old_rank: int | None = yesterday_ranks.get(user_id)
        old_score: int = yesterday.get(user_id, 0)
        diff: int = score - old_score
        diff_text: str = f"(+{diff})" if diff > 0 else f"({diff})" if diff < 0 else ""

        if old_rank is None:
            status = "NEW✚"
        elif old_rank > rank:
            status = "AURA▲"
        elif old_rank < rank:
            status = "AURA▼"
        else:
            status = "AURA━"

        prefix = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, str(rank))
        embed.add_field(name=f"{prefix} > {user_name} {status}", value=f"Aura: {score} {diff_text}", inline=False)

    log("Daily leaderboard embed created", "INFO")
    return embed


async def post_daily_leaderboard() -> None:
    """Post the daily leaderboard to the configured channel at ~09:30 local time."""
    await bot.wait_until_ready()
    load_config()

    # Run once immediately for debugging
    log("Running first post_daily_leaderboard immediately (debug)", "INFO")
    await send_leaderboard()

    while not bot.is_closed():
        wait_seconds: float = seconds_until(9, 30)
        # wait_seconds: float = 10
        hours, minutes, seconds = int(wait_seconds // 3600), int((wait_seconds % 3600) // 60), int(wait_seconds % 60)
        log(f"[Leaderboard] Waiting {hours}h {minutes}m {seconds}s until next post", "WARNING")
        await asyncio.sleep(wait_seconds)

        await send_leaderboard()


async def send_leaderboard() -> None:
    """Helper function to send the leaderboard once."""
    if CHANNEL_ID is None:
        log("CHANNEL_ID not set. Skipping daily leaderboard post.", "WARNING")
        return

    channel: TextChannel | None = bot.get_channel(CHANNEL_ID)  # type: ignore
    if channel is None:
        log(f"Channel {CHANNEL_ID} not found. Cannot post daily leaderboard.", "ERROR")
        return

    embed_or_msg: Embed | str = await daily_leaderboard_embed()
    if isinstance(embed_or_msg, Embed):
        await channel.send("Today's aura standings:")
        await channel.send(embed=embed_or_msg)
    else:
        await channel.send(embed_or_msg)

