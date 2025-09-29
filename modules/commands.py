# modules/commands.py

from discord.ext import commands
import discord
import json
import os
from modules.bot_setup import bot
from modules.daily_tasks import save_config, load_config
from modules.daily_tasks import CHANNEL_ID
from modules.aura_manager import (
    aura_data,
    set_aura as manager_set_aura,
    update_aura as manager_update_aura,
    user_aura_count,
    OWNER_ID,
    get_negative_leaderboard,
)
from modules.utils import log, seconds_until
from discord import Embed

# Path to auraCount.json
AURA_COUNT_FILE = os.path.join("data", "auraCount.json")

def load_aura_count() -> dict:
    """Load aura count (POS/NEG stats) from JSON file."""
    if os.path.exists(AURA_COUNT_FILE):
        with open(AURA_COUNT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


@bot.command()
async def set_channel(ctx: commands.Context) -> None:
    """Set the current channel as the daily leaderboard channel."""
    from modules import daily_tasks
    daily_tasks.CHANNEL_ID = ctx.channel.id
    save_config()
    await ctx.send(f"Daily leaderboard channel set to {ctx.channel.mention}")
    log(f"Daily leaderboard channel set to {ctx.channel.id} by {ctx.author}", "INFO")

@bot.command()
async def aura(ctx: commands.Context, member: discord.Member | None = None) -> None:
    member = member or ctx.author
    user_aura = aura_data.get(str(member.id), 0)
    await ctx.send(f"{member.mention}'s aura: {user_aura}")
    log(f"Aura requested for {member} ({member.id})", "INFO")


@bot.command(name="lb")
async def lb(ctx: commands.Context) -> None:
    if not aura_data:
        await ctx.send("No aura yet!")
        return

    sorted_aura = sorted(aura_data.items(), key=lambda x: x[1], reverse=True)
    embed = Embed(title="Aura Leaderboard", description="--------------------------------------")
    for rank, (uid, score) in enumerate(sorted_aura, start=1):
        user = await bot.fetch_user(int(uid))
        prefix = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, str(rank))
        embed.add_field(name=f"{prefix} > {user.name.capitalize()}", value=f"Aura: {score}", inline=False)
    await ctx.send(embed=embed)
    log("Leaderboard shown", "INFO")


@bot.command(name="leaderboard")
async def leaderboard_alias(ctx: commands.Context) -> None:
    await ctx.send("Command moved to -> '?lb'")


@bot.command()
async def set_aura(ctx: commands.Context, member: discord.Member, amount: int) -> None:
    if str(ctx.author.id) not in OWNER_ID:
        return await ctx.send("You do not have permission to set the aura.")
    manager_set_aura(member.id, amount)
    await ctx.send(f"{member.mention}'s aura set to {amount}!")
    log(f"{ctx.author} set aura for {member} to {amount}", "INFO")


@bot.command()
async def reset_aura(ctx: commands.Context, member: discord.Member) -> None:
    if str(ctx.author.id) not in OWNER_ID:
        return await ctx.send("You do not have permission to reset the aura.")
    manager_set_aura(member.id, 0)
    await ctx.send(f"{member.mention}'s aura has been reset to 0!")
    log(f"{ctx.author} reset aura for {member}", "INFO")


@bot.command()
async def modify_aura(ctx: commands.Context, member: discord.Member, amount: int) -> None:
    if str(ctx.author.id) not in OWNER_ID:
        return await ctx.send("You do not have permission to modify aura.")
    manager_update_aura(member.id, amount)
    new_val = aura_data.get(str(member.id), 0)
    if amount > 0:
        await ctx.send(f"{member.mention} received +{amount} Aura. Now: {new_val} Aura.")
    else:
        await ctx.send(f"{member.mention} lost {abs(amount)} Aura. Now: {new_val} Aura.")
    log(f"{ctx.author} modified aura for {member} by {amount}", "INFO")

@bot.command()
async def dslb(ctx: commands.Context) -> None:
    """Show leaderboard of who has given the most negative aura."""
    from modules.aura_manager import user_aura_count  # always use in-memory state

    # Filter only people with NEG > 0
    neg_scores = {uid: data["NEG"] for uid, data in user_aura_count.items() if data["NEG"] > 0}

    if not neg_scores:
        await ctx.send("Nobody has given negative aura yet...")
        return

    sorted_neg = sorted(neg_scores.items(), key=lambda x: x[1], reverse=True)

    embed = Embed(
        title="Leaderboard of Dicksuck",
        description="Leaderboard for people who need to lay off the -aura button",
    )
    for rank, (uid, neg_count) in enumerate(sorted_neg, start=1):
        try:
            user = await bot.fetch_user(int(uid))
            user_name = str(user.name).capitalize()
        except Exception:
            user_name = uid
        emoji = {1: "🍆", 2: "🚴", 3: "🤸"}.get(rank, str(rank))
        embed.add_field(
            name=f"{emoji} > {user_name}",
            value=f"Negative Aura Given: {neg_count}",
            inline=False,
        )

    await ctx.send(embed=embed)


@bot.command(name="slb")
async def slb(ctx: commands.Context) -> None:
    """Show leaderboard of who has given the most positive aura (Simp Leaderboard)."""
    from modules.aura_manager import user_aura_count  # always use in-memory state

    # Filter only people with POS > 0
    pos_scores = {uid: data["POS"] for uid, data in user_aura_count.items() if data["POS"] > 0}

    if not pos_scores:
        await ctx.send("Nobody has given positive aura yet...")
        return

    sorted_pos = sorted(pos_scores.items(), key=lambda x: x[1], reverse=True)

    embed = Embed(
        title="Simp Leaderboard",
        description="Leaderboard for people who hand out +aura like candy",
        color=discord.Color(0x32CD32),  # green for positive vibes
    )

    for rank, (uid, pos_count) in enumerate(sorted_pos, start=1):
        try:
            user = await bot.fetch_user(int(uid))
            user_name = str(user.name).capitalize()
        except Exception:
            user_name = uid

        emoji = {1: "👑", 2: "💎", 3: "🌸"}.get(rank, str(rank))
        embed.add_field(
            name=f"{emoji} > {user_name}",
            value=f"Positive Aura Given: {pos_count}",
            inline=False,
        )

    await ctx.send(embed=embed)


@bot.command()
async def daily_leaderboard(ctx: commands.Context) -> None:
    wait = seconds_until(9, 30)
    hours, minutes, seconds = int(wait // 3600), int((wait % 3600) // 60), int(wait % 60)
    await ctx.send(f"Time Until Daily Leaderboard: {hours}h {minutes}m {seconds}s")


@bot.command()
async def help(ctx: commands.Context) -> None:
    await ctx.send(
        """
**Aura Bot Commands**

User:
?aura [Member] - check aura
?lb - show leaderboard

Admin:
?set_aura [member] [amount] - set aura
?reset_aura [member] - reset aura
?modify_aura [member] [amount] - modify aura
?dsleaderboard - who gives the most negative aura
"""
    )
