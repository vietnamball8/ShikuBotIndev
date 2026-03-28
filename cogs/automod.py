# Automod module

# Libraries
import discord
import os
import aiosqlite
import datetime
from dotenv import load_dotenv
from discord.ext import commands, tasks
from discord import app_commands

# Load guild ID and owner ID
load_dotenv()
GUILD_ID = int(os.getenv("GUILD_ID"))

def is_owner_check(interaction: discord.Interaction) -> bool:
    OWNER_ID = os.getenv("OWNER_ID")
    if OWNER_ID is None:
        return False
    return interaction.user.id == int(OWNER_ID)

# Define class AutoMod
class AutoMod(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.db_name = "warnings.db"
        
    async def cog_load(self):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS warns (
                    warn_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    guild_id INTEGER,
                    moderator_id INTEGER,
                    reason TEXT,
                    timestamp TEXT
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS tempbans (
                    user_id INTEGER,
                    guild_id INTEGER,
                    unban_time TEXT
                )
            ''')
            await db.commit()
            
    def cog_unload(self):
        self.check_tempbans.cancel()
            
    @tasks.loop(minutes=1)
    async def check_tempbans(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        async with aiosqlite.connect(self.db_name) as db:
            # Find users whose time is up
            async with db.execute("SELECT user_id, guild_id FROM tempbans WHERE unban_time <= ?", (now,)) as cursor:
                to_unban = await cursor.fetchall()

            for user_id, guild_id in to_unban:
                guild = self.client.get_guild(guild_id)
                if guild:
                    try:
                        user = await self.client.fetch_user(user_id)
                        await guild.unban(user, reason="Tempban expired.")
                        print(f"✅ Automatically unbanned {user.name}")
                    except Exception as e:
                        print(f"❌ Failed to auto-unban {user_id}: {e}")

                # Remove from database so we don't try to unban them again
                await db.execute("DELETE FROM tempbans WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
            
            await db.commit()
    
    # Debugging command
    @app_commands.command(name="debug-automod", description="Owner-only debug command (AutoMod)")
    @app_commands.guilds(GUILD_ID)
    @app_commands.check(is_owner_check)
    async def debug_utils(self, interaction: discord.Interaction):
        await interaction.response.send_message("AutoMod cog is functional!")

    @debug_utils.error
    async def debug_utils_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("PERMS_ERROR: You do not have permission to run this command.", ephemeral=True)
            
    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.guilds(GUILD_ID)
    @app_commands.describe(member="The user to ban", reason="Why are they being banned?")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("PERMS_ERROR: You cannot ban someone with a higher or equal role!", ephemeral=True)
        
        await member.ban(reason=reason)
        await interaction.response.send_message(f"**{member.display_name}** has been banned.\n**Reason:** {reason}")

    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.guilds(GUILD_ID)
    @app_commands.describe(member="The user to kick", reason="Why are they being kicked?")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("PERMS_ERROR: You cannot kick someone with a higher or equal role!", ephemeral=True)
        
        await member.kick(reason=reason)
        await interaction.response.send_message(f"**{member.display_name}** has been kicked.\n**Reason:** {reason}")
        
    @app_commands.command(name="timeout", description="Timeout a member (Mute)")
    @app_commands.guilds(GUILD_ID)
    @app_commands.describe(member="The user to timeout", minutes="Duration in minutes", reason="Reason")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided"):
        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("PERMS_ERROR: You cannot timeout this user.", ephemeral=True)

        import datetime
        duration = datetime.timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)
        
        await interaction.response.send_message(f"**{member.display_name}** has been timed out for {minutes} minutes.\n**Reason:** {reason}")
        
    @app_commands.command(name="slowmode", description="Set the slowmode for the current channel")
    @app_commands.guilds(GUILD_ID)
    @app_commands.describe(seconds="Seconds between messages (0 to disable)")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction, seconds: int):
        if seconds < 0 or seconds > 21600:
            return await interaction.response.send_message("LIMIT_ERROR: Slowmode must be between 0 and 21600 seconds.", ephemeral=True)
        
        await interaction.channel.edit(slowmode_delay=seconds)
        
        if seconds == 0:
            await interaction.response.send_message("Slowmode has been disabled.")
        else:
            await interaction.response.send_message(f"Slowmode set to **{seconds}** seconds.")
            
    @app_commands.command(name="warn", description="Give a formal warning to a member")
    @app_commands.guilds(GUILD_ID)
    @app_commands.describe(member="User to warn", reason="Why are they being warned?")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        if member.bot:
            return await interaction.response.send_message("WARN_ERROR: You can't warn bots.", ephemeral=True)
        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("WARN_ERROR You cannot warn someone with a higher or equal role!", ephemeral=True)

        now_obj = datetime.datetime.now() 
        now_str = now_obj.strftime("%Y-%m-%d %H:%M:%S")
        
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                "INSERT INTO warns (user_id, guild_id, moderator_id, reason, timestamp) VALUES (?, ?, ?, ?, ?)",
                (member.id, interaction.guild.id, interaction.user.id, reason, now_obj)
            )
            await db.commit()

            async with db.execute("SELECT COUNT(*) FROM warns WHERE user_id = ? AND guild_id = ?", (member.id, interaction.guild.id)) as cursor:
                warn_count = (await cursor.fetchone())[0]

        punishment_text = ""
        
        if warn_count == 2:
            duration = datetime.timedelta(hours=1)
            await member.timeout(duration, reason="Reached 2 warnings")
            punishment_text = "\n**Auto-Punishment:** User has been timed out for 1 hour."
            
        elif warn_count == 3:
            duration = datetime.timedelta(hours=6)
            await member.timeout(duration, reason="Reached 3 warnings")
            punishment_text = "\n**Auto-Punishment:** User has been timed out for 6 hours."
            
        elif warn_count == 4:
            duration = datetime.timedelta(hours=8)
            await member.timeout(duration, reason="Reached 4 warnings")
            punishment_text = "\n**Auto-Punishment:** User has been timed out for 8 hours."
            
        elif warn_count == 5:
            duration = datetime.timedelta(hours=16)
            await member.timeout(duration, reason="Reached 5 warnings")
            punishment_text = "\n**Auto-Punishment:** User has been timed out for 16 hours."
            
        elif warn_count == 6:
            duration = datetime.timedelta(days=1)
            await member.timeout(duration, reason="Reached 6 warnings")
            punishment_text = "\n**Auto-Punishment:** User has been timed out for 1 day."
            
        elif warn_count == 7 or warn_count == 8:
            duration = datetime.timedelta(weeks=1)
            await member.timeout(duration, reason=f"Reached {warn_count} warnings")
            punishment_text = "\n**Auto-Punishment:** User has been timed out for 1 week."
            
        elif warn_count == 9:
            unban_date = now_obj + datetime.timedelta(days=7)
            unban_str = unban_date.strftime("%Y-%m-%d %H:%M:%S")

            try:
                await member.ban(reason=f"Auto-Tempban: Reached 9 warnings. Reason: {reason}")
                async with aiosqlite.connect(self.db_name) as db:
                    await db.execute(
                        "INSERT INTO tempbans (user_id, guild_id, unban_time) VALUES (?, ?, ?)",
                        (member.id, interaction.guild.id, unban_str)
                    )
                    await db.commit()
                punishment_text = f"\n**Auto-Punishment:** User temp-banned for 7 days (Unban: {unban_str})."
            except discord.Forbidden:
                punishment_text = "\nPERMS_ERROR: I don't have permission to ban this user."
            
        elif warn_count >= 10:
            await member.ban(reason="Reached 10 warnings")
            punishment_text = "\n**Auto-Punishment:** User has been permanently banned."

        await interaction.response.send_message(
            f"✅ **{member.display_name}** has been warned (Total: {warn_count}).{punishment_text}"
        )
        
    @app_commands.command(name="warnings", description="View a user's warning history")
    @app_commands.guilds(GUILD_ID)
    @app_commands.describe(member="The user to check")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute(
                "SELECT reason, moderator_id, timestamp, warn_id FROM warns WHERE user_id = ? AND guild_id = ?",
                (member.id, interaction.guild.id)
            ) as cursor:
                rows = await cursor.fetchall()

        if not rows:
            return await interaction.response.send_message(f"✨ **{member.display_name}** has a clean record!", ephemeral=True)

        embed = discord.Embed(title=f"Warning History: {member.display_name}", color=discord.Color.orange())
        for row in rows:
            reason, mod_id, time, w_id = row
            embed.add_field(
                name=f"ID: {w_id} | {time}",
                value=f"**Reason:** {reason}\n**Moderator:** <@{mod_id}>",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="delwarn", description="Remove a specific warning using its ID")
    @app_commands.guilds(GUILD_ID)
    @app_commands.describe(warn_id="The ID number of the warning (find this using /warnings)")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def delwarn(self, interaction: discord.Interaction, warn_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT user_id FROM warns WHERE warn_id = ? AND guild_id = ?", (warn_id, interaction.guild.id)) as cursor:
                row = await cursor.fetchone()
            
            if not row:
                return await interaction.response.send_message(f"NOT_FOUND_ERROR: No warning found with ID `{warn_id}` in this server.", ephemeral=True)

            await db.execute("DELETE FROM warns WHERE warn_id = ?", (warn_id,))
            await db.commit()

        await interaction.response.send_message(f"Warning ID `{warn_id}` has been deleted from <@{row[0]}>'s record.")
        
    @app_commands.command(name="clearwarns", description="Wipe all warnings for a specific member")
    @app_commands.describe(member="The user to clear")
    @app_commands.checks.has_permissions(administrator=True)
    async def clearwarns(self, interaction: discord.Interaction, member: discord.Member):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT COUNT(*) FROM warns WHERE user_id = ? AND guild_id = ?", (member.id, interaction.guild.id)) as cursor:
                count = (await cursor.fetchone())[0]

            if count == 0:
                return await interaction.response.send_message(f"**{member.display_name}** already has a clean record!", ephemeral=True)

            await db.execute("DELETE FROM warns WHERE user_id = ? AND guild_id = ?", (member.id, interaction.guild.id))
            await db.commit()

        await interaction.response.send_message(f"Cleared **{count}** warnings for **{member.display_name}**.")
    
# Connect commands
async def setup(client):
    await client.add_cog(AutoMod(client))