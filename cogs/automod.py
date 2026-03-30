# Automod module

# Libraries
import discord
import os
import aiosqlite
import datetime
import psycopg2
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
        self.db_url = os.getenv("DATABASE_URL")

    def get_connection(self):
        return psycopg2.connect(self.db_url)
        
    async def cog_load(self):
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS blocked_words (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT,
                    word TEXT
                );
            """)
            
            conn.commit()
            cur.close()
            conn.close()
            print("[DEBUG]: AutoMod Database linked successfully!")
        except Exception as e:
            print(f"[DEBUG]: LINK_ERROR: {e}")
            
    async def cog_unload(self):
        try:
            if hasattr(self, 'conn') and self.conn:
                self.conn.close()
                print("Closed Supabase connection for AutoMod.")
            
            print("[DEBUG]: AutoMod Cog has been unloaded.")
        except Exception as e:
            print(f"[DEBUG]: UNLOAD_ERROR: {e}")
            
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
    @app_commands.guilds(GUILD_ID) # Replace with your GUILD_ID
    @app_commands.describe(member="User to warn", reason="Reason to warn")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        # 1. Safety Checks
        if member.bot:
            return await interaction.response.send_message("WARN_ERROR: You can't warn bots.", ephemeral=True)
        
        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("WARN_ERROR: You cannot warn someone with a higher or equal role!", ephemeral=True)

        await interaction.response.defer() # Database calls take time, so we defer

        now_obj = datetime.datetime.now()
        
        # 2. Database Operations (Cloud)
        try:
            conn = self.get_db_conn()
            cur = conn.cursor()

            # Insert the new warning
            cur.execute(
                "INSERT INTO warnings (user_id, guild_id, moderator_id, reason, created_at) VALUES (%s, %s, %s, %s, %s)",
                (member.id, interaction.guild.id, interaction.user.id, reason, now_obj)
            )

            # Get the total count for punishments
            cur.execute("SELECT COUNT(*) FROM warnings WHERE user_id = %s AND guild_id = %s", (member.id, interaction.guild.id))
            warn_count = cur.fetchone()[0]

            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[DEBUG]: DB_ERROR: {e}", flush=True)
            return await interaction.followup.send("DB_ERROR: Could not save warning.")

        # 3. Punishment Logic
        punishment_text = ""
        
        # Mapping counts to durations (Cleaner than 10 elifs!)
        punishments = {
            2: datetime.timedelta(hours=1),
            3: datetime.timedelta(hours=6),
            4: datetime.timedelta(hours=8),
            5: datetime.timedelta(hours=16),
            6: datetime.timedelta(days=1),
            7: datetime.timedelta(weeks=1),
            8: datetime.timedelta(weeks=1)
        }

        if warn_count in punishments:
            duration = punishments[warn_count]
            await member.timeout(duration, reason=f"Reached {warn_count} warnings")
            punishment_text = f"\n**Auto-Punishment:** User timed out for {duration}."

        elif warn_count == 9:
            unban_date = (now_obj + datetime.timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            try:
                await member.ban(reason=f"Auto-Tempban: 9 warnings. Reason: {reason}")
                # Optional: Add tempban to a separate table in Supabase if you have one
                punishment_text = f"\n**Auto-Punishment:** User temp-banned for 7 days (Unban: {unban_date})."
            except discord.Forbidden:
                punishment_text = "\nPERMS_ERROR: I don't have permission to ban this user."

        elif warn_count >= 10:
            await member.ban(reason="Reached 10 warnings")
            punishment_text = "\n**Auto-Punishment:** User has been permanently banned."

        # 4. Final Response
        await interaction.followup.send(
            f"**{member.display_name}** has been warned (Total: {warn_count}).{punishment_text}"
        )
        
    @app_commands.command(name="warnings", description="Check how many warnings a user has")
    @app_commands.guilds(GUILD_ID) # Use your Guild ID
    @app_commands.describe(member="The member to check")
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer()

        try:
            conn = self.get_db_conn()
            cur = conn.cursor()

            cur.execute(
                "SELECT id, reason, moderator_id, created_at FROM warnings WHERE user_id = %s AND guild_id = %s ORDER BY created_at DESC",
                (member.id, interaction.guild.id)
            )
            rows = cur.fetchall()

            cur.close()
            conn.close()

            if not rows:
                return await interaction.followup.send(f"**{member.display_name}** has a clean record! (0 warnings)")
                
            for i, (warn_id, reason, mod_id, timestamp) in enumerate(rows[:5], 1):
                embed.add_field(
                    name=f"Warning ID: #{warn_id}",
                    value=f"**Reason:** {reason}\n**Moderator:** <@{mod_id}>",
                    inline=False
            )
            embed.set_thumbnail(url=member.display_avatar.url)

            for i, (reason, mod_id, timestamp) in enumerate(rows[:5], 1):
                mod = interaction.guild.get_member(mod_id)
                mod_name = mod.display_name if mod else f"Unknown ({mod_id})"
                date_str = timestamp.strftime("%Y-%m-%d")
                
                embed.add_field(
                    name=f"Warning #{len(rows) - i + 1}",
                    value=f"**Reason:** {reason}\n**Staff:** {mod_name}\n**Date:** {date_str}",
                    inline=False
                )

            if len(rows) > 5:
                embed.set_footer(text=f"Only showing the 5 most recent warnings.")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"[DEBUG]: CHECK_WARN_ERROR: {e}")
            await interaction.followup.send("DB_ERROR: Failed to reach the database. Try again later.")
        
    @app_commands.command(name="delwarn", description="Delete a specific warning by its ID number")
    @app_commands.guilds(GUILD_ID)
    @app_commands.describe(warn_id="The ID of the warning to delete")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def delwarn(self, interaction: discord.Interaction, warn_id: int):
        await interaction.response.defer()

        try:
            conn = self.get_db_conn()
            cur = conn.cursor()

            cur.execute("SELECT user_id FROM warnings WHERE id = %s AND guild_id = %s", (warn_id, interaction.guild.id))
            row = cur.fetchone()

            if not row:
                return await interaction.followup.send(f"NOT_FOUND_ERROR: No warning found with ID **{warn_id}** in this server.")

            cur.execute("DELETE FROM warnings WHERE id = %s", (warn_id,))
            
            conn.commit()
            cur.close()
            conn.close()

            await interaction.followup.send(f"Deleted warning ID **#{warn_id}**.")

        except Exception as e:
            print(f"[DEBUG]: DELWARN_ERROR: {e}")
            await interaction.followup.send("DELWARN_ERROR: Failed to delete warning. Is the ID correct?")
        
    @app_commands.command(name="clearwarns", description="Delete all warnings for a user")
    @app_commands.guilds(GUILD_ID)
    @app_commands.describe(member="The member to clear")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clearwarns(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer()

        try:
            conn = self.get_db_conn()
            cur = conn.cursor()

            cur.execute(
                "DELETE FROM warnings WHERE user_id = %s AND guild_id = %s",
                (member.id, interaction.guild.id)
            )
            
            conn.commit()
            cur.close()
            conn.close()

            await interaction.followup.send(f"Successfully cleared all warnings for **{member.display_name}**.")

        except Exception as e:
            print(f"[DEBUG]: CLEAR_ERROR: {e}")
            await interaction.followup.send("DB_ERROR Database error: Could not clear warnings.")
    
# Connect commands
async def setup(client):
    await client.add_cog(AutoMod(client))
