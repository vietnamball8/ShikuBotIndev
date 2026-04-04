import discord
import os
from dotenv import load_dotenv
from discord import app_commands
from discord.ext import commands
import random
import asyncio
from collections import Counter

load_dotenv()
GUILD_ID = int(os.getenv('GUILD_ID'))

class MafiaKillView(discord.ui.View):
    def __init__(self, players, mafia_id, guild_id, cog):
        super().__init__(timeout=60)
        for p_id in players:
            if p_id != mafia_id:
                self.add_item(KillButton(p_id, guild_id, cog))

class KillButton(discord.ui.Button):
    def __init__(self, victim_id, guild_id, cog):
        super().__init__(label=f"Eliminate ID: {str(victim_id)[-4:]}", style=discord.ButtonStyle.danger)
        self.victim_id = victim_id
        self.guild_id = guild_id
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        game = self.cog.get_game(self.guild_id)
        game["kill_target"] = self.victim_id
        await interaction.response.send_message("Target locked.", ephemeral=True)
        self.view.stop()
        
class TownVoteSelect(discord.ui.Select):
    def __init__(self, players, guild_id, cog):
        options = [
            discord.SelectOption(label=f"User {str(p_id)[-4:]}", value=str(p_id))
            for p_id in players
        ]
        super().__init__(placeholder="Choose a suspect to hang...", options=options)
        self.guild_id = guild_id
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        game = self.cog.get_game(self.guild_id)
        game["votes"][interaction.user.id] = int(self.values[0])
        await interaction.response.send_message(f"You have voted for <@{self.values[0]}>", ephemeral=True)

class TownVoteView(discord.ui.View):
    def __init__(self, players, guild_id, cog):
        super().__init__(timeout=60)
        self.add_item(TownVoteSelect(players, guild_id, cog))

class Mafia(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.games = {}
        
    def get_game(self, guild_id):
        if guild_id not in self.games:
            self.games[guild_id] = {
                "players": [],
                "roles": {},
                "phase": "lobby",
                "kill_target": None
            }
        return self.games[guild_id]
    
    @app_commands.command(name="mafia_join", description="Join the mafia game lobby")
    @app_commands.guilds(GUILD_ID)
    async def join(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        game = self.get_game(interaction.guild.id)
        
        if game["phase"] != "lobby":
            return await interaction.followup.send("A game is already in progress!", ephemeral=True)
        
        if interaction.user.id in game["players"]:
            return await interaction.followup.send("You are already in the lobby.", ephemeral=True)

        game["players"].append(interaction.user.id)
        await interaction.followup.send(f"{interaction.user.display_name} joined! (Total: {len(game['players'])})")
        
    @app_commands.command(name="mafia_start", description="Assign roles and start the night")
    @app_commands.guilds(GUILD_ID)
    async def start(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        game = self.get_game(interaction.guild.id)
        
        if len(game["players"]) < 2:
            return await interaction.followup.send("Need at least 3 players to start!", ephemeral=True)

        players = game["players"].copy()
        random.shuffle(players)
        
        mafia_id = players[0]
        game["roles"][mafia_id] = "Mafia"
        for citizen_id in players[1:]:
            game["roles"][citizen_id] = "Citizen"

        game["phase"] = "night"
        await interaction.followup.send("Roles have been DM'd. The city falls silent...")

        await self.start_night_phase(interaction, mafia_id)

    @app_commands.command(name="mafia_leave", description="Leave the game lobby")
    @app_commands.guilds(GUILD_ID)
    async def leave(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True) 

        game = self.get_game(interaction.guild.id)
        
        if game["phase"] != "lobby":
            return await interaction.followup.send("You can't leave now, the game has already started!", ephemeral=True)
        
        if interaction.user.id not in game["players"]:
            return await interaction.followup.send("You aren't even in the lobby!", ephemeral=True)

        game["players"].remove(interaction.user.id)
        
        await interaction.followup.send(f"{interaction.user.display_name} has left the lobby. (Total: {len(game['players'])})")
        
    async def start_night_phase(self, interaction, mafia_id):
        game = self.get_game(interaction.guild.id)
        mafia_user = await self.client.fetch_user(mafia_id)
        
        mafia_embed = discord.Embed(title="You are the MAFIA!",
                              description="You are the mafia, the one behind all the deaths of the town.",
                              color=discord.Color.red())
        
        mafia_embed.add_field(name="Side",
                        value="Mafia")
        mafia_embed.add_field(name="Target/Mission",
                        value="Your goal is to eliminate all of the villagers in the town and not getting voted.")
        
        view = MafiaKillView(game["players"], mafia_id, interaction.guild.id, self)
        
        try:
            await mafia_user.send(embed=mafia_embed, view=view)
        except discord.Forbidden:
            error_embed = discord.Embed(title="Error DM'ing the mafia.",
                                        description="Could not DM the Mafia. Turn skipped!\nMafia, please turn on DMs or the game will not go as expected.",
                                        color=discord.Color.red())
            await interaction.channel.send(embed=error_embed)

        await asyncio.sleep(45) 
        await self.start_day_phase(interaction)
        
    async def start_day_phase(self, interaction):
        game = self.get_game(interaction.guild.id)
        target = game["kill_target"]

        if target:
            death_embed = discord.Embed(title="A new day has started!",
                                    description=f"**Day Breaks.** The town wakes up, but <@{target}> was found dead!",
                                    color=discord.Color.light_gray())
            
            await interaction.channel.send(embed=death_embed)
            if target in game["players"]:
                game["players"].remove(target)
        else:
            death_embed = discord.Embed(title="A new day has started!",
                                    description=f"**Day Breaks.** The town wakes up. No one died!",
                                    color=discord.Color.gold())
            
            await interaction.channel.send(embed=death_embed)

        game["kill_target"] = None
        game["phase"] = "day"
        
        vote_embed = discord.Embed(title="Voting time", description="Discuss and vote for someone to hang! You have 60 seconds.", color=discord.Color.blue())
        view = TownVoteView(game["players"], interaction.guild.id, self)
        await interaction.channel.send(embed=vote_embed, view=view)

        await asyncio.sleep(60)
        await self.resolve_voting(interaction)

    async def resolve_voting(self, interaction):
        game = self.get_game(interaction.guild.id)
        if not game["votes"]:
            await interaction.channel.send("No one voted. The town remains undecided.")
            return

        vote_counts = Counter(game["votes"].values())
        top_target, count = vote_counts.most_common(1)[0]

        await interaction.channel.send(f"The votes are in! <@{top_target}> received {count} votes.")
        
        if top_target in game["players"]:
            game["players"].remove(top_target)
            role = game["roles"].get(top_target, "Unknown")
            await interaction.channel.send(f"**The town has hanged <@{top_target}>.** They were a **{role}**!")

        game["phase"] = "night"
        await interaction.channel.send("Night falls again...")
        
async def setup(client):
    await client.add_cog(Mafia(client))
