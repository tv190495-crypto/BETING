import os
import requests
import time

API_KEY = os.getenv("API_FOOTBALL_KEY")

BASE_URL = "https://v3.football.api-sports.io"

headers = {
    "x-apisports-key": API_KEY
}


def test_api():
    print("===================================")
    print("BACHKHOA LIVE FOOTBALL BOT")
    print("TEST API-FOOTBALL")
    print("===================================")

if not API_KEY:
    print("❌ CHƯA CÓ API_FOOTBALL_KEY")
    print("API_FOOTBALL_KEY = NOT FOUND")
    return

print("✅ RAILWAY ĐÃ NHẬN API_FOOTBALL_KEY")
print("API KEY LENGTH:", len(API_KEY))

    # Kiểm tra tài khoản / quota
    print("\n[1] Kiểm tra API status...")

    response = requests.get(
        f"{BASE_URL}/status",
        headers=headers,
        timeout=20
    )

    print("HTTP STATUS:", response.status_code)

    if response.status_code != 200:
        print("❌ API ERROR")
        print(response.text)
        return

    data = response.json()

    print("✅ API KẾT NỐI THÀNH CÔNG")

    account = data.get("response", {}).get("account", {})
    subscription = data.get("response", {}).get("subscription", {})
    requests_info = data.get("response", {}).get("requests", {})

    print("Account:", account)
    print("Subscription:", subscription)
    print("Requests:", requests_info)

    # Lấy các trận đang diễn ra
    print("\n[2] Lấy danh sách trận LIVE...")

    response = requests.get(
        f"{BASE_URL}/fixtures",
        headers=headers,
        params={
            "live": "all"
        },
        timeout=20
    )

    print("HTTP STATUS:", response.status_code)

    if response.status_code != 200:
        print("❌ Không lấy được trận LIVE")
        print(response.text)
        return

    data = response.json()
    matches = data.get("response", [])

    print(f"✅ Tìm thấy {len(matches)} trận LIVE")

    print("\n===================================")
    print("DANH SÁCH TRẬN")
    print("===================================")

    for match in matches[:10]:

        fixture = match.get("fixture", {})
        teams = match.get("teams", {})
        goals = match.get("goals", {})
        league = match.get("league", {})

        home = teams.get("home", {}).get("name", "?")
        away = teams.get("away", {}).get("name", "?")

        home_goals = goals.get("home", 0)
        away_goals = goals.get("away", 0)

        elapsed = fixture.get("status", {}).get("elapsed")
        status = fixture.get("status", {}).get("short")

        print(
            f"{home} {home_goals}-{away_goals} {away}"
        )

        print(
            f"   Phút: {elapsed} | "
            f"Status: {status} | "
            f"League: {league.get('name')}"
        )

        print(
            f"   Fixture ID: {fixture.get('id')}"
        )

        print("-----------------------------------")


if __name__ == "__main__":
    test_api()

    # Giữ Railway container chạy
    while True:
        time.sleep(3600)
