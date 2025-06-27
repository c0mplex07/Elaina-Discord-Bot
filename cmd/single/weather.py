import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import os
import math
import unicodedata
from typing import Tuple, Optional
from datetime import datetime, timedelta, timezone

os.makedirs("assets", exist_ok=True)

API_KEY = os.getenv("2f85f23cf7afe5babe7864e4d48c30a6", "4403f29d9c27407f23a50a1eb61bafec")

CITIES = [
    "Long Xuyên", "Vũng Tàu", "Bắc Giang", "Bắc Kạn", "Bạc Liêu", "Bắc Ninh",
    "Quy Nhơn", "Thủ Dầu Một", "Đồng Xoài", "Phan Thiết", "Cà Mau", "Cao Bằng",
    "Buôn Ma Thuột", "Gia Nghĩa", "Điện Biên Phủ", "Biên Hòa", "Cao Lãnh", "Pleiku",
    "Hà Giang", "Phủ Lý", "Hà Tĩnh", "Hải Dương", "Vi Thanh", "Hòa Bình", "Hưng Yên",
    "Nha Trang", "Rạch Giá", "Kon Tum", "Lai Châu", "Đà Lạt", "Lạng Sơn", "Lào Cai",
    "Tân An", "Nam Định", "Vinh", "Ninh Bình", "Phan Rang-Tháp Chàm", "Việt Trì",
    "Tuy Hòa", "Đồng Hới", "Tam Kỳ", "Quảng Ngãi", "Hạ Long", "Đồng Hà", "Sóc Trăng",
    "Sơn La", "Tây Ninh", "Thái Bình", "Thái Nguyên", "Thanh Hóa", "Huế", "Mỹ Tho",
    "Trà Vinh", "Tuyên Quang", "Vĩnh Long", "Vĩnh Yên", "Yên Bái", "Hà Nội",
    "Thành phố Hồ Chí Minh", "Đà Nẵng", "Hải Phòng", "Cần Thơ"
]

COLOR_MAP = {
    "sunny": 0xFFD700,
    "rain": 0x1E90FF,
    "cloudy": 0xA9A9A9,
    "storm": 0x800080,
    "overcast": 0x2F4F4F,
}

THUMBNAIL_MAP = {
    "sunny": "assets/sunny.jpg",
    "rain": "assets/rain.jpg",
    "cloudy": "assets/cloudy.jpg",
    "storm": "assets/storm.jpg",
    "overcast": "assets/overcast.jpg"
}

def remove_accents(input_str: str) -> str:
    normalized = unicodedata.normalize("NFKD", input_str)
    result = "".join([c for c in normalized if not unicodedata.combining(c)])
    return result.replace("Đ", "D").replace("đ", "d")

def parse_condition(description: str) -> str:
    desc = description.lower()
    if "storm" in desc or "thunder" in desc:
        return "storm"
    elif "rain" in desc:
        return "rain"
    elif "sunny" in desc or "clear" in desc:
        return "sunny"
    elif "overcast" in desc or "dark" in desc:
        return "overcast"
    elif "cloud" in desc:
        return "cloudy"
    return "overcast"

def deg_to_compass(deg: float) -> str:
    directions = ['North', 'Northeast', 'East', 'Southeast', 'South', 'Southwest', 'West', 'Northwest']
    idx = int((deg + 22.5) / 45) % 8
    return directions[idx]

def convert_owm_aqi(api_aqi: int) -> Tuple[int, str]:
    mapping = {
        1: (25, "Good"),
        2: (75, "Moderate"),
        3: (125, "Unhealthy for sensitive groups"),
        4: (175, "Unhealthy"),
        5: (250, "Very Unhealthy")
    }
    return mapping.get(api_aqi, (0, "Unknown"))

def date_to_weekday(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    weekday = dt.weekday()
    mapping = {
        0: "Monday",
        1: "Tuesday",
        2: "Wednesday",
        3: "Thursday",
        4: "Friday",
        5: "Saturday",
        6: "Sunday"
    }
    return mapping.get(weekday, date_str)

async def fetch_weather(city: str) -> Optional[dict]:
    weather_url = "https://api.openweathermap.org/data/2.5/weather"
    params_weather = {
        "q": f"{city},VN",
        "appid": API_KEY,
        "units": "metric",
        "lang": "en"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(weather_url, params=params_weather) as response:
                if response.status != 200:
                    return None
                data = await response.json()
                main = data.get("main", {})
                weather = data.get("weather", [{}])[0]
                wind = data.get("wind", {})
                sys = data.get("sys", {})
                coord = data.get("coord", {})
    except Exception:
        return None

    lat = coord.get("lat")
    lon = coord.get("lon")
    uv_index = None
    aqi_value = None
    aqi_desc = "Unknown"
    if lat is not None and lon is not None:
        uv_url = "https://api.openweathermap.org/data/2.5/uvi"
        params_uv = {
            "lat": lat,
            "lon": lon,
            "appid": API_KEY
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(uv_url, params=params_uv) as response_uv:
                    if response_uv.status == 200:
                        data_uv = await response_uv.json()
                        uv_index = data_uv.get("value")
        except Exception:
            uv_index = None

        air_url = "https://api.openweathermap.org/data/2.5/air_pollution"
        params_air = {
            "lat": lat,
            "lon": lon,
            "appid": API_KEY
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(air_url, params=params_air) as response_air:
                    if response_air.status == 200:
                        data_air = await response_air.json()
                        api_aqi = data_air.get("list", [{}])[0].get("main", {}).get("aqi")
                        aqi_value, aqi_desc = convert_owm_aqi(api_aqi)
        except Exception:
            aqi_value = None

    wind_deg = wind.get("deg")
    wind_direction = deg_to_compass(wind_deg) if wind_deg is not None else "N/A"

    return {
        "temperature": main.get("temp"),
        "humidity": main.get("humidity"),
        "wind_speed": wind.get("speed"),
        "wind_deg": wind.get("deg"),
        "wind_direction": wind_direction,
        "pressure": main.get("pressure"),
        "cloudness": weather.get("description"),
        "icon": weather.get("icon"),
        "country": sys.get("country"),
        "uv_index": uv_index,
        "aqi": aqi_value,
        "aqi_desc": aqi_desc,
        "lat": lat,
        "lon": lon
    }

async def fetch_day_extremes(lat: float, lon: float) -> Tuple[Optional[float], Optional[float]]:
    tz = timezone(timedelta(hours=7))
    now = datetime.now(tz)
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    dt_timestamp = int(now.timestamp())
    timemachine_url = "https://api.openweathermap.org/data/2.5/onecall/timemachine"
    params = {
        "lat": lat,
        "lon": lon,
        "dt": dt_timestamp,
        "appid": API_KEY,
        "units": "metric"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(timemachine_url, params=params) as response:
                if response.status != 200:
                    return None, None
                data = await response.json()
    except Exception:
        return None, None
    hourly = data.get("hourly", [])
    temps = []
    for item in hourly:
        item_dt = datetime.fromtimestamp(item.get("dt"), tz)
        if today_midnight <= item_dt <= now:
            temps.append(item.get("temp"))
    if temps:
        return max(temps), min(temps)
    else:
        return None, None

async def fetch_forecast(city: str) -> list:
    forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
    params_forecast = {
        "q": f"{city},VN",
        "appid": API_KEY,
        "units": "metric",
        "lang": "vi"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(forecast_url, params=params_forecast) as response:
                if response.status != 200:
                    return []
                data = await response.json()
    except Exception:
        return []
    
    forecasts = data.get("list", [])
    daily_forecasts = {}
    for item in forecasts:
        dt_txt = item.get("dt_txt")
        if dt_txt:
            date = dt_txt.split()[0]
            temp = item.get("main", {}).get("temp")
            pop = item.get("pop", 0)
            if date in daily_forecasts:
                daily_forecasts[date]["temps"].append(temp)
                daily_forecasts[date]["pops"].append(pop)
            else:
                daily_forecasts[date] = {"temps": [temp], "pops": [pop]}
    
    sorted_dates = sorted(daily_forecasts.keys())
    tz = timezone(timedelta(hours=7))
    today_str = datetime.now(tz).strftime("%Y-%m-%d")
    future_dates = [date for date in sorted_dates if date > today_str]
    
    forecast_results = []
    for date in future_dates[:3]:
        temps = daily_forecasts[date]["temps"]
        pops = daily_forecasts[date]["pops"]
        avg_temp = round(sum(temps) / len(temps), 1)
        max_pop = max(pops) * 100
        weekday = date_to_weekday(date)
        forecast_results.append({
            "weekday": weekday,
            "avg_temp": avg_temp,
            "chance_rain": f"{int(max_pop)}%"
        })
    return forecast_results

class WeatherCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="weather", description="Weather forecast")
    @app_commands.describe(city="City name")
    async def weather(self, interaction: discord.Interaction, city: str):
        await interaction.response.defer()

        city_normalized = remove_accents(city)
        weather_data = await fetch_weather(city_normalized)
        if not weather_data or weather_data["temperature"] is None:
            await interaction.followup.send("Location not found!")
            return

        lat = weather_data.get("lat")
        lon = weather_data.get("lon")
        day_max, day_min = None, None
        if lat is not None and lon is not None:
            day_max, day_min = await fetch_day_extremes(lat, lon)
        if day_max is None or day_min is None:
            day_max = weather_data.get("temperature")
            day_min = weather_data.get("temperature")
        
        temp = math.ceil(weather_data["temperature"])
        humidity = weather_data["humidity"]
        wind_speed = weather_data["wind_speed"]
        wind_direction = weather_data["wind_direction"]
        pressure = weather_data["pressure"]
        cloudness = weather_data["cloudness"]
        icon = weather_data["icon"]
        country = weather_data["country"]
        uv_index = weather_data["uv_index"]
        aqi = weather_data["aqi"]
        aqi_desc = weather_data["aqi_desc"]

        condition = parse_condition(cloudness)
        color = COLOR_MAP.get(condition, 0x0099ff)

        embed = discord.Embed(
            color=color,
            title=f"Current temperature is {temp}°C in {city}, {country}"
        )
        embed.set_author(name=f"Hello, {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="Highest temperature", value=f"{day_max}°C", inline=True)
        embed.add_field(name="Lowest temperature", value=f"{day_min}°C", inline=True)
        embed.add_field(name="Humidity", value=f"{humidity}%", inline=True)
        embed.add_field(name="Wind speed", value=f"{wind_speed} m/s, {wind_direction}", inline=True)
        embed.add_field(name="Pressure", value=f"{pressure} hPa", inline=True)
        embed.add_field(name="Weather condition", value=cloudness.capitalize(), inline=True)
        embed.add_field(name="UV index", value=f"{uv_index if uv_index is not None else 'N/A'}", inline=True)
        embed.add_field(name="Air quality index", value=f"{aqi if aqi is not None else 'N/A'}", inline=True)
        embed.add_field(name="Air quality", value=aqi_desc, inline=True)
        embed.set_footer(text="Information may not be completely accurate!", 
                         icon_url=self.bot.user.display_avatar.url if self.bot.user else None)

        forecast_data = await fetch_forecast(city_normalized)
        if forecast_data:
            forecast_str = ""
            for fc in forecast_data:
                forecast_str += f"{fc['weekday']}: {fc['avg_temp']}°C, chance of rain: {fc['chance_rain']}\n"
            embed.add_field(name="3-day forecast", value=forecast_str, inline=False)
        else:
            embed.add_field(name="3-day forecast", value="No data available", inline=False)

        thumbnail_path = THUMBNAIL_MAP.get(condition)
        if thumbnail_path and os.path.exists(thumbnail_path):
            file = discord.File(thumbnail_path, filename="weather_image.png")
            embed.set_image(url="attachment://weather_image.png")
        else:
            file = None
            embed.set_image(url=f"http://openweathermap.org/img/w/{icon}.png")

        if file:
            await interaction.followup.send(embed=embed, file=file)
        else:
            await interaction.followup.send(embed=embed)

    @weather.autocomplete("city")
    async def city_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=city, value=city)
            for city in CITIES if current.lower() in city.lower()
        ][:25]

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception):
        try:
            await interaction.followup.send("An error occurred while processing your request.", ephemeral=True)
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(WeatherCog(bot))
