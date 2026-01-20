import discord
import random
import time
from modules.bot_setup import bot
from modules import aura_manager
from modules.daily_tasks import save_config
from modules.utils import log
from modules.ui import coinFlipEmbed, blackJackEmbed


# COINFLIP GAME

@bot.command(aliases=['cf'])
async def coinflip(ctx, amount: str):
    authorName = str(ctx.author)

    # Check if user is in a game
    if aura_manager.isBusy(ctx.author.id):
        return await ctx.send(f"Finish your currnet game first!")
    else:
        aura_manager.lockUser(ctx.author.id, name=ctx.author.display_name)
 

    user_id = str(ctx.author.id)
    currentAura = aura_manager.aura_data.get(user_id, 0)

    if amount.lower() == "all":
        amount = currentAura
    elif amount.lower() == "half":
        amount = currentAura // 2
    else:
        try:
            amount = int(amount)
        except ValueError:
            aura_manager.unlockUserlockUser(ctx.author.id, name=ctx.author.display_name)
            return await ctx.send("Please enter a valid number or 'all'.")

    if amount <= 0:
        aura_manager.unlockUserlockUser(ctx.author.id, name=ctx.author.display_name)
        return await ctx.send("Please Enter a Valid Amount")
    if currentAura < amount:
        aura_manager.unlockUser(ctx.author.id, name=ctx.author.display_name)
        return await ctx.send(f"You Only Have {currentAura} Aura")


    view = coinFlipEmbed(ctx.author, amount) 
    msg = await ctx.send(f"**{authorName.capitalize()}** pick Heads or Tails for **{amount:,}** Aura!", view=view )
    log(f"Heads or Tails Game started for {authorName.capitalize()}", "INFO")
    await view.wait()

    if view.choice is None:
        aura_manager.unlockUser(ctx.author.id, name=ctx.author.display_name)
        return await msg.edit(content="Timed out! No aura lost", view=None)


    coinflipInt = random.randint(1,100)
    if coinflipInt % 2 == 0:
        result = "heads"
    else:
        result = "tails"


    won = (view.choice == result)
    try:
        if won:
            aura_manager.update_aura(ctx.author.id, amount, ctx.author.display_name)
            currentAura += amount
            outcome_text = f"**YOU WIN!** It was **{result.capitalize()}**.\n**✚{amount}** AURA!"
            log(f"{ctx.author.name.capitalize()} Won {amount:,} aura.","INFO")
            await ctx.send(f"{ctx.author.mention} you now have {currentAura:,} aura!")
            color = 0x6dab18
        else:
            aura_manager.update_aura(ctx.author.id, -amount, ctx.author.display_name)
            currentAura -= amount
            outcome_text = f"**YOU LOSE!** It was **{result.capitalize()}**.\n **━{amount}** AURA."
            await ctx.send(f"{ctx.author.mention} you now have {currentAura} aura!")
            log(f"{ctx.author.name.capitalize()} Lost {amount} aura.","INFO")
            color = 0x992d22

        aura_manager.save_json(aura_manager.AURA_FILE, aura_manager.aura_data)
        embed = discord.Embed(description=outcome_text, color=color)
        await msg.edit(content=None, embed=embed, view=None)

    finally:
        aura_manager.unlockUser(ctx.author.id, name=ctx.author.display_name)

# -------------------------------------------------------------------------------------------------------------------------------------------------------------------


# BLACKJACK CARD LOGIC
def drawCard():
    cards = [2, 3, 4, 5, 6, 7, 8, 9, 10, 'J', 'K', 'Q', 'A']
    return random.choice(cards)

def calculateScore(hand):
    score = 0
    aces = 0

    for card in hand:
        if card in ['J', 'K', 'Q']:
            score += 10
        elif card == 'A':
            aces += 1
            score += 11
        else:
            score += card

    #if score is over 21 and there is a ace, turn 11 into 1
    while score > 21 and aces:
        score -= 10
        aces -= 1
    return score

# -------------------------------------------------------------------------------------------------------------------------------------------------------------------


# BLACKJACK GAME
@bot.command(aliases=['bj'])
async def blackjack(ctx, amount: str):
    authorName = str(ctx.author)
    user_id = str(ctx.author.id)

    # Check if user is in a game
    if aura_manager.isBusy(ctx.author.id):
        return await ctx.send(f"Finish your currnet game first!")

    currentAura = aura_manager.aura_data.get(user_id, 0)

    # BET AMOUNT LOGIC
    if amount.lower() == "all":
        amount = currentAura
    elif amount.lower() == "half":
        amount = currentAura // 2
    else:
        try:
            amount = int(amount)
        except ValueError:
            return await ctx.send("Please enter a valid number, 'half', or 'all'.")

    if amount <= 0:
        return await ctx.send("Please Enter a Valid Amount")
    if currentAura < amount:
        return await ctx.send(f"You Only Have {currentAura} Aura")

    aura_manager.lockUser(ctx.author.id, name=ctx.author.display_name)
    
    try:
        # INITIAL DEAL
        playerHand = [drawCard(), drawCard()]
        dealerHand = [drawCard(), drawCard()]

        embed = discord.Embed(title="Blackjack", color=0x2b2d31)
        embed.add_field(name="Your Hand", value=f"{playerHand}\nScore: {calculateScore(playerHand)}")
        embed.add_field(name="Dealer's Hand", value=f"['{dealerHand[0]}', '❓']")
        
        view = blackJackEmbed(ctx.author, amount) # Pass both here
        msg = await ctx.send(embed=embed, view=view)

        # PLAYER GAME LOOP
        playing = True
        log(f"{authorName.capitalize()} Started a Blackjack game", "INFO")
        while playing:
            current_score = calculateScore(playerHand)
            if current_score >= 21:
                break

            view = blackJackEmbed(ctx.author, amount) # MUST pass amount here too!
            await msg.edit(embed=embed, view=view)
            await view.wait()

            if view.choice == "hit":
                playerHand.append(drawCard())
                new_score = calculateScore(playerHand)
                embed.set_field_at(0, name="Your Hand", value=f"{playerHand}\nScore: {new_score}")
                await msg.edit(embed=embed, view=view)
                if new_score >= 21:
                    playing = False
            elif view.choice == "stand":
                playing = False
            else:
                # --- TIMEOUT LOSS LOGIC ---
                aura_manager.update_aura(ctx.author.id, -amount, ctx.author.display_name)
                aura_manager.save_json(aura_manager.AURA_FILE, aura_manager.aura_data)

                new_balance = aura_manager.aura_data.get(user_id, 0)

                log(f"{authorName.capitalize()} timed out and lost {amount} aura", "INFO")

            await msg.edit(
                    content=f"**Timed out!** you lost **{amount}** Aura.", 
                    embed=None, 
                    view=None
                )
            return await ctx.send(f"{ctx.author.mention} > New Balance: `{new_balance} Aura`")


        # DEALER TURN (Dealer hits until 17)
        playerFinal = calculateScore(playerHand)
        if playerFinal <= 21:
            while calculateScore(dealerHand) < 17:
                dealerHand.append(drawCard())
        
        dealerFinal = calculateScore(dealerHand)
        

        # DETERMINE WINNER
        if playerFinal > 21:
            result = "BUST"
            change = -amount
            color = 0x992d22
            log(f"{authorName.capitalize()} Lost {amount} aura in Blackjack", "INFO")
        elif dealerFinal > 21:
            result = "DEALER BUSTED - YOU WIN!"
            change = amount
            color = 0x6dab18
            log(f"{authorName.capitalize()} won {amount} aura in Blackjack", "INFO")
        elif playerFinal > dealerFinal:
            result = "YOU WIN!"
            change = amount
            color = 0x6dab18
            log(f"{authorName.capitalize()} won {amount} aura in Blackjack", "INFO")
        elif playerFinal < dealerFinal:
            result = "DEALER WINS"
            change = -amount
            color = 0x992d22
            log(f"{authorName.capitalize()} Lost {amount} aura in Blackjack", "INFO")
        else:
            result = "PUSH (TIE)"
            change = 0
            color = 0x7289da
            log(f"{authorName} tied in Blackjack", "INFO")

        # UPDATE AURA
        if change != 0:
            aura_manager.update_aura(ctx.author.id, change, ctx.author.display_name)
            aura_manager.save_json(aura_manager.AURA_FILE, aura_manager.aura_data)

        # FINAL UI UPDATE
        finalEmbed = discord.Embed(title=f"Blackjack - {result}", color=color)
        finalEmbed.add_field(name="Your Hand", value=f"{playerHand}\nScore: {playerFinal}")
        finalEmbed.add_field(name="Dealer Hand", value=f"{dealerHand}\nScore: {dealerFinal}")
        await ctx.send(f"{ctx.author.mention} > New Balance: `{new_balance} Aura`")
        await msg.edit(embed=finalEmbed, view=None)

    except Exception as e:
        log(f"Blackjack Error: {e}", "ERROR")

    # Unlocks User
    finally:
        aura_manager.unlockUser(ctx.author.id, name=ctx.author.display_name)
    # -------------------------------------------------------------------------------------------------------------------------------------------------------------------
