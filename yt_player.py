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

async def play(ctx, *, url: str):
    guild_id = ctx._guild.id  # Guild aus der Message  
    voice_state = _bot.get_voice_state(guild_id, ctx.author.id)  
  
    if voice_state is None or voice_state.channel_id is None:
        await ctx.reply("You're not in a voice channel!")
        return
    channel = await _bot.fetch_channel(str(voice_state.channel_id))
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

    await ctx.reply(f"Playing {title} in {channel.mention}")

    async with await channel.connect(_bot) as vc:
        await vc.play_file(filename)
