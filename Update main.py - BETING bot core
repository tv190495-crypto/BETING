import os
import time
import requests
from datetime import datetime

API_KEY = os.getenv("API_FOOTBALL_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

API_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}

CHECK_INTERVAL = 60

sent_alerts = set()


def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        r = requests.post(url, data=data, timeout=15)
        print("TELEGRAM:", r.status_code, r.text)
    except Exception as e:
        print("TELEGRAM ERROR:", e)


def get_live_matches():
    url = f"{API_URL}/fixtures"

    params = {
        "live": "all"
    }

    try:
        r = requests.get(
            url,
            headers=HEADERS,
            params=params,
            timeout=20
        )

        print("API STATUS:", r.status_code)

        data = r.json()

        if data.get("errors"):
            print("API ERROR:", data["errors"])
            return []

        return data.get("response", [])

    except Exception as e:
        print("API ERROR:", e)
        return []


def analyze_match(match):
    fixture = match["fixture"]
    teams = match["teams"]
    goals = match["goals"]

    fixture_id = fixture["id"]

    home = teams["home"]["name"]
    away = teams["away"]["name"]

    home_goals = goals["home"] or 0
    away_goals = goals["away"] or 0

    minute = fixture["status"].get("elapsed") or 0

    total_goals = home_goals + away_goals

    # Bộ lọc thử nghiệm đầu tiên
    signal = False

    if minute >= 55 and minute <= 85:
        if total_goals >= 1:
            signal = True

    if not signal:
        return

    alert_key = f"{fixture_id}_{minute}"

    if alert_key in sent_alerts:
        return

    sent_alerts.add(alert_key)

    message = (
        "🚨 BETING · LIVE SIGNAL\n\n"
        f"⚽ {home} vs {away}\n"
        f"⏱ Phút: {minute}'\n"
        f"🔢 Tỷ số: {home_goals}-{away_goals}\n"
        f"🔥 Tổng bàn: {total_goals}\n\n"
        "📊 Tín hiệu: CÓ THỂ CÒN BÀN\n"
        "⚠️ Đây là tín hiệu thống kê, không đảm bảo kết quả."
    )

    send_telegram(message)

    print(
        f"SIGNAL: {home} vs {away} "
        f"{home_goals}-{away_goals} "
        f"minute={minute}"
    )


def main():

    print("================================")
    print("      BETING BOT STARTED")
    print("================================")

    if not API_KEY:
        print("ERROR: API_FOOTBALL_KEY NOT FOUND")
        return

    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN NOT FOUND")
        return

    if not CHAT_ID:
        print("ERROR: TELEGRAM_CHAT_ID NOT FOUND")
        return

    send_telegram("🟢 BETING BOT đã khởi động!")

    while True:

        try:
            matches = get_live_matches()

            print(
                datetime.now().strftime("%H:%M:%S"),
                "| LIVE MATCHES:",
                len(matches)
            )

            for match in matches:
                analyze_match(match)

        except Exception as e:
            print("MAIN ERROR:", e)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
