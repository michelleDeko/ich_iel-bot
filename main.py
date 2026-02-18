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
            try:
                con = sqlite3.connect('ich_iel-bot.db')
                con = con.cursor()
                con.execute("CREATE TABLE IF NOT EXISTS channels (key TEXT PRIMARY KEY, value TEXT)")
                con.execute("INSERT OR REPLACE INTO channels (key, value) VALUES (?, ?)", ("channel_id", str(channel_id)))
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
    await message.channel.send("Version 0.1 is running")

async def post_reddit():
    subreddit = "ich_iel" # I guess I could make this editable through the env file, so it's not just a bot for ich_iel lol
    title, image_url = await get_latest_post(subreddit)
    if title and image_url:
        try:
            con = sqlite3.connect('ich_iel-bot.db') # i like sqlite
            con = con.cursor()
            con.execute("SELECT value FROM channels WHERE key = ?", ("channel_id",))
            result = con.fetchone()
            if result:
                channel_id = int(result[0])
                channel = await bot.fetch_channel(channel_id)
                if channel:
                    await channel.send(f"{title}\n{image_url}")
                else:
                    print("Channel not found")
            else:
                print("No channel set")
        except sqlite3.Error as e:
            print(f"Database error: {e}")

if __name__ == "__main__":
    TOKEN = os.getenv("FLUXER_TOKEN")
    bot.run(TOKEN)