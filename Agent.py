"""
weather_email.py
-----------------
Replaces a Zapier "daily weather email" automation with a single Python script.

What it does:
1. Calls the Open-Meteo API for current temperature, condition,
   description, and humidity (no API key required).
2. Calls the Open-Meteo Forecast endpoint to get precipitation probability.
3. Builds a plain-text email and sends it through Gmail SMTP (STARTTLS).
4. Waits in a loop and automatically sends the email every day at 8:00 AM
   London time (this script must stay running for that to happen).

Run manually any time with:  python Agent.py --now
"""

import os
import sys
import time
import smtplib
import requests
import pytz
from datetime import datetime
from email.mime.text import MIMEText

# Ensure Windows terminal handles UTF-8 characters properly
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

# =====================================================================
# 1. CONFIGURATION
# =====================================================================

# --- Weather Location (Open-Meteo: Free, No API Key Required) ---
CITY = os.environ.get("WEATHER_CITY", "London")
COUNTRY_CODE = os.environ.get("WEATHER_COUNTRY_CODE", "GB")  # ISO country code

# --- Gmail SMTP ---
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_EMAIL = os.environ.get("SMTP_EMAIL", "poojashree71512@gmail.com")         # Sender Gmail
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "lygo huzg fefg agda")   # Gmail App Password
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL", "jananijana538@gmail.com") # Recipient Email

# --- Rain warning threshold (percent) ---
RAIN_THRESHOLD_PERCENT = int(os.environ.get("RAIN_THRESHOLD_PERCENT", 50))

# --- Schedule time (24-hour format, London time) ---
SCHEDULED_HOUR = 8
SCHEDULED_MINUTE = 0
LONDON_TZ = pytz.timezone("Europe/London")

# WMO Weather interpretation codes (Open-Meteo)
WMO_DESCRIPTIONS = {
    0: ("Clear", "Clear sky"),
    1: ("Mainly Clear", "Mainly clear sky"),
    2: ("Partly Cloudy", "Partly cloudy"),
    3: ("Overcast", "Overcast"),
    45: ("Fog", "Fog"),
    48: ("Fog", "Depositing rime fog"),
    51: ("Drizzle", "Light drizzle"),
    53: ("Drizzle", "Moderate drizzle"),
    55: ("Drizzle", "Dense drizzle"),
    56: ("Freezing Drizzle", "Light freezing drizzle"),
    57: ("Freezing Drizzle", "Dense freezing drizzle"),
    61: ("Rain", "Slight rain"),
    63: ("Rain", "Moderate rain"),
    65: ("Rain", "Heavy rain"),
    66: ("Freezing Rain", "Light freezing rain"),
    67: ("Freezing Rain", "Heavy freezing rain"),
    71: ("Snow", "Slight snow"),
    73: ("Snow", "Moderate snow"),
    75: ("Snow", "Heavy snow"),
    77: ("Snow", "Snow grains"),
    80: ("Rain Showers", "Slight rain showers"),
    81: ("Rain Showers", "Moderate rain showers"),
    82: ("Rain Showers", "Violent rain showers"),
    85: ("Snow Showers", "Slight snow showers"),
    86: ("Snow Showers", "Heavy snow showers"),
    95: ("Thunderstorm", "Thunderstorm"),
    96: ("Thunderstorm", "Thunderstorm with slight hail"),
    99: ("Thunderstorm", "Thunderstorm with heavy hail"),
}

# Cache to avoid duplicate requests during the same job run
_weather_cache = {}


# =====================================================================
# 2. FETCH WEATHER DATA (Open-Meteo Geocoding & Forecast APIs)
# =====================================================================

def fetch_weather_from_open_meteo():
    """Fetch current weather and hourly forecast from Open-Meteo."""
    global _weather_cache

    # 1. Geocoding lookup for CITY
    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    geo_params = {
        "name": CITY,
        "count": 1,
        "language": "en",
        "format": "json"
    }
    geo_resp = requests.get(geo_url, params=geo_params, timeout=10)
    if geo_resp.status_code != 200:
        raise RuntimeError(f"Geocoding API request failed (status {geo_resp.status_code}): {geo_resp.text}")

    geo_data = geo_resp.json()
    if not geo_data.get("results"):
        raise RuntimeError(f"City '{CITY}' not found. Check the spelling.")

    location = geo_data["results"][0]
    lat = location["latitude"]
    lon = location["longitude"]
    city_name = location["name"]

    # 2. Weather & forecast lookup
    forecast_url = "https://api.open-meteo.com/v1/forecast"
    forecast_params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,cloud_cover,wind_speed_10m",
        "hourly": "precipitation_probability",
        "forecast_days": 1,
        "timezone": "auto"
    }
    forecast_resp = requests.get(forecast_url, params=forecast_params, timeout=10)
    if forecast_resp.status_code != 200:
        raise RuntimeError(f"Forecast API request failed (status {forecast_resp.status_code}): {forecast_resp.text}")

    forecast_data = forecast_resp.json()
    _weather_cache = {
        "city_name": city_name,
        "data": forecast_data,
        "fetched_at": time.time()
    }
    return _weather_cache


def get_current_weather():
    """Fetch current weather details for CITY from Open-Meteo."""
    global _weather_cache
    if not _weather_cache or time.time() - _weather_cache.get("fetched_at", 0) > 60:
        fetch_weather_from_open_meteo()

    city_name = _weather_cache["city_name"]
    current = _weather_cache["data"].get("current", {})
    code = current.get("weather_code", 0)
    condition, description = WMO_DESCRIPTIONS.get(code, ("Unknown", f"Weather code {code}"))

    weather_info = {
        "city": city_name,
        "temperature": round(current.get("temperature_2m", 0.0), 1),
        "apparent_temperature": round(current.get("apparent_temperature", 0.0), 1),
        "condition": condition,
        "description": description,
        "humidity": current.get("relative_humidity_2m", 0),
        "wind_speed": round(current.get("wind_speed_10m", 0.0), 1),
    }
    return weather_info


# =====================================================================
# 3. GET RAIN PROBABILITY
# =====================================================================

def get_rain_probability():
    """Fetch the nearest-upcoming / maximum rain probability (%) from Open-Meteo."""
    global _weather_cache
    if not _weather_cache or time.time() - _weather_cache.get("fetched_at", 0) > 60:
        fetch_weather_from_open_meteo()

    hourly = _weather_cache["data"].get("hourly", {})
    rain_probs = hourly.get("precipitation_probability", [])

    if not rain_probs:
        return 0

    # Probability of precipitation for today
    rain_chance_percent = max(rain_probs)
    return rain_chance_percent


# =====================================================================
# 4. BUILD THE EMAIL MESSAGE
# =====================================================================

def build_email_body(weather_info, rain_chance_percent):
    """Create the plain-text email body."""
    if rain_chance_percent >= RAIN_THRESHOLD_PERCENT:
        rain_message = "Carry an umbrella today."
    else:
        rain_message = "Have a great day!"

    body = (
        "Good morning!\n\n"
        f"Here is today's weather update for {weather_info['city']}.\n\n"
        f"City: {weather_info['city']}\n"
        f"Temperature: {weather_info['temperature']} °C (Feels like: {weather_info['apparent_temperature']} °C)\n"
        f"Weather Condition: {weather_info['condition']}\n"
        f"Weather Description: {weather_info['description']}\n"
        f"Humidity: {weather_info['humidity']}%\n"
        f"Rain Chance: {rain_chance_percent}%\n"
        f"Wind Speed: {weather_info['wind_speed']} km/h\n\n"
        f"{rain_message}"
    )
    return body


# =====================================================================
# 5. SEND THE EMAIL VIA GMAIL SMTP
# =====================================================================

def send_email(subject, body):
    """Send a plain-text email using Gmail's SMTP server with STARTTLS."""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = SMTP_EMAIL
    msg["To"] = RECEIVER_EMAIL

    try:
        # Connect to Gmail's SMTP server
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
            server.starttls()                          # upgrade to a secure connection
            server.login(SMTP_EMAIL, SMTP_PASSWORD)     # log in with your App Password
            server.sendmail(SMTP_EMAIL, [RECEIVER_EMAIL], msg.as_string())
    except smtplib.SMTPAuthenticationError:
        raise RuntimeError(
            "Gmail login failed. Check SMTP_EMAIL and SMTP_PASSWORD "
            "(SMTP_PASSWORD must be a Gmail App Password, not your normal password)."
        )
    except smtplib.SMTPException as e:
        raise RuntimeError(f"Failed to send email: {e}")
    except OSError as e:
        raise RuntimeError(f"Could not connect to Gmail's SMTP server: {e}")


# =====================================================================
# 6. THE FULL WORKFLOW: run once, start to finish
# =====================================================================

def run_weather_email_job():
    """Fetch weather, build the email, send it, and print status messages."""
    try:
        print("Fetching current weather...")
        weather_info = get_current_weather()

        print("Fetching rain probability...")
        rain_chance_percent = get_rain_probability()

        # Display retrieved weather details in terminal
        print("\n" + "=" * 45)
        print(f" WEATHER REPORT: {weather_info['city'].upper()}")
        print("=" * 45)
        print(f" Temperature:        {weather_info['temperature']} °C (Feels like: {weather_info['apparent_temperature']} °C)")
        print(f" Weather Condition:  {weather_info['condition']}")
        print(f" Description:        {weather_info['description']}")
        print(f" Humidity:           {weather_info['humidity']}%")
        print(f" Rain Chance:        {rain_chance_percent}%")
        print(f" Wind Speed:         {weather_info['wind_speed']} km/h")
        if rain_chance_percent >= RAIN_THRESHOLD_PERCENT:
            print(" Advice:             ⚠️ Carry an umbrella today.")
        else:
            print(" Advice:             ☀️ Have a great day!")
        print("=" * 45 + "\n")

        print("Building email...")
        subject = f"{weather_info['city']} Weather Update"
        body = build_email_body(weather_info, rain_chance_percent)

        print(f"Sending email to {RECEIVER_EMAIL}...")
        send_email(subject, body)

        print("SUCCESS: Weather email sent to", RECEIVER_EMAIL)

    except RuntimeError as e:
        print("ERROR:", e)
    except requests.exceptions.ConnectionError:
        print("ERROR: No internet connection or the weather API could not be reached.")
    except requests.exceptions.Timeout:
        print("ERROR: The weather API request timed out. Try again.")
    except Exception as e:
        print("UNEXPECTED ERROR:", e)


# =====================================================================
# 7. SCHEDULER LOOP -- runs the job every day at 8:00 AM London time
#    This script must keep running for the scheduled email to be sent.
# =====================================================================

def start_scheduler():
    print(
        f"Scheduler started. Waiting to send the weather email every day at "
        f"{SCHEDULED_HOUR:02d}:{SCHEDULED_MINUTE:02d} London time.\n"
        "Leave this program running in the terminal."
    )

    last_run_date = None  # tracks the date we last sent the email, to avoid duplicate sends

    while True:
        now_london = datetime.now(LONDON_TZ)

        if (
            now_london.hour == SCHEDULED_HOUR
            and now_london.minute == SCHEDULED_MINUTE
            and now_london.date() != last_run_date
        ):
            run_weather_email_job()
            last_run_date = now_london.date()

        time.sleep(30)  # check twice a minute so we don't miss the exact minute


# =====================================================================
# 8. ENTRY POINT
# =====================================================================

if __name__ == "__main__":
    # Run "python weather_email.py --now" to send a test email immediately
    if "--now" in sys.argv:
        run_weather_email_job()
    else:
        start_scheduler()