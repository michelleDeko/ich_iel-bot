# at this point this bot isn't just a reddit bot anymore, maybe i should start renaming it lol
import yt_dlp
import logging
import os

AUDIO_DIR = "data/audio"

_bot = None

def setup(bot):
    global _bot
    _bot = bot
    os.makedirs(AUDIO_DIR, exist_ok=True)
    bot.command()(play)

async def play(ctx, channel_id: int, *, path: str):
    channel = await _bot.fetch_channel(str(channel_id))
    url = ctx.content[len("!play "):].strip()
    logging.info(f"Playing {url}")
    ydl_opts = {
        'format': 'm4a/bestaudio/best',
        'outtmpl': f'{AUDIO_DIR}/%(id)s.%(ext)s',
        'postprocessors': [{  # Extract audio using ffmpeg
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
        }]
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.m4a'
        title = info.get('title', 'Unknown Title')
        logging.info(f"Downloaded to {filename}")

    ctx.send(f"Playing {title} in {channel.mention}")
    
    async with await channel.connect(_bot) as vc:
        await vc.play_file(filename)
