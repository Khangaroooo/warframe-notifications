import os
import discord
import aiohttp
import asyncio
from discord.ext import tasks, commands
from datetime import datetime
from dateutil import tz
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# --- Configuration from Environment ---
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID')) 
# New API URL
API_URL = "https://api.tenno.tools/worldstate/pc/fissures"
INTERVAL = int(os.getenv('CHECK_INTERVAL', 5))

class FissureBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.seen_fissures = set()

    async def setup_hook(self):
        self.check_fissures.start()

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        channel = self.get_channel(CHANNEL_ID)
        if channel:
            await channel.send("🚀 **Warframe Fissure Monitor (Tenno.tools) is Online.**\n"
                               f"Monitoring for **Steel Path Survival** every {INTERVAL} minutes...")
        else:
            print(f"Error: Could not find channel {CHANNEL_ID}.")

    @tasks.loop(minutes=INTERVAL)
    async def check_fissures(self):
        channel = self.get_channel(CHANNEL_ID)
        if not channel:
            return

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(API_URL) as response:
                    if response.status == 200:
                        raw_data = await response.json()
                        # tenno.tools nests the list inside fissures -> data
                        fissure_list = raw_data.get('fissures', {}).get('data', [])
                        await self.process_fissures(fissure_list, channel)
                    else:
                        print(f"API Error: {response.status}")
            except Exception as e:
                print(f"Connection Error: {e}")

    async def process_fissures(self, fissures, channel):
        current_ids = {f.get('id') for f in fissures}
        to_zone = tz.gettz('America/New_York') # EST/EDT

        for fissure in fissures:
            f_id = fissure.get('id')
            
            # Filtering logic
            is_survival = fissure.get('missionType') == "Survival"
            is_steel_path = fissure.get('hard') is True  # Added hard check
            is_not_omnia = fissure.get('tier') != "Omnia"
            is_not_requiem = fissure.get('tier') != "Requiem"

            if is_survival and is_steel_path and is_not_omnia and is_not_requiem:
                if f_id not in self.seen_fissures:
                    # Map new keys from tenno.tools API
                    node = fissure.get('location', 'Unknown Node')
                    faction = fissure.get('faction', 'Unknown Faction')
                    tier = fissure.get('tier', 'Unknown Tier')
                    
                    # Handle Unix Timestamp (int) conversion
                    expiry_timestamp = fissure.get('end')
                    expiry_dt = datetime.fromtimestamp(expiry_timestamp, tz=tz.tzutc())
                    expiry_est = expiry_dt.astimezone(to_zone)
                    time_str = expiry_est.strftime('%I:%M:%S %p EST')

                    embed = discord.Embed(
                        title="🔥 Steel Path Survival Detected!",
                        description="A new high-tier survival fissure is active.",
                        color=discord.Color.red(),
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="📍 Node", value=f"**{node}**", inline=True)
                    embed.add_field(name="💀 Faction", value=faction, inline=True)
                    embed.add_field(name="💎 Tier", value=tier, inline=True)
                    embed.add_field(name="🕒 Expires At", value=f"**{time_str}**", inline=False)
                    embed.set_footer(text="Warframe Fissure Tracker | Tenno.tools API")
                    
                    await channel.send(embed=embed)
                    self.seen_fissures.add(f_id)

        # Cleanup expired IDs to keep memory usage low
        self.seen_fissures = self.seen_fissures.intersection(current_ids)

    @check_fissures.before_loop
    async def before_check(self):
        await self.wait_until_ready()

if __name__ == "__main__":
    if TOKEN:
        bot = FissureBot()
        bot.run(TOKEN)
    else:
        print("Error: No DISCORD_TOKEN found in .env file.")