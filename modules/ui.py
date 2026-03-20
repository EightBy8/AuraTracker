import discord
import json
import os
import random
from modules.utils import log
from modules.aura_manager import isBusy, lockUser, unlockUser, update_aura, aura_data


# Leaderboard embed with pageturn
class leaderboardEmbed(discord.ui.View):
    def __init__(self, data, title="Leaderboard", description="", color=0x6dab18):
        super().__init__(timeout=120)
        self.data = data
        self.title_text = title      # Store the title
        self.desc_text = description # Store the intro text
        self.color = color           # Store the color hex
        self.currentPage = 0
        self.perPage = 10
        self.end = (len(data) - 1) // self.perPage

    def createEmbed(self):
        start = self.currentPage * self.perPage
        end = start + self.perPage
        chunk = self.data[start:end]

        chunk_desc = "---------------------------\n".join(chunk)
        
        full_description = f"{self.desc_text}\n\n{chunk_desc}"

        embed = discord.Embed(
            title=f"{self.title_text}: Page {self.currentPage + 1}",
            description=full_description,
            color=discord.Color(self.color) #Uses Stored Color
        )

        if self.title_text == "Aura Leaderboard":
            log("Aura Leaderboard Posted", "SUCCESS")
        elif self.title_text == "Simp Leaderboard":
            log("Simp Leaderboard Posted", "SUCCESS")
        elif self.title_text == "Leaderboard of Dicksuck":
            log("Dicksuck Leaderboard Posted", "SUCCESS")

        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
    async def prevButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.currentPage > 0:
            self.currentPage -= 1
            await interaction.response.edit_message(embed=self.createEmbed(), view=self)
            log(f"{interaction.user.name.capitalize()} turned to page {self.currentPage + 1}", "INFO")
        else:
            await interaction.response.send_message("You're on the first page!", ephemeral=True)

    @discord.ui.button(label="Next Page", style=discord.ButtonStyle.green)
    async def nextButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        # FIX: Check against self.end before incrementing
        if self.currentPage < self.end:
            self.currentPage += 1
            await interaction.response.edit_message(embed=self.createEmbed(), view=self)
            log(f"{interaction.user.name.capitalize()} turned to page {self.currentPage + 1}", "INFO")
        else:
            await interaction.response.send_message("You're on the last page!", ephemeral=True)
    
class coinFlipEmbed(discord.ui.View):
    def __init__(self, user, amount): 
        super().__init__(timeout=60)
        self.user = user
        self.amount = amount # You can store this just in case
        self.choice = None

    @discord.ui.button(label="Heads", style=discord.ButtonStyle.primary)
    async def heads(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("This isn't your coinflip!", ephemeral=True)
            
        self.choice = "heads"
        await interaction.response.defer()
        self.stop()
        
    @discord.ui.button(label="Tails", style=discord.ButtonStyle.secondary)
    async def tails(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("This isn't your coinflip!", ephemeral=True)
            
        self.choice = "tails"
        await interaction.response.defer()
        self.stop()

class blackJackEmbed(discord.ui.View):
    def __init__(self, user, amount):
        super().__init__(timeout=60)
        self.user = user
        self.amount = amount
        self.choice = None

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.red)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("This is not your blackjack game!", ephemeral=True)
        self.choice = "hit"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.green)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("This is not your blackjack game!", ephemeral=True)
        self.choice = "stand"
        await interaction.response.defer()
        self.stop()


class randomButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.clicked = False

        # Load gain/loss messages
        baseDir = os.path.dirname(os.path.abspath(__file__)) # auraTracker/
        filePath = os.path.join(baseDir,"..","data","randomMessages.json") 
        with open(filePath, "r") as f:
            self.messages = json.load(f)

    @discord.ui.button(label="Click Me", style=discord.ButtonStyle.blurple)
    async def clickedButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.clicked:
            return
        self.clicked = True

        # Randomly decide gain or loss
        roll = random.randint(1,100)
        winCon = 50

        if roll <= winCon:
            auraChange = random.randint(1,20)
            log(f"{interaction.user.name.capitalize()} gain {auraChange}", "BUTTON")
        else:
            auraChange = -random.randint(1,15)
            log(f"{interaction.user.name.capitalize()} loss {auraChange}", "BUTTON")

        # Pick a message template once
        msg_template = f"-# Rolled a {roll}\n"
        msg_template += random.choice(self.messages["gain"]) if roll <= winCon else random.choice(self.messages["loss"])

        # Format message with mention and aura change
        msg = msg_template.format(mention=interaction.user.mention, amount=auraChange)

        # Update aura
        update_aura(interaction.user.id, auraChange, user_obj=interaction.user)

        # Get new balance
        new_balance = aura_data.get(str(interaction.user.id), 0)

        # Edit original message
        if hasattr(self, 'message') and self.message:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass

        # Send a new message with the result
        await interaction.channel.send(f"{msg}\n> New Balance: `{new_balance:,} Aura`")

        # Stop the view to clean up
        self.stop()
    
    async def on_timeout(self):
        # Disable all buttons when the view times out
        if hasattr(self, 'message') and self.message:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass

class goldenButtonEmbed(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)
        self.clicked = False

    @discord.ui.button(label="✨Click Me✨", style=discord.ButtonStyle.grey)
    async def clickedButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.clicked:
            return
        self.clicked = True

        #Update aura
        amount = 25
        update_aura(interaction.user.id, amount, user_obj=interaction.user)

        # Get new balance
        new_balance = aura_data.get(str(interaction.user.id), 0)


        # Edit original message
        if hasattr(self, 'message') and self.message:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass
        await interaction.channel.send(f"{interaction.user.mention} Pressed the golden button and gained `+{amount}` Aura!\n> New Balance: `{new_balance:,} Aura`")
        log(f"{interaction.user.display_name} Pressed the gold button", "GOLD_BUTTON")

        # Stop the view to clean up
        self.stop()


    async def on_timeout(self):
        if self.message:
            try:
                await self.message.delete()
                log("Golden Button timed out and was removed.", "GOLD_BUTTON")
            except discord.NotFound:
                pass
            except Exception as e:
                log(f"Error deleting timed out button: {e}", "ERROR")

class higherLowerEmbed(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=60)
        self.user = user
        self.choice = None

    @discord.ui.button(label="Higher", style=discord.ButtonStyle.primary)
    async def higher(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("This isn't your game!", ephemeral=True)
        self.choice = "higher"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Lower", style=discord.ButtonStyle.secondary)
    async def lower(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("This isn't your game!", ephemeral=True)
        self.choice = "lower"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Cash Out", style=discord.ButtonStyle.success)
    async def cashout(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("This isn't your game!", ephemeral=True)
        self.choice = "quit"
        await interaction.response.defer()
        self.stop()


class rockPaperScissorsEmbed(discord.ui.View):
    def __init__(self, author, amount):
        super().__init__(timeout=60)
        self.author = author
        self.amount = amount
        self.choice = None

    async def process_selection(self, interaction: discord.Interaction, choice: str):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("This is not your game!", ephemeral=True)
        
        self.choice = choice 
        await interaction.response.edit_message(content=f"what bro", view=None) 
        self.stop()

    @discord.ui.button(label="Rock", emoji="🪨", style=discord.ButtonStyle.blurple)
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_selection(interaction, "rock")
    
    @discord.ui.button(label="Paper", emoji="📄", style=discord.ButtonStyle.blurple)
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_selection(interaction, "paper")

    @discord.ui.button(label="Scissors", emoji="✂️", style=discord.ButtonStyle.blurple)
    async def scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_selection(interaction, "scissors")

