import asyncio
import datetime as dt  # Alias the whole module as 'dt'
import os
import random
import json
from discord import Embed, Color, TextChannel
from discord.ext import tasks
from modules.bot_setup import bot
from modules import aura_manager
from modules.utils import log, seconds_until
from modules.ui import leaderboardEmbed, randomButton, goldenButtonEmbed

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
                aura_manager.RESET_DAY = data.get("reset_day", 1)
                log(
                    f"Loaded CHANNEL_ID = {aura_manager.CHANNEL_ID}",
                    "SUCCESS" if aura_manager.CHANNEL_ID else "WARNING",
                )
                log(
                    f"Loaded OWNER_IDS = {aura_manager.OWNER_IDS}",
                    "SUCCESS" if aura_manager.OWNER_IDS else "WARNING",
                )
                log(
                    f"Loaded RESET_DAY = {aura_manager.RESET_DAY}",
                    "SUCCESS",
                )
        except Exception as e:
            log(f"Failed to load config.json: {e}", "ERROR")


def save_config() -> None:
    """Save channel config to JSON file."""
    data = {
        "channel_id": aura_manager.CHANNEL_ID,
        "owner_id": list(aura_manager.OWNER_IDS),
        "reset_day": aura_manager.RESET_DAY,
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    log(
        f"Saved CHANNEL_ID = {aura_manager.CHANNEL_ID}, OWNER_IDs = {aura_manager.OWNER_IDS}, and RESET_DAY = {aura_manager.RESET_DAY}",
        "SUCCESS",
    )


async def daily_aura_snapshot() -> None:
    """Take a daily snapshot of aura_data at ~09:29 local time and persist to history file."""
    await bot.wait_until_ready()

    # Takes daily snapshot everytime the bot starts (UNCOMMENT FOR DEBUG)
    # log("Running first daily_aura_snapshot immediately (debug)", "INFO")
    # await take_snapshot()

    while not bot.is_closed():
        wait_seconds: float = seconds_until(9, 29)
        #wait_seconds: float = 5 # FOR TESTING
        hours, minutes, seconds = (
            int(wait_seconds // 3600),
            int((wait_seconds % 3600) // 60),
            int(wait_seconds % 60),
        )
        log(f"Waiting {hours}h {minutes}m {seconds}s until next run", "SNAPSHOT")
        await asyncio.sleep(wait_seconds)

        await take_snapshot()


async def take_snapshot() -> None:
    """Helper function to take a snapshot immediately."""
    log("Taking daily snapshot...", "INFO")
    history: dict = aura_manager.load_history()
    aura_manager.ensure_today(history)
    today: str = dt.date.today().strftime("%Y-%m-%d")
    timestamp: str = dt.datetime.now().strftime("%H-%M-%S")
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

    # Check if the aura key exists in history entries
    if "aura" not in history[dates[-2]]:
        return "Yesterday's aura data is missing!"
    if "aura" not in history[dates[-1]]:
        return "Today's aura data is missing!"

    yesterday: dict[str, int] = history[dates[-2]]["aura"]
    today: dict[str, int] = history[dates[-1]]["aura"]

    yesterday_sorted = sorted(yesterday.items(), key=lambda x: x[1], reverse=True)
    yesterday_ranks: dict[str, int] = {
        user_id: rank for rank, (user_id, _) in enumerate(yesterday_sorted, start=1)
    }

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
                pass  # user_name stays as "User(id)" if this fails

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
        # wait_seconds: float = 10 # TESTING
        hours, minutes, seconds = (
            int(wait_seconds // 3600),
            int((wait_seconds % 3600) // 60),
            int(wait_seconds % 60),
        )
        log(f"Waiting {hours}h {minutes}m {seconds}s until next post", "LEADERBOARD")
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

    # Create the view
    view = leaderboardEmbed(data, title="Daily Aura Standings", color=0x6DAB18)
    random_message = get_random_aura_message()
    embed = view.createEmbed()

    botText = f"||@here||**{random_message}**"
    await channel.send(content=botText, embed=embed, view=view)

    log("Daily Leaderboard Posted", "SUCCESS")


async def spawn_aura_button() -> None:
    await bot.wait_until_ready()

    if aura_manager.CHANNEL_ID is None:
        log("CHANNEL_ID not set. Skipping button spawns", "BUTTON_INFO")
        return

    channel = bot.get_channel(aura_manager.CHANNEL_ID)
    if channel is None:
        log(
            f"Channel {aura_manager.CHANNEL_ID} not found. Cannot spawn random button",
            "BUTTON_INFO",
        )
        return

    while not bot.is_closed():
        try:
            # Calculate next spawn time
            next_spawn = dt.datetime.now() + dt.timedelta(minutes=25)
            log(
                f"Next check scheduled at {next_spawn.strftime('%I:%M:%S %p')}",
                "BUTTON_INFO",
            )

            await asyncio.sleep(25 * 60)  # 25 Minutes
            if random.choice([True, False]):
                channel = bot.get_channel(aura_manager.CHANNEL_ID)
                if channel is None:
                    log(
                        f"Channel {aura_manager.CHANNEL_ID} not found. Skipping this spawn",
                        "BUTTON_INFO",
                    )
                    continue
                view = randomButton()
                message = await channel.send(
                    "Click this button for a chance to get some aura!", view=view
                )
                view.message = message

                log("Button spawned", "BUTTON_INFO")
            else:
                log("Button did not spawn this time.", "BUTTON_INFO")
        except Exception as e:
            log(f"Error during random aura spawn: {e}", "ERROR")

async def spawn_golden_button() -> None:
    await bot.wait_until_ready()

    try:
        while not bot.is_closed():
            now = dt.datetime.now()

            # Active Window 9 AM to 9 PM
            if 9 <= now.hour < 21:
                endOfDay = now.replace(hour=20, minute=59, second=59, microsecond=0)
                secondsLeft = (endOfDay - now).total_seconds()

                waitTime = random.uniform(0, max(0, secondsLeft))                
                #waitTime = 5
                scheduledFor = now + dt.timedelta(seconds=waitTime)
                bot.nextGoldenSpawn = scheduledFor

                log(
                    f"Golden Button scheduled for {scheduledFor.strftime('%I:%M %p')}",
                    "GOLD_BUTTON",
                )
                await asyncio.sleep(waitTime)

                # --- SPAWN LOGIC --
                
                channel = bot.get_channel(aura_manager.CHANNEL_ID)
                if channel:
                    view = goldenButtonEmbed()
                    
                    unclaimedStreak = aura_manager.getGoldenStreak()
                    baseAmount = 40
                    currentValue = baseAmount * unclaimedStreak

                    messageText = "**A Golden Button has appeared!**"
                    if unclaimedStreak > 1:
                        messageText += f" **Worth `{currentValue:,}` Aura**!"

                    message = await channel.send(messageText, view=view)
                    view.message = message
                    log("Golden Button has been spawned.", "SUCCESS")
                else:
                    log(f"Channel {aura_manager.CHANNEL_ID} not found for Golden Button.", "ERROR")

                # --- SLEEP UNTIL 9:00 AM TOMORROW ---
                currentTime = dt.datetime.now()
                tomorrowNineAM = (currentTime + dt.timedelta(days=1)).replace(
                    hour=9, minute=0, second=0, microsecond=0
                )
                sleepUntilReset = (tomorrowNineAM - currentTime).total_seconds()

                log(
                    "Button cycle finished. Resetting at 9 AM tomorrow.", "GOLD_BUTTON"
                )
                await asyncio.sleep(max(0, sleepUntilReset))

                # --- 9:00 AM ROLE REMOVAL & RESET LOGIC ---
                bot.nextGoldenSpawn = None
                bot.userClicked = None

                roleId = aura_manager.get_golden_role_id()
                if roleId and channel and channel.guild:
                    guild = channel.guild
                    role = guild.get_role(roleId)
                    if role:
                        for member in role.members:
                            try:
                                await member.remove_roles(role, reason="Golden Button role expired at 9:00 AM reset")
                                log(f"Removed Golden Role from {member.name}", "GOLD_BUTTON")
                            except discord.Forbidden:
                                log("Missing permissions to remove Golden Role.", "ERROR")
                            except discord.HTTPException as e:
                                log(f"Failed to remove Golden Role: {e}", "ERROR")

            # Outside spawn hours (12 AM - 8:59 AM)
            else:
                targetNineAM = now.replace(hour=9, minute=0, second=0, microsecond=0)
                if now.hour >= 21:
                    targetNineAM += dt.timedelta(days=1)

                waitUntilNine = (targetNineAM - now).total_seconds()
                log("Outside spawn hours. Waiting until 9 AM...", "GOLD_BUTTON")
                await asyncio.sleep(max(0, waitUntilNine))
    except Exception as e:
        log(f"Error in spawn_golden_button: {e}", "ERROR")
        await asyncio.sleep(60)

async def checkMonthlyReset() -> None:
    """Checks daily if today's day matches the configured reset day."""
    await bot.wait_until_ready()

    while not bot.is_closed():
        now = dt.datetime.now()

        # Reload config in case it was updated via command
        load_config()
        resetDay = aura_manager.RESET_DAY

        if now.day == resetDay:
            log(f"Monthly reset day {resetDay} reached. Resetting aura balances.", "INFO")
            aura_manager.resetAllAura()


            # Send Message 
            if aura_manager.CHANNEL_ID is not None:
                channel = bot.get_channel(aura_manager.CHANNEL_ID)
                if channel is not None:
                    try:
                        await channel.send("AURA HAS BEEN RESET FOR THE MONTH")
                    except Exception as e:
                        log(f"Failed to send monthly reset announcement: {e}", "ERROR")
            
            # Sleep until tomorrow after the reset to avoid resetting again the same day
            nextDay = (now + dt.timedelta(days=1)).replace(
                hour=0, minute=5, second=0, microsecond=0
            )
            await asyncio.sleep((nextDay - dt.datetime.now()).total_seconds())
        else:
            # Calculate the next reset date and how many days remain
            todayDate = now.date()
            if todayDate.day < resetDay:
                nextResetDate = todayDate.replace(day=resetDay)
            else:
                nextMonth = todayDate.month + 1 if todayDate.month < 12 else 1
                nextYear = todayDate.year if todayDate.month < 12 else todayDate.year + 1
                nextResetDate = todayDate.replace(year=nextYear, month=nextMonth, day=resetDay)

            daysRemaining = (nextResetDate - todayDate).days
            log(
                f"Monthly reset in {daysRemaining} day(s) on {nextResetDate.isoformat()}",
                "INFO",
            )

            if daysRemaining == 1:
                if aura_manager.CHANNEL_ID is not None:
                    channel = bot.get_channel(aura_manager.CHANNEL_ID)
                    if channel is not None:
                        try:
                            await channel.send(f"Reminder: Aura will be reset TOMORROW!")
                            log(f"Sent monthly reset reminder for  XXXX-XX-{resetDay}.", "INFO")
                        except Exception as e:
                            log(f"Failed to send monthly reset reminder: {e}","ERROR",)
                    else:
                        log(f"Monthly reset reminder channel {aura_manager.CHANNEL_ID} not found.","WARNING")
                else:
                    log("Monthly reset reminder skipped because CHANNEL_ID is not set.","WARNING")

            # Wait until 9:30 and check again
            tomorrow = now + dt.timedelta(days=1)
            nextCheck = tomorrow.replace(hour=9, minute=30, second=0, microsecond=0)
            await asyncio.sleep((nextCheck - dt.datetime.now()).total_seconds())
