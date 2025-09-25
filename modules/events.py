# modules/events.py
import discord
from modules.bot_setup import bot
from modules.aura_manager import (
    user_reactions,
    update_aura as manager_update_aura,
    adjust_sender_count,
    load_aura_count,
)
from modules.utils import log

# Load aura counts into memory
load_aura_count()


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
        user_reactions.setdefault(user.id, [])
        if emoji_name not in user_reactions[user.id]:
            user_reactions[user.id].append(emoji_name)

        if emoji_name == "aura":
            manager_update_aura(target.id, 1)
            adjust_sender_count(user.id, "POS", 1)
            log(f"{user.name} gave +1 aura to {target.name}", "INFO")
        elif emoji_name == "auradown":
            manager_update_aura(target.id, -1)
            adjust_sender_count(user.id, "NEG", 1)
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

        if user.id in user_reactions and emoji_name in user_reactions[user.id]:
            if emoji_name == "aura":
                manager_update_aura(target.id, -1)
                adjust_sender_count(user.id, "POS", -1)
                log(f"{user.name} removed +aura from {target.name}", "INFO")
            elif emoji_name == "auradown":
                manager_update_aura(target.id, 1)
                adjust_sender_count(user.id, "NEG", -1)
                log(f"{user.name} removed -aura from {target.name}", "INFO")

            user_reactions[user.id].remove(emoji_name)

    except Exception as e:
        log(f"Error in on_reaction_remove: {e}", "ERROR")
