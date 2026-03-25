from flask import Flask, jsonify, request
import feedparser
import requests
from datetime import datetime, date, timedelta
import pytz
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

app = Flask(__name__)

FPL_TEAM_ID = 27088
PL_CL_SPOTS = 4  # Update each season as needed

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
    "GB": "&#x1F1EC;&#x1F1E7;",
    "MC": "&#x1F1F2;&#x1F1E8;",
    "BH": "&#x1F1E7;&#x1F1ED;",
    "SA": "&#x1F1F8;&#x1F1E6;",
    "JP": "&#x1F1EF;&#x1F1F5;",
    "US": "&#x1F1FA;&#x1F1F8;",
    "AZ": "&#x1F1E6;&#x1F1FF;",
    "SG": "&#x1F1F8;&#x1F1EC;",
    "MX": "&#x1F1F2;&#x1F1FD;",
    "BR": "&#x1F1E7;&#x1F1F7;",
    "AT": "&#x1F1E6;&#x1F1F9;",
    "HU": "&#x1F1ED;&#x1F1FA;",
    "QA": "&#x1F1F6;&#x1F1E6;",
}

NATIONALITY_FLAGS = {
    "NED": "🇳🇱", "BEL": "🇧🇪", "GBR": "🇬🇧", "ITA": "🇮🇹", "FRA": "🇫🇷",
    "SLO": "🇸🇮", "DEN": "🇩🇰", "COL": "🇨🇴", "AUS": "🇦🇺", "GER": "🇩🇪",
    "ESP": "🇪🇸", "POR": "🇵🇹", "NOR": "🇳🇴", "SWI": "🇨🇭", "POL": "🇵🇱",
    "USA": "🇺🇸", "KAZ": "🇰🇿", "ECU": "🇪🇨", "RUS": "🇷🇺", "AUT": "🇦🇹",
    "CZE": "🇨🇿", "TUR": "🇹🇷", "ERY": "🇪🇷", "RSA": "🇿🇦", "CAN": "🇨🇦",
}

MY_TEAMS = [
    {"name": "Toronto Maple Leafs", "keywords": ["Toronto Maple Leafs"]},
    {"name": "Toronto Blue Jays", "keywords": ["Toronto Blue Jays"]},
    {"name": "Manchester United", "keywords": ["Manchester United"]},
    {"name": "Toronto Raptors", "keywords": ["Toronto Raptors"]},
    {"name": "Toronto FC", "keywords": ["Toronto FC"]},
]

FIXTURE_LEAGUES = [
    ("hockey", "nhl"),
    ("baseball", "mlb"),
    ("soccer", "eng.1"),
    ("basketball", "nba"),
    ("soccer", "usa.1"),
]

LEAGUE_EMOJI = {
    "nhl": "🏒",
    "mlb": "⚾",
    "eng.1": "⚽",
    "nba": "🏀",
    "usa.1": "⚽",
    "uefa.champions": "⚽",
}

YOUTUBE_CHANNELS = [
    ("Abroad in Japan", "UCHL9bfHTxCMi-7vfxQ-AYtg"),
    ("GCN Racing", "UCu7phdCr-raU7OaJfEpHZww"),
    ("Global Cycling Network", "UCuTaETsuCOkJ0H_GAztWt0Q"),
    ("Foolish Bailey", "UCGob7q-tONG83_39Rj1M8Cw"),
    ("Foolish Baseball", "UCbW12JIVAdi5NugdakbU33A"),
]

YOUTUBE_PLAYLISTS = [
    ("About That", "PLeyJPHbRnGaZeajS8uAtr8cyc19TYBZZ9"),
]

PODCAST_FEEDS = [
    ("At The Letters", "https://feeds.simplecast.com/R14Ca9Ii", "https://open.spotify.com/show/4qDVNDRRFU3voSTRDZGSdU"),
    ("Talkin' Baseball", "https://feeds.simplecast.com/06DZNq60", "https://open.spotify.com/show/09USaYF2LTQpNwBXnFGbAT"),
    ("Wake N Jake", "https://feeds.simplecast.com/0IMFN2cF", "https://open.spotify.com/show/5NVyHnDVsk3TEXjnRNI2vj"),
    ("Baseball Today", "https://feeds.simplecast.com/9pM3N4cY", "https://open.spotify.com/show/3qg6lL01V36LLogc6f6d6b"),
]

UCI_WORLD_TOUR_2026 = [
    ("Tour Down Under", "AU", "2026-01-20", "2026-01-25", "tour-down-under"),
    ("UAE Tour", "AE", "2026-02-22", "2026-02-28", "uae-tour"),
    ("Omloop Het Nieuwsblad", "BE", "2026-02-28", "2026-02-28", "omloop-het-nieuwsblad"),
    ("Strade Bianche", "IT", "2026-03-07", "2026-03-07", "strade-bianche"),
    ("Paris-Nice", "FR", "2026-03-08", "2026-03-15", "paris-nice"),
    ("Tirreno-Adriatico", "IT", "2026-03-11", "2026-03-17", "tirreno-adriatico"),
    ("Milan-San Remo", "IT", "2026-03-21", "2026-03-21", "milano-sanremo"),
    ("Volta a Catalunya", "ES", "2026-03-23", "2026-03-29", "volta-a-catalunya"),
    ("E3 Saxo Bank Classic", "BE", "2026-03-27", "2026-03-27", "e3-saxo-bank-classic"),
    ("Gent-Wevelgem", "BE", "2026-03-29", "2026-03-29", "gent-wevelgem"),
    ("Dwars door Vlaanderen", "BE", "2026-04-01", "2026-04-01", "dwars-door-vlaanderen"),
    ("Tour of Flanders", "BE", "2026-04-05", "2026-04-05", "ronde-van-vlaanderen"),
    ("Paris-Roubaix", "FR", "2026-04-12", "2026-04-12", "paris-roubaix"),
    ("Amstel Gold Race", "NL", "2026-04-19", "2026-04-19", "amstel-gold-race"),
    ("La Flèche Wallonne", "BE", "2026-04-22", "2026-04-22", "la-fleche-wallonne"),
    ("Liège-Bastogne-Liège", "BE", "2026-04-26", "2026-04-26", "liege-bastogne-liege"),
    ("Tour de Romandie", "CH", "2026-04-28", "2026-05-03", "tour-de-romandie"),
    ("Eschborn-Frankfurt", "DE", "2026-05-01", "2026-05-01", "eschborn-frankfurt"),
    ("Giro d'Italia", "IT", "2026-05-09", "2026-05-31", "giro-d-italia"),
    ("Critérium du Dauphiné", "FR", "2026-06-07", "2026-06-14", "criterium-du-dauphine"),
    ("Swiss Tour", "CH", "2026-06-14", "2026-06-21", "tour-de-suisse"),
    ("Tour de France", "FR", "2026-07-04", "2026-07-26", "tour-de-france"),
    ("Classica San Sebastián", "ES", "2026-08-01", "2026-08-01", "clasica-de-san-sebastian"),
    ("Tour de Pologne", "PL", "2026-08-04", "2026-08-09", "tour-de-pologne"),
    ("La Vuelta España", "ES", "2026-08-15", "2026-09-06", "vuelta-a-espana"),
    ("Bretagne Classic", "FR", "2026-08-30", "2026-08-30", "bretagne-classic-ouest-france"),
    ("Grand Prix Cycliste de Québec", "CA", "2026-09-11", "2026-09-11", "gp-quebec"),
    ("Grand Prix Cycliste de Montréal", "CA", "2026-09-13", "2026-09-13", "gp-montreal"),
    ("Il Lombardia", "IT", "2026-10-03", "2026-10-03", "il-lombardia"),
    ("Gree-Tour of Guangxi", "CN", "2026-10-13", "2026-10-18", "tour-of-guangxi"),
]

F1_CALENDAR_2026 = [
    ("Australian Grand Prix", "AU", "Melbourne", "2026-03-15", "2026-03-15", "aus"),
    ("Chinese Grand Prix", "CN", "Shanghai", "2026-03-22", "2026-03-22", "chn"),
    ("Japanese Grand Prix", "JP", "Suzuka", "2026-04-05", "2026-04-05", "jpn"),
    ("Bahrain Grand Prix", "BH", "Sakhir", "2026-04-19", "2026-04-19", "bhr"),
    ("Saudi Arabian Grand Prix", "SA", "Jeddah", "2026-04-26", "2026-04-26", "sau"),
    ("Miami Grand Prix", "US", "Miami", "2026-05-03", "2026-05-03", "mia"),
    ("Emilia Romagna Grand Prix", "IT", "Imola", "2026-05-17", "2026-05-17", "emr"),
    ("Monaco Grand Prix", "MC", "Monaco", "2026-05-24", "2026-05-24", "mon"),
    ("Spanish Grand Prix", "ES", "Barcelona", "2026-05-31", "2026-05-31", "esp"),
    ("Canadian Grand Prix", "CA", "Montréal", "2026-06-14", "2026-06-14", "can"),
    ("Austrian Grand Prix", "AT", "Spielberg", "2026-06-28", "2026-06-28", "aut"),
    ("British Grand Prix", "GB", "Silverstone", "2026-07-05", "2026-07-05", "gbr"),
    ("Belgian Grand Prix", "BE", "Spa", "2026-07-26", "2026-07-26", "bel"),
    ("Hungarian Grand Prix", "HU", "Budapest", "2026-08-02", "2026-08-02", "hun"),
    ("Dutch Grand Prix", "NL", "Zandvoort", "2026-08-30", "2026-08-30", "ned"),
    ("Italian Grand Prix", "IT", "Monza", "2026-09-06", "2026-09-06", "ita"),
    ("Azerbaijan Grand Prix", "AZ", "Baku", "2026-09-20", "2026-09-20", "aze"),
    ("Singapore Grand Prix", "SG", "Singapore", "2026-10-04", "2026-10-04", "sgp"),
    ("United States Grand Prix", "US", "Austin", "2026-10-18", "2026-10-18", "usa"),
    ("Mexico City Grand Prix", "MX", "Mexico City", "2026-10-25", "2026-10-25", "mex"),
    ("São Paulo Grand Prix", "BR", "São Paulo", "2026-11-08", "2026-11-08", "bra"),
    ("Las Vegas Grand Prix", "US", "Las Vegas", "2026-11-21", "2026-11-21", "lvg"),
    ("Qatar Grand Prix", "QA", "Lusail", "2026-11-29", "2026-11-29", "qat"),
    ("Abu Dhabi Grand Prix", "AE", "Yas Marina", "2026-12-06", "2026-12-06", "auh"),
]


def get_f1_data():
    try:
        # Upcoming race
        url = "https://site.api.espn.com/apis/site/v2/sports/racing/f1/scoreboard"
        response = requests.get(url, timeout=8)
        data = response.json()
        events = data.get("events", [])

        eastern = pytz.timezone("America/Toronto")
        today = datetime.now(eastern).date()

        upcoming = None
        for event in events:
            try:
                competitions = event.get("competitions", [])
                if not competitions:
                    continue
                comp = competitions[0]
                date_str = comp.get("date", event.get("date", ""))
                if not date_str:
                    continue
                dt_utc = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                dt_eastern = dt_utc.astimezone(eastern)
                if dt_eastern.date() >= today:
                    upcoming = event
                    break
            except:
                continue

        upcoming_info = None
        if upcoming:
            try:
                comp = upcoming["competitions"][0]
                name = upcoming.get("name", "")
                venue = comp.get("venue", {})
                location = venue.get("fullName", "") or venue.get("address", {}).get("city", "")
                country_code = venue.get("address", {}).get("country", "")

                # Find qualifying and race sessions
                sessions = []
                for c in upcoming.get("competitions", []):
                    c_abbrev = c.get("type", {}).get("abbreviation", "")
                    c_date = c.get("date", "")
                    if c_date and c_abbrev:
                        try:
                            dt_utc = datetime.fromisoformat(c_date.replace("Z", "+00:00"))
                            dt_est = dt_utc.astimezone(eastern)
                            sessions.append((c_abbrev, dt_est))
                        except:
                            pass

                qual_time = None
                race_time = None
                for s_abbrev, s_dt in sessions:
                    if s_abbrev == "Qual":
                        qual_time = s_dt.strftime("%a %b %d · %I:%M %p ET")
                    elif s_abbrev == "Race":
                        race_time = s_dt.strftime("%a %b %d · %I:%M %p ET")
                        
                # Fallback: find from F1_CALENDAR_2026
                flag = FLAG_HTML.get(country_code, "🏎️")
                upcoming_info = {
                    "name": name,
                    "location": location,
                    "flag": flag,
                    "qual_time": qual_time,
                    "race_time": race_time,
                }
            except:
                pass

        # Standings
        standings_url = "https://site.api.espn.com/apis/v2/sports/racing/f1/standings"
        standings_resp = requests.get(standings_url, timeout=8)
        standings_data = standings_resp.json()

        constructors = []
        drivers = []

        for child in standings_data.get("children", []):
            stype = child.get("type", "").lower()
            entries = child.get("standings", {}).get("entries", [])
            for entry in entries:
                team = entry.get("team", {})
                athlete = entry.get("athlete", {})
                stats = {s["name"]: s["displayValue"] for s in entry.get("stats", [])}
                pts = stats.get("points", "0")
                logo = team.get("logos", [{}])[0].get("href", "") if team.get("logos") else ""
                if "constructor" in stype or "team" in stype:
                    constructors.append({
                        "name": team.get("displayName", team.get("name", "?")),
                        "logo": logo,
                        "points": pts,
                    })
                elif "driver" in stype:
                    drivers.append({
                        "name": athlete.get("displayName", "?"),
                        "team_logo": logo,
                        "points": pts,
                    })

        return {
            "upcoming": upcoming_info,
            "constructors": constructors,
            "drivers": drivers,
        }
    except:
        return {"upcoming": None, "constructors": [], "drivers": []}


def get_f1_race_results():
    """Get completed F1 race results from ESPN"""
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/racing/f1/scoreboard?dates=20260101-20261231"
        response = requests.get(url, timeout=8)
        data = response.json()
        events = data.get("events", [])
        completed = []
        for event in events:
            try:
                comp = event["competitions"][0]
                # Check if the Race session specifically is completed
                race_comp = None
                for c in event.get("competitions", []):
                    if c.get("type", {}).get("abbreviation", "") == "Race":
                        race_comp = c
                        break
                if not race_comp:
                    continue
                status = race_comp.get("status", {}).get("type", {}).get("state", "")
                if status != "post":
                    continue
                name = event.get("name", "")
                date_str = comp.get("date", "")
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date() if date_str else None
                
                competitors = race_comp.get("competitors", [])
                podium = []
                seen = set()
                sorted_competitors = sorted(competitors, key=lambda c: int(c.get("order", 99) or 99))
                for c in sorted_competitors:
                    athlete = c.get("athlete", {})
                    name = athlete.get("displayName", "?")
                    if name in seen:
                        continue
                    seen.add(name)
                    flag_url = athlete.get("flag", {}).get("href", "")
                    flag_alt = athlete.get("flag", {}).get("alt", "")
                    podium.append({
                        "name": name,
                        "flag_url": flag_url,
                        "flag_alt": flag_alt,
                    })
                    if len(podium) >= 3:
                        break
                    podium.append({
                        "name": athlete.get("displayName", "?"),
                        "flag_url": flag_url,
                        "flag_alt": flag_alt,
                    })
                completed.append({
                    "name": name,
                    "date": dt,
                    "podium": podium,
                })
            except:
                continue
        return completed
    except:
        return []


def get_cycling_podiums():
    """Scrape top 3 finishers for completed UCI WT races from PCS"""
    today = date.today()
    results = {}
    completed = [(name, country, start_str, end_str, slug)
                 for name, country, start_str, end_str, slug in UCI_WORLD_TOUR_2026
                 if date.fromisoformat(end_str) < today]

    def fetch_podium(name, slug):
        try:
            url = f"https://www.procyclingstats.com/race/{slug}/2026"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = requests.get(url, timeout=8, headers=headers)
            soup = BeautifulSoup(resp.text, "html.parser")
            podium = []
            # PCS result table — first table with class 'results'
            table = soup.find("table", class_="basic")
            if not table:
                table = soup.find("table")
            if table:
                rows = table.find_all("tr")[1:4]
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 4:
                        rider_name = cells[3].get_text(strip=True) if len(cells) > 3 else "?"
                        nat_code = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                        flag = NATIONALITY_FLAGS.get(nat_code, "")
                        podium.append({"name": rider_name, "flag": flag})
            if not podium:
                return name, []
            return name, podium
        except:
            return name, []

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fetch_podium, name, slug): name
                   for name, country, start_str, end_str, slug in completed}
        for future in as_completed(futures):
            name, podium = future.result()
            results[name] = podium
    return results


def get_cycling_calendar():
    today = date.today()
    races = []
    for name, country, start_str, end_str, pcs_slug in UCI_WORLD_TOUR_2026:
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
            "status": status,
            "pcs_url": f"https://www.procyclingstats.com/race/{pcs_slug}/2026",
        })
    return races


def render_cycling_results(races, podiums):
    completed = [r for r in races if r["status"] == "completed"]
    if not completed:
        return ""
    html = f"""
    <button class='fixture-toggle' id='cycling-results-toggle-btn' onclick='toggleSection("cycling-results-toggle-btn","cycling-results-body")'>
        <span class='toggle-arrow'>▾</span> Completed Races
    </button>
    <div class='fixture-calendar' id='cycling-results-body'>
    <div class='standings'>"""
    for race in completed:
        flag = FLAG_HTML.get(race["country"], race["country"])
        if race["start"] == race["end"]:
            date_str = race["start"].strftime("%b %d")
        else:
            date_str = f"{race['start'].strftime('%b %d')} – {race['end'].strftime('%b %d')}"
        podium = podiums.get(race["name"], [])
        podium_html = ""
        if podium:
            medals = ["🥇", "🥈", "🥉"]
            podium_html = "<div class='cycling-podium'>"
            for i, rider in enumerate(podium[:3]):
                medal = medals[i] if i < len(medals) else ""
                podium_html += f"<span class='cycling-podium-rider'>{medal} {rider['flag']} {rider['name']}</span>"
            podium_html += "</div>"
        html += f"""
        <div class='standing-row cycling-result-row'>
            <div class='cycling-result-meta'>
                <span class='race-date'>{date_str}</span>
                <span><a href='{race['pcs_url']}' target='_blank' class='race-link'>{race['name']}</a></span>
                <span class='race-country'>{flag}</span>
            </div>
            {podium_html}
        </div>"""
    html += "</div></div>"
    return html


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
            <span class='team'><a href='{race['pcs_url']}' target='_blank' class='race-link'>{race['name']}</a> {status_badge}</span>
            <span class='race-country'>{flag}</span>
        </div>"""
    html += "</div>"
    return html


def render_f1_section(f1_data, race_results):
    upcoming = f1_data.get("upcoming")
    constructors = f1_data.get("constructors", [])
    drivers = f1_data.get("drivers", [])

    # Upcoming race widget
    if upcoming:
        race_html = f"<div class='f1-session'><span class='f1-session-label'>Race</span> {race_d.strftime('%a %b %d')}</div>"
        qual_html = f"<div class='f1-session'><span class='f1-session-label'>Qualifying</span> {qual_d.strftime('%a %b %d')}</div>"

        # Fallback to calendar if API didn't return session times
        if not qual_html and not race_html:
            today = date.today()
            eastern = pytz.timezone("America/Toronto")
            for race_name, country, loc, race_date_str, _, slug in F1_CALENDAR_2026:
                race_d = date.fromisoformat(race_date_str)
                if race_d >= today:
                    qual_d = race_d - timedelta(days=1)
                    race_html = f"<div class='f1-session'><span class='f1-session-label'>Race</span> {race_d.strftime('%a %b %d')} <span class='f1-tbc'>(times TBC)</span></div>"
                    qual_html = f"<div class='f1-session'><span class='f1-session-label'>Qualifying</span> {qual_d.strftime('%a %b %d')} <span class='f1-tbc'>(times TBC)</span></div>"
                    if not upcoming.get("name"):
                        upcoming["name"] = race_name
                        upcoming["flag"] = FLAG_HTML.get(country, "🏎️")
                        upcoming["location"] = loc
                    break

        upcoming_widget = f"""
        <div class='f1-upcoming'>
            <div class='f1-upcoming-header'>
                <span class='f1-flag'>{upcoming.get('flag','')}</span>
                <div>
                    <div class='f1-race-name'>{upcoming.get('name','Upcoming Race')}</div>
                    <div class='f1-race-location'>{upcoming.get('location','')}</div>
                </div>
            </div>
            <div class='f1-sessions'>
                {qual_html}
                {race_html}
            </div>
        </div>"""
    else:
        # Fallback from hardcoded calendar
        today = date.today()
        upcoming_widget = "<p class='empty'>No upcoming race data</p>"
        for race_name, country, loc, race_date_str, _, slug in F1_CALENDAR_2026:
            race_d = date.fromisoformat(race_date_str)
            if race_d >= today:
                flag = FLAG_HTML.get(country, "🏎️")
                qual_d = race_d - timedelta(days=1)
                upcoming_widget = f"""
                <div class='f1-upcoming'>
                    <div class='f1-upcoming-header'>
                        <span class='f1-flag'>{flag}</span>
                        <div>
                            <div class='f1-race-name'>{race_name}</div>
                            <div class='f1-race-location'>{loc}</div>
                        </div>
                    </div>
                    <div class='f1-sessions'>
                        <div class='f1-session'><span class='f1-session-label'>Qualifying</span> {qual_d.strftime('%a %b %d')}</div>
                        <div class='f1-session'><span class='f1-session-label'>Race</span> {race_d.strftime('%a %b %d')}</div>
                    </div>
                </div>"""
                break

    # Race schedule — split into past and upcoming
    today = date.today()
    results_by_name = {}
    for r in race_results:
        # Strip sponsor prefixes by matching calendar names against ESPN names
        for cal_name, _, _, _, _, _ in F1_CALENDAR_2026:
            if cal_name.lower() in r["name"].lower():
                results_by_name[cal_name] = r
                break

    past_html = "<div class='standings'>"
    upcoming_sched_html = "<div class='standings'>"

    for race_name, country, loc, race_date_str, _, slug in F1_CALENDAR_2026:
        race_d = date.fromisoformat(race_date_str)
        flag = FLAG_HTML.get(country, "🏎️")
        date_str = race_d.strftime("%b %d")
        is_completed = race_d < today

        result = results_by_name.get(race_name)
        # Also try matching last 3 words
        if not result:
            words = race_name.split()
            if len(words) >= 3:
                result = results_by_name.get(" ".join(words[-3:]))

        podium_html = ""
        if is_completed and result and result.get("podium"):
            medals = ["🥇", "🥈", "🥉"]
            podium_html = "<div class='f1-podium'>"
            for i, rider in enumerate(result["podium"][:3]):
                flag_html = f'<img src="{rider["flag_url"]}" class="f1-flag-sm" alt="{rider["flag_alt"]}">' if rider.get("flag_url") else ""
                podium_html += f"<span class='f1-podium-rider'>{medals[i]} {flag_html} {rider['name']}</span>"
            podium_html += "</div>"

        if is_completed:
            past_html += f"""
        <div class='standing-row f1-schedule-row f1-completed-row'>
            <div class='f1-schedule-meta'>
                <span class='race-date'>{date_str}</span>
                <span class='team'>{race_name}</span>
                <span class='race-country'>{flag}</span>
            </div>
            {podium_html}
        </div>"""
        else:
            upcoming_sched_html += f"""
        <div class='standing-row f1-schedule-row'>
            <div class='f1-schedule-meta'>
                <span class='race-date'>{date_str}</span>
                <span class='team'>{race_name}</span>
                <span class='f1-loc'>{loc}</span>
                <span class='race-country'>{flag}</span>
            </div>
        </div>"""
    past_html += "</div>"
    upcoming_sched_html += "</div>"

    schedule_toggle = f"""
    <button class='fixture-toggle' id='f1-past-toggle-btn' onclick='toggleSection("f1-past-toggle-btn","f1-past-body")'>
        <span class='toggle-arrow'>▾</span> Past Races
    </button>
    <div class='fixture-calendar' id='f1-past-body'>
        {past_html}
    </div>
    <button class='fixture-toggle' id='f1-upcoming-toggle-btn' onclick='toggleSection("f1-upcoming-toggle-btn","f1-upcoming-body")'>
        <span class='toggle-arrow'>▾</span> Upcoming Races
    </button>
    <div class='fixture-calendar' id='f1-upcoming-body'>
        {upcoming_sched_html}
    </div>"""

    # Standings
    constructors_html = "<div class='standings'>"
    for i, c in enumerate(constructors):
        logo_html = f'<img src="{c["logo"]}" class="team-logo-sm" alt="">' if c.get("logo") else ""
        constructors_html += f"""
        <div class='standing-row'>
            <span class='pos'>{i+1}</span>
            <span class='team'>{logo_html}{c['name']}</span>
            <span class='pts'>{c['points']}</span>
        </div>"""
    constructors_html += "</div>"

    drivers_html = "<div class='standings' style='display:none' id='f1-drivers-table'>"
    for i, d in enumerate(drivers):
        logo_html = f'<img src="{d["team_logo"]}" class="team-logo-sm" alt="">' if d.get("team_logo") else ""
        drivers_html += f"""
        <div class='standing-row'>
            <span class='pos'>{i+1}</span>
            <span class='team'>{logo_html}{d['name']}</span>
            <span class='pts'>{d['points']}</span>
        </div>"""
    drivers_html += "</div>"

    standings_html = f"""
    <div class='f1-standings-toggle'>
        <button class='f1-toggle-btn f1-toggle-active' id='f1-btn-constructors' onclick='switchF1Standings("constructors")'>Constructors</button>
        <button class='f1-toggle-btn' id='f1-btn-drivers' onclick='switchF1Standings("drivers")'>Drivers</button>
    </div>
    <div id='f1-constructors-table'>{constructors_html}</div>
    <div id='f1-drivers-table-wrap' style='display:none'>{drivers_html}</div>"""

    return upcoming_widget, schedule_toggle, standings_html


def get_fpl_data():
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        bootstrap = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", headers=headers, timeout=10).json()
        entry = requests.get(f"https://fantasy.premierleague.com/api/entry/{FPL_TEAM_ID}/", headers=headers, timeout=10).json()
        current_event = entry.get("current_event", 1)
        history = requests.get(f"https://fantasy.premierleague.com/api/entry/{FPL_TEAM_ID}/history/", headers=headers, timeout=10).json()
        live_data = requests.get(f"https://fantasy.premierleague.com/api/event/{current_event}/live/", headers=headers, timeout=10).json()
        picks_data = requests.get(f"https://fantasy.premierleague.com/api/entry/{FPL_TEAM_ID}/event/{current_event}/picks/", headers=headers, timeout=10).json()
        if "detail" in picks_data or not picks_data.get("picks"):
            return None

        player_map = {p["id"]: p for p in bootstrap.get("elements", [])}
        team_map = {t["id"]: t["code"] for t in bootstrap.get("teams", [])}
        live_points_map = {e["id"]: e["stats"]["total_points"] for e in live_data.get("elements", [])}

        events = bootstrap.get("events", [])
        current_gw = next((e for e in events if e.get("is_current")), None)
        next_gw = next((e for e in events if e.get("is_next")), None)
        active_gw = current_gw or next_gw

        deadline_str = ""
        next_gw_name = ""
        if next_gw:
            deadline_raw = next_gw.get("deadline_time", "")
            next_gw_name = next_gw.get("name", "")
            if deadline_raw:
                eastern = pytz.timezone("America/Toronto")
                dt = datetime.fromisoformat(deadline_raw.replace("Z", "+00:00"))
                dt_eastern = dt.astimezone(eastern)
                deadline_str = dt_eastern.strftime("%a %b %d · %I:%M %p")

        gw_name = active_gw.get("name", f"Gameweek {current_event}") if active_gw else f"Gameweek {current_event}"
        gw_points = entry.get("summary_event_points", 0)
        gw_rank = entry.get("summary_event_rank", 0)
        overall_points = entry.get("summary_overall_points", 0)
        overall_rank = entry.get("summary_overall_rank", 0)

        past = history.get("current", [])
        overall_rank_change = None
        if len(past) >= 2:
            overall_rank_change = past[-2].get("overall_rank", 0) - overall_rank

        picks_history = picks_data.get("entry_history", {})
        team_value = picks_history.get("value", 0) / 10
        bank = picks_history.get("bank", 0) / 10
        points_on_bench = picks_history.get("points_on_bench", 0)

        picks = picks_data.get("picks", [])
        starters = [p for p in picks if p["position"] <= 11]
        bench = [p for p in picks if p["position"] > 11]
        position_labels = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}

        def format_player(pick):
            player = player_map.get(pick["element"], {})
            name = player.get("web_name", "Unknown")
            pos = position_labels.get(pick["element_type"], "?")
            pts = live_points_map.get(pick["element"], None)
            team_code = team_map.get(player.get("team", 0), None)
            badge_url = f"https://resources.premierleague.com/premierleague/badges/50/t{team_code}.png" if team_code else ""
            suffix = ""
            if pick["is_captain"]:
                suffix = " ©"
            elif pick["is_vice_captain"]:
                suffix = " (v)"
            return f"{name}{suffix}", pos, pts, badge_url

        by_position = {1: [], 2: [], 3: [], 4: []}
        for pick in starters:
            name, pos, pts, badge = format_player(pick)
            by_position[pick["element_type"]].append((name, pos, pts, badge))

        bench_names = []
        for pick in bench:
            name, pos, pts, badge = format_player(pick)
            bench_names.append((name, pos, pts))

        auto_subs = picks_data.get("automatic_subs", [])
        auto_sub_strs = []
        for sub in auto_subs:
            player_in = player_map.get(sub["element_in"], {}).get("web_name", "?")
            player_out = player_map.get(sub["element_out"], {}).get("web_name", "?")
            auto_sub_strs.append(f"{player_in} ↔ {player_out}")

        chips_played = {c["name"]: c["event"] for c in history.get("chips", [])}
        all_chips = [
            ("wildcard", "WC1", 1, 19),
            ("wildcard", "WC2", 20, 38),
            ("freehit", "FH", 1, 38),
            ("bboost", "BB", 1, 38),
            ("3xc", "TC", 1, 38),
        ]
        chip_status = []
        for chip_name, label, start_gw, end_gw in all_chips:
            played_gw = chips_played.get(chip_name)
            if played_gw:
                chip_status.append({"label": label, "used": True, "gw": played_gw})
            elif start_gw <= current_event <= end_gw:
                chip_status.append({"label": label, "used": False, "gw": None})

        return {
            "gw_name": gw_name,
            "next_gw_name": next_gw_name,
            "deadline_str": deadline_str,
            "gw_points": gw_points,
            "gw_rank": f"{gw_rank:,}",
            "overall_points": overall_points,
            "overall_rank": f"{overall_rank:,}",
            "overall_rank_change": overall_rank_change,
            "team_value": f"£{team_value:.1f}m",
            "bank": f"£{bank:.1f}m",
            "points_on_bench": points_on_bench,
            "by_position": by_position,
            "bench_names": bench_names,
            "auto_subs": auto_sub_strs,
            "current_event": current_event,
            "chip_status": chip_status,
        }
    except:
        return None


def render_fpl(fpl):
    if not fpl:
        return "<p class='empty'>FPL data unavailable</p>"

    position_order = [(1, "GK"), (2, "DEF"), (3, "MID"), (4, "FWD")]
    squad_html = ""
    for pos_id, pos_label in position_order:
        players = fpl["by_position"].get(pos_id, [])
        if not players:
            continue
        squad_html += "<div class='fpl-position-row'>"
        for name, pos, pts, badge in players:
            is_captain = "©" in name
            is_vice = "(v)" in name
            badge_html = f'<img src="{badge}" class="fpl-club-badge" alt="">' if badge else ""
            if is_captain:
                player_class = "fpl-player fpl-player-captain"
                badge_el = "<span class='fpl-captain'>C</span>"
            elif is_vice:
                player_class = "fpl-player fpl-player-vice"
                badge_el = "<span class='fpl-vice'>V</span>"
            else:
                player_class = "fpl-player"
                badge_el = ""
            clean_name = name.replace(" ©", "").replace(" (v)", "")
            multiplier = 2 if is_captain else 1
            display_pts = pts * multiplier if pts is not None else None
            if display_pts is not None and display_pts >= 8:
                pts_class = "fpl-pts-high"
            elif display_pts is not None and display_pts <= 2:
                pts_class = "fpl-pts-low"
            else:
                pts_class = "fpl-pts-mid"
            pts_html = f"<span class='{pts_class}'>{display_pts}</span>" if display_pts is not None else ""
            squad_html += f"<div class='{player_class}'>{badge_el}{badge_html}<span class='fpl-player-name'>{clean_name}</span><span class='fpl-pos-badge'>{pos_label}</span>{pts_html}</div>"
        squad_html += "</div>"

    bench_parts = []
    for name, pos, pts in fpl["bench_names"]:
        clean = name.replace(" ©", "").replace(" (v)", "")
        pts_str = f" {pts}pts" if pts is not None else ""
        bench_parts.append(f"{clean} ({pos}){pts_str}")
    bench_html = " · ".join(bench_parts) if bench_parts else ""

    auto_sub_html = ""
    if fpl["auto_subs"]:
        auto_sub_html = f"<div class='fpl-auto-subs'>Auto subs: {' · '.join(fpl['auto_subs'])}</div>"

    deadline_html = ""
    if fpl["deadline_str"] and fpl["next_gw_name"]:
        deadline_html = f"<div class='fpl-deadline'>Next deadline · {fpl['next_gw_name']}: {fpl['deadline_str']}</div>"

    team_url = f"https://fantasy.premierleague.com/entry/{FPL_TEAM_ID}/event/{fpl['current_event']}"

    overall_rank_change = fpl.get("overall_rank_change")
    if overall_rank_change and overall_rank_change > 0:
        rank_arrow = f"<span class='fpl-rank-up'>↑ {overall_rank_change:,}</span>"
        overall_stat_class = "fpl-stat fpl-stat-up"
    elif overall_rank_change and overall_rank_change < 0:
        rank_arrow = f"<span class='fpl-rank-down'>↓ {abs(overall_rank_change):,}</span>"
        overall_stat_class = "fpl-stat fpl-stat-down"
    else:
        rank_arrow = ""
        overall_stat_class = "fpl-stat"

    chips_html = ""
    if fpl.get("chip_status"):
        chips_html = "<div class='fpl-chips'>"
        for chip in fpl["chip_status"]:
            if chip["used"]:
                chips_html += f"<span class='fpl-chip fpl-chip-used'>{chip['label']} GW{chip['gw']}</span>"
            else:
                chips_html += f"<span class='fpl-chip fpl-chip-available'>{chip['label']}</span>"
        chips_html += "</div>"

    return f"""
    <div class='fpl-widget'>
        <div class='fpl-header'>
            <div class='fpl-gw'><a href='{team_url}' target='_blank' class='fpl-team-link'>{fpl['gw_name']} ↗</a></div>
            {deadline_html}
        </div>
        <div class='fpl-stats'>
            <div class='fpl-stat'>
                <div class='fpl-stat-label'>GW Points</div>
                <div class='fpl-stat-value'>{fpl['gw_points']}</div>
                <div class='fpl-stat-sub'>Rank {fpl['gw_rank']}</div>
            </div>
            <div class='{overall_stat_class}'>
                <div class='fpl-stat-label'>Overall</div>
                <div class='fpl-stat-value'>{fpl['overall_points']}</div>
                <div class='fpl-stat-sub'>Rank {fpl['overall_rank']} {rank_arrow}</div>
            </div>
            <div class='fpl-stat'>
                <div class='fpl-stat-label'>Team Value</div>
                <div class='fpl-stat-value'>{fpl['team_value']}</div>
                <div class='fpl-stat-sub'>Bank {fpl['bank']}</div>
            </div>
            <div class='fpl-stat'>
                <div class='fpl-stat-label'>Bench Pts</div>
                <div class='fpl-stat-value'>{fpl['points_on_bench']}</div>
                <div class='fpl-stat-sub'>&nbsp;</div>
            </div>
        </div>
        {chips_html}
        <div class='fpl-squad'>{squad_html}</div>
        {auto_sub_html}
        <div class='fpl-bench'>Bench: {bench_html}</div>
    </div>"""


def get_weather(lat=43.70, lon=-79.42):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,apparent_temperature,weather_code&daily=temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max&timezone=auto&forecast_days=11"
        response = requests.get(url, timeout=5)
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
        eastern = pytz.timezone("America/Toronto")
        base_date = datetime.now(eastern).date()
        day_names = []
        for n in range(8):
            d = base_date + timedelta(days=n)
            if n == 0:
                day_names.append("Today")
            elif n == 1:
                day_names.append("Tomorrow")
            else:
                day_names.append(d.strftime("%A"))
        for i in range(1, 11):
            d = date.fromisoformat(daily["time"][i])
            name = day_names[i] if i < len(day_names) else d.strftime("%A")
            code = daily["weather_code"][i]
            desc, icon = weather_codes.get(code, ("Unknown", "🌡️"))
            days.append({
                "name": name,
                "date": d.strftime("%m/%d"),
                "icon": icon, "desc": desc,
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


def get_city_name(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        headers = {"User-Agent": "TylersBriefing/1.0"}
        response = requests.get(url, timeout=5, headers=headers)
        data = response.json()
        address = data.get("address", {})
        city = (address.get("city") or address.get("town") or
                address.get("village") or address.get("municipality") or "Your Location")
        return city
    except:
        return "Your Location"


def render_weather(w, city="Toronto"):
    if not w:
        return "<p class='empty'>Weather unavailable</p>"
    forecast_html = ""
    for day in w["days"][:3]:
        forecast_html += f"""
        <div class='forecast-day'>
            <div class='forecast-name'>{day['name']}</div>
            <div class='forecast-date'>{day['date']}</div>
            <div class='forecast-icon'>{day['icon']}</div>
            <div class='forecast-desc'>{day['desc']}</div>
            <div class='forecast-temps'>{day['high']}° / {day['low']}°</div>
            <div class='forecast-precip'>{day['precip']}% precip</div>
        </div>"""
    extended_html = ""
    for day in w["days"]:
        extended_html += f"""
        <div class='forecast-day'>
            <div class='forecast-name'>{day['name']}</div>
            <div class='forecast-date'>{day['date']}</div>
            <div class='forecast-icon'>{day['icon']}</div>
            <div class='forecast-desc'>{day['desc']}</div>
            <div class='forecast-temps'>{day['high']}° / {day['low']}°</div>
            <div class='forecast-precip'>{day['precip']}% precip</div>
        </div>"""
    return f"""
    <div class='weather-widget' id='weather-widget'>
        <div class='weather-current'>
            <div class='weather-main'>
                <span class='weather-icon'>{w['current_icon']}</span>
                <span class='weather-temp'>{w['current_temp']}°C</span>
            </div>
            <div class='weather-details'>
                <div class='weather-desc'>{w['current_desc']} · <span id='weather-city'>{city}</span></div>
                <div class='weather-meta'>Feels like {w['feels_like']}°C · High {w['today_high']}° Low {w['today_low']}° · {w['today_precip']}% precip</div>
            </div>
        </div>
        <div class='weather-forecast' id='weather-forecast'>
            {forecast_html}
        </div>
        <button class='extended-forecast-toggle' id='extended-forecast-btn' onclick='toggleExtendedForecast()'>
            <span class='toggle-arrow'>▾</span> 10-Day Forecast
        </button>
        <div class='extended-forecast' id='extended-forecast'>
            {extended_html}
        </div>
    </div>"""


def get_scores(sport, league, for_date=None):
    try:
        if for_date:
            date_str = for_date.strftime("%Y%m%d")
            url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard?dates={date_str}"
        else:
            url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
        response = requests.get(url, timeout=5)
        data = response.json()
        return data.get("events", [])
    except:
        return []


def get_scores_range(sport, league, start_date, end_date):
    try:
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard?dates={start_str}-{end_str}"
        response = requests.get(url, timeout=8)
        data = response.json()
        return data.get("events", []), league
    except:
        return [], league


def get_standings(sport, league):
    url = f"https://site.api.espn.com/apis/v2/sports/{sport}/{league}/standings"
    try:
        response = requests.get(url, timeout=5)
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


def get_youtube_videos(channel_id=None, limit=2, playlist_id=None):
    if playlist_id:
        url = f"https://www.youtube.com/feeds/videos.xml?playlist_id={playlist_id}"
    else:
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        feed = feedparser.parse(url, request_headers=headers)
        videos = []
        for entry in feed.entries:
            title = entry.get("title", "No title")
            link = entry.get("link", "#")
            published = entry.get("published", "")
            video_id = entry.get("yt_videoid", "")
            if "/shorts/" in link:
                continue
            thumbnail = f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg" if video_id else ""
            videos.append({
                "title": title,
                "link": link,
                "published": published,
                "thumbnail": thumbnail
            })
            if len(videos) >= limit:
                break
        return videos
    except:
        return []


def get_podcast_episodes(url, limit=2):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        feed = feedparser.parse(url, request_headers=headers)
        episodes = []
        for entry in feed.entries[:limit]:
            title = entry.get("title", "No title")
            link = entry.get("link", "")
            if not link or not link.startswith("http"):
                link = entry.get("id", "#")
            published = entry.get("published", "")
            duration = ""
            if hasattr(entry, "itunes_duration"):
                duration = entry.itunes_duration
            thumbnail = ""
            thumbs = entry.get("media_thumbnail", [])
            if thumbs:
                thumbnail = thumbs[0].get("url", "")
            if not thumbnail and feed.feed.get("image"):
                thumbnail = feed.feed.image.get("href", "")
            episodes.append({
                "title": title,
                "link": link,
                "published": published,
                "duration": duration,
                "thumbnail": thumbnail
            })
        return episodes, feed.feed.get("title", "")
    except:
        return [], ""


def fetch_all_sports(today, yesterday):
    tasks = {
        "mlb_today": (get_scores, ("baseball", "mlb", today)),
        "mlb_yesterday": (get_scores, ("baseball", "mlb", yesterday)),
        "pl_today": (get_scores, ("soccer", "eng.1", today)),
        "pl_yesterday": (get_scores, ("soccer", "eng.1", yesterday)),
        "nhl_today": (get_scores, ("hockey", "nhl", today)),
        "nhl_yesterday": (get_scores, ("hockey", "nhl", yesterday)),
        "ucl_today": (get_scores, ("soccer", "uefa.champions", today)),
        "ucl_yesterday": (get_scores, ("soccer", "uefa.champions", yesterday)),
        "nba_today": (get_scores, ("basketball", "nba", today)),
        "nba_yesterday": (get_scores, ("basketball", "nba", yesterday)),
        "mls_today": (get_scores, ("soccer", "usa.1", today)),
        "mls_yesterday": (get_scores, ("soccer", "usa.1", yesterday)),
        "nhl_standings": (get_standings, ("hockey", "nhl")),
        "mlb_standings": (get_standings, ("baseball", "mlb")),
        "pl_standings": (get_standings, ("soccer", "eng.1")),
        "ucl_standings": (get_standings, ("soccer", "uefa.champions")),
        "fpl": (get_fpl_data, ()),
        "mlb_stories": (get_stories, ("https://www.sportsnet.ca/mlb/feed/",)),
        "pl_stories": (get_stories, ("https://www.theguardian.com/football/premierleague/rss",)),
        "ucl_stories": (get_stories, ("https://www.theguardian.com/football/championsleague/rss",)),
        "nhl_stories": (get_stories, ("https://www.sportsnet.ca/hockey/nhl/feed/",)),
        "cycling_stories": (get_stories, ("https://www.cyclingnews.com/rss",)),
        "f1_data": (get_f1_data, ()),
        "f1_results": (get_f1_race_results, ()),
        "cycling_podiums": (get_cycling_podiums, ()),
    }
    results = {}
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(fn, *args): key for key, (fn, args) in tasks.items()}
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except:
                results[key] = [] if "standings" not in key else {}
    return results


def fetch_all_news():
    tasks = {
        "cbc_toronto": (get_stories, ("https://www.cbc.ca/cmlink/rss-canada-toronto", 6)),
        "cbc_canada": (get_stories, ("https://www.cbc.ca/cmlink/rss-topstories", 5)),
        "globe_canada": (get_stories, ("https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/canada/", 5)),
        "bbc_world": (get_stories, ("https://feeds.bbci.co.uk/news/world/rss.xml", 4)),
        "guardian_world": (get_stories, ("https://www.theguardian.com/world/rss", 4)),
        "globe_world": (get_stories, ("https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/world/", 4)),
        "weather": (get_weather, ()),
    }
    results = {}
    with ThreadPoolExecutor(max_workers=7) as executor:
        futures = {executor.submit(fn, *args): key for key, (fn, args) in tasks.items()}
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except:
                results[key] = [] if key != "weather" else None
    return results


def fetch_all_media():
    results = {"videos": {}, "podcasts": {}}
    video_tasks = {name: (get_youtube_videos, (cid, 2)) for name, cid in YOUTUBE_CHANNELS}
    playlist_tasks = {name: (get_youtube_videos, (None, 2, pid)) for name, pid in YOUTUBE_PLAYLISTS}
    video_tasks.update(playlist_tasks)
    podcast_tasks = {name: (get_podcast_episodes, (url, 2)) for name, url, _ in PODCAST_FEEDS}
    all_tasks = {**{f"v_{k}": v for k, v in video_tasks.items()},
                 **{f"p_{k}": v for k, v in podcast_tasks.items()}}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fn, *args): key for key, (fn, args) in all_tasks.items()}
        for future in as_completed(futures):
            key = futures[future]
            try:
                if key.startswith("v_"):
                    results["videos"][key[2:]] = future.result()
                else:
                    results["podcasts"][key[2:]] = future.result()
            except:
                if key.startswith("v_"):
                    results["videos"][key[2:]] = []
                else:
                    results["podcasts"][key[2:]] = ([], "")
    return results


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
    if state == "pre" and status.lower() in ("scheduled", "schedule"):
        try:
            eastern = pytz.timezone("America/Toronto")
            dt_utc = datetime.fromisoformat(game["date"].replace("Z", "+00:00"))
            dt_eastern = dt_utc.astimezone(eastern)
            status = dt_eastern.strftime("%I:%M %p").lstrip("0")
        except:
            pass
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
                    {'<img class="team-logo" src="' + away_logo + '" alt="">' if away_logo else ''}
                    <span style='{away_bold}'>{away_team}</span>
                </div>
                <span class='score-num' style='{away_bold}'>{away_score}</span>
            </div>
            <div class='score-row'>
                <div class='score-team'>
                    {'<img class="team-logo" src="' + home_logo + '" alt="">' if home_logo else ''}
                    <span style='{home_bold}'>{home_team}</span>
                </div>
                <span class='score-num' style='{home_bold}'>{home_score}</span>
            </div>
            <div class='score-status'>{status}</div>
        </div>
    </a>"""


def render_scores_collapsible(yesterday_games, today_games, id_prefix):
    """Render scores with collapsible yesterday/today toggles using label as button."""
    html = ""
    if yesterday_games:
        html += f"""
        <div class='scores-section-toggle open' id='{id_prefix}-yday-btn' onclick='toggleScores("{id_prefix}-yday-btn", "{id_prefix}-yday-body")'>
            <span class='toggle-arrow'>▾</span> Yesterday's results
        </div>
        <div class='scores-toggle-body open' id='{id_prefix}-yday-body'>
            <div class='scores-grid'>"""
        for game in yesterday_games:
            html += render_game_card(game)
        html += "</div></div>"

    if today_games:
        html += f"""
        <div class='scores-section-toggle open' id='{id_prefix}-today-btn' onclick='toggleScores("{id_prefix}-today-btn", "{id_prefix}-today-body")'>
            <span class='toggle-arrow'>▾</span> Today's fixtures
        </div>
        <div class='scores-toggle-body open' id='{id_prefix}-today-body'>
            <div class='scores-grid'>"""
        for game in today_games:
            html += render_game_card(game)
        html += "</div></div>"

    if not yesterday_games and not today_games:
        html += "<p class='empty'>No games yesterday or today</p>"
    return html


def render_scores(yesterday_games, today_games):
    html = ""
    if yesterday_games:
        html += "<div class='scores-section-label'>Yesterday's results</div>"
        html += "<div class='scores-grid'>"
        for game in yesterday_games:
            html += render_game_card(game)
        html += "</div>"
    if today_games:
        html += "<div class='scores-section-label'>Today's fixtures</div>"
        html += "<div class='scores-grid'>"
        for game in today_games:
            html += render_game_card(game)
        html += "</div>"
    if not yesterday_games and not today_games:
        html += "<p class='empty'>No games yesterday or today</p>"
    return html


def render_my_teams(teams_data):
    has_any = any(t["yesterday_game"] or t["today_game"] for t in teams_data)
    if not has_any:
        return "<p class='empty'>No recent or upcoming games</p>"

    def game_sort_time(game):
        try:
            eastern = pytz.timezone("America/Toronto")
            dt_utc = datetime.fromisoformat(game["date"].replace("Z", "+00:00"))
            return dt_utc.astimezone(eastern).strftime("%H:%M")
        except:
            return "99:99"

    yesterday_cards = sorted(
        [t["yesterday_game"] for t in teams_data if t["yesterday_game"]],
        key=game_sort_time
    )
    today_cards = sorted(
        [t["today_game"] for t in teams_data if t["today_game"]],
        key=game_sort_time
    )
    no_game = [t for t in teams_data if not t["yesterday_game"] and not t["today_game"]]

    html = ""
    if yesterday_cards:
        html += "<div class='scores-section-label'>Yesterday</div>"
        html += "<div class='scores-grid'>"
        for game in yesterday_cards:
            html += render_game_card(game)
        html += "</div>"
    if today_cards:
        html += "<div class='scores-section-label'>Today</div>"
        html += "<div class='scores-grid'>"
        for game in today_cards:
            html += render_game_card(game)
        html += "</div>"
    if no_game:
        html += "<div class='scores-grid'>"
        for team in no_game:
            html += f"""
            <div class='score-card'>
                <div class='score-row'>
                    <div class='score-team'>
                        <span style='color:#999; font-size:12px;'>{team['name']}</span>
                    </div>
                </div>
                <div class='score-status'>No recent game</div>
            </div>"""
        html += "</div>"
    return html


def render_nhl_standings(data):
    try:
        all_entries = []
        for conference in data.get("children", []):
            for entry in conference["standings"]["entries"]:
                all_entries.append((entry, conference.get("name", "")))
    except:
        return "<p class='empty'>Standings unavailable</p>"

    team_lookup = {}
    for entry, conf_name in all_entries:
        name = entry["team"]["shortDisplayName"]
        stats = {s["name"]: s["displayValue"] for s in entry["stats"]}
        logo = entry["team"].get("logos", [{}])[0].get("href", "") if entry["team"].get("logos") else ""
        team_lookup[name] = {"stats": stats, "logo": logo}

    # Determine wildcard spots per conference
    # NHL: top 3 per division make playoffs, then 2 wild cards per conference
    NHL_WILD_CARDS_PER_CONF = 2
    DIVISIONS_PER_CONF = {"Eastern": ["Atlantic", "Metropolitan"], "Western": ["Central", "Pacific"]}

    playoff_teams = set()
    wildcard_teams = set()

    for conf_name, divisions in DIVISIONS_PER_CONF.items():
        conf_teams_by_pts = []
        div_leaders = set()
        for div in divisions:
            teams_in_div = [(t, team_lookup[t]) for t in NHL_DIVISIONS.get(div, []) if t in team_lookup]
            teams_in_div.sort(key=lambda x: int(x[1]["stats"].get("points", "0") or "0"), reverse=True)
            # Top 3 per division make playoffs
            for i, (t, _) in enumerate(teams_in_div):
                if i < 3:
                    playoff_teams.add(t)
                    if i == 0:
                        div_leaders.add(t)
                conf_teams_by_pts.append((t, team_lookup[t]))
        # Wild cards: next best from conference not already in playoffs
        conf_teams_by_pts.sort(key=lambda x: int(x[1]["stats"].get("points", "0") or "0"), reverse=True)
        wc_count = 0
        for t, _ in conf_teams_by_pts:
            if t not in playoff_teams and wc_count < NHL_WILD_CARDS_PER_CONF:
                wildcard_teams.add(t)
                wc_count += 1

    html = ""
    for division, teams in NHL_DIVISIONS.items():
        html += f"<div class='division-label'>{division}</div>"
        html += "<div class='standings'>"
        html += "<div class='standing-header'><span class='pos'></span><span class='team'></span><span class='stat-col'>GP</span><span class='stat-col'>W</span><span class='stat-col'>L</span><span class='stat-col'>OTL</span><span class='pts'>PTS</span></div>"
        division_teams = [(team, team_lookup[team]) for team in teams if team in team_lookup]
        division_teams.sort(key=lambda x: int(x[1]["stats"].get("points", "0") or "0"), reverse=True)
        for i, (team, tdata) in enumerate(division_teams):
            s = tdata["stats"]
            logo = tdata["logo"]
            gp = s.get("gamesPlayed", "-")
            w = s.get("wins", "-")
            l = s.get("losses", "-")
            otl = s.get("otLosses", "-")
            pts = s.get("points", "-")
            logo_html = f'<img class="team-logo-sm" src="{logo}" alt="">' if logo else ""
            row_style = ""
            if team in playoff_teams and i == 0:
                row_style = "background: #dbeafe;"  # Division leader — blue
            elif team in playoff_teams:
                row_style = "background: #eff6ff;"  # Playoff spot — light blue
            elif team in wildcard_teams:
                row_style = "background: #f0fdf4;"  # Wild card — light green
            html += f"""
            <div class='standing-row' style='{row_style}'>
                <span class='pos'>{i+1}</span>
                <span class='team'>{logo_html}{team}</span>
                <span class='stat-col'>{gp}</span>
                <span class='stat-col'>{w}</span>
                <span class='stat-col'>{l}</span>
                <span class='stat-col'>{otl}</span>
                <span class='pts'>{pts}</span>
            </div>"""
        html += "</div>"

    # Legend
    html += """
    <div class='standings-legend'>
        <span class='legend-item'><span class='legend-swatch' style='background:#dbeafe'></span> Division leader</span>
        <span class='legend-item'><span class='legend-swatch' style='background:#eff6ff'></span> Playoff spot</span>
        <span class='legend-item'><span class='legend-swatch' style='background:#f0fdf4'></span> Wild card</span>
    </div>"""
    return html


def render_mlb_standings(data):
    try:
        all_entries = []
        for conference in data.get("children", []):
            for entry in conference["standings"]["entries"]:
                all_entries.append((entry, conference.get("name", "")))
    except:
        return "<p class='empty'>Standings unavailable</p>"

    team_lookup = {}
    for entry, conf_name in all_entries:
        name = entry["team"]["shortDisplayName"]
        stats = {s["name"]: s["displayValue"] for s in entry["stats"]}
        logo = entry["team"].get("logos", [{}])[0].get("href", "") if entry["team"].get("logos") else ""
        team_lookup[name] = {"stats": stats, "logo": logo, "conf": conf_name}

    # MLB: 3 division winners + 3 wild cards per league (AL, NL)
    MLB_WILD_CARDS = 3
    AL_DIVISIONS = ["AL East", "AL Central", "AL West"]
    NL_DIVISIONS = ["NL East", "NL Central", "NL West"]

    playoff_teams = set()
    div_leader_teams = set()
    wildcard_teams = set()

    for league_divs in [AL_DIVISIONS, NL_DIVISIONS]:
        league_all = []
        for div in league_divs:
            teams_in_div = [(t, team_lookup[t]) for t in MLB_DIVISIONS.get(div, []) if t in team_lookup]
            teams_in_div.sort(key=lambda x: int(x[1]["stats"].get("wins", "0") or "0"), reverse=True)
            for i, (t, _) in enumerate(teams_in_div):
                if i == 0:
                    playoff_teams.add(t)
                    div_leader_teams.add(t)
            league_all.extend(teams_in_div)
        # Wild cards from remaining
        league_all.sort(key=lambda x: int(x[1]["stats"].get("wins", "0") or "0"), reverse=True)
        wc_count = 0
        for t, _ in league_all:
            if t not in playoff_teams and wc_count < MLB_WILD_CARDS:
                wildcard_teams.add(t)
                wc_count += 1

    html = ""
    for division, teams in MLB_DIVISIONS.items():
        html += f"<div class='division-label'>{division}</div>"
        html += "<div class='standings'>"
        html += "<div class='standing-header'><span class='pos'></span><span class='team'></span><span class='stat-col'>W</span><span class='stat-col'>L</span><span class='stat-col'>PCT</span><span class='pts'>GB</span></div>"
        division_teams = [(team, team_lookup[team]) for team in teams if team in team_lookup]
        division_teams.sort(key=lambda x: int(x[1]["stats"].get("wins", "0") or "0"), reverse=True)
        for i, (team, tdata) in enumerate(division_teams):
            s = tdata["stats"]
            logo = tdata["logo"]
            w = s.get("wins", "-")
            l = s.get("losses", "-")
            pct = s.get("winPercent", "-")
            gb = s.get("gamesBehind", "-")
            logo_html = f'<img class="team-logo-sm" src="{logo}" alt="">' if logo else ""
            row_style = ""
            if team in div_leader_teams:
                row_style = "background: #dbeafe;"
            elif team in wildcard_teams:
                row_style = "background: #f0fdf4;"
            html += f"""
            <div class='standing-row' style='{row_style}'>
                <span class='pos'>{i+1}</span>
                <span class='team'>{logo_html}{team}</span>
                <span class='stat-col'>{w}</span>
                <span class='stat-col'>{l}</span>
                <span class='stat-col'>{pct}</span>
                <span class='pts'>{gb}</span>
            </div>"""
        html += "</div>"

    html += """
    <div class='standings-legend'>
        <span class='legend-item'><span class='legend-swatch' style='background:#dbeafe'></span> Division leader</span>
        <span class='legend-item'><span class='legend-swatch' style='background:#f0fdf4'></span> Wild card</span>
    </div>"""
    return html


def render_pl_standings(data):
    try:
        all_entries = []
        for conference in data.get("children", []):
            for entry in conference["standings"]["entries"]:
                all_entries.append(entry)
        all_entries = sorted(
            all_entries,
            key=lambda e: next((s["value"] for s in e["stats"] if s["name"] == "points"), 0),
            reverse=True
        )
    except:
        return "<p class='empty'>Standings unavailable</p>"

    total = len(all_entries)
    relegation_start = total - 3  # Bottom 3

    html = "<div class='standings'>"
    html += "<div class='standing-header'><span class='pos'></span><span class='team'></span><span class='stat-col'>GP</span><span class='stat-col'>W</span><span class='stat-col'>D</span><span class='stat-col'>L</span><span class='pts'>PTS</span></div>"
    for i, entry in enumerate(all_entries):
        team = entry["team"]["shortDisplayName"]
        stats = {s["name"]: s["displayValue"] for s in entry["stats"]}
        logo = entry["team"].get("logos", [{}])[0].get("href", "") if entry["team"].get("logos") else ""
        gp = stats.get("gamesPlayed", "-")
        w = stats.get("wins", "-")
        d = stats.get("ties", "-")
        l = stats.get("losses", "-")
        pts = stats.get("points", "-")
        logo_html = f'<img class="team-logo-sm" src="{logo}" alt="">' if logo else ""
        row_style = ""
        if i < PL_CL_SPOTS:
            row_style = "background: #dbeafe;"  # CL — blue
        elif i >= relegation_start:
            row_style = "background: #fee2e2;"  # Relegation — red
        html += f"""
        <div class='standing-row' style='{row_style}'>
            <span class='pos'>{i+1}</span>
            <span class='team'>{logo_html}{team}</span>
            <span class='stat-col'>{gp}</span>
            <span class='stat-col'>{w}</span>
            <span class='stat-col'>{d}</span>
            <span class='stat-col'>{l}</span>
            <span class='pts'>{pts}</span>
        </div>"""
    html += "</div>"
    html += f"""
    <div class='standings-legend'>
        <span class='legend-item'><span class='legend-swatch' style='background:#dbeafe'></span> Champions League (Top {PL_CL_SPOTS})</span>
        <span class='legend-item'><span class='legend-swatch' style='background:#fee2e2'></span> Relegation</span>
    </div>"""
    return html


def render_ucl_standings(data):
    try:
        all_entries = []
        for group in data.get("children", []):
            for entry in group["standings"]["entries"]:
                all_entries.append(entry)
        all_entries = sorted(
            all_entries,
            key=lambda e: next((s["value"] for s in e["stats"] if s["name"] == "points"), 0),
            reverse=True
        )
    except:
        return "<p class='empty'>Standings unavailable</p>"
    html = "<div class='standings'>"
    html += "<div class='standing-header'><span class='pos'></span><span class='team'></span><span class='stat-col'>GP</span><span class='stat-col'>W</span><span class='stat-col'>D</span><span class='stat-col'>L</span><span class='pts'>PTS</span></div>"
    for i, entry in enumerate(all_entries):
        team = entry["team"]["shortDisplayName"]
        stats = {s["name"]: s["displayValue"] for s in entry["stats"]}
        logo = entry["team"].get("logos", [{}])[0].get("href", "") if entry["team"].get("logos") else ""
        gp = stats.get("gamesPlayed", "-")
        w = stats.get("wins", "-")
        d = stats.get("ties", "-")
        l = stats.get("losses", "-")
        pts = stats.get("points", "-")
        logo_html = f'<img class="team-logo-sm" src="{logo}" alt="">' if logo else ""
        html += f"""
        <div class='standing-row'>
            <span class='pos'>{i+1}</span>
            <span class='team'>{logo_html}{team}</span>
            <span class='stat-col'>{gp}</span>
            <span class='stat-col'>{w}</span>
            <span class='stat-col'>{d}</span>
            <span class='stat-col'>{l}</span>
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


def render_news_section(sources):
    html = ""
    for source_name, tag_class, stories in sources:
        if not stories:
            continue
        for entry in stories:
            title = entry.get("title", "No title")
            link = entry.get("link", "#")
            published = entry.get("published", "")
            thumbnail = entry.get("thumbnail", "")
            thumb_html = f'<img class="news-thumb" src="{thumbnail}" alt="">' if thumbnail else ""
            html += f"""
            <div class='news-item'>
                {thumb_html}
                <div class='news-content'>
                    <a href='{link}' target='_blank'>{title}</a>
                    <div class='story-meta'><span class='tag {tag_class}'>{source_name}</span> · {published}</div>
                </div>
            </div>"""
    if not html:
        html = "<p class='empty'>No stories available</p>"
    return html


def render_videos(channels_data):
    html = ""
    for channel_name, videos in channels_data:
        if not videos:
            continue
        html += f"<div class='division-label'>{channel_name}</div>"
        for video in videos:
            thumbnail = video.get("thumbnail", "")
            thumb_html = f'<img class="news-thumb" src="{thumbnail}" alt="">' if thumbnail else ""
            html += f"""
            <div class='news-item'>
                {thumb_html}
                <div class='news-content'>
                    <a href='{video["link"]}' target='_blank'>{video["title"]}</a>
                    <div class='story-meta'>{video["published"]}</div>
                </div>
            </div>"""
    if not html:
        html = "<p class='empty'>No videos available</p>"
    return html


def render_podcasts(podcasts_data):
    html = ""
    for podcast_name, episodes, artwork, spotify_url in podcasts_data:
        if not episodes:
            continue
        html += f"<div class='division-label'><a href='{spotify_url}' target='_blank' style='color:#555; text-decoration:none;'>{podcast_name} ↗</a></div>"
        for episode in episodes:
            thumb_html = f'<img class="news-thumb" src="{artwork}" alt="">' if artwork else ""
            duration = f" · {episode['duration']}" if episode.get("duration") else ""
            html += f"""
            <div class='news-item'>
                {thumb_html}
                <div class='news-content'>
                    <a href='{spotify_url}' target='_blank'>{episode["title"]}</a>
                    <div class='story-meta'>{episode["published"]}{duration}</div>
                </div>
            </div>"""
    if not html:
        html = "<p class='empty'>No episodes available</p>"
    return html


CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Google Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; color: #111; max-width: 600px; margin: 0 auto; }
.header { padding: 16px; border-bottom: 0.5px solid #eee; background: white; position: sticky; top: 0; z-index: 10; }
.header h1 { font-size: 18px; font-weight: 500; }
.header .date { font-size: 11px; color: #999; margin-top: 2px; }
.nav { display: flex; background: white; border-bottom: 0.5px solid #eee; position: sticky; top: 52px; z-index: 10; }
.nav a { flex: 1; padding: 10px; text-align: center; font-size: 13px; color: #999; text-decoration: none; border-bottom: 2px solid transparent; }
.nav a.active { color: #111; border-bottom: 2px solid #111; font-weight: 500; }
.body { padding: 12px 16px; }
.section-label { font-size: 10px; font-weight: 500; color: #999; text-transform: uppercase; letter-spacing: 0.08em; margin: 14px 0 8px; }
.scores-section-label { font-size: 11px; color: #999; margin: 8px 0 6px; font-style: italic; }
.scores-section-toggle { font-size: 11px; color: #999; margin: 8px 0 6px; font-style: italic; cursor: pointer; display: flex; align-items: center; gap: 4px; user-select: none; }
.scores-section-toggle:hover { color: #555; }
.scores-section-toggle .toggle-arrow { transition: transform 0.2s; display: inline-block; font-style: normal; }
.scores-section-toggle.open .toggle-arrow { transform: rotate(0deg); }
.scores-section-toggle:not(.open) .toggle-arrow { transform: rotate(-90deg); }
.scores-toggle-body { overflow: hidden; }
.scores-toggle-body:not(.open) { display: none; }
.division-label { font-size: 11px; font-weight: 500; color: #555; margin: 10px 0 4px; padding-left: 2px; }
.sport-divider { border: none; border-top: 2px solid #eee; margin: 20px 0; }
.news-divider { border: none; border-top: 1px solid #eee; margin: 16px 0; }
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
.forecast-date { font-size: 10px; color: #999; margin-bottom: 4px; }
.forecast-icon { font-size: 20px; margin-bottom: 2px; }
.forecast-desc { font-size: 10px; color: #999; margin-bottom: 2px; }
.forecast-temps { font-size: 12px; font-weight: 500; color: #111; }
.forecast-precip { font-size: 10px; color: #999; margin-top: 2px; }
.scores-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; margin-bottom: 8px; }
.score-card-link { text-decoration: none; color: inherit; display: block; }
.score-card { background: white; border: 0.5px solid #eee; border-radius: 10px; padding: 8px 10px; }
.score-team { display: flex; align-items: center; gap: 6px; flex: 1; }
.score-row { display: flex; justify-content: space-between; align-items: center; font-size: 13px; margin: 3px 0; }
.score-num { font-weight: 500; min-width: 20px; text-align: right; }
.score-status { font-size: 9px; color: #999; margin-top: 6px; }
.team-logo { width: 20px; height: 20px; object-fit: contain; }
.team-logo-sm { width: 16px; height: 16px; object-fit: contain; margin-right: 4px; vertical-align: middle; }
.standings { background: white; border: 0.5px solid #eee; border-radius: 10px; overflow: hidden; margin-bottom: 4px; }
.standing-header { display: flex; align-items: center; padding: 5px 10px; font-size: 10px; color: #999; font-weight: 500; text-transform: uppercase; border-bottom: 0.5px solid #eee; }
.standing-row { display: flex; align-items: center; padding: 6px 10px; border-bottom: 0.5px solid #f5f5f5; font-size: 12px; }
.standing-row:last-child { border-bottom: none; }
.live-row { background: #fff9f0; }
.pos { color: #999; width: 18px; font-size: 11px; flex-shrink: 0; }
.team { flex: 1; display: flex; align-items: center; }
.stat-col { width: 30px; text-align: center; font-size: 11px; color: #555; flex-shrink: 0; }
.pts { width: 30px; text-align: center; font-weight: 500; font-size: 12px; flex-shrink: 0; }
.race-date { font-size: 11px; color: #999; white-space: nowrap; min-width: 80px; }
.race-country { font-size: 16px; flex-shrink: 0; }
.race-link { color: #111; text-decoration: none; }
.race-link:hover { text-decoration: underline; }
.live-badge { background: #fee2e2; color: #991b1b; font-size: 9px; font-weight: 500; padding: 1px 6px; border-radius: 20px; margin-left: 6px; }
.athletic-link { display: flex; align-items: center; gap: 8px; padding: 8px 0 2px; text-decoration: none; }
.athletic-link span { font-size: 12px; color: #999; }
.athletic-link:hover span { color: #111; text-decoration: underline; }
.athletic-badge { display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px; border-radius: 4px; background: #111; color: white; font-size: 11px; font-weight: 600; flex-shrink: 0; }
.story-item { display: flex; gap: 10px; padding: 8px 0; border-bottom: 0.5px solid #f0f0f0; align-items: flex-start; }
.story-item:last-child { border-bottom: none; }
.news-item { display: flex; gap: 10px; padding: 10px 0; border-bottom: 0.5px solid #f0f0f0; align-items: flex-start; }
.news-item:last-child { border-bottom: none; }
.news-thumb { width: 72px; height: 52px; object-fit: cover; border-radius: 6px; flex-shrink: 0; }
.news-content { flex: 1; min-width: 0; }
.news-content a { font-size: 13px; color: #111; text-decoration: none; line-height: 1.4; display: block; margin-bottom: 4px; }
.news-content a:hover { text-decoration: underline; }
.tag { font-size: 9px; font-weight: 500; padding: 2px 7px; border-radius: 20px; white-space: nowrap; }
.tag-nhl { background: #dbeafe; color: #1e40af; }
.tag-mlb { background: #fee2e2; color: #991b1b; }
.tag-pl { background: #dcfce7; color: #166534; }
.tag-ucl { background: #ede9fe; color: #5b21b6; }
.tag-cycling { background: #fef9c3; color: #854d0e; }
.tag-f1 { background: #ffe4e6; color: #9f1239; }
.tag-cbc { background: #ede9fe; color: #5b21b6; }
.tag-globe { background: #f3f4f6; color: #374151; }
.tag-bbc { background: #fee2e2; color: #991b1b; }
.tag-guardian { background: #dcfce7; color: #166534; }
.story-item a { font-size: 13px; color: #111; text-decoration: none; line-height: 1.4; }
.story-item a:hover { text-decoration: underline; }
.story-meta { font-size: 10px; color: #999; margin-top: 2px; }
.empty { font-size: 13px; color: #999; padding: 8px 0; }
.fpl-widget { background: white; border: 0.5px solid #eee; border-radius: 10px; padding: 12px 14px; }
.fpl-header { margin-bottom: 12px; }
.fpl-gw { font-size: 14px; font-weight: 500; color: #111; }
.fpl-team-link { color: #111; text-decoration: none; }
.fpl-team-link:hover { text-decoration: underline; }
.fpl-deadline { font-size: 11px; color: #999; margin-top: 2px; }
.fpl-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 12px; }
.fpl-stat { background: #f5f5f5; border-radius: 8px; padding: 8px; text-align: center; }
.fpl-stat-up { background: #dcfce7; }
.fpl-stat-down { background: #fee2e2; }
.fpl-stat-label { font-size: 9px; color: #999; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px; }
.fpl-stat-value { font-size: 18px; font-weight: 500; color: #111; }
.fpl-stat-sub { font-size: 9px; color: #999; margin-top: 2px; }
.fpl-rank-up { color: #166534; font-size: 9px; font-weight: 500; }
.fpl-rank-down { color: #991b1b; font-size: 9px; font-weight: 500; }
.fpl-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.fpl-chip { font-size: 10px; font-weight: 500; padding: 3px 8px; border-radius: 20px; }
.fpl-chip-available { background: #dbeafe; color: #1e40af; }
.fpl-chip-used { background: #f3f4f6; color: #999; text-decoration: line-through; }
.fpl-squad { margin-bottom: 10px; }
.fpl-position-row { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 6px; }
.fpl-player { display: flex; align-items: center; gap: 4px; background: #f0f7ff; border-radius: 6px; padding: 4px 8px; font-size: 12px; }
.fpl-player-captain { background: #fef9c3; border: 1px solid #d97706; }
.fpl-player-vice { background: #f3f4f6; border: 1px solid #9ca3af; }
.fpl-player-name { color: #111; }
.fpl-pos-badge { font-size: 9px; color: #999; }
.fpl-club-badge { width: 16px; height: 16px; object-fit: contain; flex-shrink: 0; }
.fpl-pts-high { font-size: 10px; font-weight: 600; color: #166534; background: #dcfce7; border-radius: 4px; padding: 1px 5px; margin-left: 3px; }
.fpl-pts-mid { font-size: 10px; font-weight: 500; color: #555; background: #f3f4f6; border-radius: 4px; padding: 1px 5px; margin-left: 3px; }
.fpl-pts-low { font-size: 10px; font-weight: 500; color: #991b1b; background: #fee2e2; border-radius: 4px; padding: 1px 5px; margin-left: 3px; }
.fpl-captain { background: #d97706; color: white; border-radius: 50%; width: 14px; height: 14px; display: inline-flex; align-items: center; justify-content: center; font-size: 8px; font-weight: 600; flex-shrink: 0; }
.fpl-vice { background: #9ca3af; color: white; border-radius: 50%; width: 14px; height: 14px; display: inline-flex; align-items: center; justify-content: center; font-size: 8px; font-weight: 600; flex-shrink: 0; }
.fpl-bench { font-size: 11px; color: #999; margin-top: 6px; }
.fpl-auto-subs { font-size: 11px; color: #854d0e; background: #fef9c3; border-radius: 6px; padding: 4px 8px; margin-top: 6px; }
.fixture-toggle { display: flex; align-items: center; gap: 6px; padding: 8px 0; cursor: pointer; border: none; background: none; font-family: inherit; font-size: 12px; color: #999; width: 100%; text-align: left; }
.fixture-toggle:hover { color: #111; }
.fixture-toggle .toggle-arrow { transition: transform 0.2s; display: inline-block; }
.fixture-toggle.open .toggle-arrow { transform: rotate(0deg); }
.fixture-toggle:not(.open) .toggle-arrow { transform: rotate(-90deg); }
.fixture-calendar { display: none; margin-top: 4px; }
.fixture-calendar.open { display: block; }
.fixture-date-group { margin-bottom: 10px; }
.fixture-date-label { font-size: 10px; font-weight: 500; color: #999; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px; }
.fixture-row { display: flex; align-items: center; gap: 6px; padding: 5px 0; border-bottom: 0.5px solid #f0f0f0; font-size: 12px; }
.fixture-row:last-child { border-bottom: none; }
.fixture-logo { width: 18px; height: 18px; object-fit: contain; flex-shrink: 0; }
.fixture-teams { flex: 1; color: #111; display: flex; align-items: center; gap: 5px; flex-wrap: wrap; }
.fixture-time { font-size: 11px; color: #999; white-space: nowrap; }
.fixture-loading { font-size: 12px; color: #999; padding: 8px 0; }
.extended-forecast-toggle { display: flex; align-items: center; gap: 6px; padding: 8px 0 0; cursor: pointer; border: none; background: none; font-family: inherit; font-size: 12px; color: #999; width: 100%; text-align: left; }
.extended-forecast-toggle:hover { color: #111; }
.extended-forecast-toggle.open .toggle-arrow { transform: rotate(180deg); }
.extended-forecast { display: none; padding-top: 12px; border-top: 0.5px solid #eee; margin-top: 8px; }
.extended-forecast.open { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
.standings-legend { display: flex; flex-wrap: wrap; gap: 10px; padding: 6px 2px; margin-bottom: 4px; }
.legend-item { display: flex; align-items: center; gap: 5px; font-size: 10px; color: #666; }
.legend-swatch { display: inline-block; width: 12px; height: 12px; border-radius: 3px; flex-shrink: 0; }
/* UCL standings toggle */
.section-label-toggle { font-size: 10px; font-weight: 500; color: #999; text-transform: uppercase; letter-spacing: 0.08em; margin: 14px 0 8px; cursor: pointer; display: flex; align-items: center; gap: 5px; user-select: none; }
.section-label-toggle:hover { color: #555; }
.section-label-toggle .toggle-arrow { transition: transform 0.2s; display: inline-block; font-size: 10px; }
.section-label-toggle.open .toggle-arrow { transform: rotate(0deg); }
.section-label-toggle:not(.open) .toggle-arrow { transform: rotate(-90deg); }
.section-toggle-body { }
.section-toggle-body.hidden { display: none; }
/* F1 styles */
.f1-upcoming { background: white; border: 0.5px solid #eee; border-radius: 10px; padding: 12px 14px; margin-bottom: 8px; }
.f1-upcoming-header { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.f1-flag { font-size: 28px; }
.f1-race-name { font-size: 15px; font-weight: 500; color: #111; }
.f1-race-location { font-size: 12px; color: #999; margin-top: 2px; }
.f1-sessions { display: flex; flex-direction: column; gap: 4px; border-top: 0.5px solid #eee; padding-top: 10px; }
.f1-flag-sm { width: 16px; height: 12px; object-fit: cover; border-radius: 2px; vertical-align: middle; }
.f1-tbc { font-size: 10px; color: #999; }
.f1-session { font-size: 12px; color: #555; display: flex; gap: 8px; }
.f1-session-label { font-weight: 500; color: #111; min-width: 80px; }
.f1-standings-toggle { display: flex; gap: 8px; margin-bottom: 8px; }
.f1-toggle-btn { font-size: 12px; font-weight: 500; padding: 5px 14px; border-radius: 20px; border: 1px solid #ddd; background: white; color: #999; cursor: pointer; font-family: inherit; }
.f1-toggle-btn.f1-toggle-active { background: #111; color: white; border-color: #111; }
.f1-schedule-row { flex-direction: column; align-items: flex-start; gap: 4px; padding: 8px 10px; }
.f1-schedule-meta { display: flex; align-items: center; gap: 8px; width: 100%; font-size: 12px; }
.f1-loc { font-size: 11px; color: #999; flex: 1; }
.f1-completed-row { opacity: 0.7; }
.f1-podium { display: flex; flex-direction: column; gap: 2px; padding-left: 2px; }
.f1-podium-rider { font-size: 11px; color: #555; display: flex; align-items: center; gap: 4px; }
.f1-team-logo { width: 14px; height: 14px; object-fit: contain; }
/* Cycling results */
.cycling-result-row { flex-direction: column; align-items: flex-start; gap: 4px; padding: 8px 10px; }
.cycling-result-meta { display: flex; align-items: center; gap: 8px; width: 100%; }
.cycling-podium { display: flex; flex-direction: column; gap: 2px; padding-left: 2px; }
.cycling-podium-rider { font-size: 11px; color: #555; }

@media (prefers-color-scheme: dark) {
  body { background: #111; color: #eee; }
  .header { background: #1c1c1e; border-bottom-color: #2c2c2e; }
  .header h1 { color: #fff; }
  .header .date { color: #888; }
  .nav { background: #1c1c1e; border-bottom-color: #2c2c2e; }
  .nav a { color: #888; }
  .nav a.active { color: #fff; border-bottom-color: #fff; }
  .weather-widget { background: #1c1c1e; border-color: #2c2c2e; }
  .weather-desc { color: #eee; }
  .weather-temp { color: #eee; }
  .weather-forecast { border-top-color: #2c2c2e; }
  .forecast-name { color: #aaa; }
  .forecast-temps { color: #eee; }
  .score-card { background: #1c1c1e; border-color: #2c2c2e; }
  .score-card-link { color: #eee; }
  .standings { background: #1c1c1e; border-color: #2c2c2e; }
  .standing-header { border-bottom-color: #2c2c2e; }
  .standing-row { border-bottom-color: #2c2c2e; color: #eee; }
  .live-row { background: #2a1f0e; }
  .division-label { color: #aaa; }
  .section-label { color: #888; }
  .section-label-toggle { color: #888; }
  .sport-divider { border-top-color: #2c2c2e; }
  .news-divider { border-top-color: #2c2c2e; }
  .story-item { border-bottom-color: #2c2c2e; }
  .story-item a { color: #eee; }
  .news-item { border-bottom-color: #2c2c2e; }
  .news-content a { color: #eee; }
  .scores-section-label { color: #888; }
  .scores-section-toggle { color: #888; }
  .score-status { color: #888; }
  .stat-col { color: #aaa; }
  .athletic-link span { color: #888; }
  .athletic-badge { background: #eee; color: #111; }
  .tag-globe { background: #2c2c2e; color: #aaa; }
  .empty { color: #888; }
  .fpl-widget { background: #1c1c1e; border-color: #2c2c2e; }
  .fpl-gw { color: #eee; }
  .fpl-team-link { color: #eee; }
  .fpl-stat { background: #2c2c2e; }
  .fpl-stat-up { background: #14532d; }
  .fpl-stat-down { background: #450a0a; }
  .fpl-stat-value { color: #eee; }
  .fpl-player { background: #1a2a3a; }
  .fpl-player-captain { background: #2d1f00; border-color: #d97706; }
  .fpl-player-vice { background: #2c2c2e; border-color: #555; }
  .fpl-player-name { color: #eee; }
  .fpl-captain { background: #d97706; }
  .fpl-vice { background: #6b7280; }
  .fpl-bench { color: #888; }
  .fpl-chip-available { background: #1e3a5f; color: #93c5fd; }
  .fpl-chip-used { background: #2c2c2e; color: #666; }
  .race-link { color: #eee; }
  .fixture-toggle { color: #888; }
  .fixture-toggle:hover { color: #eee; }
  .fixture-teams { color: #eee; }
  .fixture-row { border-bottom-color: #2c2c2e; }
  .fixture-date-label { color: #888; }
  .extended-forecast-toggle { color: #888; }
  .extended-forecast { border-top-color: #2c2c2e; }
  .standings-legend { }
  .legend-item { color: #aaa; }
  .standing-row[style*='background: #dbeafe'] { background: #1e3a5f !important; }
  .standing-row[style*='background: #eff6ff'] { background: #162a40 !important; }
  .standing-row[style*='background: #f0fdf4'] { background: #14301e !important; }
  .standing-row[style*='background: #fee2e2'] { background: #3b0f0f !important; }
  .legend-swatch[style*='background:#dbeafe'] { background: #1e3a5f !important; }
  .legend-swatch[style*='background:#eff6ff'] { background: #162a40 !important; }
  .legend-swatch[style*='background:#f0fdf4'] { background: #14301e !important; }
  .legend-swatch[style*='background:#fee2e2'] { background: #3b0f0f !important; }
  .f1-upcoming { background: #1c1c1e; border-color: #2c2c2e; }
  .f1-race-name { color: #eee; }
  .f1-session { color: #aaa; }
  .f1-session-label { color: #eee; }
  .f1-sessions { border-top-color: #2c2c2e; }
  .f1-toggle-btn { background: #2c2c2e; border-color: #444; color: #aaa; }
  .f1-toggle-btn.f1-toggle-active { background: #eee; color: #111; border-color: #eee; }
  .f1-podium-rider { color: #aaa; }
  .f1-loc { color: #666; }
  .cycling-podium-rider { color: #aaa; }
}
"""

HEAD = """<meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<meta name='mobile-web-app-capable' content='yes'>
<meta name='apple-mobile-web-app-capable' content='yes'>
<meta name='apple-mobile-web-app-status-bar-style' content='default'>
<link rel='manifest' href='/manifest.json'>
<link rel='icon' href='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📰</text></svg>'>
<link href='https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500&display=swap' rel='stylesheet'>
<title>Tyler's Briefing</title>"""

NAV_NEWS = "<div class='nav'><a href='/' class='active'>News</a><a href='/sports'>Sports</a><a href='/media'>Media</a></div>"
NAV_SPORTS = "<div class='nav'><a href='/'>News</a><a href='/sports' class='active'>Sports</a><a href='/media'>Media</a></div>"
NAV_MEDIA = "<div class='nav'><a href='/'>News</a><a href='/sports'>Sports</a><a href='/media' class='active'>Media</a></div>"

CLOCK_AND_WEATHER_JS = """
<script>
function updateClock() {
    const now = new Date();
    const options = { weekday: 'long', month: 'long', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true };
    const timeStr = now.toLocaleString('en-CA', options).replace(',', ' \u00b7');
    document.querySelectorAll('.date').forEach(el => el.textContent = timeStr);
}
updateClock();

if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(function(position) {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        fetch('/weather?lat=' + lat + '&lon=' + lon)
            .then(r => r.json())
            .then(data => {
                if (data.error) return;
                document.querySelector('.weather-temp').textContent = data.current_temp + '\u00b0C';
                document.querySelector('.weather-icon').textContent = data.current_icon;
                document.querySelector('.weather-desc').innerHTML = data.current_desc + ' \u00b7 <span id="weather-city">' + data.city + '</span>';
                document.querySelector('.weather-meta').textContent = 'Feels like ' + data.feels_like + '\u00b0C \u00b7 High ' + data.today_high + '\u00b0 Low ' + data.today_low + '\u00b0 \u00b7 ' + data.today_precip + '% precip';
                const forecastEl = document.getElementById('weather-forecast');
                if (forecastEl && data.days) {
                    forecastEl.innerHTML = data.days.slice(0, 3).map(day =>
                        '<div class="forecast-day">' +
                        '<div class="forecast-name">' + day.name + '</div>' +
                        '<div class="forecast-date">' + day.date + '</div>' +
                        '<div class="forecast-icon">' + day.icon + '</div>' +
                        '<div class="forecast-desc">' + day.desc + '</div>' +
                        '<div class="forecast-temps">' + day.high + '\u00b0 / ' + day.low + '\u00b0</div>' +
                        '<div class="forecast-precip">' + day.precip + '% precip</div>' +
                        '</div>'
                    ).join('');
                }
            });
    }, function() {});
}

function toggleExtendedForecast() {
    const btn = document.getElementById('extended-forecast-btn');
    const forecast = document.getElementById('extended-forecast');
    const isOpen = forecast.classList.contains('open');
    if (isOpen) {
        forecast.classList.remove('open');
        btn.classList.remove('open');
    } else {
        forecast.classList.add('open');
        btn.classList.add('open');
    }
}

function toggleFixtures() {
    const btn = document.getElementById('fixture-toggle-btn');
    const cal = document.getElementById('fixture-calendar');
    const isOpen = cal.classList.contains('open');
    if (isOpen) {
        cal.classList.remove('open');
        btn.classList.remove('open');
        return;
    }
    btn.classList.add('open');
    cal.classList.add('open');
    if (cal.dataset.loaded) return;
    cal.dataset.loaded = 'true';
    cal.innerHTML = '<div class="fixture-loading">Loading fixtures...</div>';
    fetch('/fixtures')
        .then(r => r.json())
        .then(data => {
            if (!data.dates || data.dates.length === 0) {
                cal.innerHTML = '<p class="empty">No upcoming fixtures found</p>';
                return;
            }
            let html = '';
            data.dates.forEach(group => {
                html += '<div class="fixture-date-group"><div class="fixture-date-label">' + group.label + '</div>';
                group.games.forEach(game => {
                    const myLogo = game.my_logo ? '<img src="' + game.my_logo + '" class="fixture-logo" alt="">' : '';
                    const oppLogo = game.opp_logo ? '<img src="' + game.opp_logo + '" class="fixture-logo" alt="">' : '';
                    html += '<div class="fixture-row">' +
                        '<span class="fixture-teams">' + myLogo + ' ' + game.my_name + ' ' + game.versus + ' ' + oppLogo + ' ' + game.opp_name + '</span>' +
                        '<span class="fixture-time">' + game.time + '</span>' +
                        '</div>';
                });
                html += '</div>';
            });
            cal.innerHTML = html;
        })
        .catch(() => {
            cal.innerHTML = '<p class="empty">Fixtures unavailable</p>';
        });
}

function toggleScores(btnId, bodyId) {
    const btn = document.getElementById(btnId);
    const body = document.getElementById(bodyId);
    if (!btn || !body) return;
    const isOpen = body.classList.contains('open');
    if (isOpen) {
        body.classList.remove('open');
        btn.classList.remove('open');
    } else {
        body.classList.add('open');
        btn.classList.add('open');
    }
}

function toggleSection(btnId, bodyId) {
    const btn = document.getElementById(btnId);
    const body = document.getElementById(bodyId);
    if (!btn || !body) return;
    const isOpen = body.classList.contains('open');
    if (isOpen) {
        body.classList.remove('open');
        btn.classList.remove('open');
    } else {
        body.classList.add('open');
        btn.classList.add('open');
    }
}

function toggleSectionLabel(btnId, bodyId) {
    const btn = document.getElementById(btnId);
    const body = document.getElementById(bodyId);
    if (!btn || !body) return;
    const isOpen = btn.classList.contains('open');
    if (isOpen) {
        body.classList.add('hidden');
        btn.classList.remove('open');
    } else {
        body.classList.remove('hidden');
        btn.classList.add('open');
    }
}

function switchF1Standings(type) {
    const conBtn = document.getElementById('f1-btn-constructors');
    const drvBtn = document.getElementById('f1-btn-drivers');
    const conTable = document.getElementById('f1-constructors-table');
    const drvTable = document.getElementById('f1-drivers-table-wrap');
    if (type === 'constructors') {
        conBtn.classList.add('f1-toggle-active');
        drvBtn.classList.remove('f1-toggle-active');
        conTable.style.display = '';
        drvTable.style.display = 'none';
    } else {
        drvBtn.classList.add('f1-toggle-active');
        conBtn.classList.remove('f1-toggle-active');
        drvTable.style.display = '';
        conTable.style.display = 'none';
    }
}
</script>
"""


@app.route("/fixtures")
def fixtures():
    try:
        eastern = pytz.timezone("America/Toronto")
        today = datetime.now(eastern).date()
        start = today + timedelta(days=1)
        end = today + timedelta(days=10)

        all_keywords = []
        for team in MY_TEAMS:
            all_keywords.extend(team["keywords"])

        tasks = {}
        for sport, league in FIXTURE_LEAGUES:
            tasks[league] = (get_scores_range, (sport, league, start, end))

        results = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fn, *args): key for key, (fn, args) in tasks.items()}
            for future in as_completed(futures):
                key = futures[future]
                try:
                    games, league = future.result()
                    results[league] = games
                except:
                    results[key] = []

        by_date = {}
        for league, games in results.items():
            for game in games:
                try:
                    competition = game["competitions"][0]
                    competitors = competition["competitors"]
                    home_team = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
                    away_team = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

                    home_name = home_team["team"].get("displayName", "") or f"{home_team['team'].get('location', '')} {home_team['team'].get('name', '')}".strip()
                    away_name = away_team["team"].get("displayName", "") or f"{away_team['team'].get('location', '')} {away_team['team'].get('name', '')}".strip()
                    home_full = f"{home_team['team'].get('location', '')} {home_team['team'].get('name', '')}".strip()
                    away_full = f"{away_team['team'].get('location', '')} {away_team['team'].get('name', '')}".strip()
                    home_logo = home_team["team"].get("logo", "")
                    away_logo = away_team["team"].get("logo", "")

                    is_my_team = False
                    for kw in all_keywords:
                        if kw.lower() in home_full.lower() or kw.lower() in away_full.lower():
                            is_my_team = True
                            break
                    if not is_my_team:
                        continue

                    my_team_is_home = any(kw.lower() in home_full.lower() for team in MY_TEAMS for kw in team["keywords"])

                    if my_team_is_home:
                        my_name = home_name
                        my_logo = home_logo
                        opp_name = away_name
                        opp_logo = away_logo
                        versus = "vs"
                    else:
                        my_name = away_name
                        my_logo = away_logo
                        opp_name = home_name
                        opp_logo = home_logo
                        versus = "@"

                    date_str = game["date"]
                    dt_utc = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    dt_eastern = dt_utc.astimezone(eastern)
                    date_key = dt_eastern.date().isoformat()
                    time_str = dt_eastern.strftime("%I:%M %p").lstrip("0")

                    if date_key not in by_date:
                        by_date[date_key] = []
                    by_date[date_key].append({
                        "my_name": my_name,
                        "my_logo": my_logo,
                        "opp_name": opp_name,
                        "opp_logo": opp_logo,
                        "versus": versus,
                        "time": time_str,
                        "sort_time": dt_eastern.strftime("%H:%M"),
                    })
                except:
                    continue

        output = []
        for d in sorted(by_date.keys()):
            dt = date.fromisoformat(d)
            days_away = (dt - today).days
            if days_away == 1:
                label = f"Tomorrow · {dt.strftime('%a %b %d')}"
            else:
                label = dt.strftime("%a %b %d")
            sorted_games = sorted(by_date[d], key=lambda g: g.get("sort_time", "99:99"))
            output.append({"label": label, "games": sorted_games})

        return jsonify({"dates": output})
    except Exception as e:
        return jsonify({"dates": [], "error": str(e)})


@app.route("/weather")
def weather_api():
    try:
        lat = float(request.args.get("lat", 43.70))
        lon = float(request.args.get("lon", -79.42))
        w = get_weather(lat, lon)
        city = get_city_name(lat, lon)
        if not w:
            return jsonify({"error": "unavailable"})
        return jsonify({**w, "city": city})
    except:
        return jsonify({"error": "unavailable"})


@app.route("/")
def news():
    eastern = pytz.timezone("America/Toronto")
    now = datetime.now(eastern).strftime("%A, %B %d · %I:%M %p")
    data = fetch_all_news()
    weather = data.get("weather")
    local_html = render_news_section([("CBC Toronto", "tag-cbc", data.get("cbc_toronto", []))])
    national_html = render_news_section([
        ("CBC", "tag-cbc", data.get("cbc_canada", [])),
        ("Globe & Mail", "tag-globe", data.get("globe_canada", [])),
    ])
    global_html = render_news_section([
        ("BBC", "tag-bbc", data.get("bbc_world", [])),
        ("Guardian", "tag-guardian", data.get("guardian_world", [])),
        ("Globe & Mail", "tag-globe", data.get("globe_world", [])),
    ])
    return f"""<!DOCTYPE html>
<html><head>{HEAD}<style>{CSS}</style></head>
<body>
<div class='header'><h1>Tyler's Briefing</h1><div class='date'>{now}</div></div>
{NAV_NEWS}
<div class='body'>
<div class='section-label'>Weather</div>
{render_weather(weather)}
<hr class='news-divider'>
<div class='section-label'>Local · Toronto</div>
{local_html}
<hr class='news-divider'>
<div class='section-label'>National · Canada</div>
{national_html}
<hr class='news-divider'>
<div class='section-label'>Global</div>
{global_html}
</div>
{CLOCK_AND_WEATHER_JS}
</body></html>"""


@app.route("/sports")
def sports():
    eastern = pytz.timezone("America/Toronto")
    now = datetime.now(eastern)
    today = now.date()
    yesterday = today - timedelta(days=1)
    data = fetch_all_sports(today, yesterday)
    fpl = data.get("fpl")
    mlb_yesterday = data.get("mlb_yesterday", [])
    mlb_today = data.get("mlb_today", [])
    pl_yesterday = data.get("pl_yesterday", [])
    pl_today = data.get("pl_today", [])
    nhl_yesterday = data.get("nhl_yesterday", [])
    nhl_today = data.get("nhl_today", [])
    ucl_yesterday = data.get("ucl_yesterday", [])
    ucl_today = data.get("ucl_today", [])
    nba_yesterday = data.get("nba_yesterday", [])
    nba_today = data.get("nba_today", [])
    mls_yesterday = data.get("mls_yesterday", [])
    mls_today = data.get("mls_today", [])
    all_yesterday = mlb_yesterday + pl_yesterday + nhl_yesterday + ucl_yesterday + nba_yesterday + mls_yesterday
    all_today = mlb_today + pl_today + nhl_today + ucl_today + nba_today + mls_today
    teams_data = []
    for team in MY_TEAMS:
        yesterday_games = find_team_games(all_yesterday, team["keywords"])
        today_games = find_team_games(all_today, team["keywords"])
        teams_data.append({
            "name": team["name"],
            "yesterday_game": yesterday_games[0] if yesterday_games else None,
            "today_game": today_games[0] if today_games else None,
        })
    nhl_standings = data.get("nhl_standings", {})
    mlb_standings = data.get("mlb_standings", {})
    pl_standings = data.get("pl_standings", {})
    ucl_standings = data.get("ucl_standings", {})
    mlb_stories = data.get("mlb_stories", [])
    pl_stories = data.get("pl_stories", [])
    ucl_stories = data.get("ucl_stories", [])
    nhl_stories = data.get("nhl_stories", [])
    cycling_stories = data.get("cycling_stories", [])
    cycling_calendar = get_cycling_calendar()
    cycling_podiums = data.get("cycling_podiums", {})
    f1_data = data.get("f1_data", {"upcoming": None, "constructors": [], "drivers": []})
    f1_results = data.get("f1_results", [])

    f1_upcoming_widget, f1_schedule_toggle, f1_standings_html = render_f1_section(f1_data, f1_results)
    cycling_results_html = render_cycling_results(cycling_calendar, cycling_podiums)

    now_str = now.strftime("%A, %B %d · %I:%M %p")
    return f"""<!DOCTYPE html>
<html><head>{HEAD}<style>{CSS}</style></head>
<body>
<div class='header'><h1>Tyler's Briefing</h1><div class='date'>{now_str}</div></div>
{NAV_SPORTS}
<div class='body'>
<div class='section-label'>My Teams</div>
{render_my_teams(teams_data)}
<button class='fixture-toggle' id='fixture-toggle-btn' onclick='toggleFixtures()'>
    <span class='toggle-arrow'>▾</span> Upcoming Fixtures
</button>
<div class='fixture-calendar' id='fixture-calendar'></div>
<hr class='sport-divider'>
<div class='section-label'>MLB · Scores</div>
{render_scores_collapsible(mlb_yesterday, mlb_today, 'mlb')}
<div class='section-label'>MLB · Standings</div>
{render_mlb_standings(mlb_standings)}
<div class='section-label'>MLB · Headlines</div>
{render_stories(mlb_stories, 'MLB', 'tag-mlb')}
{athletic_link('https://theathletic.com/mlb/', 'MLB')}
<hr class='sport-divider'>
<div class='section-label'>Premier League · Scores</div>
{render_scores(pl_yesterday, pl_today)}
<div class='section-label'>Premier League · Standings</div>
{render_pl_standings(pl_standings)}
<div class='section-label'>Premier League · Headlines</div>
{render_stories(pl_stories, 'PL', 'tag-pl')}
{athletic_link('https://www.nytimes.com/athletic/football/premier-league/', 'Premier League')}
<div class='section-label'>FPL · {fpl['gw_name'] if fpl else 'Fantasy Premier League'}</div>
{render_fpl(fpl)}
<hr class='sport-divider'>
<div class='section-label'>Champions League · Scores</div>
{render_scores(ucl_yesterday, ucl_today)}
<div id='ucl-standings-label' class='section-label-toggle' onclick='toggleSectionLabel("ucl-standings-label","ucl-standings-body")'>
    <span class='toggle-arrow'>▾</span> Champions League · League Phase Standings
</div>
<div id='ucl-standings-body' class='section-toggle-body hidden'>
{render_ucl_standings(ucl_standings)}
</div>
<div class='section-label'>Champions League · Headlines</div>
{render_stories(ucl_stories, 'UCL', 'tag-ucl')}
{athletic_link('https://www.nytimes.com/athletic/football/champions-league/', 'Champions League')}
<hr class='sport-divider'>
<div class='section-label'>NHL · Scores</div>
{render_scores_collapsible(nhl_yesterday, nhl_today, 'nhl')}
<div class='section-label'>NHL · Standings</div>
{render_nhl_standings(nhl_standings)}
<div class='section-label'>NHL · Headlines</div>
{render_stories(nhl_stories, 'NHL', 'tag-nhl')}
{athletic_link('https://theathletic.com/nhl/', 'NHL')}
<hr class='sport-divider'>
<div class='section-label'>Formula 1 · Upcoming Race</div>
{f1_upcoming_widget}
{f1_schedule_toggle}
<div class='section-label'>Formula 1 · Championship Standings</div>
{f1_standings_html}
{athletic_link('https://theathletic.com/formula-1/', 'Formula 1')}
<hr class='sport-divider'>
{cycling_results_html}
<div class='section-label'>Cycling · Upcoming Races</div>
{render_cycling_calendar(cycling_calendar)}
<div class='section-label'>Cycling · Headlines</div>
{render_stories(cycling_stories, 'Cycling', 'tag-cycling')}
{athletic_link('https://theathletic.com/cycling/', 'Cycling')}
</div>
{CLOCK_AND_WEATHER_JS}
</body></html>"""


@app.route("/media")
def media():
    eastern = pytz.timezone("America/Toronto")
    now = datetime.now(eastern).strftime("%A, %B %d · %I:%M %p")
    data = fetch_all_media()
    channels_data = []
    for channel_name, _ in YOUTUBE_CHANNELS:
        videos = data["videos"].get(channel_name, [])
        channels_data.append((channel_name, videos))
    for playlist_name, _ in YOUTUBE_PLAYLISTS:
        videos = data["videos"].get(playlist_name, [])
        channels_data.append((playlist_name, videos))
    podcasts_data = []
    for podcast_name, feed_url, spotify_url in PODCAST_FEEDS:
        episodes, _ = data["podcasts"].get(podcast_name, ([], ""))
        artwork = ""
        if episodes and episodes[0].get("thumbnail"):
            artwork = episodes[0]["thumbnail"]
        if not artwork:
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                feed = feedparser.parse(feed_url, request_headers=headers)
                if feed.feed.get("image"):
                    artwork = feed.feed.image.get("href", "")
            except:
                pass
        podcasts_data.append((podcast_name, episodes, artwork, spotify_url))
    return f"""<!DOCTYPE html>
<html><head>{HEAD}<style>{CSS}</style></head>
<body>
<div class='header'><h1>Tyler's Briefing</h1><div class='date'>{now}</div></div>
{NAV_MEDIA}
<div class='body'>
<div class='section-label'>Videos</div>
{render_videos(channels_data)}
<hr class='news-divider'>
<div class='section-label'>Podcasts</div>
{render_podcasts(podcasts_data)}
</div>
{CLOCK_AND_WEATHER_JS}
</body></html>"""


@app.route("/manifest.json")
def manifest():
    return jsonify({
        "name": "Tyler's Briefing",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#111",
        "theme_color": "#1c1c1e"
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

@app.route("/debug-f1-results")
def debug_f1_results():
    import json
    results = get_f1_race_results()
    return f"<pre>{json.dumps([{**r, 'date': str(r['date'])} for r in results], indent=2)}</pre>"

@app.route("/debug-f1-results2")
def debug_f1_results2():
    import json
    url = "https://site.api.espn.com/apis/site/v2/sports/racing/f1/scoreboard"
    response = requests.get(url, timeout=8)
    data = response.json()
    events = data.get("events", [])
    out = []
    for event in events:
        comp = event["competitions"][0]
        out.append({
            "name": event.get("name", ""),
            "state": comp.get("status", {}).get("type", {}).get("state", ""),
            "competitors": len(comp.get("competitors", [])),
        })
    return f"<pre>{json.dumps(out, indent=2)}</pre>"

@app.route("/debug-f1-results3")
def debug_f1_results3():
    import json
    # Try fetching completed races with a date range
    url = "https://site.api.espn.com/apis/site/v2/sports/racing/f1/scoreboard?dates=20260101-20260325"
    response = requests.get(url, timeout=8)
    data = response.json()
    events = data.get("events", [])
    out = []
    for event in events:
        comp = event["competitions"][0]
        out.append({
            "name": event.get("name", ""),
            "state": comp.get("status", {}).get("type", {}).get("state", ""),
            "competitors": len(comp.get("competitors", [])),
        })
    return f"<pre>{json.dumps(out, indent=2)}</pre>"

@app.route("/debug-f1-results4")
def debug_f1_results4():
    import json
    url = "https://site.api.espn.com/apis/site/v2/sports/racing/f1/scoreboard?dates=20260101-20261231"
    response = requests.get(url, timeout=8)
    data = response.json()
    events = data.get("events", [])
    if not events:
        return "No events"
    # Just look at the first completed event's competitors
    for event in events:
        comp = event["competitions"][0]
        if comp.get("status", {}).get("type", {}).get("state", "") == "post":
            return f"<pre>{json.dumps(comp.get('competitors', [])[:3], indent=2)}</pre>"
    return "No completed events found"

@app.route("/debug-sports")
def debug_sports():
    import traceback
    try:
        eastern = pytz.timezone("America/Toronto")
        today = datetime.now(eastern).date()
        yesterday = today - timedelta(days=1)
        data = fetch_all_sports(today, yesterday)
        f1_data = data.get("f1_data", {"upcoming": None, "constructors": [], "drivers": []})
        f1_results = data.get("f1_results", [])
        f1_upcoming_widget, f1_schedule_toggle, f1_standings_html = render_f1_section(f1_data, f1_results)
        return f"<pre>OK</pre>"
    except Exception as e:
        return f"<pre>{traceback.format_exc()}</pre>"

@app.route("/debug-f1-results5")
def debug_f1_results5():
    import json
    url = "https://site.api.espn.com/apis/site/v2/sports/racing/f1/results?dates=20260101-20261231"
    response = requests.get(url, timeout=8)
    return f"<pre>{json.dumps(response.json(), indent=2)[:3000]}</pre>"

@app.route("/debug-f1-results6")
def debug_f1_results6():
    import json
    # Try fetching a specific event
    url = "https://site.api.espn.com/apis/site/v2/sports/racing/f1/summary?event=600057427"
    response = requests.get(url, timeout=8)
    return f"<pre>{json.dumps(response.json(), indent=2)[:3000]}</pre>"

@app.route("/debug-f1-results7")
def debug_f1_results7():
    import json
    url = "https://site.api.espn.com/apis/site/v2/sports/racing/f1/scoreboard?dates=20260301-20260310"
    response = requests.get(url, timeout=8)
    data = response.json()
    events = data.get("events", [])
    if not events:
        return "No events"
    comp = events[0]["competitions"][0]
    # Show all competitions for the event (each session)
    return f"<pre>{json.dumps(events[0].get('competitions', []), indent=2)[:5000]}</pre>"

@app.route("/debug-f1-results8")
def debug_f1_results8():
    import json
    url = "https://site.api.espn.com/apis/site/v2/sports/racing/f1/scoreboard?dates=20260301-20260310"
    response = requests.get(url, timeout=8)
    data = response.json()
    events = data.get("events", [])
    if not events:
        return "No events"
    for comp in events[0].get("competitions", []):
        if comp.get("type", {}).get("abbreviation", "") == "Race":
            return f"<pre>{json.dumps(comp.get('competitors', [])[:5], indent=2)}</pre>"
    return "No Race session found"

@app.route("/debug-f1-results9")
def debug_f1_results9():
    import json
    url = "https://site.api.espn.com/apis/site/v2/sports/racing/f1/scoreboard?dates=20260101-20261231"
    response = requests.get(url, timeout=8)
    data = response.json()
    events = data.get("events", [])
    out = []
    for event in events:
        comps = event.get("competitions", [])
        race_comp = None
        for c in comps:
            if c.get("type", {}).get("abbreviation", "") == "Race":
                race_comp = c
                break
        out.append({
            "name": event.get("name", ""),
            "num_competitions": len(comps),
            "comp_types": [c.get("type", {}).get("abbreviation", "") for c in comps],
            "race_found": race_comp is not None,
            "race_state": race_comp.get("status", {}).get("type", {}).get("state", "") if race_comp else None,
            "race_top3": [c["athlete"]["displayName"] for c in sorted(race_comp.get("competitors", []), key=lambda x: x.get("order", 99))[:3]] if race_comp else []
        })
    return f"<pre>{json.dumps(out, indent=2)}</pre>"

@app.route("/debug-f1-results10")
def debug_f1_results10():
    import json
    f1_results = get_f1_race_results()
    results_by_name = {}
    for r in f1_results:
        for cal_name, _, _, _, _, _ in F1_CALENDAR_2026:
            if cal_name.lower() in r["name"].lower():
                results_by_name[cal_name] = r
                break
    return f"<pre>{json.dumps({k: [p['name'] for p in v['podium']] for k, v in results_by_name.items()}, indent=2)}</pre>"

@app.route("/debug-f1-results11")
def debug_f1_results11():
    import json
    results = get_f1_race_results()
    return f"<pre>{json.dumps([{'name': r['name'], 'podium': r['podium']} for r in results], indent=2)}</pre>"
