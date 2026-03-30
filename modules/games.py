import discord
import random
import time
from math import ceil
from modules import aura_manager
from modules.bot_setup import bot
from modules.aura_manager import unlockUser, lockUser, isBusy
from modules.daily_tasks import save_config
from modules.ui import coinFlipEmbed, blackJackEmbed, higherLowerEmbed, rockPaperScissorsEmbed, rpsChallengeEmbed, rpsPvPEmbed
from modules.utils import log
from typing import Optional


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
        aura_manager.update_aura(ctx.author.id, -amount, ctx.author.display_name)
        aura_manager.update_aura(bot.user.id, +amount, "The House")

        await msg.edit(content=f"{ctx.author.mention} Timed out! You lost. The House takes `{amount:,}' aura", view=None)
        aura_manager.unlockUser(ctx.author.id, name=ctx.author.display_name)
        return 

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
            outcome_text = f"**YOU WIN!** It was **{result.capitalize()}**.\n**✚{amount:,}** AURA!"
            log(f"{ctx.author.name.capitalize()} Won {amount:,} aura.","COINFLIP")
            await ctx.send(f"{ctx.author.mention} > New Balance: `{currentAura:,} Aura`")
            color = 0x6dab18
        else:
            aura_manager.update_aura(ctx.author.id, -amount, ctx.author.display_name)
            aura_manager.update_aura(bot.user.id, +amount, "The House")

            currentAura -= amount
            botTotal = aura_manager.aura_data.get(str(bot.user.id))


            outcome_text = f"**YOU LOSE!** It was **{result.capitalize()}**.\n **━{amount:,}** AURA."
            await ctx.send(f"{ctx.author.mention} > New Balance: `{currentAura:,} Aura`")
            # await ctx.send(f"`{amount:,}` aura has been added to the bank. ")

            log(f"{ctx.author.name.capitalize()} Lost {amount:,} aura.","COINFLIP")
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
        return await ctx.send(f"You Only Have **{currentAura:,}** Aura") 

    aura_manager.lockUser(ctx.author.id, name=ctx.author.display_name)
    
    try:
        playerHand = [drawCard(), drawCard()]
        dealerHand = [drawCard(), drawCard()]

        embed = discord.Embed(title="Blackjack", color=0x2b2d31)
        embed.add_field(name="Your Hand", value=f"{playerHand}\nScore: {calculateScore(playerHand)}")
        embed.add_field(name="Dealer's Hand", value=f"['{dealerHand[0]}', '❓']")
        
        view = blackJackEmbed(ctx.author, amount) 
        msg = await ctx.send(f"{ctx.author.mention}'s Blackjack game for **{amount:,}** aura", embed=embed, view=view)

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
                aura_manager.update_aura(bot.user.id, +amount, "The House" )

                aura_manager.save_json(aura_manager.AURA_FILE, aura_manager.aura_data)
                
                new_balance = aura_manager.aura_data.get(user_id, 0)
                
                log(f"{authorName.capitalize()} timed out and lost {amount:,} aura", "BLACKJACK")
                
                await msg.edit(content=f"**Timed out!** You lost **{amount:,}** Aura.", embed=None, view=None)
                await ctx.send(f"{ctx.author.mention} > New Balance: `{new_balance:,} Aura`")
                # await ctx.send(f"`{amount:,}` aura has been added to the bank. ")
                return

        # DEALER TURN
        playerFinal = calculateScore(playerHand)
        if playerFinal <= 21:
            while calculateScore(dealerHand) < 17:
                dealerHand.append(drawCard())
        
        dealerFinal = calculateScore(dealerHand)
        
# DETERMINE WINNER
        bot_id_str = str(bot.user.id)
        if playerFinal > 21:
            result, change, color = "BUST", -amount, 0x992d22
            # House collects on player bust
            aura_manager.update_aura(bot.user.id, amount, "The House")
        elif dealerFinal > 21:
            result, change, color = "DEALER BUSTED - YOU WIN!", amount, 0x6dab18
        elif playerFinal > dealerFinal:
            result, change, color = "YOU WIN!", amount, 0x6dab18
        elif playerFinal < dealerFinal:
            result, change, color = "DEALER WINS", -amount, 0x992d22
            # House collects on dealer win
            aura_manager.update_aura(bot.user.id, amount, "The House")
        else:
            result, change, color = "PUSH (TIE)", 0, 0x7289da

        # UPDATE PLAYER AURA
        if change != 0:
            aura_manager.update_aura(ctx.author.id, change, ctx.author.display_name)
            aura_manager.save_json(aura_manager.AURA_FILE, aura_manager.aura_data)

        # Get  balances for the final message
        new_balance = aura_manager.aura_data.get(user_id, 0)
        bot_balance = aura_manager.aura_data.get(bot_id_str, 0)

        # FINAL UI UPDATE
        finalEmbed = discord.Embed(title=f"Blackjack - {result}", color=color)
        finalEmbed.add_field(name="Your Hand", value=f"{playerHand}\nScore: {playerFinal}")
        finalEmbed.add_field(name="Dealer Hand", value=f"{dealerHand}\nScore: {dealerFinal}")
        
        await msg.edit(embed=finalEmbed, view=None)

        status_msg = f"{ctx.author.mention} > New Balance: `{new_balance:,} Aura`"
        
        if change < 0:
            status_msg += f"\n`{amount:,}` aura added to the bank."
            
        await ctx.send(status_msg)
    except Exception as e:
        log(f"Blackjack Error: {e}", "ERROR")
    finally:
        aura_manager.unlockUser(ctx.author.id, name=ctx.author.display_name)

@bot.command(aliases=['hl'])
async def higherlower(ctx, amount: str):
    authorName = str(ctx.author)
    user_id = str(ctx.author.id)

    if aura_manager.isBusy(ctx.author.id):
        return await ctx.send("Finish your current game first!")

    currentAura = aura_manager.aura_data.get(user_id, 0)

    # Bet Amount Logic
    if amount.lower() == "all":
        amount = currentAura
    elif amount.lower() == "half":
        amount = currentAura // 2
    else:
        try:
            amount = int(amount)
        except ValueError:
            return await ctx.send("Please enter a valid number, 'half', or 'all'.")

    if amount < 5:
        return await ctx.send("The minimum bet for Higher/Lower is **5** Aura.")
    if currentAura < amount:
        return await ctx.send(f"You Only Have **{currentAura:,}** Aura")

    # Game Setup
    MULT = [1.15, 1.15, 1.25, 1.30, 1.40]
    PAYOUTS = [1.15, 1.32, 1.65, 2.15, 3.01]
    dice = random.randint(1, 100)
    pot = amount
    turn = 0
    playing = True
    
    aura_manager.lockUser(ctx.author.id, name=ctx.author.display_name)
    log(f"HL Game started for {authorName.capitalize()} for {amount:,} aura", "HL_INFO")

    try:
        embed = discord.Embed(title="Higher or Lower", color=0x2b2d31)
        embed.add_field(name="Current Dice", value=f"**{dice}**", inline=True)
        embed.add_field(name="Current Pot", value=f"**{pot:,}** Aura", inline=True)
        embed.set_footer(text=f"Round: {turn + 1}/5 | Next Multiplier: {PAYOUTS[turn]}x | Buy-in: {amount:,}")
        
        view = higherLowerEmbed(ctx.author)
        msg = await ctx.send(f"{ctx.author.mention} starting Higher/Lower!", embed=embed, view=view)

        while playing:
            await view.wait()

            # Timeout Logic
            if view.choice is None:
                aura_manager.update_aura(ctx.author.id, -amount, ctx.author.display_name)
                aura_manager.update_aura(bot.user.id, +amount, "The House") 

                aura_manager.save_json(aura_manager.AURA_FILE, aura_manager.aura_data)
                log(f"{authorName.capitalize()} HL Timed Out", "HIGHERLOWER")
                await msg.edit(content=f"**Timed out!** You lost **{amount:,}** Aura.", embed=None, view=None)
                # await ctx.send(f"`{amount:,}` aura has been added to the bank. ")

                await ctx.send(f"")
                playing = False
                break

            # Cash Out Logic
            if view.choice == "quit":
                if turn >= 2:
                    profit = pot - amount
                    if profit != 0:
                        aura_manager.update_aura(ctx.author.id, profit, ctx.author.display_name)
                        aura_manager.save_json(aura_manager.AURA_FILE, aura_manager.aura_data)
                    
                    log(f"{authorName.capitalize()} cashed out HL on round {turn} at {pot:,}", "HIGHERLOWER")
                    embed.title = "Cashed Out!"
                    embed.color = 0x6dab18
                    embed.description = f"You walked away with **{pot:,}** Aura."
                    await msg.edit(content=None, embed=embed, view=None)
                    playing = False
                    break
                else:
                    embed.description = f"Nah you can't quit until you make it to round 3."
                    view = higherLowerEmbed(ctx.author)
                    await msg.edit(embed=embed, view=view)
                    continue
                
            # Roll Logic
            roll = random.randint(1, 100)
            won = (view.choice == "higher" and roll > dice) or (view.choice == "lower" and roll < dice)
            embed.description = f"[{dice}] -> [{roll}]\n"

            if roll == dice:
                embed.description = f"TIE! Go again."
                embed.set_footer(text=f"Rolled a {roll}: Tie! Try again.")
                view = higherLowerEmbed(ctx.author)
                await msg.edit(embed=embed, view=view)
                continue

            if won:
                pot = ceil(pot * MULT[turn])
                turn += 1
                dice = roll
                
                if turn >= len(MULT): # Max Rounds Reached
                    log(f"{authorName.capitalize()} Reached round 5.", "HIGHERLOWER")
                    profit = pot - amount
                    aura_manager.update_aura(ctx.author.id, profit, ctx.author.display_name)
                    aura_manager.save_json(aura_manager.AURA_FILE, aura_manager.aura_data)
                    
                    embed.title = "MAX WINS REACHED!"
                    embed.color = 0x6dab18
                    embed.set_field_at(0, name="Final Dice", value=f"**{roll}**")
                    embed.set_field_at(1, name="Final Payout", value=f"**{pot:,}** Aura")
                    embed.set_footer(text=f"Game Completed | Multiplier: {PAYOUTS[-1]}x | Buy-in: {amount:,}")
                    await msg.edit(content=None, embed=embed, view=None)
                    playing = False
                else:
                    embed.description += f"It was {view.choice}. Good job. Again! :smiling_imp:"
                    embed.set_field_at(0, name="Current Dice", value=f"**{dice}**")
                    embed.set_field_at(1, name="Current Pot", value=f"**{pot:,}** Aura")
                    embed.set_footer(text=f"Round: {turn + 1}/5 | Next Multiplier: {PAYOUTS[turn]}x | Buy-in: {amount:,}")
                    view = higherLowerEmbed(ctx.author)
                    await msg.edit(embed=embed, view=view)

            else:
                # Loss Logic
                aura_manager.update_aura(ctx.author.id, -amount, ctx.author.display_name)
                aura_manager.update_aura(bot.user.id, +amount, "The House")

                aura_manager.save_json(aura_manager.AURA_FILE, aura_manager.aura_data)
                
                log(f"{authorName.capitalize()} lost HL game.", "HIGHERLOWER")
                embed.title = "YOU LOSE!"
                embed.color = 0x992d22
                embed.description += f"Aww you lost **{amount:,}** Aura."
                embed.set_footer(text=f"Round: {turn + 1}/5 | Pot lost: {pot} | Buy-in: {amount:,}")
                embed.clear_fields()
                await msg.edit(content=None, embed=embed, view=None)
                playing = False

        # Final balance update
        new_balance = aura_manager.aura_data.get(user_id, 0)
        await ctx.send(f"{ctx.author.mention} > New Balance: `{new_balance:,} Aura`")
        # await ctx.send(f"`{amount:,}` aura has been added to the bank. ")


    except Exception as e:
        log(f"Higher/Lower Error: {e}", "ERROR")
    finally:
        aura_manager.unlockUser(ctx.author.id, name=ctx.author.display_name)

@bot.command(aliases=['rps'])
async def rockPaperScissors(ctx, opponent: Optional[discord.Member] = None, amount: str = 0):
    userID =  str(ctx.author.id)
    vsUser = False

    if aura_manager.isBusy(ctx.author.id):
        return await ctx.send("Finish your current game first!")
    
    if isinstance(opponent, str) and amount == "0":
        amount = opponent
        opponent = None
    
    currentAura = aura_manager.aura_data.get(userID, 0)

    if isinstance(amount, str):
        if amount.lower() == "all":
            amount = currentAura
        elif amount.lower() == "half":
            amount = currentAura // 2
        else:
            try:
                amount = int(amount)
            except ValueError:
                return await ctx.send("Please enter a valid number, 'half' or 'all'." )
            
        if amount <= 0:
            return await ctx.send("You must enter a valid amount!")
        
        if currentAura < amount:
            return await ctx.send(f"You only have **{currentAura}** Aura.")
        
    winMap = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
    emojis = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
        
    # Challenge Logic
    if opponent:
        if opponent.id == ctx.author.id:
            return await ctx.send("You can't challenge yourself...")
        if opponent.bot:
            return await ctx.send("Don't ping me to challenge the house!")
        
        oppAura = aura_manager.aura_data.get(str(opponent.id), 0)
        if oppAura < amount:
            return await ctx.send(f"{opponent.mention} doesn't have enough aura 🤣 🫵")
        
        if aura_manager.isBusy(opponent.id):
            return await ctx.send(f"**{opponent.display_name}** is already in a game")
        
        # Send Challenge Embed
        aura_manager.lockUser(ctx.author.id, name=ctx.author.display_name)  # Lock author while challenging
        log(f"{ctx.author.display_name} Challenged {opponent.display_name} to RPS | Bet: {amount:,} Aura", "RPS_DUEL")
        view = rpsChallengeEmbed(ctx.author, opponent, amount)
        embed = discord.Embed(
            title = "RPS Challenge",
            description=f"{ctx.author.mention} has challenged {opponent.mention} for `{amount:,} Aura`",
            color=0xFFFFFF
        )
        msg = await ctx.send(content=opponent.mention, embed=embed, view=view)

        await view.wait()

        if not view.accepted:
            log(f"{opponent.display_name} Declined duel against {ctx.author.display_name}", "RPS_DUEL")
            aura_manager.unlockUser(ctx.author.id, name=ctx.author.display_name)
            return await ctx.send("Challenge Declined or Timed Out..")
        

        # PvP Logic
        log(f"{opponent.display_name} Accepted duel against {ctx.author.display_name} | Bet: {amount:,} Aura.", "RPS_DUEL")
        aura_manager.lockUser(opponent.id, name=opponent.display_name)
        
        try:
            pvpView = rpsPvPEmbed(ctx.author, opponent, amount)

            pvpEmbed = discord.Embed(title="RPS Duel", color=0xFFFFFF)
            pvpEmbed.add_field(name=ctx.author.display_name, value="Selecting...", inline=True)
            pvpEmbed.add_field(name="vs", value="|", inline=True)
            pvpEmbed.add_field(name=opponent.display_name, value="Selecting...", inline=True)

            await msg.edit(content=None, embed=pvpEmbed, view=pvpView)

            await pvpView.wait()

            if pvpView.p1Choice and pvpView.p2Choice:
                p1c, p2c = pvpView.p1Choice, pvpView.p2Choice

                if p1c == p2c:
                    resultText = (f"It was a **TIE**.")
                    log(f"Game: {ctx.author.display_name} vs. {opponent.display_name} | Bet: {amount:,} Aura | Winner: TIE", "RPS_DUEL")
                    color = 0x7289da

                    winMsg = (f"`Game Tied.`")
                    balMsg = (f"{ctx.author.mention}> New Balance: `{currentAura}` | {opponent.mention}> New Balance: `{oppAura}`")

                    
            
                elif winMap[p1c] == p2c:
                    resultText = (f"{ctx.author.display_name} **WINS**.")
                    log(f"Game: {ctx.author.display_name} vs. {opponent.display_name} | Bet: {amount:,} Aura | Winner: {ctx.author.display_name}", "RPS_DUEL")
                    color = 0x6dab18
                    aura_manager.update_aura(ctx.author.id, amount, ctx.author.display_name)
                    aura_manager.update_aura(opponent.id, -amount, opponent.display_name)
                    
                    # Aura Update
                    p1new = aura_manager.aura_data.get(str(ctx.author.id), 0)
                    p2new = aura_manager.aura_data.get(str(opponent.id), 0)

                    #Winstreak Update
                    p1Streak = aura_manager.updateWinstreak(ctx.author.id, True)
                    p2Streak = aura_manager.updateWinstreak(opponent.id, False)
                    
                    winMsg = (f"`{ctx.author.display_name} took {amount:,} Aura from {opponent.display_name}`\nStreak: {p1Streak}")
                    balMsg = (f"{ctx.author.mention}> New Balance: `{p1new}` | {opponent.mention}> New Balance: `{p2new}`")
                    streakMsg = (f"🔥 {ctx.author.display_name}'s Winstreak: {p1Streak}")

                
                else:
                    resultText = (f"{opponent.display_name} **WINS**")
                    log(f"Game: {ctx.author.display_name} vs. {opponent.display_name} | Bet: {amount:,} Aura | Winner: {opponent.display_name}", "RPS_DUEL")
                    color = 0x992d22
                    aura_manager.update_aura(ctx.author.id, -amount, ctx.author.display_name)
                    aura_manager.update_aura(opponent.id, amount, opponent.display_name)

                    # Aura Update
                    p1new = aura_manager.aura_data.get(str(ctx.author.id), 0)
                    p2new = aura_manager.aura_data.get(str(opponent.id), 0)

                    #Winstreak Update
                    p2Streak = aura_manager.updateWinstreak(opponent.id, True)
                    p1Streak = aura_manager.updateWinstreak(ctx.author.id, False)

                    winMsg = (f"`{opponent.display_name} took {amount:,} Aura from {ctx.author.display_name}`")
                    balMsg = (f"{ctx.author.mention}> New Balance: `{p1new:,}` | {opponent.mention}> New Balance: `{p2new:,}`")
                    streakMsg = (f"🔥 {opponent.display_name}'s Winstreak: {p2Streak}")


                aura_manager.save_json(aura_manager.AURA_FILE, aura_manager.aura_data)

                # Winner Reveal
                final = discord.Embed(title=resultText, color=color)
                final.add_field(name=ctx.author.display_name, value=f"{emojis[p1c]} {p1c.capitalize()}", inline=True)
                final.add_field(name="vs", value="|", inline=True)
                final.add_field(name=opponent.display_name, value=f"{emojis[p2c]} {p2c.capitalize()}", inline=True)

                await msg.edit(embed=final, view=None)
                await ctx.send(f"{winMsg}")
                await ctx.send(f"{balMsg}")
                await ctx.send(f"{streakMsg}")

            else:
                await msg.edit(content="Duel Timed Out..", embed=None, view=None)
                log(f"Game: {ctx.author.display_name} vs. {opponent.display_name} | Bet: {amount:,} Aura | Status: Timed Out", "RPS_DUEL")


        finally:
            aura_manager.unlockUser(ctx.author.id, name=ctx.author.display_name)
            aura_manager.unlockUser(opponent.id, name=opponent.display_name)

        return

    # vs Bot  
    #if amount <= 0:
    #    return await ctx.send("You must enter a valid amount!")
    #if currentAura < amount:
    #    return await ctx.send(f"You Only Have **{currentAura:,}** Aura")
    
    #Lock user
    aura_manager.lockUser(ctx.author.id, name = ctx.author.display_name)
    log(f"{ctx.author.display_name} Started RPS game against The House", "RPS")



    embed = discord.Embed(title="Rock Paper Scissors", color=0xFFFFFF)
    embed.add_field(name=f"{ctx.author.display_name}", value="Selecting...", inline=True)
    embed.add_field(name="vs", value="|", inline=True)
    embed.add_field(name="The House", value="Thinking...", inline=True)
    embed.set_footer(text=f"Stake: {amount:,} Aura")


    view = rockPaperScissorsEmbed(ctx.author, amount)
    msg = await ctx.send(embed=embed, view=view)
    
    await view.wait()



        

    try:
        # Timeout Logic
        if view.choice is None:
            aura_manager.update_aura(ctx.author.id, -amount, ctx.author.display_name)
            aura_manager.update_aura(bot.user.id, +amount, "The House")
            aura_manager.save_json(aura_manager.AURA_FILE, aura_manager.aura_data)
            log(f"{ctx.author.display_name} timed out. Lost {amount:,} aura", "RPS")

            embed.description = "**Game Cancelled: Timed Out**"
            embed.color = 0xFFFFFF
            return await msg.edit(embed=embed, view=None)
        

        botChoice = random.choice(["rock", "paper", "scissors"])
        userChoice = view.choice


        # Determine Winner
        # 0 = Tie, 1 = Win, 2 = Lose
        winMap = {"rock": "scissors", "paper": "rock", "scissors": "paper"}

        if userChoice == botChoice:
            resultText = (f"It was a **TIE**. We both chose {userChoice}")
            log(f"Game tied for {ctx.author.display_name}. Returning {amount:,} aura", "RPS")
            change = 0
            color = 0x7289da
            
    
        elif winMap[userChoice] == botChoice:
            resultText = (f"You **WIN**. {userChoice} beats {botChoice}")
            log(f"{ctx.author.display_name} Won {amount:,} aura", "RPS")
            change = amount
            color = 0x6dab18
        
        else:
            resultText = (f"You **LOSE**. {botChoice} beats {userChoice}")
            log(f"{ctx.author.display_name} Lost {amount:,} aura", "RPS")
            change = -amount
            color = 0x992d22
            aura_manager.update_aura(bot.user.id, +amount, "The House")

        if change != 0:
            aura_manager.update_aura(ctx.author.id, change, ctx.author.display_name)

        aura_manager.save_json(aura_manager.AURA_FILE, aura_manager.aura_data)


        finalEmbed = discord.Embed(title=resultText, color=color)
        finalEmbed.add_field(
            name=f"{ctx.author.display_name}", 
            value=f"{emojis[userChoice]} - **{userChoice.capitalize()}**", 
            inline=True
        )
        finalEmbed.add_field(name="vs", value=" |", inline=True)
        finalEmbed.add_field(
            name="The House", 
            value=f"{emojis[botChoice]} - **{botChoice.capitalize()}**", 
            inline=True
        )
        
        newBal = aura_manager.aura_data.get(userID, 0)
        finalEmbed.set_footer(text=f"Bet: {amount:,}")

        await msg.edit(content=None, embed=finalEmbed, view=None)
        await ctx.send(f"{ctx.author.mention} > New Balance: `{newBal:,} Aura`")

    finally:
        aura_manager.unlockUser(ctx.author.id, name=ctx.author.display_name)
