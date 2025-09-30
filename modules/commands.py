# modules/commands.py

from discord.ext import commands
import discord
import json
import os
from modules.bot_setup import bot
from modules.daily_tasks import save_config, load_config
from modules import aura_manager
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
    if ctx.author.id not in aura_manager.OWNER_IDS:
        return await ctx.send("You do not have permission to set channels.")

    aura_manager.CHANNEL_ID = ctx.channel.id  # <-- update this
    save_config()  # this now saves the correct CHANNEL_ID
    await ctx.send(f"Daily leaderboard channel set to {ctx.channel.mention}")
    log(f"Daily leaderboard channel set to {ctx.channel.id} by {ctx.author}", "INFO")

@bot.command()
async def add_officer(ctx: commands.Context, member: discord.Member) -> None:
    """Adds a user to 'owner_ids' in config.json"""
    if ctx.author.id != ctx.guild.owner_id:
        return await ctx.send("Only the server owner can use this command.") 
    
    if member.id not in aura_manager.OWNER_IDS:
        aura_manager.add_owner(member.id)
        save_config()
        await ctx.send(f"{member.mention} has been added as an officer.")
    else:
        await ctx.send(f"{member.mention} is already an offcier.")


@bot.command()
async def remove_officer(ctx: commands.Context, member: discord.Member) -> None:
    if ctx.author.id not in aura_manager.OWNER_IDS:
        return await ctx.send("You do not have permission to remove officers...")
    
    if member.id not in aura_manager.OWNER_IDS:
        await ctx.send(f"{member.mention} is not an officer.")
    else:
        aura_manager.remove_owner(member.id)
        save_config()
        await ctx.send(f"{member.mention} has been removed as an officer.")



@bot.command()
async def aura(ctx: commands.Context, member: discord.Member | None = None) -> None:
    member = member or ctx.author
    user_aura = aura_manager.aura_data.get(str(member.id), 0)
    await ctx.send(f"{member.mention}'s aura: {user_aura}")
    log(f"Aura requested for {member} ({member.id})", "INFO")


@bot.command(name="lb")
async def lb(ctx: commands.Context) -> None:
    if not aura_manager.aura_data:
        await ctx.send("No aura yet!")
        return

    sorted_aura = sorted(aura_manager.aura_data.items(), key=lambda x: x[1], reverse=True)
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
async def give_aura(ctx: commands.Context, member: discord.Member, amount: int) -> None:
    giver_id = str(ctx.author.id)
    receiver_id = str(member.id)

    if amount <= 0:
        return await ctx.send("You can only give a positive amount of aura.")

    # Ensure both users exist in aura_data
    aura_manager.aura_data.setdefault(giver_id, 0)
    aura_manager.aura_data.setdefault(receiver_id, 0)

    giver_aura = aura_manager.aura_data[giver_id]

    if giver_aura < amount:
        return await ctx.send(f"You don't have enough aura to give {amount} points.")

    # Transfer aura
    aura_manager.aura_data[giver_id] -= amount
    aura_manager.aura_data[receiver_id] += amount

    # Save to file
    aura_manager.save_json(aura_manager.AURA_FILE, aura_manager.aura_data)

    await ctx.send(f"{ctx.author.mention} gave {amount} aura to {member.mention}! ")

@bot.command()
async def set_aura(ctx: commands.Context, member: discord.Member, amount: int) -> None:
    if ctx.author.id not in aura_manager.OWNER_IDS:
        return await ctx.send("You do not have permission to set the aura.")
    aura_manager.set_aura(member.id, amount)
    await ctx.send(f"{member.mention}'s aura set to {amount}!")
    log(f"{ctx.author} set aura for {member} to {amount}", "INFO")


@bot.command()
async def reset_aura(ctx: commands.Context, member: discord.Member) -> None:
    if ctx.author.id not in aura_manager.OWNER_IDS:
        return await ctx.send("You do not have permission to reset the aura.")
    aura_manager.set_aura(member.id, 0)
    await ctx.send(f"{member.mention}'s aura has been reset to 0!")
    log(f"{ctx.author} reset aura for {member}", "INFO")


@bot.command()
async def modify_aura(ctx: commands.Context, member: discord.Member, amount: int) -> None:
    if ctx.author.id not in aura_manager.OWNER_IDS:
        return await ctx.send("You do not have permission to modify aura.")
    aura_manager.update_aura(member.id, amount)
    new_val = aura_manager.aura_data.get(str(member.id), 0)
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
async def dailylb(ctx: commands.Context) -> None:
    wait = seconds_until(9, 30)
    hours, minutes, seconds = int(wait // 3600), int((wait % 3600) // 60), int(wait % 60)
    await ctx.send(f"Time Until Daily Leaderboard: {hours}h {minutes}m {seconds}s")


@bot.command()
async def help(ctx: commands.Context) -> None:
    await ctx.send(
"""

## Aura Bot Commands

### __*User:*__
- ?aura [Member] - check aura
- ?give_aura [Memeber] [Amount] - Send aura to another user
- ?lb - shows leaderboard
- ?slb - shows who gives the most positive aura
- ?dslb - shows who gives the most negative aura
- ?dailylb - shows countdown for next daily leaderboard post


### __*Aura Officer Commands :*__
- `?set_aura [member] [amount] - set aura`
- `?reset_aura [member] - reset aura`
- `?modify_aura [member] [amount] - modify aura`
- `?set_channel - sets the channel for daily leaderboards to be sent`
- `?add_officer - adds user to aura officer list`

"""
    )
