# Info module

# Libraries
import discord
import os
import datetime
import random
import aiohttp
from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands

# Load guild ID and owner ID
load_dotenv()
GUILD_ID = int(os.getenv("GUILD_ID"))

def is_owner_check(interaction: discord.Interaction) -> bool:
    OWNER_ID = os.getenv("OWNER_ID")
    if OWNER_ID is None:
        return False
    return interaction.user.id == int(OWNER_ID)

# Define class Info
class Info(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    # Debugging command
    @app_commands.command(name="debug-info", description="Owner-only debug command (Info)")
    @app_commands.guilds(GUILD_ID)
    @app_commands.check(is_owner_check)
    async def debug_utils(self, interaction: discord.Interaction):
        await interaction.response.send_message("Info cog is functional!")
        
    @app_commands.command(name="on-this-day", description="See an event that happened on this day but different timelime.")
    @app_commands.guilds(GUILD_ID)
    async def on_this_day(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        now = datetime.datetime.now()
        month = now.strftime("%m")
        day = now.strftime("%d")
        
        url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/all/{month}/{day}"
        
        headers = {'User-Agent': 'ShikuBot/1.0 (contact: caominhkhang190823@gmail.com) aiohttp/3.10'}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        events = data.get('events', [])

                        if not events:
                            return await interaction.followup.send("I couldn't find any events for today!")

                        event = random.choice(events)
                        year = event.get('year')
                        text = event.get('text')
                        
                        pages = event.get('pages', [])
                        wiki_url = pages[0]['content_urls']['desktop']['page'] if pages else "https://wikipedia.org"
                        thumbnail = pages[0].get('thumbnail', {}).get('source') if pages else None

                        embed = discord.Embed(
                            title=f"On this day: {now.strftime('%B %d')}",
                            description=f"**In the year {year}:**\n{text}",
                            color=discord.Color.gold(),
                            url=wiki_url
                        )
                        
                        if thumbnail:
                            embed.set_thumbnail(url=thumbnail)
                            
                        embed.set_footer(text=f"Source: Wikipedia API | Request sent by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
                        
                        await interaction.followup.send(embed=embed)
                    else:
                        print(f"DEBUG: Status Code {response.status}")
                        await interaction.followup.send("ERROR: Wikipedia is currently unavailable.")
                        
        except Exception as e:
            await interaction.followup.send(f"ERROR: {e}")
            print(f"ERROR: {e}")
            
    @app_commands.command(name="server-info", description="Check server's info.")
    @app_commands.guilds(GUILD_ID)
    async def server_info(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        guild = interaction.guild
        
        member_count = guild.member_count
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        created_at = int(guild.created_at.timestamp())
        
        role_count = len(guild.roles)
        emoji_count = len(guild.emojis)
        animated_emojis = len([e for e in guild.emojis if e.animated])
        static_emojis = emoji_count - animated_emojis
        
        embed = discord.Embed(
            title=f"📊 {guild.name}'s info:",
            color=discord.Color.blurple()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
        embed.add_field(name="Server ID", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="Created On", value=f"<t:{created_at}:D> (<t:{created_at}:R>)", inline=False)
        
        embed.add_field(name="Members", value=f"{member_count}", inline=True)
        embed.add_field(name="Boosts", value=f"Level {guild.premium_tier} ({guild.premium_subscription_count})", inline=True)
        
        embed.add_field(name="Roles", value=f"{role_count}", inline=True)
        embed.add_field(
            name="Emojis", 
            value=f" Total: {emoji_count}\n Static: {static_emojis}\n Animated: {animated_emojis}", 
            inline=True
        )
        
        embed.add_field(
            name="Channels", 
            value=f"{text_channels} Text | {voice_channels} Voice | {categories} Categories", 
            inline=False
        )
        
        embed.set_footer(
            text=f"Requested by {interaction.user.display_name}", 
            icon_url=interaction.user.display_avatar.url
        )
        
        await interaction.followup.send(embed=embed)
        
    @app_commands.command(name="user-info", description="Get detailed information about a user")
    @app_commands.describe(user="The user you want to check (defaults to you)")
    @app_commands.guilds(GUILD_ID)
    async def user_info(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        await interaction.response.defer()

        joined_server = int(user.joined_at.timestamp())
        created_account = int(user.created_at.timestamp())

        roles = [role.mention for role in user.roles if role != interaction.guild.default_role]
        roles_display = ", ".join(roles[:10]) if roles else "No Roles"
        if len(roles) > 10:
            roles_display += f" ...and {len(roles) - 10} more"

        status = "Member"
        if user.guild_permissions.administrator:
            status = "Administrator 👑"
        elif user == interaction.guild.owner:
            status = "Server Owner 🏰"

        embed = discord.Embed(
            title=f"👤 User Info: {user.display_name}",
            color=user.color
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        
        embed.add_field(name="Full Name", value=f"`{user.name}`", inline=True)
        embed.add_field(name="User ID", value=f"`{user.id}`", inline=True)
        embed.add_field(name="Status", value=status, inline=True)

        embed.add_field(name="Account Created", value=f"<t:{created_account}:D>\n(<t:{created_account}:R>)", inline=True)
        embed.add_field(name="Joined Server", value=f"<t:{joined_server}:D>\n(<t:{joined_server}:R>)", inline=True)

        embed.add_field(name=f"Roles ({len(roles)})", value=roles_display, inline=False)
        
        embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

        await interaction.followup.send(embed=embed)
        
    

    @debug_utils.error
    async def debug_utils_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("PERMS_ERROR: You do not have permission to run this command.", ephemeral=True)
            
    

# Connect commands
async def setup(client):
    await client.add_cog(Info(client))