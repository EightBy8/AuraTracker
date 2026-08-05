import os
import discord
import modules.aura_manager as aura_manager
from modules.bot_setup import bot
from modules.aura_manager import (
    load_aura,
    load_history,
    ensure_today,
    save_json,
    load_aura_count,
    HISTORY_FILE,
)
from modules.utils import log
from modules.daily_tasks import (
    load_config,
    daily_aura_snapshot,
    post_daily_leaderboard,
    spawn_aura_button,
    spawn_golden_button,
    checkMonthlyReset,
)

# Load data into memory before registering commands/events
load_config()
load_aura()
load_aura_count()
history = load_history()
ensure_today(history)
save_json(HISTORY_FILE, history)

# Import commands and events so they register with the bot
import modules.commands  # noqa: E402,F401
import modules.events  # noqa: E402,F401
import modules.games
import modules.fishing  # noqa: E402,F401


async def clear_golden_roles() -> None:
    """Removes the Golden Role from any members who currently have it on bot startup."""
    role_id = aura_manager.get_golden_role_id()

    if not role_id:
        log("No Golden Role ID configured; skipping startup cleanup.", "GOLD_BUTTON")
        return

    # Wait until the bot internal cache is completely ready
    await bot.wait_until_ready()

    guild = None
    if aura_manager.CHANNEL_ID:
        channel = bot.get_channel(aura_manager.CHANNEL_ID)
        if channel and channel.guild:
            guild = channel.guild

    if not guild and bot.guilds:
        guild = bot.guilds[0]

    if not guild:
        log("Could not locate guild for Golden Role cleanup.", "ERROR")
        return

    role = guild.get_role(role_id)
    if not role:
        log(f"Golden Role with ID {role_id} not found in guild.", "ERROR")
        return

    # Fallback to fetching all members if role.members cache is empty (Intents check)
    members_with_role = role.members
    if not members_with_role:
        try:
            async for member in guild.fetch_members(limit=None):
                if role in member.roles:
                    members_with_role.append(member)
        except Exception as e:
            log(f"Failed to fetch guild members for role check: {e}", "ERROR")

    if not members_with_role:
        log("No members found holding the Golden Role on startup.", "GOLD_BUTTON")
        return

    for member in members_with_role:
        try:
            await member.remove_roles(
                role, reason="Startup cleanup: Resetting Golden Role"
            )
            log(
                f"Removed Golden Role from {member.display_name} on startup.",
                "GOLD_BUTTON",
            )
        except discord.Forbidden:
            log(
                "Missing permissions to remove Golden Role (check role hierarchy!).",
                "ERROR",
            )
        except discord.HTTPException as e:
            log(f"Failed to remove Golden Role on startup: {e}", "ERROR")


@bot.event
async def on_ready():
    # Run role cleanup now that cache/gateway is ready
    await clear_golden_roles()

    versionNumber = "v2.6.0"
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game(name=versionNumber)
    )
    log(f"Logged in as {bot.user} | {versionNumber}", "SUCCESS")

async def setup_hook():
    """Called automatically by discord.py when bot is ready to start background tasks."""
    bot.loop.create_task(daily_aura_snapshot())
    bot.loop.create_task(post_daily_leaderboard())
    bot.loop.create_task(spawn_aura_button())
    bot.loop.create_task(spawn_golden_button())
    bot.loop.create_task(checkMonthlyReset())
    log("Background tasks scheduled", "SUCCESS")


# Assign proper coroutine function
bot.setup_hook = setup_hook

# Run bot
log("Bot is starting...", "SUCCESS")
bot.run(os.getenv("DISCORD_TOKEN"))
