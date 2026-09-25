import os
import time
import requests
import json
from datetime import datetime

API_KEY = os.getenv("API_FOOTBALL_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
HISTORY_FILE = "beting_history.json"


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []

    try:
        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except Exception as e:
        print(
            "HISTORY LOAD ERROR:",
            e
        )
        return []


def save_history(history):
    try:
        with open(
            HISTORY_FILE,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                history,
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:
        print(
            "HISTORY SAVE ERROR:",
            e
        )


history_data = load_history()

print(
    "HISTORY RECORDS:",
    len(history_data)
)
API_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}

CHECK_INTERVAL = 60

sent_alerts = set()

def save_match_snapshot(
    fixture_id,
    home_team,
    away_team,
    minute,
    home_goals,
    away_goals,
    total_shots,
    total_sot,
    total_corners,
    ou_line=None,
    ou_over=None,
    ou_under=None
):

    snapshot = {
        "timestamp": datetime.utcnow().isoformat(),
        "fixture_id": fixture_id,
        "home_team": home_team,
        "away_team": away_team,
        "minute": minute,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "total_goals": home_goals + away_goals,
        "total_shots": total_shots,
        "total_sot": total_sot,
        "total_corners": total_corners,
        "ou_line": ou_line,
        "ou_over": ou_over,
        "ou_under": ou_under
    }

    history_data.append(snapshot)

    save_history(history_data)

    print(
        "HISTORY SNAPSHOT SAVED:",
        fixture_id,
        "|",
        minute,
        "'",
        "|",
        home_goals,
        "-",
        away_goals,
        "| SHOTS:",
        total_shots,
        "| SOT:",
        total_sot,
        "| CORNERS:",
        total_corners
    )
def api_get(endpoint, params=None):

    try:

        response = requests.get(
            f"{API_URL}/{endpoint}",
            headers=HEADERS,
            params=params,
            timeout=20
        )

        print("API STATUS:", response.status_code)

        if response.status_code != 200:
            print("API ERROR:", response.text[:500])
            return []

        data = response.json()

        return data.get("response", [])

    except Exception as e:

        print("API REQUEST ERROR:", e)

        return []


def send_telegram(message):

    try:

        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": message
            },
            timeout=20
        )

        print("TELEGRAM:", response.status_code)

        if response.status_code != 200:
            print("TELEGRAM ERROR:", response.text[:500])

    except Exception as e:

        print("TELEGRAM ERROR:", e)


def get_live_matches():

    return api_get(
        "fixtures",
        {
            "live": "all"
        }
    )


def get_statistics(fixture_id):
    stats = api_get(
        "fixtures/statistics",
        {"fixture": fixture_id}
    )

    print(
        "STATISTICS RAW:",
        stats
    )

    if not stats:
        print(
            "SKIP - NO LIVE STATISTICS:",
            fixture_id
        )
        return None

    print(
        "LIVE STATISTICS AVAILABLE:",
        fixture_id
    )

    return stats
    odds = get_live_odds(
        fixture_id
    )

    if not odds:
        print(
            "SKIP - NO LIVE ODDS:",
            fixture_id
        )
        return stats
def get_events(fixture_id):
    events = api_get(
        "fixtures/events",
        {"fixture": fixture_id}
    )

    print(
        "EVENTS RAW:",
        events
    )

    return events

def get_live_odds(fixture_id):
    odds = api_get(
        "odds/live",
        {"fixture": fixture_id}
    )

    if not odds:
        print(
            "LIVE ODDS UNAVAILABLE:",
            fixture_id
        )
        return None

    print(
        "LIVE ODDS AVAILABLE:",
        fixture_id
    )

    return odds


def get_live_ou_market(odds):
    if not odds:
        return None

    try:
        markets = odds[0].get("odds", [])

        for market in markets:
            market_name = str(
                market.get("name", "")
            ).lower()

            if "over/under" not in market_name:
                continue

            values = market.get("values", [])

            result = []

            for item in values:
                value = item.get("value")
                odd = item.get("odd")

                if value is None or odd is None:
                    continue

                try:
                    odd = float(odd)
                except:
                    continue

                result.append({
                    "value": value,
                    "odd": odd
                })

            if result:
                print(
                    "LIVE O/U MARKET:",
                    result
                )

                return result

    except Exception as e:
        print(
            "O/U PARSE ERROR:",
            e
        )

    print(
        "LIVE O/U MARKET UNAVAILABLE"
    )

    return None
    

def get_stat_value(stats, team_name, stat_type):

    for team_data in stats:

        team = team_data.get(
            "team",
            {}
        ).get(
            "name"
        )

        if team != team_name:
            continue

        for item in team_data.get(
            "statistics",
            []
        ):

            if item.get("type") != stat_type:
                continue

            value = item.get("value")

            if value is None:
                return 0

            if isinstance(value, str):
                value = value.replace("%", "")

            try:
                return float(value)
            except:
                return 0

    return 0


def calculate_signal(
    minute,
    total_goals,
    total_shots,
    shots_on_target,
    corners
):

    score = 0

    if minute >= 75:
        score += 25
    elif minute >= 70:
        score += 20
    elif minute >= 65:
        score += 15
    elif minute >= 60:
        score += 10
    elif minute >= 45:
        score += 5

    if total_goals >= 3:
        score += 20
    elif total_goals == 2:
        score += 15
    elif total_goals == 1:
        score += 10

    if total_shots >= 25:
        score += 20
    elif total_shots >= 20:
        score += 15
    elif total_shots >= 15:
        score += 10
    elif total_shots >= 10:
        score += 5

    if shots_on_target >= 10:
        score += 20
    elif shots_on_target >= 8:
        score += 15
    elif shots_on_target >= 6:
        score += 10
    elif shots_on_target >= 4:
        score += 5

    if corners >= 10:
        score += 10
    elif corners >= 8:
        score += 8
    elif corners >= 6:
        score += 5

    if score > 100:
        score = 100

    return score


def analyze_match(match):

    fixture = match.get(
        "fixture",
        {}
    )

    teams = match.get(
        "teams",
        {}
    )

    goals = match.get(
        "goals",
        {}
    )

    fixture_id = fixture.get("id")

    home = teams.get(
        "home",
        {}
    ).get(
        "name",
        "Home"
    )

    away = teams.get(
        "away",
        {}
    ).get(
        "name",
        "Away"
    )

    home_goals = goals.get("home") or 0
    away_goals = goals.get("away") or 0

    minute = fixture.get(
        "status",
        {}
    ).get(
        "elapsed"
    ) or 0

    total_goals = home_goals + away_goals

    print(
        "ANALYZING:",
        home,
        "vs",
        away,
        f"{home_goals}-{away_goals}",
        f"minute={minute}"
    )

    if minute < 45:

        print(
            "SKIP EARLY MATCH:",
            fixture_id
        )

        return

    if fixture_id in sent_alerts:

        print(
            "ALREADY ALERTED:",
            fixture_id
        )

        return

    # ==============================
    # LIVE STATISTICS
    # ==============================

    stats = get_statistics(
        fixture_id
    )

    # ==============================
    # LIVE EVENTS
    # ==============================

    events = get_events(
        fixture_id
    )

    # ==============================
    # LIVE ODDS
    # ==============================

    odds = get_live_odds(
        fixture_id
    )

    # ==============================
    # DEFAULT STATISTICS
    # ==============================

    total_shots = 0
    shots_on_target = 0
    corners = 0

    if stats:

        home_shots = get_stat_value(
            stats,
            home,
            "Total Shots"
        )

        away_shots = get_stat_value(
            stats,
            away,
            "Total Shots"
        )

        total_shots = (
            home_shots +
            away_shots
        )

        home_sot = get_stat_value(
            stats,
            home,
            "Shots on Goal"
        )

        away_sot = get_stat_value(
            stats,
            away,
            "Shots on Goal"
        )

        shots_on_target = (
            home_sot +
            away_sot
        )

        home_corners = get_stat_value(
            stats,
            home,
            "Corner Kicks"
        )

        away_corners = get_stat_value(
            stats,
            away,
            "Corner Kicks"
        )

        corners = (
            home_corners +
            away_corners
        )

        print(
            "LIVE STATS PARSED:",
            "shots=",
            total_shots,
            "| SOT=",
            shots_on_target,
            "| corners=",
            corners
        )

    else:

        print(
            "NO LIVE STATISTICS - USING EVENTS:",
            fixture_id
        )

    # ==============================
    # LIVE O/U
    # ==============================

    ou_market = get_live_ou_market(
        odds
    )

    if ou_market:

        print(
            "LIVE O/U READY:",
            ou_market
        )

    else:

        print(
            "NO LIVE O/U:",
            fixture_id
        )

    # ==============================
    # SIGNAL
    # ==============================

signal = calculate_signal(
    minute=minute,
    total_goals=total_goals,
    total_shots=total_shots,
    shots_on_target=shots_on_target,
    corners=corners
)
    # ==============================
    # SAVE HISTORY SNAPSHOT
    # ==============================

    save_match_snapshot(
        fixture_id,
        home,
        away,
        minute,
        home_goals,
        away_goals,
        total_shots,
        shots_on_target,
        corners
    )

    print(
        "SIGNAL SCORE:",
        f"{signal}/100",
        "| shots=",
        total_shots,
        "| SOT=",
        shots_on_target,
        "| corners=",
        corners
    )

def main():

    print("")
    print("================================")
    print("BETING V3 STARTED")
    print("================================")
    print("MODE: LIVE FOOTBALL ANALYSIS")
    print("================================")

    if not API_KEY:

        print(
            "ERROR: API_FOOTBALL_KEY NOT FOUND"
        )

        return

    if not BOT_TOKEN:

        print(
            "ERROR: BOT_TOKEN NOT FOUND"
        )

        return

    if not CHAT_ID:

        print(
            "ERROR: TELEGRAM_CHAT_ID NOT FOUND"
        )

        return

    send_telegram(
        "BETING V3 DA KHOI DONG!\n\n"
        "Live football analysis\n"
        "Live statistics\n"
        "Keo rung signal engine\n"
        "Anti spam enabled"
    )

    while True:

        try:

            matches = get_live_matches()

            print(
                datetime.now().strftime("%H:%M:%S"),
                "| LIVE MATCHES:",
                len(matches)
            )

            for match in matches:

                try:

                    analyze_match(
                        match
                    )

                except Exception as e:

                    print(
                        "MATCH ERROR:",
                        e
                    )

        except Exception as e:

            print(
                "MAIN ERROR:",
                e
            )

        time.sleep(
            CHECK_INTERVAL
        )


if __name__ == "__main__":

    main()
