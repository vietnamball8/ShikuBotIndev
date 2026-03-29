# Utils module

# Libraries
import discord
import os
import requests
from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands
from deep_translator import GoogleTranslator
from easy_pil import Editor, load_image_async, Font

# Load guild ID and owner ID
load_dotenv()
GUILD_ID = int(os.getenv("GUILD_ID"))
LOGGING_OWNER_ID = int(os.getenv("OWNER_ID"))
WELCOME_CHANNEL_ID = os.getenv("WELCOME_CHANNEL_ID")

def is_owner_check(interaction: discord.Interaction) -> bool:
    OWNER_ID = os.getenv("OWNER_ID")
    if OWNER_ID is None:
        return False
    return interaction.user.id == int(OWNER_ID)

# Define class Help Dropdown
class HelpDropdown(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.weather_api_key = os.getenv("WEATHER_API_KEY")
        options = []
        
        for name, cog in bot.cogs.items():
            options.append(discord.SelectOption(
                label=name, 
                description=f"Commands for {name}", 
                emoji="📁"
            ))

        super().__init__(placeholder="Choose a category...", options=options)

    async def callback(self, interaction: discord.Interaction):
        cog = self.bot.get_cog(self.values[0])
        commands_list = cog.get_app_commands()
        
        help_text = ""
        for cmd in commands_list:
            help_text += f"**/{cmd.name}** - {cmd.description}\n"

        embed = discord.Embed(
            title=f"{self.values[0]} Commands",
            description=help_text or "No commands found in this category.",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=60)
        self.add_item(HelpDropdown(bot))

# Define class Utils
class Utils(commands.Cog):
    def __init__(self, client):
        self.client = client
        
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if not channel:
            return
 
        try:
            background = Editor("./welcome_bg.png").resize((800, 450))
        except Exception:
            print("Warning: welcome_bg.png not found, using black background.")
            background = Editor("black").resize((800, 450))

        profile_image = await load_image_async(str(member.display_avatar.url))
        profile = Editor(profile_image).resize((150, 150)).circle_image()

        font_big = Font.poppins(size=50, variant="bold")
        font_small = Font.poppins(size=30, variant="regular")

        background.paste(profile, (325, 50))
        background.text((400, 220), f"WELCOME", color="white", font=font_big, align="center")
        background.text((400, 280), f"{member.name}", color="#ffcc00", font=font_big, align="center")
        background.text((400, 350), f"Member #{member.guild.member_count}", color="lightgray", font=font_small, align="center")

        file = discord.File(fp=background.image_bytes, filename="welcome.png")

        embed = discord.Embed(title="Welcome to the server!",
                              description=f"Welcome to the server, {member.mention}!",
                              color=discord.Color.dark_grey())
        embed.add_field(name="Interact with other users!", value="https://discord.com/channels/1247440062870851625/1272373335908421674", inline=True)
        embed.add_field(name="Get notified!", value="https://discord.com/channels/1247440062870851625/1261350011933818981", inline=True)
        embed.add_field(name="Get to the latest news of the server!", value="https://discord.com/channels/1247440062870851625/1288069598163374100", inline=False)
        embed.add_field(name="Receive minor updates!", value="https://discord.com/channels/1247440062870851625/1288069598163374100", inline=True)
        
        
        await channel.send(embed=embed, file=file)

    # Debugging command
    @app_commands.command(name="debug-utils", description="Owner-only debug command (Utils)")
    @app_commands.guilds(GUILD_ID)
    @app_commands.check(is_owner_check)
    async def debug_utils(self, interaction: discord.Interaction):
        await interaction.response.send_message("Utils cog is functional!")
    
    # Printing a message
    @app_commands.command(name="print-msg", description="Make the bot print a message (Admin-only)")
    @app_commands.describe(message="What should the bot say?")
    @app_commands.guilds(GUILD_ID)
    @app_commands.default_permissions(administrator=True)
    async def print_message(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer(ephemeral=True)
        try:
            embed = discord.Embed(title="Message sent",
                                description=f"The message was sent in **#{interaction.channel.name}**",
                                color=discord.Color.blue(),
                                timestamp=interaction.created_at)
            embed.add_field(name="Message content", value=message, inline=False)
            embed.add_field(name="Sent by", value=interaction.user.mention, inline=False)
            
            await interaction.user.send(embed=embed)
        
            await interaction.followup.send("Message sent!", ephemeral=True)
            await interaction.channel.send(message)
        except Exception as e:
            print(f"PRINT_ERROR: {e}")
            await interaction.followup.send(f"PRINT_ERROR: {e}")

    @debug_utils.error
    async def debug_utils_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("PERMS_ERROR: You do not have permission to run this command.", ephemeral=True)
            
    @app_commands.command(name="reply-msg", description="Make the bot reply to a message (Admin-only)")
    @app_commands.describe(message="What should the bot reply with?")
    @app_commands.describe(message_id="The message ID of the message to reply.")
    @app_commands.guilds(GUILD_ID)
    @app_commands.default_permissions(administrator=True)
    async def reply_message(self, interaction: discord.Interaction, message_id: str, message: str):
        await interaction.response.defer(ephemeral=True)
        try:
            clean_id = message_id.strip()
        
            if not clean_id.isdigit():
                await interaction.response.send_message("That ID contains letters or symbols. It must be numbers only!", ephemeral=True)
                return
            
            target_message = int(clean_id)
            replying_message = await interaction.channel.fetch_message(target_message)
            
            embed = discord.Embed(title="Message sent",
                                description=f"The message was sent in **#{interaction.channel.name}**",
                                color=discord.Color.blue(),
                                timestamp=interaction.created_at)
            embed.add_field(name="Message content", value=message, inline=False)
            embed.add_field(name="Sent by", value=interaction.user.mention, inline=False)
            
            await interaction.user.send(embed=embed)
            
            await replying_message.reply(message)
            await interaction.followup.send("Message sent!", ephemeral=True)
        except discord.NotFound:
            await interaction.followup.send(f"PRINT_ERROR: Not a valid ID in this channel.")
        except ValueError:
            await interaction.followup.send(f"PRINT_ERROR: Invalid ID type.")
        except Exception as e:
            print(f"PRINT_ERROR: {e}")
            await interaction.followup.send(f"PRINT_ERROR: {e}")
            
    @app_commands.command(name="edit-msg", description="Make the bot edit a message (Admin-only)")
    @app_commands.describe(message="What should the bot edit the message with?")
    @app_commands.describe(message_id="The message ID of the message to edit.")
    @app_commands.guilds(GUILD_ID)
    @app_commands.default_permissions(administrator=True)
    async def edit_message(self, interaction: discord.Interaction, message_id: str, message: str):
        await interaction.response.defer(ephemeral=True)
        try:
            clean_id = message_id.strip()
        
            if not clean_id.isdigit():
                await interaction.response.send_message("That ID contains letters or symbols. It must be numbers only!", ephemeral=True)
                return
            
            target_message = int(clean_id)
            editing_message = await interaction.channel.fetch_message(target_message)
            
            if editing_message.author.id != self.client.user.id:
                await interaction.followup.send("This command can only edit the text that ShikuBot sends.", ephemeral=True)
            
            embed = discord.Embed(title="Message edited",
                                description=f"The message was edited in **#{interaction.channel.name}**",
                                color=discord.Color.blue(),
                                timestamp=editing_message.edited_at)
            embed.add_field(name="Message content", value=message, inline=False)
            embed.add_field(name="Edited by", value=interaction.user.mention, inline=False)
            
            await interaction.user.send(embed=embed)
            
            await editing_message.edit(content=message)
            await interaction.followup.send("Message edited!", ephemeral=True)
        except discord.NotFound:
            await interaction.followup.send(f"PRINT_ERROR: Not a valid ID in this channel.")
        except ValueError:
            await interaction.followup.send(f"PRINT_ERROR: Invalid ID type.")
        except Exception as e:
            print(f"PRINT_ERROR: {e}")
            await interaction.followup.send(f"PRINT_ERROR: {e}")
            
    @app_commands.command(name="dm", description="Send a direct message to a user through the bot")
    @app_commands.describe(user="The user to message", message="What do you want to say?")
    @app_commands.guilds(GUILD_ID)
    async def dm(self, interaction: discord.Interaction, user: discord.Member, message: str):
        await interaction.response.defer(ephemeral=True)

        if user == self.client.user:
            return await interaction.followup.send("I can't DM myself! I'm already right here.", ephemeral=True)

        try:
            await user.send(content=message)
            
            embed = discord.Embed(title="Direct message sent",
                                description=f"The message was sent to {user}.",
                                color=discord.Color.blue(),
                                timestamp=interaction.created_at)
            embed.add_field(name="Message content", value=message, inline=False)
            embed.add_field(name="Sent by", value=interaction.user.mention, inline=False)
            
            await interaction.user.send(embed=embed)
            
            await interaction.followup.send(f"Successfully sent the DM to {user.mention}!", ephemeral=True)

        except discord.Forbidden:
            await interaction.followup.send(f"DM_ERROR: I couldn't DM {user.mention}. They likely have their DMs closed or have blocked me.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"DM_ERROR: An unexpected error occurred: {e}", ephemeral=True)

    @debug_utils.error
    async def debug_utils_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("PERMS_ERROR: You do not have permission to run this command.", ephemeral=True)
            
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.guild is None:
            LOG_CHANNEL_ID = 123456789012345678
            log_channel = self.client.get_channel(LOG_CHANNEL_ID)
            
            if log_channel:
                log_embed = discord.Embed(
                    title="📥 Inbound DM Received",
                    description=message.content if message.content else "(No text content)",
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow()
                )
                log_embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
                log_embed.set_footer(text=f"User ID: {message.author.id}")
                
                # If they sent an image/file, log that too
                if message.attachments:
                    log_embed.add_field(name="Attachments", value=f"{len(message.attachments)} file(s) sent.")

                await log_channel.send(embed=log_embed)
                
    @app_commands.command(name="purge", description="Delete a specific amount of messages")
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    @app_commands.guilds(GUILD_ID)
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: int):
        if amount < 1 or amount > 100:
            return await interaction.response.send_message(
                "VALUE_ERROR: Please choose a number between 1 and 100.", 
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        try:
            deleted = await interaction.channel.purge(limit=amount)
            
            await interaction.followup.send(
                f"Successfully deleted **{len(deleted)}** messages.", 
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.followup.send(
                "MISSING_PERMS: I don't have the `Manage Messages` permission to do that!", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"PURGE_ERROR: An error occurred: {e}", ephemeral=True)

    @purge.error
    async def purge_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "PERMS_ERROR: You don't have permission to purge messages!", 
                ephemeral=True
            )
            
    @app_commands.command(name="help", description="List all available commands")
    @app_commands.guilds(GUILD_ID)
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Help Menu",
            description="Select a category from the dropdown menu below to view my commands!",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=self.client.user.display_avatar.url)
        embed.add_field(name="Total Cogs", value=f"`{len(self.client.cogs)}`", inline=True)
        
        view = HelpView(self.client)
        await interaction.response.send_message(embed=embed, view=view)
        
    @app_commands.command(name="translate", description="Translate text to another language")
    @app_commands.describe(text="Text to translate", to_language="Target language")
    @app_commands.choices(to_language=[
        app_commands.Choice(name="English 🇺🇸", value="en"),
        app_commands.Choice(name="Hindi 🇮🇳", value="hi"),
        app_commands.Choice(name="Bengali 🇮🇳", value="bn"),
        app_commands.Choice(name="Spanish 🇪🇸", value="es"),
        app_commands.Choice(name="French 🇫🇷", value="fr"),
        app_commands.Choice(name="Japanese 🇯🇵", value="ja")
    ])
    @app_commands.guilds(GUILD_ID)
    async def translate(self, interaction: discord.Interaction, text: str, to_language: app_commands.Choice[str]):
        await interaction.response.defer()

        try:
            translated_text = GoogleTranslator(source='auto', target=to_language.value).translate(text)
            
            dest_emoji = "🇮🇳" if to_language.value in ["hi", "bn"] else "🌍"
            
            embed = discord.Embed(
                title=f"{dest_emoji} Translation Result",
                color=discord.Color.blue()
            )
            embed.add_field(name="Original", value=f"```{text}```", inline=False)
            embed.add_field(name=f"Translated to {to_language.name}", value=f"```{translated_text}```", inline=False)
            
            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"ERROR: {e}")
            await interaction.followup.send("TRANS_ERROR: Translation failed. Please try again later.")

    @app_commands.command(name="weather", description="Check the weather for a city")
    @app_commands.describe(city="The name of the city (e.g., London, Tokyo, Mumbai)")
    @app_commands.guilds(GUILD_ID)
    async def weather(self, interaction: discord.Interaction, city: str):
        await interaction.response.defer()

        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.api_key}&units=metric"

        try:
            response = requests.get(url).json()

            if response["cod"] == "404":
                return await interaction.followup.send(f"❌ City `{city}` not found. Check your spelling!")

            main = response["main"]
            weather_data = response["weather"][0]
            wind = response["wind"]
            
            temp = main["temp"]
            feels_like = main["feels_like"]
            humidity = main["humidity"]
            description = weather_data["description"].capitalize()
            icon_code = weather_data["icon"]
            
            embed = discord.Embed(
                title=f"Weather in {response['name']}, {response['sys']['country']}",
                description=f"**{description}**",
                color=discord.Color.blue()
            )
            
            icon_url = f"http://openweathermap.org/img/wn/{icon_code}@2x.png"
            embed.set_thumbnail(url=icon_url)

            embed.add_field(name="Temperature", value=f"{temp}°C", inline=True)
            embed.add_field(name="Feels Like", value=f"{feels_like}°C", inline=True)
            embed.add_field(name="Humidity", value=f"{humidity}%", inline=True)
            embed.add_field(name="Wind Speed", value=f"{wind['speed']} m/s", inline=True)
            
            embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"WEATHER_ERROR: {e}")
            await interaction.followup.send("WEATHER_ERROR: I couldn't fetch the weather right now. My connection might be down.")

# Connect commands
async def setup(client):
    await client.add_cog(Utils(client))
