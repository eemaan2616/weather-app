import os

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv("WEATHER_API_KEY")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


@app.route("/")
def home():
    city = request.args.get("city")
    weather = None
    error = None

    if city:
        params = {
            "q": city,
            "appid": API_KEY,
            "units": "metric"
        }

        response = requests.get(BASE_URL, params=params)

        if response.status_code == 200:
            data = response.json()

            condition = data["weather"][0]["main"]

            weather_icons = {
                "Clear": "☀️",
                "Clouds": "☁️",
                "Rain": "🌧️",
                "Drizzle": "🌦️",
                "Thunderstorm": "⛈️",
                "Snow": "❄️",
                "Mist": "🌫️",
                "Fog": "🌫️"
            }

            icon = weather_icons.get(condition, "🌤️")

            weather = {
                "city": data["name"],
                "temperature": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "humidity": data["main"]["humidity"],
                "wind_speed": data["wind"]["speed"],
                "description": data["weather"][0]["description"],
                "icon": icon
            }

        elif response.status_code == 404:
            error = "City not found. Please try again."

        else:
            error = "Something went wrong while fetching the weather."

    return render_template(
        "index.html",
        city=city,
        weather=weather,
        error=error
    )


if __name__ == "__main__":
    app.run(debug=True)