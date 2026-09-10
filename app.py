import os
from datetime import datetime, date, timedelta

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv("WEATHER_API_KEY")

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


WEATHER_ICONS = {
    "Clear": "☀️",
    "Clouds": "☁️",
    "Rain": "🌧️",
    "Drizzle": "🌦️",
    "Thunderstorm": "⛈️",
    "Snow": "❄️",
    "Mist": "🌫️",
    "Fog": "🌫️",
    "Haze": "🌫️"
}


# Store recent searches while the app is running
recent_searches = []


def get_weather(city):
    """Get current weather and forecast for a city."""

    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric"
    }

    try:
        # Get current weather
        response = requests.get(
            BASE_URL,
            params=params,
            timeout=10
        )

        if response.status_code == 404:
            return None, [], f'We could not find "{city}". Please check the spelling.'

        if response.status_code == 401:
            return None, [], "There is a problem with the weather API key."

        response.raise_for_status()

        data = response.json()

        condition = data["weather"][0]["main"]

        weather = {
            "city": data["name"],
            "temperature": round(data["main"]["temp"]),
            "feels_like": round(data["main"]["feels_like"]),
            "humidity": data["main"]["humidity"],
            "wind_speed": round(data["wind"]["speed"], 1),
            "description": data["weather"][0]["description"],
            "icon": WEATHER_ICONS.get(condition, "🌤️")
        }


        # Get forecast
        forecast_response = requests.get(
            FORECAST_URL,
            params=params,
            timeout=10
        )

        forecast = []

        if forecast_response.status_code == 200:

            forecast_data = forecast_response.json()

            daily_forecast = {}

            for item in forecast_data["list"]:

                date_time = item["dt_txt"]

                if "12:00:00" in date_time:

                    date_string = date_time.split(" ")[0]

                    forecast_date = datetime.strptime(
                        date_string,
                        "%Y-%m-%d"
                    ).date()


                    if forecast_date == date.today():

                        display_date = "Today"

                    elif forecast_date == date.today() + timedelta(days=1):

                        display_date = "Tomorrow"

                    else:

                        display_date = forecast_date.strftime("%A")


                    condition = item["weather"][0]["main"]

                    daily_forecast[date_string] = {

                        "date": display_date,

                        "temperature": round(
                            item["main"]["temp"]
                        ),

                        "description": item["weather"][0]["description"],

                        "icon": WEATHER_ICONS.get(
                            condition,
                            "🌤️"
                        )
                    }


            forecast = list(
                daily_forecast.values()
            )[:5]


        return weather, forecast, None


    except requests.exceptions.Timeout:

        return None, [], "The weather service took too long to respond."


    except requests.exceptions.ConnectionError:

        return None, [], "Could not connect to the weather service."


    except requests.exceptions.RequestException:

        return None, [], "Something went wrong while fetching the weather."


@app.route("/")
def home():

    city = request.args.get("city", "").strip()

    weather = None
    forecast = []
    error = None


    if city:

        weather, forecast, error = get_weather(city)


        # Add successful searches to recent searches
        if weather:

            city_name = weather["city"]

            if city_name in recent_searches:

                recent_searches.remove(city_name)

            recent_searches.insert(0, city_name)

            # Keep only the latest 5 searches
            del recent_searches[5:]


    return render_template(

        "index.html",

        city=city,

        weather=weather,

        forecast=forecast,

        recent_searches=recent_searches,

        error=error

    )


if __name__ == "__main__":

    app.run(debug=True)