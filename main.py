


bot_token = os.environ.get('bot_token')
api_key = os.environ.get('api_key')

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import discord
from discord.ext import commands, tasks
import requests
import cv2
import numpy as np
import ffmpeg
from pydub import AudioSegment
import asyncio
from datetime import datetime, timedelta
from webserver import keep_alive

# Assume api_key and bot_token are defined elsewhere
# api_key = 'your_weatherapi_key'
# bot_token = 'your_discord_bot_token'

# Define all intents
intents = discord.Intents().all()

# Initialize bot with intents
bot = commands.Bot(command_prefix='/', intents=intents)

# Channel ID to send the video to
CHANNEL_ID = 1249840156605677628

# Event listener for bot's on_ready event
@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    # Start the daily shorts task
    daily_shorts.start()

# Command to display the weather video
@bot.command()
async def shorts(ctx):
    # Fetch weather data
    weather_data = get_weather()

    # Check if weather_data contains 'current'
    if 'current' not in weather_data:
        await ctx.send("Error: Unable to fetch weather data.")
        return

    # Generate video with weather information
    video_path = generate_video(weather_data)

    # Repair the video to ensure it works on Discord
    repaired_video_path = repair_video(video_path)

    # Send video as a message
    await ctx.send(file=discord.File(repaired_video_path))

# Function to fetch weather data from WeatherAPI
def get_weather():
    # Coordinates for the location
    latitude = 32.15
    longitude = 34.83
    url = f'http://api.weatherapi.com/v1/current.json?key={api_key}&q={latitude},{longitude}'
    response = requests.get(url)
    data = response.json()
    
    # Print the JSON response for debugging
    print(data)
    
    return data

# Function to generate the video
def generate_video(weather_data):
    # Extract temperature from weather data
    temperature = weather_data['current']['temp_c']

    # Define decision based on temperature
    if temperature >= 30:
        decision = "חם רצח עדיף לבוא ערום"[::-1]
        sound_effect = "hot.mp3"  # You need to provide this audio file
    elif temperature >= 24:
        decision = "כן, חם אחושרמוטה"[::-1]
        sound_effect = "very_hot.mp3"  # You need to provide this audio file
    elif temperature < 15:
        decision = "נו וואי ברא, קפוא רצח"[::-1]
        sound_effect = "cold.mp3"  # You need to provide this audio file
    else:
        decision = "לא, קר נודר נדר"[::-1]
        sound_effect = "not_hot.mp3"  # You need to provide this audio file

    # Create images with text
    question_image = create_image("ללבוש מכנסים קצרים היום?"[::-1])
    answer_image = create_image(decision)
    background_image = create_image("")  # Blank background

    # Create video from images with fade effect
    video_path = "shorts.mp4"
    create_video_with_fade([question_image, background_image, answer_image], video_path, sound_effect)

    # Add audio effects to the video
    final_video_path = add_audio_effects(video_path, sound_effect)

    return final_video_path

# Function to create an image with text
def create_image(text):
    # Create image
    image = Image.new('RGB', (800, 400), color='#87CEEB')
    draw = ImageDraw.Draw(image)

    # Add text
    font = ImageFont.truetype('arialbd.ttf', size=70)  # Use bold font

    # Add text to image
    draw.text((400, 200), text, fill='white', font=font, anchor='mm')

    # Convert image to numpy array
    image_np = np.array(image)

    return image_np

# Function to create a video from images with fade effect
def create_video_with_fade(images, video_path, sound_effect):
    height, width, layers = images[0].shape
    video = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*'mp4v'), 24, (width, height))

    # Create fade effect
    fade_duration = 24  # 1 second at 24 fps

    # Write the first image for 4 seconds
    for _ in range(4 * 24):
        video.write(images[0])

    for i in range(len(images) - 1):
        for j in range(fade_duration):
            alpha = j / fade_duration
            frame = cv2.addWeighted(images[i], 1 - alpha, images[i + 1], alpha, 0)
            video.write(frame)

    # Load the sound effect to determine its duration
    effect = AudioSegment.from_file(sound_effect)
    effect_duration = len(effect) // 1000  # Duration in seconds

    # Write the last image for the duration of the sound effect
    for _ in range(effect_duration * 24):
        video.write(images[-1])

    video.release()

# Function to add audio effects to the video
def add_audio_effects(video_path, sound_effect):
    drumroll = AudioSegment.from_file("drumroll.mp3")  # You need to provide this audio file
    effect = AudioSegment.from_file(sound_effect)

    final_audio = drumroll + effect

    # Export the final audio to a file
    audio_path = "audio.mp3"
    final_audio.export(audio_path, format="mp3")

    # Merge video and audio
    final_video_path = "final_" + video_path
    (
        ffmpeg
        .concat(
            ffmpeg.input(video_path),
            ffmpeg.input(audio_path),
            v=1, a=1
        )
        .output(final_video_path, vcodec='libx264', acodec='aac', audio_bitrate='192k', strict='experimental')
        .run(overwrite_output=True)
    )

    return final_video_path

# Function to repair the video using ffmpeg
def repair_video(video_path):
    repaired_video_path = "repaired_" + video_path
    (
        ffmpeg
        .input(video_path)
        .output(repaired_video_path, vcodec='libx264', acodec='aac', strict='experimental')
        .run(overwrite_output=True)
    )
    return repaired_video_path

# Task to send the video every day at 7 AM
@tasks.loop(hours=24)
async def daily_shorts():
    now = datetime.utcnow()
    target_time = datetime.combine(now.date(), datetime.strptime("07:00:00", "%H:%M:%S").time())
    if now > target_time:
        target_time += timedelta(days=1)
    await asyncio.sleep((target_time - now).total_seconds())

    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        # Fetch weather data
        weather_data = get_weather()

        # Check if weather_data contains 'current'
        if 'current' not in weather_data:
            await channel.send("Error: Unable to fetch weather data.")
            return

        # Generate video with weather information
        video_path = generate_video(weather_data)

        # Repair the video to ensure it works on Discord
        repaired_video_path = repair_video(video_path)

        # Send video as a message
        await channel.send(file=discord.File(repaired_video_path))
keep_alive()

# Run the bot
bot.run(bot_token)
