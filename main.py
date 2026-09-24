import os
import time
import requests


# ==================================================
# BETING
# Telegram Bot: @beting_live6886_bot
# API: API-FOOTBALL
# ==================================================

BOT_NAME = "BETING"
TELEGRAM_USERNAME = "@beting_live6886_bot"

API_KEY = os.getenv("API_FOOTBALL_KEY", "").strip()

BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY,
    "Accept": "application/json"
}


# ==================================================
# HIỂN THỊ HEADER
# ==================================================

def show_header():

    print("")
    print("==============================================")
    print("                 BETING")
    print("          @beting_live6886_bot")
    print("==============================================")
    print("       LIVE FOOTBALL ANALYSIS SYSTEM")
    print("==============================================")
    print("")


# ==================================================
# KIỂM TRA API KEY
# ==================================================

def check_api_key():

    print("[1] KIỂM TRA API_FOOTBALL_KEY")
    print("----------------------------------------------")

    if not API_KEY:

        print("❌ KHÔNG TÌM THẤY API_FOOTBALL_KEY")
        print("")
        print("Kiểm tra Railway:")
        print("Variables")
        print("→ API_FOOTBALL_KEY")
        print("")

        return False

    print("✅ RAILWAY ĐÃ NHẬN API_FOOTBALL_KEY")

    # Không bao giờ in API KEY thật ra log
    print("API KEY LENGTH:", len(API_KEY))

    print("")

    return True


# ==================================================
# KIỂM TRA API-FOOTBALL
# ==================================================

def check_api():

    print("[2] KIỂM TRA KẾT NỐI API-FOOTBALL")
    print("----------------------------------------------")

    try:

        response = requests.get(
            f"{BASE_URL}/status",
            headers=HEADERS,
            timeout=20
        )

        print("HTTP STATUS:", response.status_code)

        if response.status_code != 200:

            print("❌ API KHÔNG TRẢ VỀ 200")

            print("")
            print("API RESPONSE:")
            print(response.text)

            return False

        data = response.json()

        errors = data.get("errors", {})

        if errors:

            print("❌ API TRẢ VỀ ERROR:")

            print(errors)

            return False

        api_response = data.get("response", {})

        print("✅ KẾT NỐI API-FOOTBALL THÀNH CÔNG")

        print("")

        print("ACCOUNT:")
        print(api_response.get("account", {}))

        print("")

        print("SUBSCRIPTION:")
        print(api_response.get("subscription", {}))

        print("")

        print("REQUESTS:")
        print(api_response.get("requests", {}))

        print("")

        return True

    except requests.exceptions.Timeout:

        print("❌ API TIMEOUT")

        return False

    except requests.exceptions.ConnectionError:

        print("❌ KHÔNG KẾT NỐI ĐƯỢC API")

        return False

    except Exception as e:

        print("❌ LỖI:")
        print(str(e))

        return False


# ==================================================
# LẤY TRẬN ĐANG LIVE
# ==================================================

def get_live_matches():

    print("[3] LẤY DANH SÁCH TRẬN ĐANG LIVE")
    print("----------------------------------------------")

    try:

        response = requests.get(
            f"{BASE_URL}/fixtures",
            headers=HEADERS,
            params={
                "live": "all"
            },
            timeout=30
        )

        print("HTTP STATUS:", response.status_code)

        if response.status_code != 200:

            print("❌ KHÔNG LẤY ĐƯỢC TRẬN LIVE")

            print("")
            print(response.text)

            return []

        data = response.json()

        errors = data.get("errors", {})

        if errors:

            print("❌ API ERROR:")

            print(errors)

            return []

        matches = data.get("response", [])

        print("")
        print(f"✅ TÌM THẤY {len(matches)} TRẬN LIVE")
        print("")

        if len(matches) == 0:

            print("ℹ️ HIỆN TẠI KHÔNG CÓ TRẬN LIVE")
            print("")

            return []

        print("==============================================")
        print("              DANH SÁCH TRẬN LIVE")
        print("==============================================")

        for match in matches[:30]:

            fixture = match.get("fixture", {})

            teams = match.get("teams", {})

            goals = match.get("goals", {})

            league = match.get("league", {})

            status = fixture.get("status", {})

            # --------------------------------------
            # ĐỘI BÓNG
            # --------------------------------------

            home_data = teams.get("home", {})

            away_data = teams.get("away", {})

            home = home_data.get("name", "?")

            away = away_data.get("name", "?")

            # --------------------------------------
            # TỶ SỐ
            # --------------------------------------

            home_goals = goals.get("home")

            away_goals = goals.get("away")

            if home_goals is None:
                home_goals = 0

            if away_goals is None:
                away_goals = 0

            # --------------------------------------
            # THỜI GIAN
            # --------------------------------------

            elapsed = status.get("elapsed")

            status_short = status.get("short")

            # --------------------------------------
            # GIẢI ĐẤU
            # --------------------------------------

            league_name = league.get("name", "?")

            country = league.get("country", "?")

            # --------------------------------------
            # FIXTURE ID
            # --------------------------------------

            fixture_id = fixture.get("id")

            # --------------------------------------
            # IN RA
            # --------------------------------------

            print("----------------------------------------------")

            print(
                f"{home} {home_goals} - "
                f"{away_goals} {away}"
            )

            print(
                f"⏱ Phút: {elapsed}"
            )

            print(
                f"📌 Status: {status_short}"
            )

            print(
                f"🏆 Giải: {league_name}"
            )

            print(
                f"🌍 Quốc gia: {country}"
            )

            print(
                f"🆔 Fixture ID: {fixture_id}"
            )

        print("----------------------------------------------")
        print("")

        return matches

    except requests.exceptions.Timeout:

        print("❌ LẤY TRẬN LIVE BỊ TIMEOUT")

        return []

    except requests.exceptions.ConnectionError:

        print("❌ LỖI KẾT NỐI API")

        return []

    except Exception as e:

        print("❌ LỖI:")
        print(str(e))

        return []


# ==================================================
# MAIN
# ==================================================

def main():

    show_header()

    # ----------------------------------------------
    # BƯỚC 1
    # ----------------------------------------------

    if not check_api_key():

        print("")
        print("⛔ BETING CHƯA THỂ CHẠY")
        print("")

        return

    # ----------------------------------------------
    # BƯỚC 2
    # ----------------------------------------------

    if not check_api():

        print("")
        print("⛔ API-FOOTBALL CHƯA KẾT NỐI ĐƯỢC")
        print("")

        return

    # ----------------------------------------------
    # BƯỚC 3
    # ----------------------------------------------

    get_live_matches()

    # ----------------------------------------------
    # HOÀN TẤT
    # ----------------------------------------------

    print("")
    print("==============================================")
    print("       ✅ BETING ĐÃ KHỞI ĐỘNG THÀNH CÔNG")
    print("==============================================")
    print("")
    print("Telegram:", TELEGRAM_USERNAME)
    print("")


# ==================================================
# CHẠY CHƯƠNG TRÌNH
# ==================================================

if __name__ == "__main__":

    main()

    # Giữ Railway container hoạt động
    while True:

        time.sleep(3600)
