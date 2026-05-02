import os
import asyncio
import aiohttp
import discord
from datetime import datetime
from dateutil import tz
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# --- Configuration from Environment ---
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
API_URL = "https://api.tenno.tools/worldstate/pc/fissures"
INTERVAL = int(os.getenv('CHECK_INTERVAL', 5)) * 60  # Convert minutes to seconds

class FissureMonitor:
    def __init__(self):
        self.seen_fissures = set()
        self.to_zone = tz.gettz('America/New_York')

    async def fetch_fissures(self, session):
        """Fetch current fissures from Tenno.tools"""
        try:
            async with session.get(API_URL) as response:
                if response.status == 200:
                    raw_data = await response.json()
                    return raw_data.get('fissures', {}).get('data', [])
                else:
                    print(f"[{datetime.now()}] API Error: {response.status}")
        except Exception as e:
            print(f"[{datetime.now()}] Connection Error: {e}")
        return []

    async def process_fissures(self, fissures, webhook):
        """Filter and send notifications via Webhook"""
        current_ids = {f.get('id') for f in fissures}
        
        for fissure in fissures:
            f_id = fissure.get('id')
            
            # Filtering logic
            is_survival = fissure.get('missionType') == "Survival"
            is_steel_path = fissure.get('hard') is True
            is_not_omnia = fissure.get('tier') != "Omnia"
            is_not_requiem = fissure.get('tier') != "Requiem"
            is_corrupted = fissure.get('faction') == "Corrupted"

            if all([is_survival, is_steel_path, is_not_omnia, is_not_requiem, is_corrupted]):
                if f_id not in self.seen_fissures:
                    node = fissure.get('location', 'Unknown Node')
                    faction = fissure.get('faction', 'Unknown Faction')
                    tier = fissure.get('tier', 'Unknown Tier')
                    
                    # Time conversion
                    expiry_timestamp = fissure.get('end')
                    expiry_dt = datetime.fromtimestamp(expiry_timestamp, tz=tz.tzutc())
                    expiry_est = expiry_dt.astimezone(self.to_zone)
                    time_str = expiry_est.strftime('%I:%M:%S %p EST')

                    # Create Embed
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
                    
                    # Send via Webhook
                    await webhook.send(embed=embed, username="Fissure Monitor")
                    self.seen_fissures.add(f_id)

        # Cleanup expired IDs
        self.seen_fissures = self.seen_fissures.intersection(current_ids)

    async def start(self):
        """Main execution loop"""
        print(f"🚀 Fissure Monitor Started. Interval: {INTERVAL/60} minutes.")
        
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
            
            while True:
                fissures = await self.fetch_fissures(session)
                if fissures:
                    await self.process_fissures(fissures, webhook)
                
                await asyncio.sleep(INTERVAL)

if __name__ == "__main__":
    if not WEBHOOK_URL:
        print("Error: WEBHOOK_URL not found in .env file.")
    else:
        monitor = FissureMonitor()
        try:
            asyncio.run(monitor.start())
        except KeyboardInterrupt:
            print("Monitor stopped.")