# modules/fishing.py
import copy
import discord
import random
import asyncio
import json
import os
import uuid
from modules.bot_setup import bot
from modules import aura_manager
from modules.aura_manager import update_aura, aura_data, save_json, AURA_FILE
from modules.utils import log

FISHING_FILE = os.path.join("data", "fishing.json")

# ---- In-memory fishing inventories ----
fishing_inventories: dict[str, list[dict]] = {}

# ---- Separate fishing lock (independent from game lock) ----
_fishing_users: set[int] = set()

def isFishing(user_id: int) -> bool:
    return user_id in _fishing_users

def startFishing(user_id: int, name: str = "Unknown") -> None:
    _fishing_users.add(user_id)
    log(f"{name} started fishing (locked)", "FISHING")

def stopFishing(user_id: int, name: str = "Unknown") -> None:
    _fishing_users.discard(user_id)
    log(f"{name} stopped fishing (unlocked)", "FISHING")

# ---- Fish tables ----
FISH_TYPES = {
    "Bass":      {"base": 5,  "rarity_weight": 25},
    "Trout":     {"base": 5,  "rarity_weight": 25},
    "Catfish":   {"base": 4,  "rarity_weight": 20},
    "Cod":       {"base": 4,  "rarity_weight": 15},
    "Salmon":    {"base": 7,  "rarity_weight": 10},
    "Tuna":      {"base": 10, "rarity_weight": 4},
    "Swordfish": {"base": 15, "rarity_weight": 1},
}

SIZES = [
    {"label": "Small",     "range": (1, 5),   "mult": 0.6},
    {"label": "Medium",    "range": (6, 15),  "mult": 1.0},
    {"label": "Large",     "range": (16, 30), "mult": 1.5},
    {"label": "Huge",      "range": (31, 50), "mult": 2.2},
    {"label": "Legendary", "range": (51, 99), "mult": 3.5},
]

SIZE_WEIGHTS = [40, 30, 18, 9, 3]

COLORS_COMMON = ["Gray", "Silver", "Brown", "Olive", "Dark Green"]
COLORS_RARE   = ["Golden", "Blue", "Rainbow", "Crimson", "Albino", "Midnight Black"]

SPECIAL_FEATURES = [
    "Glows in the Dark",
    "Huge Lips",
    "Big Eyes",
    "Enormous Fins",
    "Striped Pattern",
    "Spotted Pattern",
    "Sparkles",
    "Two-Headed",
    "Extra Fins",
    "Metallic Sheen",
    "Electric Blue Stripes",
    "Battle Scars",
]

RARITY_CONFIG = {
    "Common":    {"weight": 70, "color_pool": COLORS_COMMON,                  "max_features": 0, "mult": 1.0, "emoji": "🐟"},
    "Uncommon":  {"weight": 20, "color_pool": COLORS_COMMON + COLORS_RARE[:2],"max_features": 1, "mult": 2.0, "emoji": "🐠"},
    "Rare":      {"weight": 8,  "color_pool": COLORS_RARE,                    "max_features": 2, "mult": 4.5, "emoji": "🦈"},
    "Legendary": {"weight": 2,  "color_pool": COLORS_RARE,                    "max_features": 4, "mult": 8.0, "emoji": "✨"},
}

RARITY_NAMES   = list(RARITY_CONFIG.keys())
RARITY_WEIGHTS = [RARITY_CONFIG[r]["weight"] for r in RARITY_NAMES]

RARITY_COLORS = {
    "Common":    0x808080,
    "Uncommon":  0x1eff00,
    "Rare":      0x0070dd,
    "Legendary": 0xff8000,
    "BOSS":      0xff0000,
    "ADMIN":     0x9b59b6,
}

# ---- Boss fish table ----
BOSS_FISH = [
    {
        "type": "The Leviathan",
        "size": "Colossal", "weight": 999, "color": "Obsidian",
        "features": ["Ancient Runes", "Glows in the Dark", "Two-Headed", "Enormous Fins"],
        "rarity": "BOSS", "emoji": "🐉", "value": 100, "pinned": False, "isBossFish": True,
    },
    {
        "type": "Grandpa Bass",
        "size": "Huge", "weight": 847, "color": "Mossy Green",
        "features": ["Battle Scars", "Big Eyes", "Metallic Sheen"],
        "rarity": "BOSS", "emoji": "👴", "value": 100, "pinned": False, "isBossFish": True,
    },
    {
        "type": "The Void Eel",
        "size": "Legendary", "weight": 312, "color": "Midnight Black",
        "features": ["Glows in the Dark", "Electric Blue Stripes", "Sparkles"],
        "rarity": "BOSS", "emoji": "🌑", "value": 100, "pinned": False, "isBossFish": True,
    },
    {
        "type": "Crimson Kraken",
        "size": "Colossal", "weight": 1200, "color": "Crimson",
        "features": ["Extra Fins", "Enormous Fins", "Battle Scars", "Sparkles"],
        "rarity": "BOSS", "emoji": "🦑", "value": 100, "pinned": False, "isBossFish": True,
    },
    {
        "type": "The Golden Carp",
        "size": "Large", "weight": 88, "color": "Golden",
        "features": ["Metallic Sheen", "Sparkles"],
        "rarity": "BOSS", "emoji": "✨", "value": 100, "pinned": False, "isBossFish": True,
    },
]

def generate_boss_fish() -> dict:
    return copy.deepcopy(random.choice(BOSS_FISH))


# ---- Admin fish (spawned via ?fish_boss, distinct from real boss events) ----
ADMIN_FISH_NAMES = ["Blizzy Carp", "Donabass"]

def generate_admin_fish() -> dict:
    """Generate a unique admin-spawned fish with randomised appearance."""
    name         = random.choice(ADMIN_FISH_NAMES)
    size_data    = random.choices(SIZES, weights=SIZE_WEIGHTS, k=1)[0]
    weight_lbs   = random.randint(*size_data["range"])
    color        = random.choice(COLORS_COMMON + COLORS_RARE)
    num_features = random.randint(1, 3)
    features     = random.sample(SPECIAL_FEATURES, k=num_features)
    return {
        "id":          str(uuid.uuid4())[:8],
        "type":        name,
        "size":        size_data["label"],
        "weight":      weight_lbs,
        "color":       color,
        "features":    features,
        "rarity":      "ADMIN",
        "emoji":       "👑",
        "value":       15,
        "pinned":      False,
        "isBossFish":  False,
        "isAdminFish": True,   # blocks trading
    }


# ---- Fish generation ----
def generate_fish() -> dict:
    rarity   = random.choices(RARITY_NAMES, weights=RARITY_WEIGHTS, k=1)[0]
    cfg      = RARITY_CONFIG[rarity]
    fish_names   = list(FISH_TYPES.keys())
    fish_weights = [FISH_TYPES[f]["rarity_weight"] for f in fish_names]
    fish_type    = random.choices(fish_names, weights=fish_weights, k=1)[0]
    base_value   = FISH_TYPES[fish_type]["base"]
    size_data    = random.choices(SIZES, weights=SIZE_WEIGHTS, k=1)[0]
    weight_lbs   = random.randint(*size_data["range"])
    color        = random.choice(cfg["color_pool"])
    num_features = random.randint(0, cfg["max_features"]) if cfg["max_features"] > 0 else 0
    features     = random.sample(SPECIAL_FEATURES, k=min(num_features, len(SPECIAL_FEATURES)))
    feature_bonus = 1.0 + (len(features) * 0.25)
    value = max(1, int(base_value * size_data["mult"] * cfg["mult"] * feature_bonus) + random.randint(-1, 2))
    return {
        "id":         str(uuid.uuid4())[:8],
        "type":       fish_type,
        "size":       size_data["label"],
        "weight":     weight_lbs,
        "color":      color,
        "features":   features,
        "rarity":     rarity,
        "emoji":      cfg["emoji"],
        "value":      value,
        "pinned":     False,
        "isBossFish": False,
    }


def fish_summary(fish: dict, index: int | None = None) -> str:
    features_text = f" | {', '.join(fish['features'])}" if fish["features"] else ""
    pin_icon  = "📌 " if fish.get("pinned") else ""
    boss_icon = "💀 " if fish.get("isBossFish") else ""
    prefix    = f"**#{index}** " if index is not None else ""
    return (
        f"{prefix}{pin_icon}{boss_icon}{fish['emoji']} **{fish['color']} {fish['type']}** "
        f"({fish['rarity']}) — {fish['size']}, {fish['weight']} lbs{features_text} "
        f"— `{fish['value']:,} aura`"
    )


def fish_embed(fish: dict, title: str) -> discord.Embed:
    """Full-detail embed for a single fish."""
    embed = discord.Embed(title=title, color=RARITY_COLORS.get(fish["rarity"], 0xffffff))
    embed.add_field(name="Type",   value=fish["type"],  inline=True)
    embed.add_field(name="Rarity", value=fish["rarity"],inline=True)
    embed.add_field(name="Color",  value=fish["color"], inline=True)
    embed.add_field(name="Size",   value=f"{fish['size']} ({fish['weight']} lbs)", inline=True)
    embed.add_field(name="Value",  value=f"`{fish['value']:,}` aura", inline=True)
    if fish.get("features"):
        embed.add_field(name="Special", value=", ".join(fish["features"]), inline=False)
    return embed


# ---- Persistence ----
def load_fishing_inventories() -> None:
    global fishing_inventories
    if os.path.exists(FISHING_FILE):
        try:
            with open(FISHING_FILE, "r", encoding="utf-8") as f:
                fishing_inventories = json.load(f)
            log("Fishing inventories loaded", "SUCCESS" if fishing_inventories else "WARNING")
        except Exception as e:
            log(f"Failed to load fishing.json: {e}", "ERROR")
            fishing_inventories = {}
    else:
        fishing_inventories = {}

# Load immediately on import so inventory persists across reboots
load_fishing_inventories()


def save_fishing_inventories() -> None:
    with open(FISHING_FILE, "w", encoding="utf-8") as f:
        json.dump(fishing_inventories, f, indent=4)
    log("Fishing inventories saved", "SUCCESS")


def get_inventory(user_id: int) -> list[dict]:
    return fishing_inventories.get(str(user_id), [])


def add_fish(user_id: int, fish: dict) -> None:
    uid = str(user_id)
    if uid not in fishing_inventories:
        fishing_inventories[uid] = []
    fishing_inventories[uid].append(fish)
    save_fishing_inventories()


def remove_fish(user_id: int, index: int) -> dict | None:
    uid = str(user_id)
    inv = fishing_inventories.get(uid, [])
    i = index - 1
    if 0 <= i < len(inv):
        fish = inv.pop(i)
        save_fishing_inventories()
        return fish
    return None


# ============================================================
# UI VIEWS
# ============================================================

class FishingButton(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=5)
        self.user   = user
        self.caught = False

    @discord.ui.button(label="🎣 Reel it in!", style=discord.ButtonStyle.success)
    async def reel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("That's not your fishing rod!", ephemeral=True)
        self.caught = True
        await interaction.response.defer()
        self.stop()

    async def on_timeout(self):
        if hasattr(self, "message") and self.message:
            try:
                await self.message.edit(content="🐟 The fish got away...", view=None)
            except discord.NotFound:
                pass


class BossEventView(discord.ui.View):
    """3 unique players must click within 30 seconds to catch the boss."""
    REQUIRED = 3

    def __init__(self, fish_obj: dict, channel):
        super().__init__(timeout=30)
        self.fish_obj  = fish_obj
        self.channel   = channel
        self.clickers: list[discord.User] = []   # ordered list of unique clickers
        self.message   = None

    def _build_embed(self) -> discord.Embed:
        count = len(self.clickers)
        bar   = "🟩" * count + "⬜" * (self.REQUIRED - count)
        names = ", ".join(u.display_name for u in self.clickers) if self.clickers else "*nobody yet*"
        embed = discord.Embed(
            title=f"{self.fish_obj['emoji']} A BOSS FISH HAS APPEARED!",
            description=(
                f"**{self.fish_obj['color']} {self.fish_obj['type']}**\n"
                f"3 anglers must click to reel it in!\n\n"
                f"{bar}  **{count}/{self.REQUIRED}**\n"
                f"Participants: {names}"
            ),
            color=0xff0000,
        )
        embed.add_field(name="Size",    value=f"{self.fish_obj['size']} ({self.fish_obj['weight']} lbs)", inline=True)
        embed.add_field(name="Value",   value=f"`{self.fish_obj['value']:,}` aura each",                  inline=True)
        embed.add_field(name="Special", value=", ".join(self.fish_obj["features"]),                       inline=False)
        embed.set_footer(text="30 seconds to catch it!")
        return embed

    @discord.ui.button(label="🎣 Help reel it in!", style=discord.ButtonStyle.danger)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user

        if any(u.id == user.id for u in self.clickers):
            return await interaction.response.send_message("You're already helping!", ephemeral=True)

        self.clickers.append(user)
        count = len(self.clickers)
        log(f"{user.display_name} joined boss event ({count}/{self.REQUIRED})", "FISHING")

        if count < self.REQUIRED:
            # Update the counter embed
            await interaction.response.edit_message(embed=self._build_embed(), view=self)
        else:
            # All 3 clicked — success!
            await interaction.response.defer()
            self.stop()

    async def on_timeout(self):
        if self.message:
            try:
                count = len(self.clickers)
                embed = discord.Embed(
                    title="🐟 The boss fish escaped...",
                    description=f"Only **{count}/{self.REQUIRED}** anglers showed up in time.",
                    color=0x555555,
                )
                await self.message.edit(embed=embed, view=None)
            except discord.NotFound:
                pass


async def run_boss_event(channel, fish_obj: dict) -> None:
    """Spawn the boss event UI, wait, then distribute fish or report failure."""
    view = BossEventView(fish_obj, channel)
    msg  = await channel.send(
        "@here 🐉 **A LEGENDARY BOSS FISH HAS APPEARED!** 🐉",
        embed=view._build_embed(),
        view=view,
    )
    view.message = msg
    await view.wait()

    if len(view.clickers) >= BossEventView.REQUIRED:
        # Give fish to all participants
        winners = view.clickers[:BossEventView.REQUIRED]
        mentions = " ".join(u.mention for u in winners)
        for user in winners:
            prize = copy.deepcopy(fish_obj)
            add_fish(user.id, prize)

        result_embed = discord.Embed(
            title=f"{fish_obj['emoji']} Boss Fish Caught!",
            description=f"{mentions} reeled in the **{fish_obj['color']} {fish_obj['type']}**!\nEach angler received it in their inventory.",
            color=0xffd700,
        )
        result_embed.add_field(name="Value", value=f"`{fish_obj['value']:,}` aura each")
        await channel.send(embed=result_embed)
        log(f"Boss event won: {fish_obj['type']} given to {[u.display_name for u in winners]}", "FISHING")
    else:
        log(f"Boss event failed: only {len(view.clickers)}/{BossEventView.REQUIRED} clicked", "FISHING")


class InventoryView(discord.ui.View):
    def __init__(self, requester, target, pages, total_value, total_fish):
        super().__init__(timeout=120)
        self.requester  = requester
        self.target     = target
        self.pages      = pages
        self.total_value = total_value
        self.total_fish = total_fish
        self.page       = 0

    def build_embed(self):
        embed = discord.Embed(
            title=f"🎣 {self.target.display_name}'s Fish Tank",
            description=self.pages[self.page],
            color=0x1e90ff,
        )
        embed.set_footer(
            text=f"Page {self.page + 1}/{len(self.pages)} | "
                 f"{self.total_fish} fish | Total value: {self.total_value:,} aura"
        )
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.requester.id:
            return await interaction.response.send_message("Not your inventory view!", ephemeral=True)
        if self.page > 0:
            self.page -= 1
            await interaction.response.edit_message(embed=self.build_embed(), view=self)
        else:
            await interaction.response.send_message("Already on the first page!", ephemeral=True)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.green)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.requester.id:
            return await interaction.response.send_message("Not your inventory view!", ephemeral=True)
        if self.page < len(self.pages) - 1:
            self.page += 1
            await interaction.response.edit_message(embed=self.build_embed(), view=self)
        else:
            await interaction.response.send_message("Already on the last page!", ephemeral=True)


class SellPinnedConfirmView(discord.ui.View):
    """Confirmation prompt when selling a pinned fish individually."""
    def __init__(self, user):
        super().__init__(timeout=30)
        self.user      = user
        self.confirmed = False

    @discord.ui.button(label="Yes, sell it", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("Not your fish!", ephemeral=True)
        self.confirmed = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("Not your fish!", ephemeral=True)
        await interaction.response.defer()
        self.stop()


class TradeConfirmView(discord.ui.View):
    """Both parties must accept the trade."""
    def __init__(self, proposer, recipient):
        super().__init__(timeout=60)
        self.proposer    = proposer
        self.recipient   = recipient
        self.p_accepted  = False
        self.r_accepted  = False

    def _both_accepted(self):
        return self.p_accepted and self.r_accepted

    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id
        if uid == self.proposer.id:
            self.p_accepted = True
        elif uid == self.recipient.id:
            self.r_accepted = True
        else:
            return await interaction.response.send_message("This trade isn't for you!", ephemeral=True)

        if self._both_accepted():
            await interaction.response.defer()
            self.stop()
        else:
            who = interaction.user.display_name
            await interaction.response.send_message(f"✅ {who} accepted. Waiting for the other party...", ephemeral=False)

    @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id
        if uid not in (self.proposer.id, self.recipient.id):
            return await interaction.response.send_message("This trade isn't for you!", ephemeral=True)
        self.p_accepted = False
        self.r_accepted = False
        await interaction.response.defer()
        self.stop()


# ============================================================
# COMMANDS
# ============================================================

@bot.command(aliases=["cast"])
async def fish(ctx):
    """Start a fishing session. A button will appear at a random time."""
    user_id = ctx.author.id

    if isFishing(user_id):
        return await ctx.send("Your line is already in the water! Wait for a bite.")

    startFishing(user_id, name=ctx.author.display_name)

    try:
        wait_time = random.randint(5, 600)
        mins, secs = divmod(wait_time, 60)
        wait_str = f"{mins}m {secs}s" if mins else f"{secs}s"
        log(f"{ctx.author.display_name} cast their line — bite in {wait_str}", "FISHING")

        wait_msg = await ctx.send(f"🎣 {ctx.author.mention} cast their line... *(wait for it)*")
        await asyncio.sleep(wait_time)

        try:
            await wait_msg.delete()
        except discord.NotFound:
            pass

        view     = FishingButton(ctx.author)
        bite_msg = await ctx.send(
            f"🐟 {ctx.author.mention} **Something's on the line! REEL IT IN!**", view=view
        )
        view.message = bite_msg
        await view.wait()

        if not view.caught:
            log(f"{ctx.author.display_name} missed the fish", "FISHING")
            return

        # 1% chance of boss event on any catch
        if random.randint(1, 100) == 1:
            boss = generate_boss_fish()
            log(f"Boss event triggered by {ctx.author.display_name}!", "FISHING")
            await bite_msg.edit(
                content=f"⚠️ {ctx.author.mention} hooked something enormous... the line is pulling everyone in!",
                view=None,
            )
            await run_boss_event(ctx.channel, boss)
            return

        # Normal catch — show the catcher's name in the embed title
        fish_obj  = generate_fish()
        add_fish(user_id, fish_obj)
        inv_count = len(get_inventory(user_id))

        embed = fish_embed(fish_obj, f"{fish_obj['emoji']} {ctx.author.display_name} caught a fish!")
        embed.set_footer(text=f"Inventory: {inv_count} fish | Use ?sell to cash out")
        await bite_msg.edit(content=None, embed=embed, view=None)
        log(
            f"{ctx.author.display_name} caught a {fish_obj['rarity']} {fish_obj['color']} "
            f"{fish_obj['type']} worth {fish_obj['value']} aura", "FISHING"
        )

    except Exception as e:
        log(f"Fishing error: {e}", "ERROR")
        await ctx.send("Something went wrong while fishing. Try again!")
    finally:
        stopFishing(user_id, name=ctx.author.display_name)


@bot.command(aliases=["inv"])
async def inventory(ctx, member: discord.Member | None = None):
    """View your (or another user's) fish inventory."""
    target = member or ctx.author
    inv    = get_inventory(target.id)

    if not inv:
        msg = "Your fish tank is empty! Use `?fish` to catch some." if target == ctx.author \
              else f"{target.display_name} hasn't caught any fish yet."
        return await ctx.send(msg)

    per_page    = 10
    total_value = sum(f["value"] for f in inv)
    pages       = []
    for page in range((len(inv) - 1) // per_page + 1):
        start = page * per_page
        chunk = inv[start:start + per_page]
        lines = [fish_summary(f, index=start + i + 1) for i, f in enumerate(chunk)]
        pages.append("\n".join(lines))

    view  = InventoryView(ctx.author, target, pages, total_value, len(inv))
    await ctx.send(embed=view.build_embed(), view=view)


@bot.command()
async def sell(ctx, target: str = None):
    """?sell all | ?sell <number>"""
    user_id = ctx.author.id
    uid     = str(user_id)
    inv     = get_inventory(user_id)

    if not inv:
        return await ctx.send("You don't have any fish to sell! Go `?fish` first.")
    if target is None:
        return await ctx.send("Usage: `?sell all` or `?sell <number>`.")

    if target.lower() == "all":
        sellable     = [f for f in inv if not f.get("pinned")]
        pinned_count = len(inv) - len(sellable)

        if not sellable:
            return await ctx.send("All your fish are pinned! Use `?unpin <number>` first.")

        total      = sum(f["value"] for f in sellable)
        fish_count = len(sellable)
        fishing_inventories[uid] = [f for f in inv if f.get("pinned")]
        save_fishing_inventories()
        update_aura(user_id, total, ctx.author.display_name)
        save_json(AURA_FILE, aura_data)

        pin_note = f" ({pinned_count} pinned fish kept)" if pinned_count else ""
        embed = discord.Embed(
            title="🪙 Fish Sold!",
            description=f"Sold **{fish_count}** fish for **{total:,} aura**{pin_note}.",
            color=0xffd700,
        )
        embed.set_footer(text=f"New Balance: {aura_data.get(uid, 0):,} aura")
        await ctx.send(embed=embed)
        log(f"{ctx.author.display_name} sold {fish_count} fish for {total:,} aura", "FISHING")

    else:
        try:
            index = int(target)
        except ValueError:
            return await ctx.send("Please use `?sell all` or `?sell <number>`.")

        if index < 1 or index > len(inv):
            return await ctx.send(f"Invalid number. You have **{len(inv)}** fish.")

        fish_obj = inv[index - 1]

        # Pinned — ask for confirmation
        if fish_obj.get("pinned"):
            confirm_view = SellPinnedConfirmView(ctx.author)
            confirm_msg  = await ctx.send(
                f"⚠️ Fish #{index} is pinned ({fish_obj['emoji']} **{fish_obj['color']} {fish_obj['type']}**). "
                f"Are you sure you want to sell it for `{fish_obj['value']:,}` aura?",
                view=confirm_view,
            )
            await confirm_view.wait()
            await confirm_msg.delete()
            if not confirm_view.confirmed:
                return await ctx.send("Sale cancelled.")

        removed = remove_fish(user_id, index)
        if removed is None:
            return await ctx.send("Something went wrong. Try again.")

        update_aura(user_id, removed["value"], ctx.author.display_name)
        save_json(AURA_FILE, aura_data)

        embed = discord.Embed(
            title="🪙 Fish Sold!",
            description=(
                f"Sold {removed['emoji']} **{removed['color']} {removed['type']}** "
                f"({removed['rarity']}, {removed['size']}, {removed['weight']} lbs) "
                f"for **{removed['value']:,} aura**."
            ),
            color=0xffd700,
        )
        embed.set_footer(text=f"New Balance: {aura_data.get(uid, 0):,} aura | Remaining: {len(get_inventory(user_id))}")
        await ctx.send(embed=embed)
        log(f"{ctx.author.display_name} sold a {removed['rarity']} {removed['type']} for {removed['value']:,} aura", "FISHING")


@bot.command()
async def pin(ctx, index: int = None):
    """Pin a fish to protect it from ?sell all."""
    if index is None:
        return await ctx.send("Usage: `?pin <number>` — check numbers with `?inventory`.")
    inv = get_inventory(ctx.author.id)
    if not inv:
        return await ctx.send("You don't have any fish!")
    if index < 1 or index > len(inv):
        return await ctx.send(f"Invalid number. You have **{len(inv)}** fish.")
    fish_obj = inv[index - 1]
    if fish_obj.get("pinned"):
        return await ctx.send(f"Fish #{index} is already pinned.")
    fish_obj["pinned"] = True
    save_fishing_inventories()
    await ctx.send(f"📌 Pinned **{fish_obj['emoji']} {fish_obj['color']} {fish_obj['type']}** (#{index}).")
    log(f"{ctx.author.display_name} pinned fish #{index} ({fish_obj['type']})", "FISHING")


@bot.command()
async def unpin(ctx, index: int = None):
    """Unpin a fish so it can be sold."""
    if index is None:
        return await ctx.send("Usage: `?unpin <number>` — check numbers with `?inventory`.")
    inv = get_inventory(ctx.author.id)
    if not inv:
        return await ctx.send("You don't have any fish!")
    if index < 1 or index > len(inv):
        return await ctx.send(f"Invalid number. You have **{len(inv)}** fish.")
    fish_obj = inv[index - 1]
    if not fish_obj.get("pinned"):
        return await ctx.send(f"Fish #{index} isn't pinned.")
    fish_obj["pinned"] = False
    save_fishing_inventories()
    await ctx.send(f"📌 Unpinned **{fish_obj['emoji']} {fish_obj['color']} {fish_obj['type']}** (#{index}).")
    log(f"{ctx.author.display_name} unpinned fish #{index} ({fish_obj['type']})", "FISHING")


@bot.command()
async def aquarium(ctx, member: discord.Member | None = None):
    """Show pinned fish showcase. Up to 5 pinned fish displayed."""
    target  = member or ctx.author
    inv     = get_inventory(target.id)
    pinned  = [f for f in inv if f.get("pinned")]

    if not pinned:
        msg = "Your aquarium is empty! Use `?pin <number>` to showcase a fish." if target == ctx.author \
              else f"{target.display_name}'s aquarium is empty."
        return await ctx.send(msg)

    showcase = pinned[:5]
    embed = discord.Embed(
        title=f"🐠 {target.display_name}'s Aquarium",
        description=f"Showcasing **{len(showcase)}** fish" + (" *(showing first 5)*" if len(pinned) > 5 else ""),
        color=0x1e90ff,
    )
    for i, f in enumerate(showcase, start=1):
        boss_tag    = " 💀 BOSS" if f.get("isBossFish") else ""
        features_str = ", ".join(f["features"]) if f["features"] else "None"
        embed.add_field(
            name=f"{f['emoji']} #{i} — {f['color']} {f['type']}{boss_tag}",
            value=(
                f"**Rarity:** {f['rarity']}\n"
                f"**Size:** {f['size']} ({f['weight']} lbs)\n"
                f"**Special:** {features_str}\n"
                f"**Value:** `{f['value']:,}` aura"
            ),
            inline=True,
        )
    await ctx.send(embed=embed)


@bot.command()
async def trade(ctx, recipient: discord.Member, your_fish: int, their_fish_or_aura: str):
    """
    Trade a fish with another user.
    ?trade @user <your fish #> <their fish #>  — fish for fish
    ?trade @user <your fish #> 0               — give fish for free (no exchange)
    """
    proposer_id  = ctx.author.id
    recipient_id = recipient.id

    if recipient.bot:
        return await ctx.send("You can't trade with a bot!")
    if recipient_id == proposer_id:
        return await ctx.send("You can't trade with yourself!")
    if aura_manager.isBusy(proposer_id) or aura_manager.isBusy(recipient_id):
        return await ctx.send("One of you is currently in a game!")

    p_inv = get_inventory(proposer_id)
    r_inv = get_inventory(recipient_id)

    if not p_inv:
        return await ctx.send("You don't have any fish to trade!")
    if your_fish < 1 or your_fish > len(p_inv):
        return await ctx.send(f"Invalid fish number. You have **{len(p_inv)}** fish.")

    p_fish = p_inv[your_fish - 1]

    if p_fish.get("isAdminFish"):
        return await ctx.send("Admin fish can't be traded!")

    # Parse their_fish_or_aura as an integer (fish index or 0)
    try:
        their_val = int(their_fish_or_aura)
    except ValueError:
        return await ctx.send("Usage: `?trade @user <your fish #> <their fish # or 0 for free>`")

    # Determine trade type
    # 0  → give fish for free, no exchange
    # 1+ → fish-for-fish (their fish index)
    if their_val == 0:
        # Free gift — no exchange
        embed = discord.Embed(
            title="🎁 Gift Offer",
            description=(
                f"{ctx.author.mention} wants to give {recipient.mention} their "
                f"{p_fish['emoji']} **{p_fish['color']} {p_fish['type']}** "
                f"({p_fish['rarity']}, `{p_fish['value']:,}` aura) for **free**."
            ),
            color=0x9b59b6,
        )
        embed.set_footer(text="Both parties must accept within 60 seconds.")
        confirm_view = TradeConfirmView(ctx.author, recipient)
        trade_msg    = await ctx.send(content=recipient.mention, embed=embed, view=confirm_view)
        await confirm_view.wait()
        await trade_msg.edit(view=None)

        if not (confirm_view.p_accepted and confirm_view.r_accepted):
            return await ctx.send("Trade cancelled or timed out.")

        # Execute gift
        p_inv = get_inventory(proposer_id)
        if your_fish < 1 or your_fish > len(p_inv) or p_inv[your_fish - 1].get("type") != p_fish["type"]:
            return await ctx.send("Trade failed — inventory changed during negotiation.")

        removed = remove_fish(proposer_id, your_fish)
        removed["pinned"] = False
        add_fish(recipient_id, removed)
        await ctx.send(
            f"✅ {ctx.author.mention} gifted **{removed['color']} {removed['type']}** "
            f"to {recipient.mention}!"
        )
        log(f"Gift: {ctx.author.display_name} -> {recipient.display_name} ({removed['type']})", "FISHING")

    elif their_val >= 1:
        # Fish-for-fish
        if not r_inv:
            return await ctx.send(f"{recipient.display_name} doesn't have any fish!")
        if their_val > len(r_inv):
            return await ctx.send(f"Invalid fish number. {recipient.display_name} only has **{len(r_inv)}** fish.")

        r_fish = r_inv[their_val - 1]

        if r_fish.get("isAdminFish"):
            return await ctx.send("Admin fish can't be traded!")

        embed = discord.Embed(
            title="🔄 Trade Offer",
            description=(
                f"{ctx.author.mention} offers {p_fish['emoji']} **{p_fish['color']} {p_fish['type']}** "
                f"({p_fish['rarity']}, `{p_fish['value']:,}` aura)\n"
                f"For {r_fish['emoji']} **{r_fish['color']} {r_fish['type']}** "
                f"({r_fish['rarity']}, `{r_fish['value']:,}` aura) from {recipient.mention}"
            ),
            color=0x9b59b6,
        )
        embed.set_footer(text="Both parties must accept within 60 seconds.")
        confirm_view = TradeConfirmView(ctx.author, recipient)
        trade_msg    = await ctx.send(content=recipient.mention, embed=embed, view=confirm_view)
        await confirm_view.wait()
        await trade_msg.edit(view=None)

        if not (confirm_view.p_accepted and confirm_view.r_accepted):
            return await ctx.send("Trade cancelled or timed out.")

        # Execute fish-for-fish — re-fetch to catch any inventory changes
        p_inv = get_inventory(proposer_id)
        if your_fish < 1 or your_fish > len(p_inv) or p_inv[your_fish - 1].get("type") != p_fish["type"]:
            return await ctx.send("Trade failed — your inventory changed during negotiation.")
        r_inv = get_inventory(recipient_id)
        if their_val < 1 or their_val > len(r_inv):
            return await ctx.send("Trade failed — recipient's inventory changed.")

        p_removed = remove_fish(proposer_id, your_fish)
        r_removed = remove_fish(recipient_id, their_val)
        p_removed["pinned"] = False
        r_removed["pinned"] = False
        add_fish(recipient_id, p_removed)
        add_fish(proposer_id,  r_removed)
        await ctx.send(
            f"✅ Trade complete! {ctx.author.mention} got **{r_removed['color']} {r_removed['type']}**, "
            f"{recipient.mention} got **{p_removed['color']} {p_removed['type']}**."
        )
        log(f"Trade completed: {ctx.author.display_name} <-> {recipient.display_name}", "FISHING")

    else:
        return await ctx.send("Invalid value. Use a fish number (1+) or 0 to give for free.")


@bot.command()
async def fishpedia(ctx, member: discord.Member | None = None):
    """Show collection progress — which fish types you've caught."""
    target = member or ctx.author
    inv    = get_inventory(target.id)

    all_types    = list(FISH_TYPES.keys())
    caught_types = {f["type"] for f in inv}
    total        = len(all_types)
    caught_count = len(caught_types)
    pct          = caught_count / total * 100 if total > 0 else 0

    # Progress bar
    filled = int(pct / 10)
    bar    = "🟩" * filled + "⬜" * (10 - filled)

    # Stats
    rarest = None
    rarity_order = ["Legendary", "Rare", "Uncommon", "Common", "BOSS"]
    for rarity in rarity_order:
        match = [f for f in inv if f["rarity"] == rarity]
        if match:
            rarest = max(match, key=lambda f: f["value"])
            break

    biggest           = max(inv, key=lambda f: f["weight"]) if inv else None
    total_caught_ever = len(inv)

    embed = discord.Embed(
        title=f"📖 {target.display_name}'s Fishpedia",
        color=0x2ecc71,
    )
    embed.add_field(
        name="Collection Progress",
        value=f"{bar} **{caught_count}/{total}** types ({pct:.0f}%)",
        inline=False,
    )

    # Type checklist
    checklist = []
    for ft in all_types:
        icon = "✅" if ft in caught_types else "🔒"
        checklist.append(f"{icon} {ft}")
    embed.add_field(name="Fish Types", value="\n".join(checklist), inline=True)

    # Stats column
    stats = []
    if rarest:
        stats.append(f"**Rarest:** {rarest['emoji']} {rarest['color']} {rarest['type']} ({rarest['rarity']})")
    if biggest:
        stats.append(f"**Biggest:** {biggest['emoji']} {biggest['color']} {biggest['type']} ({biggest['weight']} lbs)")
    stats.append(f"**Total fish:** {total_caught_ever}")
    embed.add_field(name="Stats", value="\n".join(stats) if stats else "Go catch some fish!", inline=True)

    await ctx.send(embed=embed)  # <-- was missing, causing the command to silently do nothing


@bot.command(name="remove_fish")
async def remove_fish_cmd(ctx, member: discord.Member, index: int):
    """[Officer only] Remove a specific fish from a user's inventory."""
    if ctx.author.id not in aura_manager.OWNER_IDS:
        return await ctx.send("Only officers can use this command.")

    inv = get_inventory(member.id)
    if not inv:
        return await ctx.send(f"{member.display_name} doesn't have any fish.")
    if index < 1 or index > len(inv):
        return await ctx.send(f"Invalid number. {member.display_name} has **{len(inv)}** fish.")

    fish_obj = remove_fish(member.id, index)
    if fish_obj is None:
        return await ctx.send("Something went wrong. Try again.")

    await ctx.send(
        f"🗑️ Removed {fish_obj['emoji']} **{fish_obj['color']} {fish_obj['type']}** "
        f"({fish_obj['rarity']}, #{index}) from {member.display_name}'s inventory."
    )
    log(f"{ctx.author.display_name} removed fish #{index} ({fish_obj['type']}) from {member.display_name}", "FISHING")


@bot.command()
async def fish_boss(ctx):
    """[Officer only] Spawn a Blizzy Carp or Donabass boss event (admin fish, 15 aura)."""
    if ctx.author.id not in aura_manager.OWNER_IDS:
        return await ctx.send("Only officers can use this command.")
    admin_fish = generate_admin_fish()
    log(f"{ctx.author.display_name} spawned admin boss event ({admin_fish['type']})", "FISHING")
    await run_boss_event(ctx.channel, admin_fish)
