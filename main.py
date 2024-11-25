# main.py

from typing import Final, Dict
import discord
from discord.ext import commands
from dotenv import load_dotenv
import json
import os
import datetime
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv()
TOKEN: Final[str] = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError(Fore.RED + "[ERROR] DISCORD_TOKEN is not set in the environment.")

# File to store aura data
AURA_FILE: Final[str] = "aura.json"

# Bot setup
intents: discord.Intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True
bot: commands.Bot = commands.Bot(command_prefix="?", intents=intents)

# aura data storage
aura_data: Dict[str, int] = {}
user_reactions: Dict[int, list[str]] = {}

OWNER_ID: Final[str] = "109482185949446144"


def log(message: str, level: str = "INFO") -> None:
    """
    Print a log message with a timestamp and a specific level.
    Args:
        message (str): The message to log.
        level (str): The log level (e.g., INFO, ERROR, SUCCESS).
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if level == "INFO":
        print(Fore.CYAN + f"[{timestamp}] [INFO] {message}")
    elif level == "ERROR":
        print(Fore.RED + f"[{timestamp}] [ERROR] {message}")
    elif level == "SUCCESS":
        print(Fore.GREEN + f"[{timestamp}] [SUCCESS] {message}")
    elif level == "WARNING":
        print(Fore.YELLOW + f"[{timestamp}] [WARNING] {message}")
    else:
        print(f"[{timestamp}] [{level}] {message}")


def load_aura() -> None:
    """
    Load aura from the JSON file if it exists, else initialize an empty dictionary.
    """
    global aura
    if os.path.exists(AURA_FILE):
        with open(AURA_FILE, "r") as file:
            aura_data.update(json.load(file))
        log("Aura successfully loaded", "SUCCESS")
    else:
        aura_data.clear()
        log("No save file found. Initializing aura to empty.", "WARNING")


def save_aura() -> None:
    """
    Save the current aura dictionary to the JSON file.
    """
    with open(AURA_FILE, "w") as file:
        json.dump(aura_data, file)
    log("Aura successfully saved to file", "SUCCESS")


def update_aura(user_id: int, change: int) -> None:
    """
    Update the aura for a user by a given change value and save to file.
    Args:
        user_id (int): The Discord user's ID.
        change (int): The amount to change the user's aura by.
    """
    user_id_str = str(user_id)
    aura_data[user_id_str] = aura_data.get(user_id_str, 0) + change
    save_aura()
    log(f"Updated aura for user {user_id}: {aura_data[user_id_str]}", "INFO")


@bot.event
async def on_ready() -> None:
    """
    Event triggered when the bot is ready.
    """
    load_aura()
    log(f"Bot {bot.user} is now running!", "SUCCESS")


@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User) -> None:
    target = reaction.message.author
    if user.bot or target.bot or user == target:
        return  # Ignore bot reactions and self-reactions

    emoji_name = reaction.emoji if isinstance(reaction.emoji, str) else reaction.emoji.name
    user_id = user.id

    # Track user reactions
    if user_id not in user_reactions:
        user_reactions[user_id] = []
    if emoji_name not in user_reactions[user_id]:
        user_reactions[user_id].append(emoji_name)

    if emoji_name == "aura":
        update_aura(target.id, 1)
    elif emoji_name == "auradown":
        update_aura(target.id, -1)

    current_aura = aura_data.get(str(target.id), 0)
    log(f"{target.name} ({target.id}) now has {current_aura} aura.", "INFO")


@bot.event
async def on_reaction_remove(reaction: discord.Reaction, user: discord.User) -> None:
    target = reaction.message.author
    if user.bot or target.bot or user == target:
        return  # Ignore bot reactions and self-reactions

    emoji_name = reaction.emoji if isinstance(reaction.emoji, str) else reaction.emoji.name
    user_id = user.id

    # Validate and update aura
    if user_id in user_reactions and emoji_name in user_reactions[user_id]:
        if emoji_name == "aura":
            update_aura(target.id, -1)
        elif emoji_name == "auradown":
            update_aura(target.id, 1)

        # Remove the reaction from tracking
        user_reactions[user_id].remove(emoji_name)

    current_aura = aura_data.get(str(target.id), 0)
    log(f"{target.name} ({target.id}) now has {current_aura} aura after reaction removed.", "INFO")

@bot.command()
async def set_aura(ctx: commands.Context, member: discord.Member, amount: int) -> None:
    """
    Command to set the aura of a user (only allowed by the special user).
    Args:
        ctx (commands.Context): The context of the command.
        member (discord.Member): The member whose aura is to be set.
        amount (int): The amount to set the user's aura to.
    """
    if str(ctx.author.id) != OWNER_ID:
        await ctx.send("You do not have permission to set the aura.")
        return

    update_aura(member.id, amount)
    await ctx.send(f"{member.name}'s aura has been set to {amount}!")
    log(f"Set {member.name}'s aura to {amount} ({member.id}).", "INFO")


@bot.command()
async def reset_aura(ctx: commands.Context, member: discord.Member) -> None:
    """
    Command to reset the aura of a user (only allowed by the special user).
    Args:
        ctx (commands.Context): The context of the command.
        member (discord.Member): The member whose aura is to be reset.
    """
    if str(ctx.author.id) != OWNER_ID:
        await ctx.send("You do not have permission to reset the aura.")
        return

    update_aura(member.id, 0)
    await ctx.send(f"{member.name}'s aura has been reset to 0!")
    log(f"Reset {member.name}'s aura ({member.id}).", "INFO")

@bot.command()
async def aura(ctx: commands.Context, member: discord.Member = None) -> None:
    """
    Command to check a user's aura.
    Args:
        ctx (commands.Context): The context of the command.
        member (discord.Member, optional): The member whose aura are checked. Defaults to the command author.
    """
    member = member or ctx.author
    user_aura = aura_data.get(str(member.id), 0)
    await ctx.send(f"{member.name}'s aura is: {user_aura}!")
    log(f"Aura requested for {member.name} ({member.id}).", "INFO")


@bot.command()
async def leaderboard(ctx: commands.Context) -> None:
    """
    Command to display the leaderboard of aura.
    Args:
        ctx (commands.Context): The context of the command.
    """
    if not aura_data:
        await ctx.send("No aura has been earned yet!")
        log("Leaderboard requested, but no aura exists.", "WARNING")
        return

    sorted_aura = sorted(aura_data.items(), key=lambda x: x[1], reverse=True)
    leaderboard_lines = []

    for rank, (target_id, score) in enumerate(sorted_aura, start=1):
        target_user = await bot.fetch_user(target_id)
        if rank == 1:
            leaderboard_lines.append(f"{rank}. \\>\\>\\> (**Sigma**) *`{target_user}`*: {score} aura")
        elif rank == 2:
            leaderboard_lines.append(f"{rank}. \\>\\> (**Alpha**) *`{target_user}`*: {score} aura")
        elif rank == 3:
            leaderboard_lines.append(f"{rank}. \\> (**Skibidi**) *`{target_user}`*: {score} aura")
        else:
            leaderboard_lines.append(f"{rank}. **{target_user}**: {score} aura")

    leaderboard_text = "\n".join(leaderboard_lines)
    await ctx.send(f"# Leaderboard:\n{leaderboard_text}")
    log("Leaderboard displayed with rankings and special text for first place.", "INFO")


# Run the bot
def main() -> None:
    try:
        bot.run(TOKEN)
    except Exception as e:
        log(f"Failed to start bot: {e}", "ERROR")


if __name__ == "__main__":
    main()
