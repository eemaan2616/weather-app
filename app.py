import os
import sqlite3
from datetime import datetime, date, timedelta

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv("WEATHER_API_KEY")

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

DATABASE = "weather.db"


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


# ------------------------------------------------
# DATABASE
# ------------------------------------------------

def get_db_connection():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


def init_database():

    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS recent_searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT UNIQUE NOT NULL,
            searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()

    connection.close()


def add_recent_search(city):

    connection = get_db_connection()

    connection.execute(
        "DELETE FROM recent_searches WHERE city = ?",
        (city,)
    )

    connection.execute(
        "INSERT INTO recent_searches (city) VALUES (?)",
        (city,)
    )

    connection.execute("""
        DELETE FROM recent_searches
        WHERE id NOT IN (
            SELECT id
            FROM recent_searches
            ORDER BY searched_at DESC, id DESC
            LIMIT 5
        )
    """)

    connection.commit()

    connection.close()


def get_recent_searches():

    connection = get_db_connection()

    rows = connection.execute("""
        SELECT city
        FROM recent_searches
        ORDER BY searched_at DESC, id DESC
        LIMIT 5
    """).fetchall()

    connection.close()

    return [row["city"] for row in rows]


# ------------------------------------------------
# WEATHER
# ------------------------------------------------

def get_weather(city=None, latitude=None, longitude=None):

    params = {
        "appid": API_KEY,
        "units": "metric"
    }

    if city:

        params["q"] = city

    elif latitude is not None and longitude is not None:

        params["lat"] = latitude
        params["lon"] = longitude

    else:

        return None, [], "No location was provided."


    try:

        # ------------------------------------------------
        # CURRENT WEATHER
        # ------------------------------------------------

        response = requests.get(
            BASE_URL,
            params=params,
            timeout=10
        )


        if response.status_code == 404:

            return (
                None,
                [],
                f'We could not find "{city}". Please check the spelling.'
            )


        if response.status_code == 401:

            return (
                None,
                [],
                "There is a problem with the weather API key."
            )


        response.raise_for_status()

        data = response.json()

        condition = data["weather"][0]["main"]


        # ------------------------------------------------
        # SUNRISE / SUNSET
        # ------------------------------------------------

        sunrise_timestamp = data["sys"]["sunrise"]

        sunset_timestamp = data["sys"]["sunset"]

        sunrise = datetime.fromtimestamp(
            sunrise_timestamp
        ).strftime("%I:%M %p").lstrip("0")

        sunset = datetime.fromtimestamp(
            sunset_timestamp
        ).strftime("%I:%M %p").lstrip("0")


        # ------------------------------------------------
        # WIND DIRECTION
        # ------------------------------------------------

        wind_direction = data["wind"].get("deg")


        if wind_direction is not None:

            directions = [
                "N",
                "NE",
                "E",
                "SE",
                "S",
                "SW",
                "W",
                "NW"
            ]

            direction_index = round(
                wind_direction / 45
            ) % 8

            wind_direction_label = directions[
                direction_index
            ]

        else:

            wind_direction_label = "N/A"


        # ------------------------------------------------
        # VISIBILITY
        # ------------------------------------------------

        visibility_meters = data.get(
            "visibility"
        )


        if visibility_meters is not None:

            visibility_km = round(
                visibility_meters / 1000,
                1
            )

        else:

            visibility_km = "N/A"


        # ------------------------------------------------
        # CURRENT WEATHER DATA
        # ------------------------------------------------

        weather = {

            "city": data["name"],

            "temperature": round(
                data["main"]["temp"]
            ),

            "feels_like": round(
                data["main"]["feels_like"]
            ),

            "humidity": data["main"]["humidity"],

            "wind_speed": round(
                data["wind"]["speed"],
                1
            ),

            "wind_direction": wind_direction_label,

            "pressure": data["main"]["pressure"],

            "visibility": visibility_km,

            "sunrise": sunrise,

            "sunset": sunset,

            "description": data["weather"][0]["description"],

            "condition": condition,

            "icon": WEATHER_ICONS.get(
                condition,
                "🌤️"
            )

        }


        # ------------------------------------------------
        # 5-DAY FORECAST
        # ------------------------------------------------

        forecast_response = requests.get(
            FORECAST_URL,
            params=params,
            timeout=10
        )

        forecast = []


        if forecast_response.status_code == 200:

            forecast_data = forecast_response.json()

            daily_data = {}


            for item in forecast_data["list"]:

                date_string = item["dt_txt"].split(" ")[0]

                forecast_date = datetime.strptime(
                    date_string,
                    "%Y-%m-%d"
                ).date()


                if forecast_date <= date.today():

                    continue


                if date_string not in daily_data:

                    daily_data[date_string] = {

                        "date": forecast_date,

                        "temperatures": [],

                        "descriptions": [],

                        "conditions": []

                    }


                daily_data[date_string]["temperatures"].append(
                    item["main"]["temp"]
                )


                daily_data[date_string]["descriptions"].append(
                    item["weather"][0]["description"]
                )


                daily_data[date_string]["conditions"].append(
                    item["weather"][0]["main"]
                )


            sorted_days = sorted(
                daily_data.values(),
                key=lambda day: day["date"]
            )


            for day_data in sorted_days[:5]:

                forecast_date = day_data["date"]


                if forecast_date == date.today() + timedelta(days=1):

                    display_date = "Tomorrow"

                else:

                    display_date = forecast_date.strftime(
                        "%A"
                    )


                high_temperature = max(
                    day_data["temperatures"]
                )


                low_temperature = min(
                    day_data["temperatures"]
                )


                conditions = day_data["conditions"]

                most_common_condition = max(
                    set(conditions),
                    key=conditions.count
                )


                descriptions = day_data["descriptions"]

                most_common_description = max(
                    set(descriptions),
                    key=descriptions.count
                )


                forecast.append({

                    "date": display_date,

                    "high": round(
                        high_temperature
                    ),

                    "low": round(
                        low_temperature
                    ),

                    "description": most_common_description,

                    "condition": most_common_condition,

                    "icon": WEATHER_ICONS.get(
                        most_common_condition,
                        "🌤️"
                    )

                })


        return weather, forecast, None


    except requests.exceptions.Timeout:

        return (
            None,
            [],
            "The weather service took too long to respond."
        )


    except requests.exceptions.ConnectionError:

        return (
            None,
            [],
            "Could not connect to the weather service."
        )


    except requests.exceptions.RequestException:

        return (
            None,
            [],
            "Something went wrong while fetching the weather."
        )


# ------------------------------------------------
# HOME PAGE
# ------------------------------------------------

@app.route("/")
def home():

    city = request.args.get(
        "city",
        ""
    ).strip()


    weather = None
    forecast = []
    error = None


    if city:

        weather, forecast, error = get_weather(
            city=city
        )


        if weather:

            add_recent_search(
                weather["city"]
            )


    recent_searches = get_recent_searches()


    return render_template(

        "index.html",

        city=city,

        weather=weather,

        forecast=forecast,

        recent_searches=recent_searches,

        error=error

    )


# ------------------------------------------------
# LOCATION
# ------------------------------------------------

@app.route("/location")
def location():

    latitude = request.args.get("lat")

    longitude = request.args.get("lon")


    if not latitude or not longitude:

        return render_template(

            "index.html",

            city="",

            weather=None,

            forecast=[],

            recent_searches=get_recent_searches(),

            error="Could not determine your location."

        )


    weather, forecast, error = get_weather(

        latitude=latitude,

        longitude=longitude

    )


    if weather:

        add_recent_search(
            weather["city"]
        )


    return render_template(

        "index.html",

        city="",

        weather=weather,

        forecast=forecast,

        recent_searches=get_recent_searches(),

        error=error

    )


# ------------------------------------------------
# START APPLICATION
# ------------------------------------------------

init_database()


if __name__ == "__main__":

    app.run(debug=True)