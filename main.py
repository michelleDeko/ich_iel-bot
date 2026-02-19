import fluxer
import requests
import json
import asyncio
from dotenv import load_dotenv
import sqlite3
import os

# this is a bot which posts the latest image post from ich_iel
# the code probably sucks, but it works, so I don't care
# the bot is also "stupid" because it doesn't check if the post has already been posted, this would be the next thing I would try

bot = fluxer.Bot(command_prefix="/", intents=fluxer.Intents.GUILD_MESSAGES | fluxer.Intents.GUILDS)
load_dotenv()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    asyncio.create_task(post_reddit_periodically())

async def post_reddit_periodically():
    while True:
        await post_reddit()
        await asyncio.sleep(int(os.getenv("INTERVAL", 3600)))

async def get_latest_post(subreddit):
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=5"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ich_iel-Bot/0.1)"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        try:
            data = response.json()
            if data["data"]["children"]:
                for child in data["data"]["children"]:
                    post = child["data"]
                    if post.get("post_hint") == "image" and post.get("url", "").endswith((".jpg", ".png", ".jpeg", ".gif")):
                        return post["title"], post["url"]
        except (KeyError, json.JSONDecodeError):
            return None, None
    return None, None

@bot.command()
async def setChannel(message):
    args = message.content.split()
    if len(args) == 2:
        try:
            channel_id = int(args[1])
            channel = await bot.fetch_channel(channel_id)
            guild_id = getattr(channel, "guild_id", None) or getattr(channel, "guild", {}).get("id", None)
            print(f"Setting channel to {channel_id} for guild {guild_id}")
            try:
                con = sqlite3.connect('ich_iel-bot.db')
                con = con.cursor()
                con.execute("CREATE TABLE IF NOT EXISTS channels (guild_id INTEGER PRIMARY KEY, channel_id INTEGER)")
                con.execute("INSERT OR REPLACE INTO channels (guild_id, channel_id) VALUES (?, ?)", (guild_id, channel_id))
                con.connection.commit()
                await message.channel.send(f"Channel set to {channel_id}")
            except sqlite3.Error as e:
                await message.channel.send(f"Database error: {e}")
        except ValueError:
            await message.channel.send("Invalid channel ID")
    else:
        await message.channel.send("Channel not found or invalid command format. Use: /setChannel <channel_id>")

@bot.command()
async def version(message):
    await message.channel.send("Version 0.2 is running")

async def post_reddit():
    subreddit = "ich_iel" # I guess I could make this editable through the env file, so it's not just a bot for ich_iel lol
    title, image_url = await get_latest_post(subreddit)
    if title and image_url:
        try:
            con = sqlite3.connect('ich_iel-bot.db') # i like sqlite
            con = con.cursor()
            con.execute("SELECT guild_id, channel_id FROM channels")
            rows = con.fetchall()
            if not rows:
                print("No channels set")
                return
            for guild_id, channel_id in rows:
                try:
                    channel = await bot.fetch_channel(int(channel_id))
                    if channel:
                        await channel.send(f"{title}\nOriginal post: {image_url}")
                    else:
                        print(f"Channel {channel_id} not found for guild {guild_id}")
                except Exception as e:
                    print(f"Error sending to channel {channel_id}: {e}")
        except sqlite3.Error as e:
            print(f"Database error: {e}")

if __name__ == "__main__":
    TOKEN = os.getenv("FLUXER_TOKEN")
    bot.run(TOKEN)