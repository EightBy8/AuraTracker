# modules/events.py
import discord
from discord.ext import commands
from modules.bot_setup import bot
from modules.daily_tasks import save_config
from modules.utils import log
from modules import aura_manager

# Load aura counts into memory
aura_manager.load_aura_count()

@bot.event
async def on_ready():
    updated = False
    for guild in bot.guilds:
        owner_id = guild.owner_id
        if owner_id not in aura_manager.OWNER_IDS:
            aura_manager.OWNER_IDS.append(owner_id)
            log(f"Added server owner {owner_id} to 'OWNER_IDS'", "SUCCESS")
            updated = True

    if updated:
        save_config()
        log(f"Saved CHANNEL_ID = {aura_manager.CHANNEL_ID} and OWNER_IDs = {aura_manager.OWNER_IDS}", "SUCCESS")

@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User | discord.Member) -> None:
    """
    Track reaction adds and update aura/sender counters.
    Ignores bot reactions and self-reacts.
    """
    try:
        if user.bot: return

        message: discord.Message | None = reaction.message
        target: discord.User | discord.Member = message.author
        if message is None: return
        if target is None or getattr(target, "bot", False): return
        if user.id == target.id: return

        emoji_name: str = reaction.emoji if isinstance(reaction.emoji, str) else reaction.emoji.name
        aura_manager.user_reactions.setdefault(user.id, [])
        if emoji_name not in aura_manager.user_reactions[user.id]:
            aura_manager.user_reactions[user.id].append(emoji_name)

        if emoji_name == "aura":
            aura_manager.update_aura(target.id, 1)
            aura_manager.adjust_sender_count(user.id, "POS", 1)
            log(f"{user.name} gave +1 aura to {target.name}", "INFO")
        elif emoji_name == "auradown":
            aura_manager.update_aura(target.id, -1)
            aura_manager.adjust_sender_count(user.id, "NEG", 1)
            log(f"{user.name} gave -1 aura to {target.name}", "INFO")

    except Exception as e:
        log(f"Error in on_reaction_add: {e}", "ERROR")


@bot.event
async def on_reaction_remove(reaction: discord.Reaction, user: discord.User | discord.Member) -> None:
    """
    Track reaction removals; reverse the aura & sender counters if appropriate.
    """
    try:
        if user.bot: return

        message: discord.Message | None = reaction.message
        target: discord.User | discord.Member = message.author
        if message is None: return
        if target is None or getattr(target, "bot", False): return
        if user.id == target.id: return

        emoji_name: str = reaction.emoji if isinstance(reaction.emoji, str) else reaction.emoji.name

        if user.id in aura_manager.user_reactions and emoji_name in aura_manager.user_reactions[user.id]:
            if emoji_name == "aura":
                aura_manager.update_aura(target.id, -1)
                aura_manager.adjust_sender_count(user.id, "POS", -1)
                log(f"{user.name} removed +aura from {target.name}", "INFO")
            elif emoji_name == "auradown":
                aura_manager.update_aura(target.id, 1)
                aura_manager.adjust_sender_count(user.id, "NEG", -1)
                log(f"{user.name} removed -aura from {target.name}", "INFO")

            aura_manager.user_reactions[user.id].remove(emoji_name)

    except Exception as e:
        log(f"Error in on_reaction_remove: {e}", "ERROR")


@bot.event
async def on_command_error(ctx, error):
    # Command not found
    if isinstance(error, commands.CommandNotFound):
        log(f"{ctx.author} entered a invalid command","WARNING")
        return await ctx.send("That command does not exist. Try `?help`")

    elif isinstance(error, commands.MissingRequiredArgument):
        log(f"{ctx.author} forgot arugments in their command", "WARNING")
        return await ctx.send("You forgot to include the amount!")

    else:
        log(f"UNHANDELED ERROR {error}", "ERROR")

