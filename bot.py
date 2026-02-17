import os
import discord
from discord.ext import commands
import yt_dlp
import asyncio
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# MUSIC DATA PER SERVER
# =========================
music = {}

def get_guild_data(guild):
    if guild.id not in music:
        music[guild.id] = {
            "queue": [],
            "loop": False,
            "volume": 0.5,
            "now": None
        }
    return music[guild.id]

# =========================
# YTDLP
# =========================
ytdl = yt_dlp.YoutubeDL({
    "format": "bestaudio",
    "noplaylist": True,
    "quiet": True
})

FFMPEG_OPTIONS = {
    "options": "-vn"
}

# =========================
# PLAY NEXT
# =========================
async def play_next(ctx):
    data = get_guild_data(ctx.guild)
    vc = ctx.voice_client

    if data["loop"] and data["now"]:
        url = data["now"]
    elif data["queue"]:
        url = data["queue"].pop(0)
        data["now"] = url
    else:
        data["now"] = None
        return

    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

    if "entries" in info:
        info = info["entries"][0]

    source = info["url"]
    title = info["title"]

    audio = discord.PCMVolumeTransformer(
        discord.FFmpegPCMAudio(source, **FFMPEG_OPTIONS),
        volume=data["volume"]
    )

    vc.play(audio, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
    await ctx.send(f"🎵 Now playing: **{title}**")

# =========================
# JOIN
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

    await ctx.send("✅ Join voice")

# =========================
# PLAY
# =========================
@bot.command()
async def play(ctx, *, search):
    if not ctx.voice_client:
        await ctx.invoke(join)

    data = get_guild_data(ctx.guild)

    if not search.startswith("http"):
        search = f"ytsearch:{search}"

    data["queue"].append(search)

    if not ctx.voice_client.is_playing():
        await play_next(ctx)
    else:
        await ctx.send("➕ Ditambahkan ke queue")

# =========================
# SKIP
# =========================
@bot.command()
async def skip(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.send("⏭ Skip")

# =========================
# QUEUE
# =========================
@bot.command()
async def queue(ctx):
    data = get_guild_data(ctx.guild)
    if not data["queue"]:
        return await ctx.send("Queue kosong")

    msg = "\n".join(f"{i+1}. {q}" for i, q in enumerate(data["queue"][:10]))
    await ctx.send(f"📜 Queue:\n{msg}")

# =========================
# NOW PLAYING
# =========================
@bot.command()
async def now(ctx):
    data = get_guild_data(ctx.guild)
    if data["now"]:
        await ctx.send(f"🎵 Now playing:\n{data['now']}")
    else:
        await ctx.send("Tidak ada lagu")

# =========================
# PAUSE
# =========================
@bot.command()
async def pause(ctx):
    if ctx.voice_client:
        ctx.voice_client.pause()
        await ctx.send("⏸ Paused")

# =========================
# RESUME
# =========================
@bot.command()
async def resume(ctx):
    if ctx.voice_client:
        ctx.voice_client.resume()
        await ctx.send("▶ Resume")

# =========================
# STOP
# =========================
@bot.command()
async def stop(ctx):
    data = get_guild_data(ctx.guild)
    data["queue"].clear()
    if ctx.voice_client:
        ctx.voice_client.stop()
    await ctx.send("⏹ Stop + queue clear")

# =========================
# LOOP
# =========================
@bot.command()
async def loop(ctx):
    data = get_guild_data(ctx.guild)
    data["loop"] = not data["loop"]
    await ctx.send(f"🔁 Loop {'ON' if data['loop'] else 'OFF'}")

# =========================
# VOLUME
# =========================
@bot.command()
async def volume(ctx, vol: int):
    data = get_guild_data(ctx.guild)

    if not 0 <= vol <= 100:
        return await ctx.send("0-100")

    data["volume"] = vol / 100

    if ctx.voice_client and ctx.voice_client.source:
        ctx.voice_client.source.volume = data["volume"]

    await ctx.send(f"🔊 Volume {vol}%")

# =========================
# LEAVE
# =========================
@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Bye")

# =========================
@bot.event
async def on_ready():
    print("🔥 PRO MUSIC BOT READY")

bot.run(TOKEN)
