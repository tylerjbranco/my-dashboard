from flask import Flask
import feedparser
import requests
from datetime import datetime

app = Flask(__name__)

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
.header { padding: 16px; border-bottom: 0.5px solid #eee; background: white; position: sticky; top: 0; }
.header h1 { font-size: 18px; font-weight: 500; }
.header .date { font-size: 11px; color: #999; margin-top: 2px; }
.nav { display: flex; background: white; border-bottom: 0.5px solid #eee; }
.nav a { flex: 1; padding: 10px; text-align: center; font-size: 13px; color: #999; text-decoration: none; border-bottom: 2px solid transparent; }
.nav a.active { color: #111; border-bottom: 2px solid #111; font-weight: 500; }
.body { padding: 12px 16px; }
.section-label { font-size: 10px; font-weight: 500; color: #999; text-transform: uppercase; letter-spacing: 0.08em; margin: 14px 0 8px; }
.scores-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 8px; }
.score-card { background: white; border: 0.5px solid #eee; border-radius: 10px; padding: 8px 10px; }
.score-league { font-size: 9px; color: #999; text-transform: uppercase; margin-bottom: 4px; }
.score-row { display: flex; justify-content: space-between; font-size: 13px; margin: 2px 0; }
.score-num { font-weight: 500; }
.score-status { font-size: 9px; color: #999; margin-top: 4px; }
.standings { background: white; border: 0.5px solid #eee; border-radius: 10px; overflow: hidden; margin-bottom: 4px; }
.standing-row { display: flex; align-items: center; padding: 7px 10px; border-bottom: 0.5px solid #f5f5f5; font-size: 12px; }
.standing-row:last-child { border-bottom: none; }
.pos { color: #999; width: 20px; font-size: 11px; }
.team { flex: 1; }
.pts { font-weight: 500; font-size: 12px; }
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
    nhl_games = get_scores("hockey", "nhl")
    mlb_games = get_scores("baseball", "mlb")
    nhl_standings = get_standings("hockey", "nhl")
    mlb_standings = get_standings("baseball", "mlb")
    pl_standings = get_standings("soccer", "eng.1")
    nhl_stories = get_stories("https://www.sportsnet.ca/hockey/nhl/feed/")
    mlb_stories = get_stories("https://www.sportsnet.ca/mlb/feed/")
    pl_stories = get_stories("https://www.theguardian.com/football/premierleague/rss")
    cycling_stories = get_stories("https://www.cyclingnews.com/rss")
    now = datetime.now().strftime("%A, %B %d · %I:%M %p")
    return f"""<!DOCTYPE html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>My Dashboard</title><style>{CSS}</style></head>
<body>
<div class='header'><h1>My Dashboard</h1><div class='date'>{now}</div></div>
<div class='nav'><a href='/' class='active'>Sports</a><a href='/news'>News</a></div>
<div class='body'>
<div class='section-label'>Today's scores</div>
{render_scores(nhl_games, 'NHL')}
{render_scores(mlb_games, 'MLB')}
<div class='section-label'>NHL standings</div>
{render_standings(nhl_standings, 'NHL')}
<div class='section-label'>MLB standings</div>
{render_standings(mlb_standings, 'MLB')}
<div class='section-label'>Premier League table</div>
{render_standings(pl_standings, 'PL')}
<div class='section-label'>Latest stories</div>
{render_stories(nhl_stories, 'NHL', 'tag-nhl')}
{render_stories(mlb_stories, 'MLB', 'tag-mlb')}
{render_stories(pl_stories, 'PL', 'tag-pl')}
{render_stories(cycling_stories, 'Cycling', 'tag-cycling')}
</div></body></html>"""

@app.route("/news")
def news():
    cbc_stories = get_stories("https://www.cbc.ca/cmlink/rss-topstories", 8)
    globe_stories = get_stories("https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/canada/", 8)
    now = datetime.now().strftime("%A, %B %d · %I:%M %p")
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
