# Fun module

# Libraries
import discord
import os
import random
import aiohttp
from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands

# RPS class
class RPSBattleView(discord.ui.View):
    def __init__(self, player1, player2, is_bot=False):
        super().__init__(timeout=30.0)
        self.p1 = player1
        self.p2 = player2
        self.is_bot = is_bot
        self.p1_choice = None
        self.p2_choice = None
        self.message = None

    def get_winner(self):
        if self.p1_choice == self.p2_choice:
            return "It's a **Tie**!", discord.Color.light_grey()
        
        win_map = {"Rock": "Scissors", "Paper": "Rock", "Scissors": "Paper"}
        if win_map[self.p1_choice] == self.p2_choice:
            return f"**{self.p1.display_name} Wins!**", discord.Color.green()
        return f"**{self.p2.display_name} Wins!**", discord.Color.green()

    async def on_timeout(self):
        if self.p1_choice and self.p2_choice:
            return

        if not self.p1_choice and not self.p2_choice:
            desc = "**Match Cancelled:** Neither player chose a weapon."
        elif not self.p1_choice:
            desc = f"**Timeout:** {self.p1.mention} failed to move! {self.p2.mention} wins."
        else:
            desc = f"**Timeout:** {self.p2.mention} failed to move! {self.p1.mention} wins."

        embed = discord.Embed(title="RPS Battle: Timeout", description=desc, color=discord.Color.red())
        
        for child in self.children:
            child.disabled = True
            
        if self.message:
            await self.message.edit(embed=embed, view=self)

    async def process_choice(self, interaction: discord.Interaction, choice: str):
        if interaction.user not in [self.p1, self.p2]:
            return await interaction.response.send_message("You aren't in this battle!", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        if interaction.user == self.p1:
            self.p1_choice = choice
        else:
            self.p2_choice = choice
        
        await self.update_game(interaction)

    @discord.ui.button(label="Rock", emoji="🪨")
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_choice(interaction, "Rock")

    @discord.ui.button(label="Paper", emoji="📜")
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_choice(interaction, "Paper")

    @discord.ui.button(label="Scissors", emoji="✂️")
    async def scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_choice(interaction, "Scissors")

    async def update_game(self, interaction: discord.Interaction):
        if self.is_bot:
            self.p2_choice = random.choice(["Rock", "Paper", "Scissors"])
        
        if self.p1_choice and self.p2_choice:
            self.stop() 
            result_text, color = self.get_winner()
            embed = discord.Embed(title="RPS Battle Results", color=color)
            embed.add_field(name=self.p1.display_name, value=self.p1_choice)
            embed.add_field(name=self.p2.display_name, value=self.p2_choice)
            embed.description = result_text
            
            await interaction.message.edit(content=None, embed=embed, view=None)
        else:
            await interaction.followup.send("✅ Choice recorded! Waiting for opponent...", ephemeral=True)

class AcceptView(discord.ui.View):
    def __init__(self, p1, p2):
        super().__init__(timeout=60)
        self.p1 = p1
        self.p2 = p2

    @discord.ui.button(label="Accept Battle", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.p2:
            return await interaction.response.send_message("Only the challenged player can accept!", ephemeral=True)
        
        new_view = RPSBattleView(self.p1, self.p2)
        await interaction.response.edit_message(content=f"**Battle Started!**", view=new_view)
        new_view.message = await interaction.original_response()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.p2:
            return await interaction.response.send_message("Only the challenged player can decline!", ephemeral=True)
        await interaction.response.edit_message(content="The battle was declined.", view=None)
        
# Animal class
class AnimalView(discord.ui.View):
    def __init__(self, animal_type: str):
        super().__init__(timeout=60)
        self.animal_type = animal_type

    @discord.ui.button(label="New Image 🔄", style=discord.ButtonStyle.gray)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        image_url = await get_animal_image(self.animal_type)
        
        embed = interaction.message.embeds[0]
        embed.set_image(url=image_url)
        await interaction.edit_original_response(embed=embed, view=self)

async def get_animal_image(animal_type: str):
    """Helper function to fetch the image URL from APIs"""
    async with aiohttp.ClientSession() as session:
        if animal_type == "cat":
            url = "https://api.thecatapi.com/v1/images/search"
            async with session.get(url) as resp:
                data = await resp.json()
                return data[0]['url']
        else: # Dog
            url = "https://dog.ceo/api/breeds/image/random"
            async with session.get(url) as resp:
                data = await resp.json()
                return data['message']

# Load guild ID and owner ID
load_dotenv()
GUILD_ID = int(os.getenv("GUILD_ID"))

def is_owner_check(interaction: discord.Interaction) -> bool:
    OWNER_ID = os.getenv("OWNER_ID")
    if OWNER_ID is None:
        return False
    return interaction.user.id == int(OWNER_ID)

# Define class Fun
class Fun(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    # Debugging command
    @app_commands.command(name="debug-fun", description="Owner-only debug command (Fun)")
    @app_commands.guilds(GUILD_ID)
    @app_commands.check(is_owner_check)
    async def debug_utils(self, interaction: discord.Interaction):
        await interaction.response.send_message("Fun cog is functional!")
    
    @debug_utils.error
    async def debug_utils_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("PERMS_ERROR: You do not have permission to run this command.", ephemeral=True)
    
    # Coinflip
    @app_commands.command(name="coinflip", description="Flip a coin!")
    @app_commands.guilds(GUILD_ID)
    async def coinflip(self, interaction: discord.Interaction):
        coinflip_result = ["Heads", "Tails"]
        result = random.choice(coinflip_result)
        
        embed = discord.Embed(title="Coinflip",
                              description=f"The coin landed on **{result}**!",
                              color=discord.Color.gold() if result == "Heads" else discord.Color.orange())
        
        embed.set_footer(text=f"Coin flipped by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)
        
    # Meme command
    @app_commands.command(name="meme", description="Fetch a random meme from reddit!")
    @app_commands.guilds(GUILD_ID)
    async def meme(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        try:
            async with aiohttp.ClientSession() as session:
                for _ in range(5):
                    async with session.get("https://meme-api.com/gimme") as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if data.get('nsfw') is True:
                                continue
                            
                            embed = discord.Embed(title=data['title'],
                                                url=data['postLink'],
                                                color=discord.Color.blue())
                            
                            embed.set_image(url=data["url"])
                            embed.set_footer(text=f"r/{data['subreddit']} | Meme requested by {interaction.user.display_name}",
                                            icon_url=interaction.user.display_avatar.url)
                            await interaction.followup.send(embed=embed)
                            return
                            
                await interaction.followup.send("Could not find a meme, try running the command again!", ephemeral=True)
        
        except Exception as e:
            print(f"MEME_ERROR: {e}")
            await interaction.followup.send(f"MEME_ERROR: {e}", ephemeral=True)
            
    @app_commands.command(name="dice-roll", description="Roll a dice")
    @app_commands.guilds(GUILD_ID)
    @app_commands.describe(die="Choose your type of dice:")
    @app_commands.choices(die=[
        app_commands.Choice(name="D6", value=6),
        app_commands.Choice(name="D20", value=20),
        app_commands.Choice(name="D50", value=50),
        app_commands.Choice(name="D100", value=100)
    ])
    async def dice(self, interaction: discord.Interaction, die: app_commands.Choice[int]):
        await interaction.response.defer()
        
        try:
            result = random.randint(1, die.value)
            embed = discord.Embed(title="Dice roll",
                                description=f"You rolled a dice, it landed on **{result}**!",
                                color=discord.Color.light_gray())
            embed.set_footer(text=f"Dice rolled by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
            
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"DICE_ERROR: {e}")
            print(f"DICE_ERROR: {e}")
            
    @app_commands.command(name="rps", description="Battle a player or the bot")
    @app_commands.guilds(GUILD_ID)
    @app_commands.describe(opponent="Who do you want to battle?")
    async def rps(self, interaction: discord.Interaction, opponent: discord.Member = None):
        if opponent is None or opponent.bot:
            bot_user = opponent if (opponent and opponent.bot) else self.client.user
            view = RPSBattleView(interaction.user, bot_user, is_bot=True)
            
            await interaction.response.send_message(
                content=f"**Bot Battle!** Choose your weapon against {bot_user.mention}:", 
                view=view
            )
            
            view.message = await interaction.original_response()
        
        elif opponent == interaction.user:
            await interaction.response.send_message("You can't battle yourself!", ephemeral=True)
            
        else:
            view = AcceptView(interaction.user, opponent)
            await interaction.response.send_message(
                content=f"⚔️ {opponent.mention}, {interaction.user.mention} has challenged you! Do you accept?", 
                view=view
            )
            
    @app_commands.command(name="8ball", description="Ask magic 8ball a question!")
    @app_commands.guilds(GUILD_ID)
    @app_commands.describe(question="Ask 8ball a question!")
    async def magic8ball(self, interaction: discord.Interaction, question: str):
        await interaction.response.defer()
        
        magic8ball_response = ["It is certain", "It is decidedly so", "Without a doubt", "Yes definitely", "You may rely on it",
                               "As I see it, yes", "Most likely", "Outlook good", "Yes", "Signs point to yes", "Reply hazy, try again",
                               "Ask again later", "Better not tell you now", "Cannot predict now", "Concentrate and ask again",
                               "Don't count on it", "My reply is no", "My sources say no", "Outlook not so good", "Very doubtful"]
        
        answer = random.choice(magic8ball_response)
        embed = discord.Embed(title="8ball response",
                              description="Here's the response of 8ball:")
        
        embed.add_field(name="Your question:", value=f"**{question}**", inline=False)
        embed.add_field(name="8ball response:", value=f"{answer}", inline=False)
        embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        
        await interaction.followup.send(embed=embed)
        
    @app_commands.command(name="animal", description="Get a random picture of a cat or dog!")
    @app_commands.guilds(GUILD_ID)
    @app_commands.describe(animal_type="Choose your favorite pet!")
    @app_commands.choices(animal_type=[
        app_commands.Choice(name="Cat", value="cat"),
        app_commands.Choice(name="Dog", value="dog")
    ])
    async def animal(self, interaction: discord.Interaction, animal_type: app_commands.Choice[str]):
        await interaction.response.defer()
        
        try:
            image_url = await get_animal_image(animal_type.value)
            
            embed = discord.Embed(
                title=f"A wild {animal_type.value} appeared!",
                color=discord.Color.blue()
            )
            embed.set_image(url=image_url)
            
            # Create the view with the refresh button
            view = AnimalView(animal_type.value)
            await interaction.followup.send(embed=embed, view=view)

        except Exception as e:
            print(f"IMAGE_ERROR: {e}")
            await interaction.followup.send(f"IMAGE_ERROR: Error fetching the animal image: {e}")
            
    @app_commands.command(name="snake-eyes", description="Play a game of snake-eyes!")
    @app_commands.guilds(GUILD_ID)
    async def snake_eyes(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        die1, die2 = random.randint(1, 6), random.randint(1, 6)
        ones_count = [die1, die2].count(1)

        if ones_count == 2:
            result_text, color = "**You won with double snake eyes!**", discord.Color.green()
        elif ones_count == 1:
            result_text, color = "**You won with a single snake eye!**", discord.Color.yellow()
        else:
            result_text, color = "**You lost...**", discord.Color.dark_gray()

        embed = discord.Embed(title="Snake Eyes", description="Here's the result of the game:", color=color)
        embed.add_field(name="Dice 1:", value=f"Rolled dice: **{die1}**")
        embed.add_field(name="Dice 2:", value=f"Rolled dice: **{die2}**")
        embed.add_field(name="Result", value=result_text, inline=False)
        embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        
        await interaction.followup.send(embed=embed)
        
    @app_commands.command(name="dictionary", description="Look up the definition of a word")
    @app_commands.guilds(GUILD_ID)
    @app_commands.describe(word="The word you want to search for")
    async def dictionary(self, interaction: discord.Interaction, word: str):
        await interaction.response.defer()

        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 404:
                        return await interaction.followup.send(f"DICT_ERROR: I couldn't find the word **{word}**.")
                    
                    data = await response.json()
                    entry = data[0]
                    word_name = entry.get('word', word).capitalize()
                    phonetic = entry.get('phonetic', 'N/A')
                    
                    meanings = entry.get('meanings', [])
                    if not meanings:
                        return await interaction.followup.send("DICT_ERROR: No definitions found.")
                    
                    first_meaning = meanings[0]
                    part_of_speech = first_meaning.get('partOfSpeech', 'unknown')
                    definition = first_meaning['definitions'][0].get('definition', 'No definition available.')
                    example = first_meaning['definitions'][0].get('example', 'No example available.')

                    embed = discord.Embed(
                        title=f"Dictionary: {word_name}",
                        description=f"*{phonetic}*",
                        color=discord.Color.teal()
                    )
                    embed.add_field(name=f"Type: {part_of_speech.capitalize()}", value=definition, inline=False)
                    embed.add_field(name="Example", value=f"*{example}*", inline=False)
                    embed.set_footer(text=f"Source: Free Dictionary API | Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

                    await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"DICT_ERROR: {e}")
            await interaction.followup.send("❌ An error occurred while fetching the definition.")
            
    @app_commands.command(name="quote", description="Get a random inspirational quote!")
    @app_commands.guilds(GUILD_ID)
    async def quote(self, interaction: discord.Interaction):
        await interaction.response.defer()

        url = "https://zenquotes.io/api/random"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        quote_text = data[0]['q']
                        author = data[0]['a']

                        embed = discord.Embed(
                            description=f"## “{quote_text}”",
                            color=discord.Color.random()
                        )
                        embed.set_author(name=author)
                        embed.set_footer(text=f"Source: ZenQuotes.io | Requested by {interaction.user.display_name}",
                                         icon_url=interaction.user.display_avatar.url)

                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send("QUOTE_ERROR: I couldn't reach the quote server. Try again later!")

        except Exception as e:
            print(f"QUOTE_ERROR: {e}")
            await interaction.followup.send(f"QUOTE_ERROR: An error occurred while fetching the quote: {e}")
        
        
        
                        

# Connect commands
async def setup(client):
    await client.add_cog(Fun(client))