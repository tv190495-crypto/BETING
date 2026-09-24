import os
import time
import requests
from datetime import datetime

# ==============================
# CONFIG
# ==============================

API_KEY = os.getenv("API_FOOTBALL_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

API_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}

CHECK_INTERVAL = 60

# Chống gửi trùng:
# Mỗi trận chỉ gửi 1 cảnh báo trong một lần chạy bot
sent_alerts = set()
# ==============================
# LỊCH SỬ TÌNH HUỐNG
# ==============================

HISTORY_FILE = "history.json"


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []

    try:
        import json

        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        print("HISTORY LOAD ERROR:", e)
        return []


def save_history(history):

    try:
        import json

        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(
                history,
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:
        print("HISTORY SAVE ERROR:", e)


history_data = load_history()

print("HISTORY RECORDS:", len(history_data))

# ==============================
# API FOOTBALL
# ==============================

def api_get(endpoint, params=None):

    try:
        response = requests.get(
            f"{API_URL}/{endpoint}",
            headers=HEADERS,
            params=params or {},
            timeout=20
        )

        print("API STATUS:", response.status_code)

        data = response.json()

        if data.get("errors"):
            print("API ERROR:", data["errors"])
            return []

        return data.get("response", [])

    except Exception as e:
        print("API REQUEST ERROR:", e)
        return []


# ==============================
# TELEGRAM
# ==============================

def send_telegram(message):

    try:

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        response = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": message
            },
            timeout=15
        )

        print("TELEGRAM:", response.status_code)

    except Exception as e:
        print("TELEGRAM ERROR:", e)


# ==============================
# LIVE MATCHES
# ==============================

def get_live_matches():

    return api_get(
        "fixtures",
        {
            "live": "all"
        }
    )


# ==============================
# EVENTS
# ==============================

def get_events(fixture_id):

    return api_get(
        "fixtures/events",
        {
            "fixture": fixture_id
        }
    )


# ==============================
# STATISTICS
# ==============================

def get_statistics(fixture_id):

    return api_get(
        "fixtures/statistics",
        {
            "fixture": fixture_id
        }
    )


# ==============================
# READ STAT
# ==============================

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

                value = value.replace(
                    "%",
                    ""
                )

            try:
                return float(value)

            except:
                return 0

    return 0


# ==============================
# RECENT GOAL
# ==============================

def get_recent_goal(events, minute):

    goal_minutes = []

    for event in events:

        if event.get("type") != "Goal":
            continue

        elapsed = event.get(
            "time",
            {}
        ).get(
            "elapsed"
        )

        if elapsed is None:
            continue

        try:
            goal_minutes.append(
                int(elapsed)
            )

        except:
            pass

    if not goal_minutes:

        return False, None

    last_goal = max(
        goal_minutes
    )

    recent_goal = (
        minute - last_goal <= 15
    )

    return recent_goal, last_goal


# ==============================
# SIGNAL ENGINE
# ==============================

def calculate_signal(
    minute,
    total_goals,
    total_shots,
    shots_on_target,
    corners,
    recent_goal
):

    score = 0

    # --------------------------
    # MINUTE
    # --------------------------

    if 55 <= minute <= 85:

        score += 20

    elif 45 <= minute < 55:

        score += 10


    # --------------------------
    # TOTAL GOALS
    # --------------------------

    if total_goals >= 3:

        score += 20

    elif total_goals == 2:

        score += 15

    elif total_goals == 1:

        score += 10


    # --------------------------
    # TOTAL SHOTS
    # --------------------------

    if total_shots >= 25:

        score += 20

    elif total_shots >= 18:

        score += 15

    elif total_shots >= 12:

        score += 8


    # --------------------------
    # SHOTS ON TARGET
    # --------------------------

    if shots_on_target >= 10:

        score += 20

    elif shots_on_target >= 7:

        score += 15

    elif shots_on_target >= 5:

        score += 8


    # --------------------------
    # CORNERS
    # --------------------------

    if corners >= 10:

        score += 15

    elif corners >= 7:

        score += 10

    elif corners >= 5:

        score += 5


    # --------------------------
    # RECENT GOAL
    # --------------------------

    if recent_goal:

        score += 10


    return min(
        score,
        100
    )


# ==============================
# ANALYZE MATCH
# ==============================

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

    fixture_id = fixture.get(
        "id"
    )

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

    home_goals = goals.get(
        "home"
    ) or 0

    away_goals = goals.get(
        "away"
    ) or 0

    minute = fixture.get(
        "status",
        {}
    ).get(
        "elapsed"
    ) or 0

    total_goals = (
        home_goals +
        away_goals
    )

    print(
        "ANALYZING:",
        home,
        "vs",
        away,
        f"{home_goals}-{away_goals}",
        f"minute={minute}"
    )





    # --------------------------
    # STATISTICS
    # --------------------------

    stats = get_statistics(
        fixture_id
    )

    if not stats:

        print(
            "NO STATISTICS:",
            fixture_id
        )

        return


    # --------------------------
    # SHOTS
    # --------------------------

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


    # --------------------------
    # SHOTS ON TARGET
    # --------------------------

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


    # --------------------------
    # CORNERS
    # --------------------------

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


   # --------------------------
# RECENT GOAL
# Tạm thời chưa gọi Events để tiết kiệm API
# --------------------------

recent_goal = False
last_goal = None


    # --------------------------
    # CALCULATE SIGNAL
    # --------------------------

    signal = calculate_signal(
        minute=minute,
        total_goals=total_goals,
        total_shots=total_shots,
        shots_on_target=shots_on_target,
        corners=corners,
        recent_goal=recent_goal
    )


    print(
        "SIGNAL SCORE:",
        f"{signal}/100",
        "| shots=",
        total_shots,
        "| SOT=",
        shots_on_target,
        "| corners=",
        corners,
        "| last_goal=",
        last_goal
    )


    # --------------------------
    # ALERT THRESHOLD
    # --------------------------

    if signal < 75:

        return


    # --------------------------
    # ANTI SPAM
    # --------------------------

    if fixture_id in sent_alerts:

        return

    sent_alerts.add(
        fixture_id
    )


    # --------------------------
    # SIGNAL LEVEL
    # --------------------------

    if signal >= 85:

        level = "🔥🔥 RẤT CAO"

    else:

        level = "🔥 CAO"


    # --------------------------
    # LAST GOAL TEXT
    # --------------------------

    if last_goal:

        last_goal_text = (
            f"{last_goal}'"
        )

    else:

        last_goal_text = "Chưa có"


    # --------------------------
    # TELEGRAM MESSAGE
    # --------------------------

    message = (
        "🚨 BETING · GOAL SIGNAL\n\n"
        f"⚽ {home} vs {away}\n"
        f"⏱ Phút: {minute}'\n"
        f"🔢 Tỷ số: {home_goals}-{away_goals}\n\n"
        f"🔥 SIGNAL: {signal}/100\n"
        f"📊 Tổng sút: {int(total_shots)}\n"
        f"🎯 SOT: {int(shots_on_target)}\n"
        f"🚩 Góc: {int(corners)}\n"
        f"⚽ Bàn gần nhất: {last_goal_text}\n\n"
        f"{level}\n"
        "📌 Đánh giá: KHẢ NĂNG CÒN BÀN\n\n"
        "⚠️ Đây là tín hiệu thống kê, "
        "không đảm bảo kết quả."
    )

    send_telegram(
        message
    )


# ==============================
# MAIN
# ==============================

def main():

    print("")
    print("================================")
    print("      BETING V2 STARTED")
    print("================================")
    print("VERSION: 2.0")
    print("MODE: LIVE STATISTICS")
    print("================================")


    # --------------------------
    # CHECK ENV
    # --------------------------

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


    # --------------------------
    # START TELEGRAM
    # --------------------------

    send_telegram(
        "🟢 BETING V2 ĐÃ KHỞI ĐỘNG!\n\n"
        "⚽ Live football analysis\n"
        "📊 Statistics engine\n"
        "🔥 Goal signal engine\n"
        "🛡 Anti-spam enabled"
    )


    # --------------------------
    # LOOP
    # --------------------------

    while True:

        try:

            matches = get_live_matches()

            print(
                datetime.now().strftime(
                    "%H:%M:%S"
                ),
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


# ==============================
# START
# ==============================

if __name__ == "__main__":

    main()
