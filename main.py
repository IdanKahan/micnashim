import discord
from discord.ext import commands, tasks
import requests
import asyncio
from datetime import datetime, timedelta
import os
from webserver import keep_alive

# Define constants
bot_token = os.environ.get('bot_token')
api_key = os.environ.get('api_key')
CHANNEL_ID = 1249840156605677628  # Replace with your target channel ID

# Define all intents
intents = discord.Intents().all()

# Initialize bot with intents
bot = commands.Bot(command_prefix='/', intents=intents)

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

    # Determine the video path based on the temperature
    temperature = weather_data['current']['temp_c']
    video_path = get_video_path(temperature)

    # Send the video as a message
    await ctx.send(file=discord.File(video_path))

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

# Function to get video path based on temperature
def get_video_path(temperature):
    if temperature >= 30:
        return "very_hot.mp4"  # Local path to the "very hot" video
    elif temperature >= 24:
        return "hot.mp4"  # Local path to the "hot" video
    elif temperature < 15:
        return "very_cold.mp4"  # Local path to the "very cold" video
    else:
        return "cold.mp4"  # Local path to the "cold" video

# Task to send the video every day at 7 AM
@tasks.loop(hours=24)
async def daily_shorts():
    now = datetime.utcnow()
    target_time = datetime.combine(now.date(), datetime.strptime("04:00:00", "%H:%M:%S").time())
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

        # Determine the video path based on the temperature
        temperature = weather_data['current']['temp_c']
        video_path = get_video_path(temperature)

        # Send the video as a message with the specified text
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        await channel.send("----------------------------------------------------")
        await channel.send(f"                                    {date_str}                                      ")
        await channel.send(file=discord.File(video_path))

# Keep the bot alive with a webserver
keep_alive()

# Run the bot
bot.run(bot_token)
