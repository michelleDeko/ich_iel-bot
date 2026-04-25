import fluxer
import requests
import json
import asyncio
from dotenv import load_dotenv
import sqlite3
import os
import re
import logging
import random

# this is a bot which posts the latest image post from ich_iel
# the code probably sucks, but it works, so I don't care

load_dotenv()
prefix = os.getenv("COMMAND_PREFIX", "/")
bot = fluxer.Bot(command_prefix=prefix, intents=fluxer.Intents.GUILD_MESSAGES | fluxer.Intents.GUILDS | fluxer.Intents.MESSAGE_CONTENT)

task = None

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
log_formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

file_handler = logging.FileHandler("data/bot.log", encoding="utf-8")
file_handler.setFormatter(log_formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    handlers=[file_handler, console_handler],
)

@bot.event
async def on_ready():
    global task
    logging.info(f"Logged in as {bot.user}")
    if task is None or task.done():
        task = asyncio.create_task(post_reddit_periodically())

async def post_reddit_periodically():
    while True:
        await post_reddit()
        await asyncio.sleep(int(os.getenv("INTERVAL", 3600)))

async def get_latest_post(subreddit):
    post_limit = os.getenv("POST_LIMIT", 20)
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={post_limit}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ich_iel-Bot/0.3)"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        if response.headers.get("Content-Type", "").startswith("application/json"):
            try:
                data = response.json()
                logging.debug(f"Fetched data from Reddit: {data}")
                posts = []
                if data["data"]["children"]:
                    for child in data["data"]["children"]:
                        post = child["data"]
                        if post.get("post_hint") == "image" and post.get("url", "").endswith((".jpg", ".png", ".jpeg", ".gif")):
                            logging.debug(f"Found image post: {post['title']} - {post['url']}")
                            posts.append((post["title"], post["url"]))
                return posts
            except (KeyError, json.JSONDecodeError):
                logging.error(f"Error parsing Reddit response: {response.text}")
                return []
        else:
            logging.warning(f"Unexpected content type from Reddit: {response.headers.get('Content-Type')}")
            logging.warning(f"Response content: {response.text}")
            return []
    else:
        logging.error(f"Failed to fetch Reddit data (maybe a block?): {response.status_code}")
        return []

async def init_db():
    try:
        con = sqlite3.connect('data/ich_iel-bot.db')
        cur = con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS channels (guild_id INTEGER PRIMARY KEY, channel_id INTEGER)")
        cur.execute("CREATE TABLE IF NOT EXISTS posted (guild_id INTEGER, post_id VARCHAR(255), PRIMARY KEY (guild_id, post_id))")
        con.commit()
        logging.info("Database initialized successfully")
    except sqlite3.Error as e:
        logging.error(f"Database initialization error: {e}")

@bot.command()
async def setChannel(message):
    args = message.content.split()
    if len(args) == 2:
        try:
            channel_id = int(args[1])
            channel = await bot.fetch_channel(channel_id)
            guild_id = getattr(channel, "guild_id", None) or getattr(channel, "guild", {}).get("id", None)
            author_id = message.author.id
            guild = await bot.fetch_guild(guild_id)
            member = await guild.fetch_member(author_id)
            if not member.user.id == guild.owner_id:
                await message.channel.send(f"You need to be administrator to use this command.")
                return
            logging.info(f"Setting channel to {channel_id} for guild {guild_id}")
            try:
                con = sqlite3.connect('data/ich_iel-bot.db')
                cur = con.cursor()
                cur.execute("INSERT OR REPLACE INTO channels (guild_id, channel_id) VALUES (?, ?)", (guild_id, channel_id))
                con.commit()
                await message.channel.send(f"Channel set to {channel_id}")
            except sqlite3.Error as e:
                logging.error(f"Database error: {e}")
                await message.channel.send(f"Database error: {e}")
        except ValueError:
            await message.channel.send("Invalid channel ID")
    else:
        await message.channel.send("Channel not found or invalid command format. Use: /setChannel <channel_id>")

@bot.command()
async def version(message):
    await message.channel.send("Version 0.4.1 is running\nSource code: https://github.com/michelleDeko/ich_iel-bot")

# the cat bot died, so i wanted to add this command to this bot
@bot.command()
async def cat(message):
    response = requests.get("https://api.thecatapi.com/v1/images/search")
    if response.status_code == 200:
        data = response.json()
        if data and isinstance(data, list) and "url" in data[0]:
            await message.channel.send(data[0]["url"])
        else:
            await message.channel.send("Could not fetch cat image")
    else:
        await message.channel.send("Failed to fetch cat image")

# i thought dogs and foxes would be nice to have too
@bot.command()
async def dog(message):
    response = requests.get("https://dog.ceo/api/breeds/image/random")
    if response.status_code == 200:
        data = response.json()
        if data and isinstance(data, dict) and "message" in data:
            await message.channel.send(data["message"])
        else:
            await message.channel.send("Could not fetch dog image")
    else:
        await message.channel.send("Failed to fetch dog image")

@bot.command()
async def fox(message):
    response = requests.get("https://randomfox.ca/floof/")
    if response.status_code == 200:
        data = response.json()
        if data and isinstance(data, dict) and "image" in data:
            await message.channel.send(data["image"])
        else:
            await message.channel.send("Could not fetch fox image")
    else:
        await message.channel.send("Failed to fetch fox image")

async def post_reddit():
    subreddit = os.getenv("SUBREDDIT", "ich_iel")
    posts = await get_latest_post(subreddit)
    if not posts:
        logging.info("No image posts found.")
        return
    try:
        con = sqlite3.connect('data/ich_iel-bot.db')
        cur = con.cursor()
        cur.execute("SELECT guild_id, channel_id FROM channels")
        rows = cur.fetchall()
        if not rows:
            logging.info("No channels set")
            return
        for guild_id, channel_id in rows:
            logging.info(f"Processing guild {guild_id}")
            for title, image_url in posts:
                post_id_match = re.search(r"/([^/]+)\.(jpg|png|jpeg|gif)$", image_url)
                if not post_id_match:
                    continue
                post_id = post_id_match.group(1)
                is_posted = cur.execute("SELECT post_id FROM posted WHERE guild_id = ? AND post_id = ?", (guild_id, post_id)).fetchone()
                if is_posted:
                    logging.debug(f"Post {post_id} already posted in guild {guild_id}, skipping.")
                    continue
                try:
                    channel = await bot.fetch_channel(int(channel_id))
                    if channel:
                        if await check_guild(guild_id):
                            await channel.send(f"{title}\nOriginal post: {image_url}")
                            cur.execute("INSERT OR REPLACE INTO posted (guild_id, post_id) VALUES (?, ?)", (guild_id, post_id))
                            con.commit()
                            logging.info(f"Posted to channel {channel_id} in guild {guild_id}")
                            break
                        else:
                            logging.warning(f"Bot is not in guild {guild_id}, removing guild from database")
                            cur.execute("DELETE FROM channels WHERE guild_id = ?", (guild_id,))
                            cur.execute("DELETE FROM posted WHERE guild_id = ?", (guild_id,))
                            con.commit()
                            break
                    else:
                        logging.warning(f"Channel {channel_id} not found for guild {guild_id}")
                except Exception as e:
                    logging.error(f"Error sending to channel {channel_id}: {e}")
            logging.debug("All posts processed.")
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")

@bot.event
async def on_message(message):
    cat_keywords = ["cat", "katze", "meow", "miau"]
    if any(word in message.content.lower() for word in cat_keywords):
        # I need more cat emotes
        cat_reactions = ["<:flowercat:1494345195448304817>", "😾", "<:blehcat:1494355924738195854>", "<:honestreactioncat:1494356157782122892>"]
        reaction = random.choice(cat_reactions)
        await message.add_reaction(reaction)

async def check_guild(guild_id):
    try:
        guild = await bot.fetch_guild(guild_id)
        logging.info(f"Bot is still in guild: {guild.name}")
        return True
    except fluxer.NotFound:
        logging.warning(f"Bot is not in guild {guild_id}")
        return False
    except fluxer.Forbidden:
        logging.warning(f"Bot doesn't have access to guild {guild_id}")
        return False

if __name__ == "__main__":
    logging.info("Starting bot...")
    asyncio.run(init_db())
    TOKEN = os.getenv("FLUXER_TOKEN")
    if not TOKEN:
        logging.error("Error: FLUXER_TOKEN not found in environment variables")
    else:
        bot.run(TOKEN)