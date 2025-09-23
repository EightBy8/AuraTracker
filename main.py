# main.py

from typing import Final, Dict
import discord
from discord.ext import commands
from dotenv import load_dotenv
import json
import os
import datetime
import asyncio
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True, strip=False)

# Load environment variables
load_dotenv()
TOKEN: Final[str] = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError(Fore.RED + "[ERROR] DISCORD_TOKEN is not set in the environment.")

# File to store aura data / aura daily history
AURA_FILE: Final[str] = "aura.json" 
HISTORY_FILE: Final[str] = "auraHistory.json"
AURACOUNTER_FILE: Final[str] = "auraCount.json"

# Bot setup
intents: discord.Intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True
bot: commands.Bot = commands.Bot(command_prefix="?", intents=intents, help_command=None)

# aura data storage
aura_data: Dict[str, int] = {}
user_reactions: Dict[int, list[str]] = {}
userAruaCount: Dict[str, Dict[str, str]] = {}

OWNER_ID: Final[list[str]] = "187365945327616000","109482185949446144"


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
    Load aura from the JSON file if it exists, else initialize an empty dictionary. FOR AURA LEADERBOARD
    """
    global aura
    if os.path.exists(AURA_FILE):
        with open(AURA_FILE, "r") as file:
            aura_data.update(json.load(file))
            log("'aura' successfully loaded", "SUCCESS")
    else:
        aura_data.clear()
        save_aura()
        log("No save file found. Initializing aura to empty.", "WARNING")

def load_history() -> dict:
    """
    Load aura from the JSON file if it exists, else initialize an empty dictionary. FOR AURA DAILY BOARD
    """
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as file:
            content = file.read().strip()
            if not content:
                data = {}
            else:
                data = json.loads(content)
        log("'auraHistory' Loaded", "SUCCESS")
        return data
    return{}

def loadAuraCount() -> None:
    global userAruaCount
    if os.path.exists(AURACOUNTER_FILE):
        with open(AURACOUNTER_FILE, "r") as file:
            userAruaCount = json.load(file)
            log("'auraCount' Data Loaded", "SUCCESS")
    else:
        userAruaCount = {}
        saveAuraCount()
        log("No 'auraCount' file found, creating one...", "WARNING")

def save_aura() -> None:
    """
    Save the current aura dictionary to the JSON file.
    """
    with open(AURA_FILE, "w") as file:
        json.dump(aura_data, file, indent=4)
    log("Aura successfully saved to file", "SUCCESS")

def save_history(history: dict) -> None:
    with open(HISTORY_FILE, "w") as file:
        json.dump(history, file, indent=4)

def saveAuraCount() -> None:
    with open(AURACOUNTER_FILE, "w") as file:
        json.dump(userAruaCount, file, indent=4)
    log("Saved Negative Aura Count To File", "SUCCESS")

def ensure_today_history(history: dict) -> None:
    today = datetime.date.today().strftime("%Y-%m-%d")
    if today not in history:
        log("Adding todays date into history", "WARNING")
        history[today] ={}

def setAuraValue(user_id: int, amount: int) -> None:
    aura_data[str(user_id)] = amount
    save_aura()
    log(f"Set Aura for {user_id}: {amount}", "INFO")

def update_aura(user: discord.user, change: int) -> None:
    """
    Update the aura for a user by a given change value and save to file.
    Args:
        user_id (int): The Discord user's ID.
        change (int): The amount to change the user's aura by.
    """
    user_id_str = str(user.id)
    aura_data[user_id_str] = aura_data.get(user_id_str, 0) + change
    save_aura()

    log(f"Updated aura for {user.name.capitalize()} ({user.id}) ({aura_data[user_id_str]})", "INFO")


async def dailyAuraSnapshot():
    await bot.wait_until_ready()
    targetTime = datetime.time(hour=9, minute=29, second=0)

    while not bot.is_closed():

        now = datetime.datetime.now()
        nextRun = datetime.datetime.combine(now.date(), targetTime)

        if now >= nextRun: #If the time has already passed the target time
            nextRun += datetime.timedelta(days=1) #Push the embed post a day

        waitSeconds = (nextRun - now).total_seconds() # How many seconds until next day

        hours = int(waitSeconds // 3600)
        minutes = int((waitSeconds % 3600) // 60)
        seconds = int(waitSeconds % 60)
        log(f"Waiting {hours}h {minutes}m {seconds}s until next Snapshot..","WARNING")

        await asyncio.sleep(waitSeconds)

        now = datetime.datetime.now()
        log("Taking daily snapshot...", "INFO")
        history = load_history()
        ensure_today_history(history)

        today = datetime.date.today().strftime("%Y-%m-%d")
        timestamp = now.strftime("%H-%M-%S")

        history[today] = {
            "time": timestamp,
            "aura": aura_data.copy()
        }

        save_history(history)
        log("Saving Daily Snapshot", "SUCCESS")

async def dailyLeaderboard(history: dict) -> discord.Embed: 
    dates = sorted(history.keys())
    if len(dates) < 2:
        return "Not enough data to build daily leaderboard yet!"
    
    yesterday = history[dates[-2]]["aura"]
    today = history[dates[-1]]["aura"]
    
    yesterday_sorted = sorted(yesterday.items(), key=lambda x: x[1], reverse=True)
    today_sorted = sorted(today.items(), key=lambda x: x[1], reverse=True)

    yesterday_ranks = {user_id: rank for rank, (user_id, _) in enumerate(yesterday_sorted, start=1)}
    #today_ranks = {user_id: rank for rank, (user_id, _) in enumerate(today_sorted, start=1)}

    dailyEmbed = discord.Embed(
        title = "Daily Aura Ranking",
        description = "--------------------------------------",
        color = discord.Color(0x32CD32))
    
    dailyEmbed.set_footer(text = (f'Updated: {dates[-1]}'))

    for rank, (user_id, score) in enumerate(today_sorted, start=1):          # Loop through today's sorted leaderboard
        user = await bot.fetch_user(int(user_id))# Fetch the Discord user object by ID
        user_name = str(user.name).capitalize()
        old_rank = yesterday_ranks.get(user_id, None)
        old_score = yesterday.get(user_id, 0)
        diff = score - old_score #Calculate difference between aura 

        if diff > 0: #Gained Aura
            diff_text =(f"(+{diff})")
        elif diff < 0: #Lost Aura
            diff_text=(f"({diff})")
        else:
            diff_text=""

        if old_rank is None:
            auraRank = ("NEW✚")
            name = (f'{rank} > {user_name} {auraRank}')
        elif old_rank > rank: 
            auraRank = ("AURA▲")
            name = (f'{rank} > {user_name} {auraRank}')
        elif old_rank < rank:
            auraRank = ("AURA▼")
            name = (f'{rank} > {user_name} {auraRank}')
        else:
            auraRank = ("AURA━")
            name = (f'{rank} > {user_name} {auraRank}')

        if rank == 1:
            name = f"🥇 > {user_name} {auraRank} "
        elif rank == 2:
            name = f" 🥈 > {user_name} {auraRank} "
        elif rank == 3:
            name = f"🥉 > {user_name} {auraRank} "

        dailyEmbed.add_field(name=name, value=f"Aura: {score} {diff_text}", inline=False)

    log(f"Showing Daily Leaderboard Embed", "INFO")
    return dailyEmbed
        
async def postDailyLeaderboard():
    await bot.wait_until_ready()
    channel = bot.get_channel(622609287914717231)
    init(strip=False)
    init(strip=False)
    targetTime = datetime.time(hour=9, minute=30, second=0) #Time when daily embed gets posted CAN BE CHANGED

    while not bot.is_closed():
        now = datetime.datetime.now()
        nextRun = datetime.datetime.combine(now.date(), targetTime)

        if now >= nextRun: #If the time has already passed the target time
            nextRun += datetime.timedelta(days=1) #Push the embed post a day

        waitSeconds = (nextRun - now).total_seconds() # How many seconds until next day
        
        hours = int(waitSeconds // 3600)
        minutes = int((waitSeconds % 3600) // 60)
        seconds = int(waitSeconds % 60)
        log(f"Waiting {hours}h {minutes}m {seconds}s until next leaderboard post...","WARNING")

        await asyncio.sleep(waitSeconds) 

        history = load_history()
        dailyEmbed = await dailyLeaderboard(history)

        if isinstance(dailyEmbed, discord.Embed):
            await channel.send(f"@everyone Here are today's aura standings. LOCK TF IN! ")
            await channel.send(embed=dailyEmbed)
        else:
            await channel.send(dailyEmbed)  # fallback for string return


@bot.event
async def on_ready() -> None:
    """
    Event triggered when the bot is ready.
    """
    load_aura()
    loadAuraCount()
    history = load_history()
    ensure_today_history(history)
    save_history(history)
    bot.loop.create_task(dailyAuraSnapshot())
    bot.loop.create_task(postDailyLeaderboard())
    log(f"Bot {bot.user} is now running!", "SUCCESS")

@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User) -> None:
    """
    Check for reaction and add aura
    """
    sender = user
    target = reaction.message.author

    emoji_name = reaction.emoji if isinstance(reaction.emoji, str) else reaction.emoji.name
    user_id = user.id

    # Track user reactions
    if user_id not in user_reactions:
        user_reactions[user_id] = []
    if emoji_name not in user_reactions[user_id]:
        user_reactions[user_id].append(emoji_name)

    if emoji_name == "aura":
        update_aura(target, 1)
        senderID = str(sender.id)
        if senderID not in userAruaCount:
            userAruaCount[senderID] = {"POS": 0, "NEG": 0}

        senderID = str(sender.id)
        currentPos = userAruaCount[senderID]["POS"] #Amount of postive aura a user has sent
        userAruaCount[senderID]["POS"] = max(0, currentPos +1)
        saveAuraCount()
        log(f"Added +1 to {sender.name.capitalize()}'s Positive Aura Count ")

    elif emoji_name == "auradown":
        update_aura(target, -1)
        senderID = str(sender.id)
        if senderID not in userAruaCount: #If User has not sent any aura; Init and set both counts to 0
            userAruaCount[senderID] = {"POS": 0, "NEG": 0}

        senderID = str(sender.id)
        currentNeg = userAruaCount[senderID]["NEG"] #Amount of negaitve aura a user has sent
        userAruaCount[senderID]["NEG"] = max(0, currentNeg +1) #userAruaCount won't go below 0
        saveAuraCount()
        log(f"Added +1 to {sender.name.capitalize()}'s Negative Aura Count ")

    current_aura = aura_data.get(str(target.id), 0)
    log(f"{target.name} ({target.id}) now has {current_aura} aura.", "INFO")

@bot.event
async def on_reaction_remove(reaction: discord.Reaction, user: discord.User) -> None:
    sender = user
    target = reaction.message.author


    emoji_name = reaction.emoji if isinstance(reaction.emoji, str) else reaction.emoji.name
    user_id = user.id

    # Validate and update aura
    if user_id in user_reactions and emoji_name in user_reactions[user_id]:
        if emoji_name == "aura":
            update_aura(target, -1)
            senderID = str(sender.id)
            if senderID not in userAruaCount:
                userAruaCount[senderID] = {"POS": 0, "NEG": 0}

            senderID = str(sender.id)
            currentPos = userAruaCount[senderID]["POS"]
            userAruaCount[senderID]["POS"] = max(0, currentPos -1)
            saveAuraCount()
            log(f"Removed -1 from {sender.name.capitalize()}'s Given Positive Aura Count ({currentPos})")
            
        elif emoji_name == "auradown":
            update_aura(target, 1)
            senderID = str(sender.id)
            if senderID not in userAruaCount:
                userAruaCount[senderID] = {"POS": 0, "NEG": 0}

            senderID = str(sender.id)
            currentNeg = userAruaCount[senderID]["NEG"]
            userAruaCount[senderID]["NEG"] = max(0, currentNeg - 1)
            saveAuraCount()
            log(f"-1 To {sender.name.capitalize()}'s Given Negative Aura Count ({currentNeg}) ")

        # Remove the reaction from tracking
        user_reactions[user_id].remove(emoji_name)
            
    current_aura = aura_data.get(str(target.id), 0)
    #log(f"{target.name} ({target.id}) now has {current_aura} aura after reaction removed.", "INFO")

@bot.command()
async def daily_leaderboard(ctx):
    targetTime = datetime.time(hour=9, minute=30, second=0) #Time when daily embed gets posted CAN BE CHANGED
    now = datetime.datetime.now()
    nextRun = datetime.datetime.combine(now.date(), targetTime)

    if now >= nextRun: #If the time has already passed the target time
        nextRun += datetime.timedelta(days=1) #Push the embed post a day

    waitSeconds = (nextRun - now).total_seconds() # How many seconds until next day
    
    hours = int(waitSeconds // 3600)
    minutes = int((waitSeconds % 3600) // 60)
    seconds = int(waitSeconds % 60)

    await ctx.send(f'Time Until Daily Leaderboard: {hours}h {minutes}m {seconds}s')

@bot.command()
async def set_aura(ctx: commands.Context, member: discord.Member, amount: int) -> None:
    """
    Command to set the aura of a user (only allowed by the special user).
    Args:
        ctx (commands.Context): The context of the command.
        member (discord.Member): The member whose aura is to be set.
        amount (int): The amount to set the user's aura to.
    """
    if str(ctx.author.id) not in OWNER_ID:
        await ctx.send("You do not have permission to set the aura.")
        return
    setAuraValue(member.id, amount)
    await ctx.send(f"<@{member.id}>'s aura has been set to {amount}!")
    #log(f"Set {member.name}'s aura to {amount} ({member.id}).", "INFO")

@bot.command()
async def reset_aura(ctx: commands.Context, member: discord.Member) -> None:
    """
    Command to reset the aura of a user (only allowed by the special user).
    Args:
        ctx (commands.Context): The context of the command.
        member (discord.Member): The member whose aura is to be reset.
    """
    if str(ctx.author.id) not in OWNER_ID:
        await ctx.send("You do not have permission to reset the aura.")
        return

    setAuraValue(member.id, 0)
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
    await ctx.send(f"<@{member.id}>'s aura is: {user_aura}!")
    log(f"Aura requested for {member.name} ({member.id}).", "INFO")

@bot.command()
async def leaderboard(ctx: commands.Context) -> None:
    if not aura_data:
        await ctx.send("No aura has been earned yet!")
        log("Leaderboard requested, but no aura exists.", "WARNING")
        return

    sorted_aura = sorted(aura_data.items(), key=lambda x: x[1], reverse=True)    
    
    embed = discord.Embed(
        title="Aura Leaderboard",
        description = "--------------------------------------",
        color=discord.Color(0xff82dc)
    )

    for rank, (targer_id, score) in enumerate(sorted_aura, start=1):
        target_user = await bot.fetch_user(targer_id)
        user_name = str(target_user.name).capitalize()

        if rank == 1:
            name = (f'🥇 > {user_name}')
        elif rank == 2:
            name = (f'🥈 > {user_name}')
        elif rank == 3:
            name = (f'🥉 > {user_name}')
        else:
            name = (f'{rank} > {user_name}')
        
        embed.add_field(name=name, value=f"Aura: {score}", inline=False)

    await ctx.send(embed=embed)
    log("Leaderboard Embed Shown", "INFO")


    """
    Command to display the leaderboard of aura.
    Args:
        ctx (commands.Context): The context of the command.
    




    for rank, (target_id, score) in enumerate(sorted_aura, start=1):
        target_user = await bot.fetch_user(target_id)
        if rank == 1:
            leaderboard_lines.append(f"{rank}. \\>\\>\\> (**🥇**) *`{target_user}`*: {score} aura")
        elif rank == 2:
            leaderboard_lines.append(f"{rank}. \\>\\> (**🥈**) *`{target_user}`*: {score} aura")
        elif rank == 3:
            leaderboard_lines.append(f"{rank}. \\> (**🥉**) *`{target_user}`*: {score} aura")
        else:
            leaderboard_lines.append(f"{rank}. **{target_user}**: {score} aura")

    leaderboard_text = "\n".join(leaderboard_lines)
    await ctx.send(f"# Leaderboard:\n{leaderboard_text}")
    log("Leaderboard displayed with rankings and special text for first place.", "INFO")
"""

@bot.command()
async def modify_aura(ctx: commands.Context, member: discord.Member, amount: int) -> None:
    """
    Add or subtract aura from a user’s current amount (only allowed by OWNER_ID).
    Positive `amount` adds aura, negative subtracts.
    """
    if str(ctx.author.id) not in OWNER_ID:
        await ctx.send("You do not have permission to modify aura.")
        return
    update_aura(member.id, amount)
    new_aura = aura_data.get(str(member.id), 0)
    log(f"Modified <@{member.id}> aura, they now have {new_aura}", "INFO")

    if amount > 0:
        await ctx.send(f"<@{member.id}> has received +{amount} Aura. They now have: {new_aura} Aura!")
    else:
        await ctx.send(f"<@{member.id}> has lost {amount} Aura. They now have: {new_aura}")

@bot.command()
async def dsleaderboard(ctx: commands.Context) -> None:
    if not userAruaCount:
        await ctx.send("Nobody has given out negative aura yet...")
        return
    
    sortedAura = sorted(userAruaCount.items(), key=lambda x: x[1]["NEG"], reverse=True)

    embed = discord.Embed(
        title="Negative Aura Leaderboard",
        description="Leaderboard for people who need to lay off the -aura button",
        color=discord.Color(0xFFEA00)
    )
    
    for rank, (user_id_str, score) in enumerate(sortedAura, start=1):
        target_user = await bot.fetch_user(int(user_id_str))
        user_name = str(target_user.name).capitalize()

        if rank == 1:
            name = f'🍆 > {user_name}'
        elif rank == 2:
            name = f'🚴 > {user_name}'
        elif rank == 3:
            name = f'🤸 > {user_name}'
        else:
            name = f'{rank} > {user_name}'
        
        embed.add_field(name=name, value=f"Negative Aura Given: {score}", inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def help(ctx: commands.Context) -> None:
    helpText ="""
        # Aura Bot Commands

        ## User Commands
        ```
        ?aura [Member] - Checks user's aura
        ?leaderboard - Show the leaderboard
        ```

        ## Admin Commands
        ```
        ?set_aura [member] [amount] - Set aura 
        ?reset_aura [member] - Reset aura
        ?modify_aura [member] [amount] - Add/subtract aura 
        ```
        """

    await ctx.send(helpText)



# Run the bot
def main() -> None:
    try:
        bot.run(TOKEN)
    except Exception as e:
        log(f"Failed to start bot: {e}", "ERROR")


if __name__ == "__main__":
    main()
