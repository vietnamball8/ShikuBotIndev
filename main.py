# ------- ShikuBot -------
# Built by vietnam8, co-owned by Shiku Gamer.
# Language: Python
# Creation date: 03/06/2025 (DD/MM/YYYY format)
# This bot is the main application of the server The Shiku Gamer

# Libraries
# ------------------------------------
import os
import discord
import datetime
import random
import time
from groq import Groq
from discord.ext import commands, tasks
from dotenv import load_dotenv
from easy_pil import Editor, load_image_async, Font
# ------------------------------------

# Load token
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
WELCOME_CHANNEL_ID = os.getenv("WELCOME_CHANNEL_ID")
MEMBER_ROLE_ID = os.getenv("MEMBER_ROLE_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
AI_CHAT_CHANNEL_ID = int(os.getenv("AI_CHAT_CHANNEL_ID"))

client_groq = Groq(api_key=GROQ_API_KEY)
chat_sessions = {}

if TOKEN is None:
    print("TOKEN_ERROR: Token not found!")
    exit() 
else:
    print("Token loaded successfully.")
# ------------------------------------

# Define class Client
class Client(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_index = 0
        
    async def setup_hook(self):
        self.cycle_statuses.start()
        
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
                print(f'Loaded: {filename}')

    async def on_ready(self):
        print(f"Logged on as {self.user}!")
        print("------------------------------------")
        
        try:
            guild = discord.Object(id=GUILD_ID)
            synced = await self.tree.sync(guild=guild)
            print(f"Synced {len(synced)} commands to guild {guild.id}")
            
        except Exception as e:
            print(f"SYNC_ERROR: Syncing commands failed: {e}")

    # IMPORTANT: This only logs messages TEMPORARILY not permanent, your message sent DM is not stored in any way or databases.
    async def on_message(self, message):
        if message.author == self.user:
            return
        
        if message.guild is None:
            print(f"DM received from {message.author}: {message.content}")
        else:
            print(f"Message from {message.author}: {message.content}")

    @tasks.loop(seconds=10)
    async def cycle_statuses(self):
        if not self.is_ready():
            return

        user_count = len(self.users)

        statuses = [
            f"Helping {user_count} members!",
            "The Shiku Gamer Main Bot",
            f"Watching Shiku Gamer's live",
            "Checking #suggestions..."
        ]

        current_status = statuses[self.status_index]

        await self.change_presence(
            activity=discord.CustomActivity(name=current_status)
        )

        self.status_index = (self.status_index + 1) % len(statuses)

# ------------------------------------

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.messages = True
intents.dm_messages = True
client = Client(command_prefix="shiku!", intents=intents)
# ------------------------------------

# Welcome & goodbye message
@client.event
async def on_member_join(member):
    channel = client.get_channel(WELCOME_CHANNEL_ID)
    if not channel:
        try:
            channel = await client.fetch_channel(WELCOME_CHANNEL_ID)
        except discord.NotFound:
            print(f"INVALID_ID_ERROR: {WELCOME_CHANNEL_ID} not found.")
            return
        except discord.Forbidden:
            print(f"PERMS_ERROR: Bot lacks permission to see channel {WELCOME_CHANNEL_ID}.")
            return
        
    try:
        background = Editor("./welcome.png").resize((800, 450))
        
        avatar_image = await load_image_async(str(member.display_avatar.url))
        avatar = Editor(avatar_image).resize((150, 150)).circle_image()
        
        font_big = Font.poppins(size=50, variant="bold")
        font_small = Font.poppins(size=30, variant="regular")

        background.paste(avatar, (475, 50))
        background.text((550, 220), "WELCOME", color="white", font=font_big, align="center")
        background.text((550, 280), f"{member.name}", color="#000000", font=font_big, align="center")
        background.text((550, 350), f"Member #{member.guild.member_count}", color="gray", font=font_small, align="center")

        file = discord.File(fp=background.image_bytes, filename="welcome_card.png")
    except Exception as e:
        print(f"Image Error: {e}")
        file = None

    embed = discord.Embed(
        title="Welcome to the server!",
        description=f"Welcome to **The Shiku Gamer**, {member.mention}!\n\nInteract with other users! https://discord.com/channels/1247440062870851625/1272373335908421674\nWatch new videos! https://discord.com/channels/1247440062870851625/1261350011933818981\nGet latest updates! https://discord.com/channels/1247440062870851625/1288069598163374100\nStay tuned on small updates! https://discord.com/channels/1247440062870851625/1288151985144467589",
        color=discord.Color.dark_gray(),
        timestamp=datetime.datetime.now()
    )
    
    if file:
        embed.set_image(url="attachment://welcome_card.png")
        
    await channel.send(embed=embed, file=file)
    
@client.event
async def on_member_remove(member):
    channel = client.get_channel(WELCOME_CHANNEL_ID)
    
    if not channel:
        try:
            channel = await client.fetch_channel(WELCOME_CHANNEL_ID)
        except Exception as e:
            print(f"MISSING_ERROR: Could not find channel {WELCOME_CHANNEL_ID}: {e}")
            return
    
    goodbye_messages = [f"Goodbye, **{member.name}**!", f"Farewell, **{member.name}**!", f"It was a pleasure, **{member.name}**!",
                        f"Don't cry because it's over, smile because it was beautiful, **{member.name}**!"]
    
    goodbye_message = random.choice(goodbye_messages)
    
    embed = discord.Embed(title="A member left...",
                          description=f"{goodbye_message}",
                          color=discord.Color.dark_red(),
                          timestamp=datetime.datetime.now())
    
    await channel.send(embed=embed)
    
    
    
    
# ------------------------------------

# AI chat

cooldowns = {}

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.channel.id == AI_CHAT_CHANNEL_ID:
        
        user_id = message.author.id
        current_time = time.time()
        
        print(f"DEBUG: Checking cooldown for {user_id}. Current dict: {cooldowns}")
        
        if user_id in cooldowns:
            time_passed = current_time - cooldowns[user_id]
            if time_passed < 10:
                wait_time = 10 - time_passed
                await message.reply(f"**Arrr! Slow down, matey!** You can talk to Shiku again in `{wait_time:.1f}` seconds.", delete_after=wait_time)
                return
            
        cooldowns[user_id] = current_time
        
        try:
            completion = client_groq.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[
                    {"role": "system", "content": "You are Shiku, a funny pirate. Keep responses under 3 sentences."},
                    {"role": "user", "content": message.clean_content}
                ],
                max_tokens=150,
                temperature=0.7
            )

            pirate_response = completion.choices[0].message.content
            await message.reply(pirate_response)

        except Exception as e:
            print(f"AI_ERROR: {e}")
            await message.reply("Arrr! The engine is stalled! Try again in a bit, matey.")

# Run client
client.run(TOKEN)

# Credits:
# Developer: vietnam8
# Co-owner: shikugamer
# ------------------------------------