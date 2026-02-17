import os
import discord
from discord.ext import commands
import yt_dlp
import asyncio
from dotenv import load_dotenv

# =========================
# LOAD ENV
# =========================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# =========================
# DISCORD SETUP
# =========================
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# MUSIC DATA PER SERVER
# =========================
music = {}

def get_data(guild):
    if guild.id not in music:
        music[guild.id] = {
            "queue": [],
            "now": None,
            "loop": False,
            "volume": 0.5
        }
    return music[guild.id]

# =========================
# YTDLP CONFIG
# =========================
ytdl = yt_dlp.YoutubeDL({
    "format": "bestaudio/best",
    "quiet": True,
    "default_search": "ytsearch"
})

FFMPEG_OPTIONS = {
    "options": "-vn"
}

# =========================
# PLAY NEXT SONG
# =========================
async def play_next(ctx):
    data = get_data(ctx.guild)
    vc = ctx.voice_client

    if not vc:
        return

    if data["loop"] and data["now"]:
        url = data["now"]
    elif data["queue"]:
        url = data["queue"].pop(0)
        data["now"] = url
    else:
        data["now"] = None
        await ctx.send("Queue selesai")
        return

    loop = asyncio.get_event_loop()

    try:
        info = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=False)
        )

        if "entries" in info:
            info = info["entries"][0]

        source_url = info["url"]
        title = info.get("title", "Unknown")

        audio = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(source_url, **FFMPEG_OPTIONS),
            volume=data["volume"]
        )

        vc.play(
            audio,
            after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
        )

        await ctx.send(f"🎵 Now playing: **{title}**")

    except Exception as e:
        await ctx.send("Error play lagu")
        print(e)
        await play_next(ctx)

# =========================
# JOIN VC
# =========================
@bot.command()
async def join(ctx):
    if not ctx.author.voice:
        return await ctx.send("Masuk voice channel dulu")

    channel = ctx.author.voice.channel

    if ctx.voice_client:
        await ctx.voice_client.move_to(channel)
    else:
        await channel.connect()

    await ctx.send("Join voice")

# =========================
# PLAY MUSIC
# =========================
@bot.command()
async def play(ctx, *, search):
    if not ctx.voice_client:
        await ctx.invoke(join)

    data = get_data(ctx.guild)
    data["queue"].append(search)

    if not ctx.voice_client.is_playing():
        await play_next(ctx)
    else:
        await ctx.send("Ditambahkan ke queue")

# =========================
# SKIP
# =========================
@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Skip")

# =========================
# QUEUE
# =========================
@bot.command()
async def queue(ctx):
    data = get_data(ctx.guild)

    if not data["queue"]:
        return await ctx.send("Queue kosong")

    msg = "\n".join(f"{i+1}. {q}" for i, q in enumerate(data["queue"][:10]))
    await ctx.send(f"Queue:\n{msg}")

# =========================
# NOW PLAYING
# =========================
@bot.command()
async def now(ctx):
    data = get_data(ctx.guild)
    if data["now"]:
        await ctx.send(f"Now playing:\n{data['now']}")
    else:
        await ctx.send("Tidak ada lagu")

# =========================
# PAUSE
# =========================
@bot.command()
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("Paused")

# =========================
# RESUME
# =========================
@bot.command()
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("Resume")

# =========================
# STOP
# =========================
@bot.command()
async def stop(ctx):
    data = get_data(ctx.guild)
    data["queue"].clear()

    if ctx.voice_client:
        ctx.voice_client.stop()

    await ctx.send("Stop + queue clear")

# =========================
# LOOP TOGGLE
# =========================
@bot.command()
async def loop(ctx):
    data = get_data(ctx.guild)
    data["loop"] = not data["loop"]
    await ctx.send(f"Loop {'ON' if data['loop'] else 'OFF'}")

# =========================
# VOLUME
# =========================
@bot.command()
async def volume(ctx, vol: int):
    if not 0 <= vol <= 100:
        return await ctx.send("Volume 0-100")

    data = get_data(ctx.guild)
    data["volume"] = vol / 100

    if ctx.voice_client and ctx.voice_client.source:
        ctx.voice_client.source.volume = data["volume"]

    await ctx.send(f"Volume {vol}%")

# =========================
# LEAVE VC
# =========================
@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Keluar voice")

# =========================
@bot.event
async def on_ready():
    print("PRO MUSIC BOT ONLINE")

bot.run(TOKEN)
