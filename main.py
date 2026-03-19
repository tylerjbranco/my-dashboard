from flask import Flask, jsonify
import feedparser
import requests
from datetime import datetime, date, timedelta
import pytz

app = Flask(__name__)

NHL_DIVISIONS = {
    "Atlantic": ["Bruins", "Sabres", "Red Wings", "Panthers", "Canadiens", "Senators", "Lightning", "Maple Leafs"],
    "Metropolitan": ["Hurricanes", "Blue Jackets", "Devils", "Islanders", "Rangers", "Flyers", "Penguins", "Capitals"],
    "Central": ["Blackhawks", "Avalanche", "Stars", "Wild", "Predators", "Blues", "Jets", "Utah"],
    "Pacific": ["Ducks", "Flames", "Oilers", "Kings", "Sharks", "Kraken", "Canucks", "Golden Knights"],
}

MLB_DIVISIONS = {
    "AL East": ["Orioles", "Red Sox", "Yankees", "Rays", "Blue Jays"],
    "AL Central": ["White Sox", "Guardians", "Tigers", "Royals", "Twins"],
    "AL West": ["Astros", "Angels", "Athletics", "Mariners", "Rangers"],
    "NL East": ["Braves", "Marlins", "Mets", "Phillies", "Nationals"],
    "NL Central": ["Cubs", "Reds", "Brewers", "Pirates", "Cardinals"],
    "NL West": ["Diamondbacks", "Rockies", "Dodgers", "Padres", "Giants"],
}

FLAG_HTML = {
    "AU": "&#x1F1E6;&#x1F1FA;",
    "AE": "&#x1F1E6;&#x1F1EA;",
    "BE": "&#x1F1E7;&#x1F1EA;",
    "IT": "&#x1F1EE;&#x1F1F9;",
    "FR": "&#x1F1EB;&#x1F1F7;",
    "ES": "&#x1F1EA;&#x1F1F8;",
    "NL": "&#x1F1F3;&#x1F1F1;",
    "CH": "&#x1F1E8;&#x1F1ED;",
    "DE": "&#x1F1E9;&#x1F1EA;",
    "PL": "&#x1F1F5;&#x1F1F1;",
    "CA": "&#x1F1E8;&#x1F1E6;",
    "CN": "&#x1F1E8;&#x1F1F3;",
}

MY_TEAMS = [
    {"name": "Maple Leafs", "sport": "hockey", "league": "nhl", "keywords": ["Toronto Maple Leafs"]},
    {"name": "Blue Jays", "sport": "baseball", "league": "mlb", "keywords": ["Toronto Blue Jays"]},
    {"name": "Man United", "sport": "soccer", "league": "eng.1", "keywords": ["Manchester United"]},
    {"name": "Raptors", "sport": "basketball", "league": "nba", "keywords": ["Toronto Raptors"]},
    {"name": "Toronto FC", "sport": "soccer", "league": "usa.1", "keywords": ["Toronto FC"]},
]

UCI_WORLD_TOUR_2026 = [
    ("Tour Down Under", "AU", "2026-01-20", "2026-01-25"),
    ("UAE Tour", "AE", "2026-02-22", "2026-02-28"),
    ("Omloop Het Nieuwsblad", "BE", "2026-02-28", "2026-02-28"),
    ("Strade Bianche", "IT", "2026-03-07", "2026-03-07"),
    ("Paris-Nice", "FR", "2026-03-08", "2026-03-15"),
    ("Tirreno-Adriatico", "IT", "2026-03-11", "2026-03-17"),
    ("Milan-San Remo", "IT", "2026-03-21", "2026-03-21"),
    ("Volta a Catalunya", "ES", "2026-03-23", "2026-03-29"),
    ("E3 Saxo Bank Classic", "BE", "2026-03-27", "2026-03-27"),
    ("Gent-Wevelgem", "BE", "2026-03-29", "2026-03-29"),
    ("Dwars door Vlaanderen", "BE", "2026-04-01", "2026-04-01"),
    ("Tour of Flanders", "BE", "2026-04-05", "2026-04-05"),
    ("Paris-Roubaix", "FR", "2026-04-12", "2026-04-12"),
    ("Amstel Gold Race", "NL", "2026-04-19", "2026-04-19"),
    ("La Flèche Wallonne", "BE", "2026-04-22", "2026-04-22"),
    ("Liège-Bastogne-Liège", "BE", "2026-04-26", "2026-04-26"),
    ("Tour de Romandie", "CH", "2026-04-28", "2026-05-03"),
    ("Eschborn-Frankfurt", "DE", "2026-05-01", "2026-05-01"),
    ("Giro d'Italia", "IT", "2026-05-09", "2026-05-31"),
    ("Critérium du Dauphiné", "FR", "2026-06-07", "2026-06-14"),
    ("Swiss Tour", "CH", "2026-06-14", "2026-06-21"),
    ("Tour de France", "FR", "2026-07-04", "2026-07-26"),
    ("Classica San Sebastián", "ES", "2026-08-01", "2026-08-01"),
    ("Tour de Pologne", "PL", "2026-08-04", "2026-08-09"),
    ("La Vuelta España", "ES", "2026-08-15", "2026-09-06"),
    ("Bretagne Classic", "FR", "2026-08-30", "2026-08-30"),
    ("Grand Prix Cycliste de Québec", "CA", "2026-09-11", "2026-09-11"),
    ("Grand Prix Cycliste de Montréal", "CA", "2026-09-13", "2026-09-13"),
    ("Il Lombardia", "IT", "2026-10-03", "2026-10-03"),
    ("Gree-Tour of Guangxi", "CN", "2026-10-13", "2026-10-18"),
]

def get_cycling_calendar():
    today = date.today()
    races = []
    for name, country, start_str, end_str in UCI_WORLD_TOUR_2026:
        start = date.fromisoformat(start_str)
        end = date.fromisoformat(end_str)
        if end < today:
            status = "completed"
        elif start <= today <= end:
            status = "live"
        else:
            status = "upcoming"
        races.append({
            "name": name,
            "country": country,
            "start": start,
            "end": end,
            "status": status
        })
    return races

def render_cycling_calendar(races):
    html = "<div class='standings'>"
    for race in races:
        if race["status"] == "completed":
            continue
        if race["start"] == race["end"]:
            date_str = race["start"].strftime("%b %d")
        else:
            date_str = f"{race['start'].strftime('%b %d')} – {race['end'].strftime('%b %d')}"
        if race["status"] == "live":
            status_badge = "<span class='live-badge'>Live</span>"
            row_class = "standing-row live-row"
        else:
            status_badge = ""
            row_class = "standing-row"
        flag = FLAG_HTML.get(race["country"], race["country"])
        html += f"""
        <div class='{row_class}'>
            <span class='race-date'>{date_str}</span>
            <span class='team'>{race['name']} {status_badge}</span>
            <span class='race-country'>{flag}</span>
        </div>"""
    html += "</div>"
    return html

def get_weather():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=43.70&longitude=-79.42&current=temperature_2m,apparent_temperature,weather_code&daily=temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max&timezone=America%2FToronto&forecast_days=4"
        response = requests.get(url)
        data = response.json()
        weather_codes = {
            0: ("Clear sky", "☀️"), 1: ("Mainly clear", "🌤️"), 2: ("Partly cloudy", "⛅"),
            3: ("Overcast", "☁️"), 45: ("Foggy", "🌫️"), 48: ("Icy fog", "🌫️"),
            51: ("Light drizzle", "🌦️"), 53: ("Drizzle", "🌦️"), 55: ("Heavy drizzle", "🌦️"),
            61: ("Light rain", "🌧️"), 63: ("Rain", "🌧️"), 65: ("Heavy rain", "🌧️"),
            71: ("Light snow", "🌨️"), 73: ("Snow", "🌨️"), 75: ("Heavy snow", "❄️"),
            77: ("Snow grains", "❄️"), 80: ("Light showers", "🌦️"), 81: ("Showers", "🌧️"),
            82: ("Heavy showers", "🌧️"), 85: ("Snow showers", "🌨️"), 86: ("Heavy snow showers", "❄️"),
            95: ("Thunderstorm", "⛈️"), 96: ("Thunderstorm", "⛈️"), 99: ("Thunderstorm", "⛈️"),
        }
        current = data["current"]
        daily = data["daily"]
        current_code = current["weather_code"]
        current_desc, current_icon = weather_codes.get(current_code, ("Unknown", "🌡️"))
        current_temp = round(current["temperature_2m"])
        feels_like = round(current["apparent_temperature"])
        days = []
        day_names = ["Today", "Tomorrow"]
        for i in range(1, 4):
            d = date.fromisoformat(daily["time"][i])
            name = day_names[i] if i < len(day_names) else d.strftime("%A")
            code = daily["weather_code"][i]
            desc, icon = weather_codes.get(code, ("Unknown", "🌡️"))
            days.append({
                "name": name, "icon": icon, "desc": desc,
                "high": round(daily["temperature_2m_max"][i]),
                "low": round(daily["temperature_2m_min"][i]),
                "precip": daily["precipitation_probability_max"][i]
            })
        return {
            "current_temp": current_temp, "feels_like": feels_like,
            "current_desc": current_desc, "current_icon": current_icon,
            "today_high": round(daily["temperature_2m_max"][0]),
            "today_low": round(daily["temperature_2m_min"][0]),
            "today_precip": daily["precipitation_probability_max"][0],
            "days": days
        }
    except:
        return None

def render_weather(w):
    if not w:
        return "<p class='empty'>Weather unavailable</p>"
    forecast_html = ""
    for day in w["days"]:
        forecast_html += f"""
        <div class='forecast-day'>
            <div class='forecast-name'>{day['name']}</div>
            <div class='forecast-icon'>{day['icon']}</div>
            <div class='forecast-desc'>{day['desc']}</div>
            <div class='forecast-temps'>{day['high']}° / {day['low']}°</div>
            <div class='forecast-precip'>{day['precip']}% precip</div>
        </div>"""
    return f"""
    <div class='weather-widget'>
        <div class='weather-current'>
            <div class='weather-main'>
                <span class='weather-icon'>{w['current_icon']}</span>
                <span class='weather-temp'>{w['current_temp']}°C</span>
            </div>
            <div class='weather-details'>
                <div class='weather-desc'>{w['current_desc']}</div>
                <div class='weather-meta'>Feels like {w['feels_like']}°C · High {w['today_high']}° Low {w['today_low']}° · {w['today_precip']}% precip</div>
            </div>
        </div>
        <div class='weather-forecast'>{forecast_html}</div>
    </div>"""

def get_scores(sport, league, for_date=None):
    try:
        if for_date:
            date_str = for_date.strftime("%Y%m%d")
            url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard?dates={date_str}"
        else:
            url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
        response = requests.get(url)
        data = response.json()
        return data.get("events", [])
    except:
        return []

def get_standings(sport, league):
    url = f"https://site.api.espn.com/apis/v2/sports/{sport}/{league}/standings"
    try:
        response = requests.get(url)
        data = response.json()
        return data
    except:
        return {}

def find_team_games(games, keywords):
    matches = []
    for game in games:
        try:
            competition = game["competitions"][0]
            for competitor in competition["competitors"]:
                team = competitor["team"]
                full_name = f"{team.get('location', '')} {team.get('name', '')}".strip()
                short_name = team.get("shortDisplayName", "")
                for kw in keywords:
                    if kw.lower() in full_name.lower() or kw.lower() in short_name.lower():
                        if game not in matches:
                            matches.append(game)
                        break
        except:
            continue
    return matches

def get_stories(url, limit=5):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        feed = feedparser.parse(url, request_headers=headers)
        stories = []
        for entry in feed.entries[:limit * 2]:
            title = entry.get("title", "No title")
            published = entry.get("published", "")
            link = entry.get("link", "")
            if not link or not link.startswith("http"):
                for l in entry.get("links", []):
                    if l.get("rel") == "alternate" and l.get("type") == "text/html":
                        link = l.get("href", "")
                        break
            if not link or not link.startswith("http"):
                link = entry.get("id", "")
            if not link or not link.startswith("http"):
                continue
            thumbnail = ""
            for l in entry.get("links", []):
                if l.get("rel") == "enclosure" and "image" in l.get("type", ""):
                    thumbnail = l.get("href", "")
                    break
            if not thumbnail:
                for mc in entry.get("media_content", []):
                    if mc.get("url"):
                        thumbnail = mc.get("url", "")
                        break
            if not thumbnail:
                thumbs = entry.get("media_thumbnail", [])
                if thumbs:
                    thumbnail = thumbs[0].get("url", "")
            stories.append({
                "title": title,
                "link": link,
                "published": published,
                "thumbnail": thumbnail
            })
            if len(stories) >= limit:
                break
        return stories
    except:
        return []

def athletic_link(url, label):
    return f"""
    <a href='{url}' target='_blank' class='athletic-link'>
        <span class='athletic-badge'>A</span>
        <span>More {label} coverage on The Athletic</span>
    </a>"""

def render_game_card(game):
    competition = game["competitions"][0]
    home = competition["competitors"][0]
    away = competition["competitors"][1]
    home_team = home["team"]["shortDisplayName"]
    away_team = away["team"]["shortDisplayName"]
    home_score = home["score"]
    away_score = away["score"]
    home_logo = home["team"].get("logo", "")
    away_logo = away["team"].get("logo", "")
    status = game["status"]["type"]["shortDetail"]
    state = game["status"]["type"]["state"]
    game_id = game["id"]
    uid = game.get("uid", "")
    if "s:1~" in uid:
        league_slug = "mlb"
    elif "s:70~" in uid:
        league_slug = "nhl"
    elif "s:600~" in uid:
        league_slug = "soccer"
    elif "s:40~" in uid:
        league_slug = "nba"
    else:
        league_slug = "soccer"
    game_url = f"https://www.espn.com/{league_slug}/game/_/gameId/{game_id}"
    home_bold = ""
    away_bold = ""
    if state == "post":
        try:
            if int(home["score"]) > int(away["score"]):
                home_bold = "font-weight: 600;"
            elif int(away["score"]) > int(home["score"]):
                away_bold = "font-weight: 600;"
        except:
            pass
    return f"""
    <a href='{game_url}' target='_blank' class='score-card-link'>
        <div class='score-card'>
            <div class='score-row'>
                <div class='score-team'>
                    {'<img class="team-logo" src="' + away_logo + '" alt="">' if away_logo else '
