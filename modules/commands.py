# modules/commands.py

from discord.ext import commands
import discord
import json
import os
from modules.bot_setup import bot
from modules.daily_tasks import save_config, load_config
from modules import aura_manager
from modules.utils import log, seconds_until
from modules.ui import leaderboardEmbed, randomButton
from discord import Embed

# Path to auraCount.json
AURA_COUNT_FILE = os.path.join("data", "auraCount.json")


#Test Page Turn Embed Layout
class pageTurn(discord.ui.View):
    def __init__(self, data):
        super().__init__(timeout=120) # Added () after __init__
        self.data = data
        self.currentPage = 0
        self.perPage = 10

    def createEmbed(self):
            # 1. Calculate the chunk of data to show
            start = self.currentPage * self.perPage
            end = start + self.perPage
            chunk = self.data[start:end]
            
            # description between each user
            description = "--------------------------------------\n".join(chunk)

            # 3. Create the Embed object (Title, Description, Color)
            embed = discord.Embed(
                title=f"Aura Leaderboard Page {self.currentPage + 1}",
                description=f"\n{description}",
                color=discord.Color(0x32CD32)
            )

            # 4. Calculate total pages
            total_pages = (len(self.data) - 1) // self.perPage + 1

            # 5. Set the footer on the embed object
            embed.set_footer(text=f"Page {self.currentPage + 1} of {total_pages}")
            
            return embed
            
    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
    async def prevButton(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.currentPage > 0:
                self.currentPage -= 1
                await interaction.response.edit_message(embed=self.createEmbed(), view=self)
                log(f"{interaction.user.name.capitalize()} Turned the page", "INFO")

            else:
                # Let the user know they can't go back further
                await interaction.response.send_message("You're on the first page!", ephemeral=True)


    @discord.ui.button(label="Next Page", style=discord.ButtonStyle.green)
    async def nextButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 1. Update the page tracker
        self.currentPage += 1
        
        # 2. Create the NEW embed
        newEmbed = self.createEmbed()
        
        # 3. EDIT the message (This is the "Turning the page" part)
        await interaction.response.edit_message(embed=newEmbed, view=self)
        log(f"{interaction.user.name.capitalize()} Turned the page", "INFO")

class testButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # The button dies NEVER!

    @discord.ui.button(label="Click Me!", style=discord.ButtonStyle.green,)
    async def buttonCallback(self, interaction: discord.Interaction, button: discord.ui.Button):
        # This code runs when the button is clicked
        await interaction.response.send_message(f"{interaction.user.name} clicked the button.", ephemeral=False)
        log(f"{interaction.user.name.capitalize()} Cliked The Button","SUCCESS")



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

    aura_manager.CHANNEL_ID = ctx.channel.id  
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

from modules.daily_tasks import send_leaderboard # Import the function you just fixed

@bot.command()
async def test_daily(ctx):
    """Manually triggers the daily leaderboard for testing."""
    # 1. Check if the user is an officer
    if ctx.author.id not in aura_manager.OWNER_IDS:
        return await ctx.send("❌ You don't have permission to run this test.")

    await ctx.send("🔄 Running manual daily leaderboard test...")

    # 2. Trigger the functions from modules/daily_tasks.py
    from modules.daily_tasks import send_leaderboard, take_snapshot
    
    try:
        # We take a snapshot first so there is "Today" data to compare against
        await take_snapshot() 
        # Then we send the leaderboard
        await send_leaderboard()
        await ctx.send("✅ Test complete! Check the designated leaderboard channel.")
    except Exception as e:
        await ctx.send(f"⚠️ Test failed! Check console. Error: {e}")
        log(f"Manual daily leaderboard test failed: {e}", "ERROR")

@bot.command()
async def aura(ctx: commands.Context, member: discord.Member | None = None) -> None:
    member = member or ctx.author
    user_aura = aura_manager.aura_data.get(str(member.id), 0)
    await ctx.send(f"{member.mention}'s aura: {user_aura:,}")
    log(f"Aura requested for {member} ({member.id})", "INFO")


@bot.command()
async def lb(ctx, page: int = 1):

    # Check if user is in a game
    if aura_manager.isBusy(ctx.author.id):
        return await ctx.send(f"Finish your currnet game first!")

    # Define 'data' properly
    data = aura_manager.aura_data
    if not data:
        return await ctx.send("No Data for Leaderboard Yet...")

    # Sort the data
    sorted_aura = sorted(data.items(), key=lambda x: x[1], reverse=True)

    # Format Data
    formatted_data = []
    for rank, (uid, score) in enumerate(sorted_aura, start=1):
        formattedScore = f"{score:,}"
        prefix = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, str(rank))
        formatted_data.append(f"{prefix}> <@{uid}> \n\u2003Aura: {formattedScore}\n")

    # Initialize the View
    view = leaderboardEmbed(
        data=formatted_data, 
        title="Aura Leaderboard", 
        description="Leaderboard for people with the most aura",
        color=0x6dab18
    )

    # Set the starting page based on user input
    target_page = page - 1
    if 0 <= target_page <= view.end:
        view.currentPage = target_page
        await ctx.send(embed=view.createEmbed(), view=view)
    else:
        await ctx.send(f"Invalid page! Choose between 1 and {view.end + 1}.")


#----------------------------------------------------------------------------------------------------------------------------------------------------------------
# OLD LEADERBOARD EMBED, WONT WORK WITH OVER 20 MEMBERS

# async def lb(ctx: commands.Context) -> None:
#     if not aura_manager.aura_data:
#         await ctx.send("No aura yet!")
#         return
#
#     sorted_aura = sorted(aura_manager.aura_data.items(), key=lambda x: x[1], reverse=True)
#     embed = Embed(title="Aura Leaderboard", description="--------------------------------------",color=discord.Color(0x32CD32), ) 
#     for rank, (uid, score) in enumerate(sorted_aura, start=1):
#         user = await bot.fetch_user(int(uid))
#         prefix = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, str(rank))
#         embed.add_field(name=f"{prefix} > {user.name.capitalize()}", value=f"Aura: {score}", inline=False)
#     await ctx.send(embed=embed)
#     log("Leaderboard shown", "INFO")
#----------------------------------------------------------------------------------------------------------------------------------------------------------------


@bot.command(name="leaderboard")
async def leaderboard_alias(ctx: commands.Context) -> None:
    await ctx.send("Command moved to -> '?lb'")


@bot.command()
async def give_aura(ctx: commands.Context, member: discord.Member, amount: str) -> None:
    giver_id = str(ctx.author.id)
    receiver_id = str(member.id)

    # Check if user is in a game
    if aura_manager.isBusy(ctx.author.id):
        return await ctx.send(f"Finish your currnet game first!")
    elif aura_manager.isBusy(member.id):
        return await ctx.send(f"That user is currently in a game!")
    
    # Get the giver's current balance
    currentAura = aura_manager.aura_data.get(giver_id, 0)

    # Convert "all" or string to integer
    if amount.lower() == "all":
        amount = currentAura
    elif amount.lower() == "half":
        amount = currentAura // 2
    else:
        try:
            amount = int(amount)
        except ValueError:
            return await ctx.send("Please enter a valid number or 'all'.")

    # Basic checks
    if amount <= 0:
        return await ctx.send("You can only give a positive amount of aura.")
    
    if member.id == ctx.author.id:
        return await ctx.send("You can't give aura to yourself!")

    # Ensure receiver exists in aura_data
    aura_manager.aura_data.setdefault(receiver_id, 0)

    # Check if they have enough
    if currentAura < amount:
        return await ctx.send(f"You don't have enough aura to give {amount:,}.")

    # Transfer aura
    aura_manager.aura_data[giver_id] -= amount
    aura_manager.aura_data[receiver_id] += amount

    # Save to file
    aura_manager.save_json(aura_manager.AURA_FILE, aura_manager.aura_data)

    await ctx.send(f"{ctx.author.mention} gave **{amount:,}** aura to {member.mention}!")
    log(f"{ctx.author.name.capitalize()} gave {amount} aura to {member.name.capitalize()}", "INFO")

@bot.command()
async def set_aura(ctx: commands.Context, member: discord.Member, amount: int) -> None:
    authorName = ctx.author.display_name.capitalize()
    if ctx.author.id not in aura_manager.OWNER_IDS:
        return await ctx.send("You do not have permission to set the aura.")
    aura_manager.set_aura(member.id, amount)
    await ctx.send(f"{member.mention} > New Balance: `{amount:,} Aura`")
    log(f"{authorName} set aura for {member} to {amount}", "INFO")


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
    aura_manager.update_aura(member.id, amount, ctx.author.display_name)
    new_val = aura_manager.aura_data.get(str(member.id), 0)
    if amount > 0:
        await ctx.send("Modifying Aura...")
        await ctx.send(f"{member.mention} > New Balance: `{amount} Aura`")
    else:
        await ctx.send("Modifying Aura...")
        await ctx.send(f"{member.mention} > New Balance: `{amount} Aura`")
    log(f"{ctx.author} modified aura for {member} by {amount}", "INFO")

@bot.command()
async def dslb(ctx, page: int = 1):
    """Show paginated leaderboard of who has given the most negative aura."""
    from modules.aura_manager import user_aura_count

    # Check if user is in a game
    if aura_manager.isBusy(ctx.author.id):
        return await ctx.send(f"Finish your currnet game first!")

    # Filter only people with NEG > 0
    neg_scores = {uid: data["NEG"] for uid, data in user_aura_count.items() if data["NEG"] > 0}

    if not neg_scores:
        await ctx.send("Nobody has given negative aura yet...")
        return

    # Sort the data
    sorted_neg = sorted(neg_scores.items(), key=lambda x: x[1], reverse=True)

    # Format into a list of strings
    formatted_data = []
    for rank, (uid, neg_count) in enumerate(sorted_neg, start=1):
        emoji = {1: "🍆", 2: "🚴", 3: "🤸"}.get(rank, str(rank))
        formatted_data.append(f"{emoji} > <@{uid}>\n\u2003Negative Aura Given: {neg_count}\n")

    # Embed Title and Description
    view = leaderboardEmbed(
        data=formatted_data,
        title="Leaderboard of Dicksuck",
        description="Leaderboard for people who need to lay off the -aura button",
        color=0xEBF527
    )

    # Handle starting page logic
    target_page = page - 1
    if target_page < 0 or target_page > view.end:
        await ctx.send(f"Invalid page! Choose a page between `1` and `{view.end + 1}`.")
        return
    
    view.currentPage = target_page
    
    #Send it
    await ctx.send(embed=view.createEmbed(), view=view)

@bot.command(name="slb")
async def slb(ctx: commands.Context, page: int = 1) -> None:
    """Show paginated Simp Leaderboard."""
    from modules.aura_manager import user_aura_count 

    # Check if user is in a game
    if aura_manager.isBusy(ctx.author.id):
        return await ctx.send(f"Finish your currnet game first!")

    # 1. Filter only people with POS > 0
    pos_scores = {uid: data["POS"] for uid, data in user_aura_count.items() if data["POS"] > 0}

    if not pos_scores:
        await ctx.send("Nobody has given positive aura yet...")
        return

    # 2. Sort the data
    sorted_pos = sorted(pos_scores.items(), key=lambda x: x[1], reverse=True)

    # 3. Format into a list of strings
    formatted_data = []
    for rank, (uid, pos_count) in enumerate(sorted_pos, start=1):
        emoji = {1: "👑", 2: "💎", 3: "🌸"}.get(rank, str(rank))
        formatted_data.append(f"{emoji} > <@{uid}>\n\u2003Positive Aura Given: {pos_count}\n")

    # 4. Embed Title and Description
    view = leaderboardEmbed(
        data=formatted_data,
        title="Simp Leaderboard",
        description="Leaderboard for people who hand out +aura like candy",
        color=0xfd87e2
    )

    # Handle starting page logic
    target_page = page - 1
    if target_page < 0 or target_page > view.end:
        await ctx.send(f"Invalid page! Choose a page between `1` and `{view.end + 1}`.")
        return
    
    view.currentPage = target_page
    
    # Send the embed and the view
    await ctx.send(embed=view.createEmbed(), view=view)
    
@bot.command()
async def dailylb(ctx: commands.Context) -> None:
    # Check if user is in a game
    if aura_manager.isBusy(ctx.author.id):
        return await ctx.send(f"Finish your currnet game first!")

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
- ?give_aura [Memeber] [Amount | "all", "half"] - Send aura to another user
- ?lb - shows leaderboard
- ?slb - shows who gives the most positive aura
- ?dslb - shows who gives the most negative aura
- ?dailylb - shows countdown for next daily leaderboard post
- ?coinflip, ?cf - [Amount | "all", "half"] - play a coinflip game
- ?blackjack, ?bj - [Amount | "all", "half"] - play a blackjack game


### __*Aura Officer Commands :*__
- `?set_aura [member] [amount] - set aura`
- `?reset_aura [member] - reset aura`
- `?modify_aura [member] [amount] - modify aura`
- `?set_channel - sets the channel for daily leaderboards to be sent`
- `?add_officer - adds user to aura officer list`

"""
    )


@bot.command()
async def randomTest(ctx: commands.Context) -> None:
    if ctx.author.id not in aura_manager.OWNER_IDS:
        return await ctx.send("This command shouldn't even be here....")
    view = randomButton()
    await ctx.send("Click this button for some aura! (or not)", view=view)
