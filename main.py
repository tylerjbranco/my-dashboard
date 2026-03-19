from flask import Flask
import feedparser
import requests
from datetime import datetime, date
import pytz

app = Flask(__name__)

COUNTRY_FLAGS = {
    "AU": "🇦🇺",
    "AE": "🇦🇪",
    "BE": "🇧🇪",
    "IT": "🇮🇹",
    "FR": "🇫🇷",
    "ES": "🇪🇸",
    "NL": "🇳🇱",
    "CH": "🇨🇭",
    "DE": "🇩🇪",
    "PL": "🇵🇱",
    "CA": "🇨🇦",
    "CN": "🇨🇳",
    "GB": "🇬🇧",
    "US": "🇺🇸",
}

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
            "flag": COUNTRY_FLAGS.get(country, "🏳️"),
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
        html += f"""
        <div class='{row_class}'>
            <span class='race-date'>{date_str}</span>
            <span class='team'>{race['name']} {status_badge}</span>
            <span class='race-flag'>{race['flag']}</span>
        </div>"""
    html += "</div>"
    return html

def get_weather():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=43.70&longitude=-79.42&current=temperature_2m,apparent_temperature,weather_code&daily=temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max&timezone=America%2FToronto&forecast_days=4"
        response = requests.get(url)
        data = response.json()

        weather_codes = {
            0: ("Clear sky", "☀️"),
            1: ("Mainly clear", "🌤️"),
            2: ("Partly cloudy", "⛅"),
            3: ("Overcast", "☁️"),
            45: ("Foggy", "🌫️"),
            48: ("Icy fog", "🌫️"),
            51: ("Light drizzle", "🌦️"),
            53: ("Drizzle", "🌦️"),
            55: ("Heavy drizzle", "🌦️"),
            61: ("Light rain", "🌧️"),
            63: ("Rain", "🌧️"),
            65: ("Heavy rain", "🌧️"),
            71: ("Light snow", "🌨️"),
            73: ("Snow", "🌨️"),
            75: ("Heavy snow", "❄️"),
            77: ("Snow grains", "❄️"),
            80: ("Light showers", "🌦️"),
            81: ("Showers", "🌧️"),
            82: ("Heavy showers", "🌧️"),
            85: ("Snow showers", "🌨️"),
            86: ("Heavy snow showers", "❄️"),
            95: ("Thunderstorm", "⛈️"),
            96: ("Thunderstorm", "⛈️"),
            99: ("Thunderstorm", "⛈️"),
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
                "name": name,
                "icon": icon,
                "desc": desc,
                "high": round(daily["temperature_2m_max"][i]),
                "low": round(daily["temperature_2m_min"][i]),
                "precip": daily["precipitation_probability_max"][i]
            })

        today_high = round(daily["temperature_2m_max"][0])
        today_low = round(daily["temperature_2m_min"][0])
        today_precip = daily["precipitation_probability_max"][0]

        return {
            "current_temp": current_temp,
            "feels_like": feels_like,
            "current_desc": current_desc,
            "current_icon": current_icon,
            "today_high": today_high,
            "today_low": today_low,
            "today_precip": today_precip,
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
        <div class='weather-forecast'>
            {forecast_html}
        </div>
    </div>"""

def get_scores(sport, league):
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    try:
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

def get_stories(url, limit=5):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        feed = feedparser.parse(url, request_headers=headers)
        return feed.entries[:limit]
    except:
        return []

def render_scores(games, league):
    if not games:
        return "<p class='empty'>No games today</p>"
    html = "<div class='scores-grid'>"
    for game in games:
        competition = game["competitions"][0]
        home = competition["competitors"][0]
        away = competition["competitors"][1]
        home_team = home["team"]["shortDisplayName"]
        away_team = away["team"]["shortDisplayName"]
        home_score = home["score"]
        away_score = away["score"]
        status = game["status"]["type"]["shortDetail"]
        html += f"""
        <div class='score-card'>
            <div class='score-league'>{league}</div>
            <div class='score-row'><span>{away_team}</span><span class='score-num'>{away_score}</span></div>
            <div class='score-row'><span>{home_team}</span><span class='score-num'>{home_score}</span></div>
            <div class='score-status'>{status}</div>
        </div>"""
    html += "</div>"
    return html

def render_standings(data, label):
    try:
        all_entries = []
        for conference in data.get("children", []):
            entries = conference["standings"]["entries"]
            all_entries.extend(entries)
        all_entries = sorted(
            all_entries,
            key=lambda e: next((s["value"] for s in e["stats"] if s["name"] == "points"), 0),
            reverse=True
        )[:8]
    except:
        return "<p class='empty'>Standings unavailable</p>"
    html = "<div class='standings'>"
    for i, entry in enumerate(all_entries):
        team = entry["team"]["shortDisplayName"]
        stats = {s["name"]: s["displayValue"] for s in entry["stats"]}
        pts = stats.get("points", stats.get("wins", "-"))
        html += f"""
        <div class='standing-row'>
            <span class='pos'>{i+1}</span>
            <span class='team'>{team}</span>
            <span class='pts'>{pts}</span>
        </div>"""
    html += "</div>"
    return html

def render_stories(stories, tag, tag_class):
    if not stories:
        return "<p class='empty'>No stories available</p>"
    html = ""
    for entry in stories:
        title = entry.get("title", "No title")
        link = entry.get("link", "#")
        published = entry.get("published", "")
        html += f"""
        <div class='story-item'>
            <span class='tag {tag_class}'>{tag}</span>
            <div>
                <a href='{link}' target='_blank'>{title}</a>
                <div class='story-meta'>{published}</div>
            </div>
        </div>"""
    return html

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; color: #111; max-width: 600px; margin: 0 auto; }
.header { padding: 16px; border-bottom: 0.5px solid #eee; background: white; position: sticky; top: 0; z-index: 10; }
.header h1 { font-size: 18px; font-weight: 500; }
.header .date { font-size: 11px; color: #999; margin-top: 2px; }
.nav { display: flex; background: white; border-bottom: 0.5px solid #eee; position: sticky; top: 52px; z-index: 10; }
.nav a { flex: 1; padding: 10px; text-align: center; font-size: 13px; color: #999; text-decoration: none; border-bottom: 2px solid transparent; }
.nav a.active { color: #111; border-bottom: 2px solid #111; font-weight: 500; }
.body { padding: 12px 16px; }
.section-label { font-size: 10px; font-weight: 500; color: #999; text-transform: uppercase; letter-spacing: 0.08em; margin: 14px 0 8px; }
.sport-divider { border: none; border-top: 2px solid #eee; margin: 20px 0; }
.weather-widget { background: white; border: 0.5px solid #eee; border-radius: 10px; padding: 12px 14px; margin-bottom: 8px; }
.weather-current { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.weather-main { display: flex; align-items: center; gap: 8px; }
.weather-icon { font-size: 32px; }
.weather-temp { font-size: 32px; font-weight: 500; }
.weather-desc { font-size: 14px; font-weight: 500; color: #111; }
.weather-meta { font-size: 11px; color: #999; margin-top: 3px; }
.weather-forecast { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; border-top: 0.5px solid #eee; padding-top: 12px; }
.forecast-day { text-align: center; }
.forecast-name { font-size: 11px; font-weight: 500; color: #666; margin-bottom: 4px; }
.forecast-icon { font-size: 20px; margin-bottom: 2px; }
.forecast-desc { font-size: 10px; color: #999; margin-bottom: 2px; }
.forecast-temps { font-size: 12px; font-weight: 500; color: #111; }
.forecast-precip { font-size: 10px; color: #999; margin-top: 2px; }
.scores-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 8px; }
.score-card { background: white; border: 0.5px solid #eee; border-radius: 10px; padding: 8px 10px; }
.score-league { font-size: 9px; color: #999; text-transform: uppercase; margin-bottom: 4px; }
.score-row { display: flex; justify-content: space-between; font-size: 13px; margin: 2px 0; }
.score-num { font-weight: 500; }
.score-status { font-size: 9px; color: #999; margin-top: 4px; }
.standings { background: white; border: 0.5px solid #eee; border-radius: 10px; overflow: hidden; margin-bottom: 4px; }
.standing-row { display: flex; align-items: center; padding: 7px 10px; border-bottom: 0.5px solid #f5f5f5; font-size: 12px; gap: 8px; }
.standing-row:last-child { border-bottom: none; }
.live-row { background: #fff9f0; }
.pos { color: #999; width: 20px; font-size: 11px; }
.team { flex: 1; }
.pts { font-weight: 500; font-size: 12px; }
.race-date { font-size: 11px; color: #999; white-space: nowrap; min-width: 80px; }
.race-flag { font-size: 16px; }
.live-badge { background: #fee2e2; color: #991b1b; font-size: 9px; font-weight: 500; padding: 1px 6px; border-radius: 20px; margin-left: 6px; }
.story-item { display: flex; gap: 10px; padding: 8px 0; border-bottom: 0.5px solid #f0f0f0; align-items: flex-start; }
.story-item:last-child { border-bottom: none; }
.tag { font-size: 9px; font-weight: 500; padding: 2px 7px; border-radius: 20px; white-space: nowrap; margin-top: 2px; }
.tag-nhl { background: #dbeafe; color: #1e40af; }
.tag-mlb { background: #fee2e2; color: #991b1b; }
.tag-pl { background: #dcfce7; color: #166534; }
.tag-cycling { background: #fef9c3; color: #854d0e; }
.tag-cbc { background: #ede9fe; color: #5b21b6; }
.tag-globe { background: #f3f4f6; color: #374151; }
.story-item a { font-size: 13px; color: #111; text-decoration: none; line-height: 1.4; }
.story-item a:hover { text-decoration: underline; }
.story-meta { font-size: 10px; color: #999; margin-top: 2px; }
.empty { font-size: 13px; color: #999; padding: 8px 0; }
"""

@app.route("/")
def sports():
    weather = get_weather()
    mlb_games = get_scores("baseball", "mlb")
    pl_games = get_scores("soccer", "eng.1")
    nhl_games = get_scores("hockey", "nhl")
    nhl_standings = get_standings("hockey", "nhl")
    mlb_standings = get_standings("baseball", "mlb")
    pl_standings = get_standings("soccer", "eng.1")
    mlb_stories = get_stories("https://www.sportsnet.ca/mlb/feed/")
    pl_stories = get_stories("https://www.theguardian.com/football/premierleague/rss")
    nhl_stories = get_stories("https://www.sportsnet.ca/hockey/nhl/feed/")
    cycling_stories = get_stories("https://www.cyclingnews.com/rss")
    cycling_calendar = get_cycling_calendar()
    eastern = pytz.timezone("America/Toronto")
    now = datetime.now(eastern).strftime("%A, %B %d · %I:%M %p")
    return f"""<!DOCTYPE html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>My Dashboard</title><style>{CSS}</style></head>
<body>
<div class='header'><h1>My Dashboard</h1><div class='date'>{now}</div></div>
<div class='nav'><a href='/' class='active'>Sports</a><a href='/news'>News</a></div>
<div class='body'>
<div class='section-label'>Toronto Weather</div>
{render_weather(weather)}
<hr class='sport-divider'>
<div class='section-label'>MLB · Scores</div>
{render_scores(mlb_games, 'MLB')}
<div class='section-label'>MLB · Standings</div>
{render_standings(mlb_standings, 'MLB')}
<div class='section-label'>MLB · Headlines</div>
{render_stories(mlb_stories, 'MLB', 'tag-mlb')}
<hr class='sport-divider'>
<div class='section-label'>Premier League · Scores</div>
{render_scores(pl_games, 'PL')}
<div class='section-label'>Premier League · Standings</div>
{render_standings(pl_standings, 'PL')}
<div class='section-label'>Premier League · Headlines</div>
{render_stories(pl_stories, 'PL', 'tag-pl')}
<hr class='sport-divider'>
<div class='section-label'>NHL · Scores</div>
{render_scores(nhl_games, 'NHL')}
<div class='section-label'>NHL · Standings</div>
{render_standings(nhl_standings, 'NHL')}
<div class='section-label'>NHL · Headlines</div>
{render_stories(nhl_stories, 'NHL', 'tag-nhl')}
<hr class='sport-divider'>
<div class='section-label'>Cycling · Upcoming Races</div>
{render_cycling_calendar(cycling_calendar)}
<div class='section-label'>Cycling · Headlines</div>
{render_stories(cycling_stories, 'Cycling', 'tag-cycling')}
</div></body></html>"""

@app.route("/news")
def news():
    cbc_stories = get_stories("https://www.cbc.ca/cmlink/rss-topstories", 8)
    globe_stories = get_stories("https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/canada/", 8)
    eastern = pytz.timezone("America/Toronto")
    now = datetime.now(eastern).strftime("%A, %B %d · %I:%M %p")
    return f"""<!DOCTYPE html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>My Dashboard</title><style>{CSS}</style></head>
<body>
<div class='header'><h1>My Dashboard</h1><div class='date'>{now}</div></div>
<div class='nav'><a href='/'>Sports</a><a href='/news' class='active'>News</a></div>
<div class='body'>
<div class='section-label'>CBC</div>
{render_stories(cbc_stories, 'CBC', 'tag-cbc')}
<div class='section-label'>Globe and Mail</div>
{render_stories(globe_stories, 'Globe', 'tag-globe')}
</div></body></html>"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
