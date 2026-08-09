import discord
import json
import os
import random
from modules import bot_setup
from modules import aura_manager
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
            auraChange = -random.randint(1,10)
            log(f"{interaction.user.name.capitalize()} loss {auraChange}", "BUTTON")

        # Pick a message template once
        msg_template = f"-# Rolled a {roll}\n"
        msg_template += random.choice(self.messages["gain"]) if roll <= winCon else random.choice(self.messages["loss"])

        # Format message with mention and aura change
        msg = msg_template.format(mention=interaction.user.mention, amount=auraChange)

        # Update aura
        update_aura(interaction.user.id, auraChange, user_obj=interaction.user)

        # Get new balance
        newBalance = aura_data.get(str(interaction.user.id), 0)

        # Edit original message
        if hasattr(self, 'message') and self.message:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass

        # Send a new message with the result
        await interaction.channel.send(f"{msg}\n> New Balance: `{newBalance:,} Aura`")

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
        interaction.client.userClicked = interaction.user.display_name

        # Calculate scaled reward based on unclaimed days streak
        unclaimedDays = aura_manager.getGoldenStreak()
        baseAmount = 40
        amount = baseAmount * unclaimedDays

        # --- GIVE GOLDEN ROLE ---
        roleMsg = ""
        roleId = aura_manager.get_golden_role_id()
        if roleId and interaction.guild:
            role = interaction.guild.get_role(roleId)
            if role:
                try:
                    await interaction.user.add_roles(role, reason="Claimed Golden Button")
                    roleMsg = f" and received the **{role.name}** role!"
                    log(f"Gave Golden Role to {interaction.user.display_name}", "GOLD_BUTTON")
                except discord.Forbidden:
                    log("Missing permissions to give Golden Role. Check role hierarchy!", "ERROR")
                except discord.HTTPException as e:
                    log(f"Failed to give Golden Role: {e}", "ERROR")

        # Update balance & reset streak
        update_aura(interaction.user.id, amount, user_obj=interaction.user)
        aura_manager.resetGoldenStreak()

        newBalance = aura_data.get(str(interaction.user.id), 0)

        # Remove original button message
        if hasattr(self, 'message') and self.message:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass

        await interaction.channel.send(
            f"{interaction.user.mention} Pressed the golden button and gained `+{amount:,}` Aura!{roleMsg}\n> New Balance: `{newBalance:,} Aura`"
        )
        log(f"{interaction.user.display_name} pressed the gold button for {amount} Aura (x{unclaimedDays} streak)", "GOLD_BUTTON")

        self.stop()

    async def on_timeout(self):
        aura_manager.incrementGoldenStreak()
        currentStreak = aura_manager.getGoldenStreak()

        if hasattr(self, 'message') and self.message:
            try:
                await self.message.delete()
                log(f"Golden Button timed out unclaimed. | STREAK: x{currentStreak}.", "GOLD_BUTTON")
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

# RPS vs Bot Embed 
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

    @discord.ui.button(label="Rock", emoji="🪨", style=discord.ButtonStyle.green)
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_selection(interaction, "rock")
    
    @discord.ui.button(label="Paper", emoji="📄", style=discord.ButtonStyle.red)
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_selection(interaction, "paper")

    @discord.ui.button(label="Scissors", emoji="✂️", style=discord.ButtonStyle.grey)
    async def scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_selection(interaction, "scissors")

# Embed for RPS Request
class rpsChallengeEmbed(discord.ui.View):
    def __init__(self, author, opponent, amount):
        super().__init__(timeout=60)
        self.author = author 
        self.opponent = opponent
        self.amount = amount
        self.accepted = False

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            return await interaction.response.send_message("This game isn't for you lil bro..", ephemeral=True)
        
        self.accepted = True
        await interaction.response.send_message(f"{self.author.mention} vs. {self.opponent.mention}", ephemeral=False)
        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.interactions, button:discord.Button):
        if interaction.user.id != self.opponent.id:
            return await interaction.response.send_message("This game isn't for you lil bro..", ephemeral=True)
        
        self.accepted = False
        await interaction.response.send_message(f"{interaction.user.mention} Declined the duel.", ephemeral=False)
        self.stop()

# Request Aura Embed
class RequestAuraEmbed(discord.ui.View):
    def __init__(self, author: discord.User, reqUser: discord.User, amount: int):
        super().__init__(timeout=60)
        self.author = author      # Person requesting aura
        self.reqUser = reqUser    # Person being asked for aura
        self.amount = amount
        self.message: discord.Message | None = None

    async def on_timeout(self) -> None:
        """Disable buttons and mark request as expired after 60 seconds."""
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        if self.message:
            try:
                await self.message.edit(content="**Request Expired:** No response in time.", view=self)
                aura_manager.unlockUser(str(self.author.id), self.author.name)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.reqUser.id:
            return await interaction.response.send_message("This request isn't for you lil bro..", ephemeral=True)

        # Double check sender's balance at the time of click
        giverBalance = aura_data.get(str(self.reqUser.id), 0)
        if giverBalance < self.amount:
            return await interaction.response.send_message(
                f"You don't have enough aura to  this request! (Current balance: `{giverBalance}`)",
                ephemeral=True
            )

        # Execute balance update
        update_aura(self.reqUser.id, -self.amount, user_obj=self.reqUser)
        update_aura(self.author.id, self.amount, user_obj=self.author)

        aura_manager.unlockUser(str(self.author.id), self.author.name)

        # Disable buttons
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        await interaction.response.edit_message(content=f"**Request Accepted!** {self.reqUser.mention} sent `{self.amount}` Aura to {self.author.mention}.",view=self)
        log(f"{self.reqUser.display_name} sent {self.amount} aura to {self.author.display_name}", "REQUEST")

        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.reqUser.id:
            return await interaction.response.send_message("This request isn't for you lil bro..", ephemeral=True)

        # Disable buttons
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        await interaction.response.edit_message(
            content=f"**Request Declined:** {self.reqUser.mention} rejected the request for `{self.amount}` Aura.",
            view=self
        )

        log(f"{self.reqUser.display_name} declined the {self.amount} aura request from {self.author.display_name}", "REQUEST")
        aura_manager.unlockUser(str(self.author.id), self.author.name)
        self.stop()


def createJackpotEmbed(userMention: str, jackpotAmount: int, newBalance: int) -> discord.Embed:
    """Creates a standardized embed for Jackpot announcements."""
    embed = discord.Embed(
        title="JACKPOT",
        description=f"🎉 {userMention} won the jackpot for **+{jackpotAmount:,}** Aura!",
        color=0xFEE75C, 
    )
    embed.add_field(
        name="New Total Balance",
        value=f"`{newBalance:,} Aura`",
        inline=False,
    )
    return embed



# RPS PvP Embed
class rpsPvPEmbed(discord.ui.View):
    def __init__(self, p1, p2, amount):
        super().__init__(timeout=60)
        self.p1 = p1
        self.p2 = p2
        self.amount = amount
        self.p1Choice = None
        self.p2Choice = None

    async def handleChoice(self, interaction, choice):
        
        if interaction.user.id == self.p1.id:
            if self.p1Choice: return await interaction.response.send_message("Already picked!", ephemeral=True)
            self.p1Choice = choice
        elif interaction.user.id == self.p2.id:
            if self.p2Choice: return await interaction.response.send_message("Already picked!", ephemeral=True)
            self.p2Choice = choice
        else:
            return await interaction.response.send_message("This isn't your duel!", ephemeral=True)
        
        log(f"{interaction.user.display_name} made a choice: {choice.capitalize()}", "RPS")

        await interaction.response.defer()

        # Update Embed to show "Ready"
        embed = interaction.message.embeds[0]
        # Update field 0 (P1) or field 2 (P2)
        idx = 0 if interaction.user.id == self.p1.id else 2
        name = self.p1.display_name if idx == 0 else self.p2.display_name

        embed.set_field_at(idx, name=name, value="✅ Ready!", inline=True)
        await interaction.message.edit(embed=embed)

        # If both picked, finish
        if self.p1Choice and self.p2Choice:
            self.stop()

    @discord.ui.button(label="Rock", emoji="🪨", style=discord.ButtonStyle.green)
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handleChoice(interaction, "rock")

    @discord.ui.button(label="Paper", emoji="📄", style=discord.ButtonStyle.red)
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handleChoice(interaction, "paper")

    @discord.ui.button(label="Scissors", emoji="✂️", style=discord.ButtonStyle.grey)
    async def scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handleChoice(interaction, "scissors")

