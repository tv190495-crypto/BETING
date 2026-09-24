import os
import time
import requests
from datetime import datetime

# ============================================================

# BETING - LIVE FOOTBALL ANALYSIS BOT

# ============================================================

API_KEY = os.getenv("API_FOOTBALL_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

API_URL = "https://v3.football.api-sports.io"

HEADERS = {
"x-apisports-key": API_KEY
}

# Kiểm tra live mỗi 60 giây

CHECK_INTERVAL = 60

# Mỗi trận chỉ cảnh báo 1 lần

sent_alerts = set()

# ============================================================

# API REQUEST

# ============================================================

def api_get(endpoint, params=None):

```
try:

    url = f"{API_URL}/{endpoint}"

    response = requests.get(
        url,
        headers=HEADERS,
        params=params,
        timeout=20
    )

    print(
        "API STATUS:",
        response.status_code
    )

    if response.status_code != 200:
        print(
            "API ERROR:",
            response.text[:500]
        )
        return []

    data = response.json()

    return data.get(
        "response",
        []
    )

except Exception as e:

    print(
        "API REQUEST ERROR:",
        e
    )

    return []
```

# ============================================================

# TELEGRAM

# ============================================================

def send_telegram(message):

```
try:

    url = (
        f"https://api.telegram.org/bot"
        f"{BOT_TOKEN}/sendMessage"
    )

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=20
    )

    print(
        "TELEGRAM:",
        response.status_code
    )

    if response.status_code != 200:
        print(
            "TELEGRAM ERROR:",
            response.text[:500]
        )

except Exception as e:

    print(
        "TELEGRAM ERROR:",
        e
    )
```

# ============================================================

# LIVE MATCHES

# ============================================================

def get_live_matches():

```
return api_get(
    "fixtures",
    {
        "live": "all"
    }
)
```

# ============================================================

# STATISTICS

# ============================================================

def get_statistics(fixture_id):

```
return api_get(
    "fixtures/statistics",
    {
        "fixture": fixture_id
    }
)
```

# ============================================================

# GET STAT VALUE

# ============================================================

def get_stat_value(
stats,
team_name,
stat_type
):

```
for team_data in stats:

    team = (
        team_data
        .get("team", {})
        .get("name")
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

        if isinstance(
            value,
            str
        ):

            value = value.replace(
                "%",
                ""
            )

        try:

            return float(value)

        except:

            return 0

return 0
```

# ============================================================

# SIGNAL ENGINE

# ============================================================

def calculate_signal(
minute,
total_goals,
total_shots,
shots_on_target,
corners,
recent_goal
):

```
score = 0

# --------------------------------------------------------
# PHÚT THI ĐẤU
# --------------------------------------------------------

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

# --------------------------------------------------------
# TỔNG SỐ BÀN
# --------------------------------------------------------

if total_goals >= 3:
    score += 20

elif total_goals == 2:
    score += 15

elif total_goals == 1:
    score += 10

# --------------------------------------------------------
# TỔNG CÚ SÚT
# --------------------------------------------------------

if total_shots >= 25:
    score += 20

elif total_shots >= 20:
    score += 15

elif total_shots >= 15:
    score += 10

elif total_shots >= 10:
    score += 5

# --------------------------------------------------------
# SÚT TRÚNG ĐÍCH
# --------------------------------------------------------

if shots_on_target >= 10:
    score += 20

elif shots_on_target >= 8:
    score += 15

elif shots_on_target >= 6:
    score += 10

elif shots_on_target >= 4:
    score += 5

# --------------------------------------------------------
# PHẠT GÓC
# --------------------------------------------------------

if corners >= 10:
    score += 10

elif corners >= 8:
    score += 8

elif corners >= 6:
    score += 5

# --------------------------------------------------------
# BÀN GẦN ĐÂY
# --------------------------------------------------------

if recent_goal:
    score += 10

# --------------------------------------------------------
# GIỚI HẠN 100
# --------------------------------------------------------

if score > 100:
    score = 100

return score
```

# ============================================================

# ANALYZE MATCH

# ============================================================

def analyze_match(match):

```
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

home = (
    teams
    .get("home", {})
    .get("name", "Home")
)

away = (
    teams
    .get("away", {})
    .get("name", "Away")
)

home_goals = (
    goals.get("home") or 0
)

away_goals = (
    goals.get("away") or 0
)

minute = (
    fixture
    .get("status", {})
    .get("elapsed") or 0
)

total_goals = (
    home_goals +
    away_goals
)

print("")
print(
    "ANALYZING:",
    home,
    "vs",
    away,
    f"{home_goals}-{away_goals}",
    f"minute={minute}"
)

# ========================================================
# QUICK FILTER
# ========================================================

if minute < 45:

    print(
        "SKIP EARLY MATCH:",
        fixture_id
    )

    return

if total_goals < 1:

    print(
        "SKIP 0-0:",
        fixture_id
    )

    return

# ========================================================
# ANTI SPAM
# ========================================================

if fixture_id in sent_alerts:

    print(
        "ALREADY ALERTED:",
        fixture_id
    )

    return

# ========================================================
# GET STATISTICS
# ========================================================

stats = get_statistics(
    fixture_id
)

if not stats:

    print(
        "NO STATISTICS:",
        fixture_id
    )

    return

# ========================================================
# SHOTS
# ========================================================

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

# ========================================================
# SHOTS ON TARGET
# ========================================================

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

# ========================================================
# CORNERS
# ========================================================

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

# ========================================================
# RECENT GOAL
# ========================================================

# Chưa gọi Events ở phiên bản này
# để tiết kiệm API quota.

recent_goal = False

last_goal = None

# ========================================================
# CALCULATE SIGNAL
# ========================================================

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
    corners
)

# ========================================================
# ALERT CONDITION
# ========================================================

if signal < 70:

    print(
        "SIGNAL TOO LOW:",
        signal
    )

    return

# ========================================================
# MARK ALERT
# ========================================================

sent_alerts.add(
    fixture_id
)

# ========================================================
# SIGNAL LEVEL
# ========================================================

if signal >= 85:

    level = "🔥🔥 RẤT CAO"

elif signal >= 75:

    level = "🔥 CAO"

else:

    level = "🟠 ĐÁNG CHÚ Ý"

# ========================================================
# LAST GOAL TEXT
# ========================================================

if last_goal:

    last_goal_text = (
        f"{last_goal}'"
    )

else:

    last_goal_text = (
        "Chưa xác định"
    )

# ========================================================
# TELEGRAM MESSAGE
# ========================================================

message = (

    "🚨 BETING · KÈO RUNG\n\n"

    f"⚽ {home} vs {away}\n"

    f"⏱ {minute}' | "
    f"{home_goals}-{away_goals}\n\n"

    f"🔥 Signal: "
    f"{signal}/100\n"

    f"📊 Sút: "
    f"{int(total_shots)}\n"

    f"🎯 SOT: "
    f"{int(shots_on_target)}\n"

    f"🚩 Góc: "
    f"{int(corners)}\n"

    f"⚽ Bàn gần nhất: "
    f"{last_goal_text}\n\n"

    f"{level}\n"

    "🎯 KẾT LUẬN: "
    "CÓ TÍN HIỆU KÈO RUNG\n\n"

    "⚠️ Tín hiệu dựa trên "
    "thống kê trực tiếp và không "
    "đảm bảo kết quả."
)

send_telegram(
    message
)
```

# ============================================================

# MAIN

# ============================================================

def main():

```
print("")
print("================================")
print("       BETING V3 STARTED")
print("================================")
print("VERSION: 3.0")
print("MODE: LIVE FOOTBALL ANALYSIS")
print("================================")

# ========================================================
# CHECK ENVIRONMENT
# ========================================================

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

# ========================================================
# TELEGRAM START MESSAGE
# ========================================================

send_telegram(

    "🟢 BETING V3 ĐÃ KHỞI ĐỘNG!\n\n"

    "⚽ Live football analysis\n"
    "📊 Live statistics engine\n"
    "🔥 Kèo rung signal engine\n"
    "🛡 Anti-spam enabled"
)

# ========================================================
# MAIN LOOP
# ========================================================

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
```

# ============================================================

# START BOT

# ============================================================

if **name** == "**main**":

```
main()
```

```

### Làm đúng 3 thao tác

1. Mở **GitHub → BETING → `main.py`**.
2. **Ctrl + A → xóa sạch → dán toàn bộ đoạn trên → Commit changes.**
3. Chờ Railway tự Deploy rồi gửi tôi **log Railway**.

⚠️ **Không sửa thêm gì khác lúc này.** Sau khi bản này chạy ổn, chúng ta mới nâng tiếp lên bản có **lịch sử tình huống tương tự + O/U live + so sánh odds + quyết định kèo rung**.
```
