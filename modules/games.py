import discord
import random
import time
from modules.bot_setup import bot
from modules import aura_manager
from modules.daily_tasks import save_config
from modules.utils import log
from modules.ui import coinFlipEmbed, blackJackEmbed
from modules.aura_manager import unlockUser, lockUser, isBusy


# COINFLIP GAME

@bot.command(aliases=['cf'])
async def coinflip(ctx, amount: str):
    authorName = str(ctx.author)

    # Check if user is in a game
    if aura_manager.isBusy(ctx.author.id):
        return await ctx.send(f"Finish your currnet game first!")
    

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
            return await ctx.send("Please enter a valid number or 'all'.")

    if amount <= 0:
        return await ctx.send("Please Enter a Valid Amount")
    if currentAura < amount:
        return await ctx.send(f"You Only Have {currentAura} Aura")


    view = coinFlipEmbed(ctx.author, amount)
    aura_manager.lockUser(ctx.author.id, name=ctx.author.display_name)
    msg = await ctx.send(f"**{ctx.author.mention}** pick Heads or Tails for **{amount:,}** Aura!", view=view )
    log(f"Game started for {authorName.capitalize()}", "CF_INFO")
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
            log(f"{ctx.author.name.capitalize()} Won {amount:,} aura.","COINFLIP")
            await ctx.send(f"{ctx.author.mention} > New Balance: `{currentAura:,} Aura`")
            color = 0x6dab18
        else:
            aura_manager.update_aura(ctx.author.id, -amount, ctx.author.display_name)
            currentAura -= amount
            outcome_text = f"**YOU LOSE!** It was **{result.capitalize()}**.\n **━{amount}** AURA."
            await ctx.send(f"{ctx.author.mention} > New Balance: `{currentAura:,} Aura`")
            log(f"{ctx.author.name.capitalize()} Lost {amount} aura.","COINFLIP")
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

    if aura_manager.isBusy(ctx.author.id):
        return await ctx.send(f"Finish your current game first!")

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
        return await ctx.send(f"You Only Have **{currentAura:,}** Aura") # Added commas

    aura_manager.lockUser(ctx.author.id, name=ctx.author.display_name)
    
    try:
        playerHand = [drawCard(), drawCard()]
        dealerHand = [drawCard(), drawCard()]

        embed = discord.Embed(title="Blackjack", color=0x2b2d31)
        embed.add_field(name="Your Hand", value=f"{playerHand}\nScore: {calculateScore(playerHand)}")
        embed.add_field(name="Dealer's Hand", value=f"['{dealerHand[0]}', '❓']")
        
        view = blackJackEmbed(ctx.author, amount) 
        msg = await ctx.send(f"{ctx.author.mention}'s Blackjack game for **{amount}** aura", embed=embed, view=view)

        playing = True
        log(f"Game started for {authorName.capitalize()}", "BJ_INFO")
        
        while playing:
            current_score = calculateScore(playerHand)
            if current_score >= 21:
                break

            view = blackJackEmbed(ctx.author, amount)
            await msg.edit(embed=embed, view=view)
            await view.wait()

            if view.choice == "hit":
                playerHand.append(drawCard())
                new_score = calculateScore(playerHand)
                embed.set_field_at(0, name="Your Hand", value=f"{playerHand}\nScore: {new_score}")
                if new_score >= 21:
                    playing = False
            elif view.choice == "stand":
                playing = False
            else:
                # --- TIMEOUT LOSS LOGIC ---
                aura_manager.update_aura(ctx.author.id, -amount, ctx.author.display_name)
                aura_manager.save_json(aura_manager.AURA_FILE, aura_manager.aura_data)
                
                new_balance = aura_manager.aura_data.get(user_id, 0)
                
                log(f"{authorName.capitalize()} timed out and lost {amount} aura", "BLACKJACK")
                
                await msg.edit(content=f"**Timed out!** You lost **{amount:,}** Aura.", embed=None, view=None)
                return await ctx.send(f"{ctx.author.mention} > New Balance: `{new_balance:,} Aura`")

        # DEALER TURN
        playerFinal = calculateScore(playerHand)
        if playerFinal <= 21:
            while calculateScore(dealerHand) < 17:
                dealerHand.append(drawCard())
        
        dealerFinal = calculateScore(dealerHand)
        
        # DETERMINE WINNER
        if playerFinal > 21:
            result, change, color = "BUST", -amount, 0x992d22
        elif dealerFinal > 21:
            result, change, color = "DEALER BUSTED - YOU WIN!", amount, 0x6dab18
        elif playerFinal > dealerFinal:
            result, change, color = "YOU WIN!", amount, 0x6dab18
        elif playerFinal < dealerFinal:
            result, change, color = "DEALER WINS", -amount, 0x992d22
        else:
            result, change, color = "PUSH (TIE)", 0, 0x7289da

        # UPDATE AURA
        if change != 0:
            aura_manager.update_aura(ctx.author.id, change, ctx.author.display_name)
            aura_manager.save_json(aura_manager.AURA_FILE, aura_manager.aura_data)

        # Define new_balance HERE for the normal end message
        new_balance = aura_manager.aura_data.get(user_id, 0)

        # FINAL UI UPDATE
        finalEmbed = discord.Embed(title=f"Blackjack - {result}", color=color)
        finalEmbed.add_field(name="Your Hand", value=f"{playerHand}\nScore: {playerFinal}")
        finalEmbed.add_field(name="Dealer Hand", value=f"{dealerHand}\nScore: {dealerFinal}")
        
        await msg.edit(embed=finalEmbed, view=None)
        await ctx.send(f"{ctx.author.mention} > New Balance: `{new_balance:,} Aura`")

    except Exception as e:
        log(f"Blackjack Error: {e}", "ERROR")
    finally:
        aura_manager.unlockUser(ctx.author.id, name=ctx.author.display_name)
    # -------------------------------------------------------------------------------------------------------------------------------------------------------------------
