import os
import time
import requests
import json
from datetime import datetime

API_KEY = os.getenv("API_FOOTBALL_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
HISTORY_FILE = "beting_history.json"
RESULTS_FILE = "beting_results.json"


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
COLLECT_FROM_MINUTE = 30
ALERT_FROM_MINUTE = 45

def load_results():
    if not os.path.exists(RESULTS_FILE):
        return []
    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print("RESULTS LOAD ERROR:", e)
        return []


def save_results():
    try:
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(alert_results, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("RESULTS SAVE ERROR:", e)


alert_results = load_results()
sent_alerts = {
    r.get("fixture_id") for r in alert_results
    if r.get("fixture_id") is not None
}


def daily_result_summary(day=None):
    day = day or datetime.now().astimezone().date().isoformat()
    rows = [r for r in alert_results if str(r.get("alert_date")) == day]
    wins = sum(1 for r in rows if r.get("result") == "WIN")
    half_wins = sum(1 for r in rows if r.get("result") == "HALF WIN")
    losses = sum(1 for r in rows if r.get("result") == "LOST")
    pending = sum(1 for r in rows if r.get("result") == "PENDING")
    settled = wins + half_wins + losses
    return {
        "date": day, "total": len(rows), "settled": settled,
        "wins": wins, "half_wins": half_wins,
        "losses": losses, "pending": pending
    }


def result_message(record):
    summary = daily_result_summary(record.get("alert_date"))
    return (
        f"{'✅' if record.get('result') in ('WIN', 'HALF WIN') else '❌'} BETING · {record.get('result')}\n\n"
        f"⚽ {record.get('home')} vs {record.get('away')}\n"
        f"📈 Over {record.get('handicap')} @ {record.get('over_odd')}\n"
        f"⏱ Báo phút {record.get('alert_minute')}' | "
        f"{record.get('alert_home_goals')}-{record.get('alert_away_goals')}\n"
        f"🏁 Kết quả: {record.get('final_home_goals')}-{record.get('final_away_goals')}\n\n"
        f"📅 TỔNG KẾT {summary['date']}\n"
        f"✅ WIN: {summary['wins']}\n"
        f"🟡 HALF WIN: {summary['half_wins']}\n"
        f"❌ LOST: {summary['losses']}\n"
        f"⏳ Chờ kết quả: {summary['pending']}"
    )


def settle_alert(record, final_home, final_away):
    if record.get("result") != "PENDING":
        return False

    start_goals = int(record.get("alert_home_goals", 0)) + int(record.get("alert_away_goals", 0))
    final_goals = int(final_home or 0) + int(final_away or 0)
    added_goals = max(0, final_goals - start_goals)
    line_offset = round(float(record.get("handicap", 0)) - start_goals, 2)

    if abs(line_offset - 0.5) < 0.01:
        result = "WIN" if added_goals >= 1 else "LOST"
    elif abs(line_offset - 0.75) < 0.01:
        if added_goals >= 2:
            result = "WIN"
        elif added_goals == 1:
            result = "HALF WIN"
        else:
            result = "LOST"
    else:
        return False

    record["result"] = result
    record["settled_at"] = datetime.now().astimezone().isoformat()
    record["final_home_goals"] = int(final_home or 0)
    record["final_away_goals"] = int(final_away or 0)
    record["added_goals"] = added_goals
    save_results()
    send_telegram(result_message(record))
    print("BET RESULT:", record.get("fixture_id"), "|", result)
    return True


def process_pending_results(live_matches):
    live_by_id = {
        m.get("fixture", {}).get("id"): m
        for m in live_matches
        if m.get("fixture", {}).get("id") is not None
    }

    for record in alert_results:
        if record.get("result") != "PENDING":
            continue
        fixture_id = record.get("fixture_id")
        live = live_by_id.get(fixture_id)

        if live:
            goals = live.get("goals", {})
            fh = goals.get("home") or 0
            fa = goals.get("away") or 0
            start_goals = int(record.get("alert_home_goals", 0)) + int(record.get("alert_away_goals", 0))
            added = int(fh) + int(fa) - start_goals
            offset = round(float(record.get("handicap", 0)) - start_goals, 2)
            # Khi Over đã chắc chắn thắng thì chốt ngay, không cần chờ FT.
            if (abs(offset - 0.5) < 0.01 and added >= 1) or (abs(offset - 0.75) < 0.01 and added >= 2):
                settle_alert(record, fh, fa)
            continue

        # Trận vừa rời danh sách live: gọi 1 lần để lấy tỷ số/trạng thái cuối.
        fixture_data = api_get("fixtures", {"id": fixture_id})
        if not fixture_data:
            continue
        finished = fixture_data[0]
        status = finished.get("fixture", {}).get("status", {}).get("short", "")
        if status not in ("FT", "AET", "PEN"):
            continue
        goals = finished.get("goals", {})
        settle_alert(record, goals.get("home") or 0, goals.get("away") or 0)


def save_match_snapshot(
    fixture_id, home_team, away_team, minute,
    home_goals, away_goals, total_shots, total_sot, total_corners,
    ou_line=None, ou_over=None, ou_under=None, data_quality="FULL"
):
    snapshot = {
        "timestamp": datetime.now().astimezone().isoformat(),
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
        "ou_under": ou_under,
        "data_quality": data_quality
    }

    # Một fixture chỉ giữ một snapshot cho mỗi phút. Nếu API trả lại
    # cùng phút, cập nhật bản mới nhất thay vì làm phình history.
    replaced = False
    for i in range(len(history_data) - 1, -1, -1):
        old = history_data[i]
        if old.get("fixture_id") == fixture_id and old.get("minute") == minute:
            history_data[i] = snapshot
            replaced = True
            break

    if not replaced:
        history_data.append(snapshot)

    save_history(history_data)
    print(
        "HISTORY SNAPSHOT", "UPDATED" if replaced else "SAVED",
        fixture_id, "|", minute, "'", "|",
        home_goals, "-", away_goals,
        "| SHOTS:", total_shots, "| SOT:", total_sot,
        "| CORNERS:", total_corners
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

    if not stats:
        print("SKIP - NO LIVE STATISTICS:", fixture_id)
        return None

    print("LIVE STATISTICS AVAILABLE:", fixture_id)
    return stats


def get_events(fixture_id, current_minute):

    events = api_get(
        "fixtures/events",
        {"fixture": fixture_id}
    )

    if not events:
        return {
            "latest_goal_minute": None,
            "minutes_since_goal": None,
            "goals_last_5": 0,
            "goals_last_10": 0,
            "goals_last_15": 0,
            "goals_last_20": 0
        }

    goal_minutes = []

    for event in events:

        if event.get("type") != "Goal":
            continue

        time_data = event.get(
            "time",
            {}
        )

        elapsed = time_data.get(
            "elapsed"
        )

        if elapsed is None:
            continue

        try:
            elapsed = int(elapsed)
        except:
            continue

        goal_minutes.append(
            elapsed
        )

    goal_minutes.sort()

    if not goal_minutes:

        print(
            "GOAL MINUTES: NONE"
        )

        return {
            "latest_goal_minute": None,
            "minutes_since_goal": None,
            "goals_last_5": 0,
            "goals_last_10": 0,
            "goals_last_15": 0,
            "goals_last_20": 0
        }

    latest_goal_minute = goal_minutes[-1]

    # current_minute đã có từ live fixtures; không gọi thêm /fixtures?id=.
    try:
        current_minute = int(current_minute or 0)
    except (TypeError, ValueError):
        current_minute = 0

    minutes_since_goal = (
        current_minute - latest_goal_minute
    )

    goals_last_5 = sum(
        1
        for m in goal_minutes
        if current_minute - 5 <= m <= current_minute
    )

    goals_last_10 = sum(
        1
        for m in goal_minutes
        if current_minute - 10 <= m <= current_minute
    )

    goals_last_15 = sum(
        1
        for m in goal_minutes
        if current_minute - 15 <= m <= current_minute
    )

    goals_last_20 = sum(
        1
        for m in goal_minutes
        if current_minute - 20 <= m <= current_minute
    )

    print(
        "GOAL MINUTES:",
        goal_minutes
    )

    print(
        "GOAL TEMPO:",
        "last5=",
        goals_last_5,
        "| last10=",
        goals_last_10,
        "| last15=",
        goals_last_15,
        "| last20=",
        goals_last_20,
        "| since_last=",
        minutes_since_goal
    )

    return {
        "latest_goal_minute": latest_goal_minute,
        "minutes_since_goal": minutes_since_goal,
        "goals_last_5": goals_last_5,
        "goals_last_10": goals_last_10,
        "goals_last_15": goals_last_15,
        "goals_last_20": goals_last_20
    }
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

        markets = odds[0].get(
            "odds",
            []
        )

        result = []

        for market in markets:

            market_name = str(
                market.get("name", "")
            ).lower()

            if "over/under" not in market_name:
                continue

            values = market.get(
                "values",
                []
            )

            for item in values:

                value = item.get(
                    "value"
                )

                odd = item.get(
                    "odd"
                )

                handicap = (
                    item.get("handicap")
                    or item.get("line")
                    or item.get("point")
                    or item.get("total")
                )

                if value is None or odd is None:
                    continue

                try:
                    odd = float(odd)
                except:
                    continue

                result.append({
                    "value": value,
                    "handicap": handicap,
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
def select_main_ou(
    ou_market,
    total_goals
):

    if not ou_market:
        return None

    pairs = {}

    for item in ou_market:

        try:
            handicap = float(
                item.get("handicap")
            )

            odd = float(
                item.get("odd")
            )

        except:
            continue

        value = str(
            item.get("value", "")
        ).lower()

        if handicap not in pairs:
            pairs[handicap] = {}

        if "over" in value:
            pairs[handicap]["over"] = odd

        elif "under" in value:
            pairs[handicap]["under"] = odd

    # ==================================================
    # KÈO RUNG:
    # Ưu tiên line tổng bàn hiện tại + 0.5
    # Sau đó +0.75
    #
    # Ví dụ:
    # Tổng bàn = 1
    #   Ưu tiên O/U 1.5
    #   Nếu không có -> O/U 1.75
    #
    # Tổng bàn = 2
    #   Ưu tiên O/U 2.5
    #   Nếu không có -> O/U 2.75
    # ==================================================

    total_goals = float(
        total_goals
    )

    preferred_lines = [
        total_goals + 0.5,
        total_goals + 0.75
    ]

    for preferred_line in preferred_lines:

        # Làm tròn để tránh lỗi float
        preferred_line = round(
            preferred_line,
            2
        )

        if preferred_line not in pairs:
            continue

        data = pairs[
            preferred_line
        ]

        if (
            "over" not in data
            or "under" not in data
        ):
            continue

        result = {
            "handicap": preferred_line,
            "over_odd": data["over"],
            "under_odd": data["under"],
            # Chỉ line current goals + 0.5 tương đương chính xác với
            # biến cố "có ít nhất 1 bàn nữa". +0.75 là Asian split line.
            "next_goal_compatible": (
                abs(preferred_line - (total_goals + 0.5)) < 0.001
                or abs(preferred_line - (total_goals + 0.75)) < 0.001
            )
        }

        print(
            "MAIN LIVE O/U - KÈO RUNG:",
            result
        )

        return result

    print(
        "KÈO RUNG O/U UNAVAILABLE:",
        "total_goals=",
        total_goals,
        "| preferred=",
        preferred_lines
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
    minute, total_goals, total_shots, shots_on_target, corners,
    minutes_since_goal=None, goals_last_5=0, goals_last_10=0,
    goals_last_15=0, goals_last_20=0
):
    # V4: score cường độ, không phải xác suất %.
    signal = 0

    # Thời điểm trận: tối đa 20 điểm.
    if minute >= 80:
        signal += 20
    elif minute >= 75:
        signal += 18
    elif minute >= 70:
        signal += 15
    elif minute >= 65:
        signal += 12
    elif minute >= 60:
        signal += 9
    elif minute >= 45:
        signal += 5

    # Tổng bàn: tối đa 12 điểm.
    if total_goals >= 4:
        signal += 12
    elif total_goals == 3:
        signal += 10
    elif total_goals == 2:
        signal += 8
    elif total_goals == 1:
        signal += 5

    # Cường độ sút: tối đa 25 điểm.
    if total_shots is not None:
        if total_shots >= 30:
            signal += 25
        elif total_shots >= 25:
            signal += 21
        elif total_shots >= 20:
            signal += 17
        elif total_shots >= 15:
            signal += 12
        elif total_shots >= 10:
            signal += 7

    # Chất lượng cú sút: tối đa 23 điểm.
    if shots_on_target is not None:
        if shots_on_target >= 12:
            signal += 23
        elif shots_on_target >= 10:
            signal += 20
        elif shots_on_target >= 8:
            signal += 17
        elif shots_on_target >= 6:
            signal += 13
        elif shots_on_target >= 4:
            signal += 8

    # Góc: proxy áp lực, tối đa 10 điểm.
    if corners is not None:
        if corners >= 12:
            signal += 10
        elif corners >= 10:
            signal += 8
        elif corners >= 8:
            signal += 6
        elif corners >= 6:
            signal += 4

    # Nhịp bàn chỉ cộng MỘT lần để tránh double counting 5/10/15/20.
    tempo_points = 0
    if goals_last_5 >= 1:
        tempo_points = 10
    elif goals_last_10 >= 1:
        tempo_points = 8
    elif goals_last_15 >= 1:
        tempo_points = 5
    elif goals_last_20 >= 1:
        tempo_points = 3
    elif minutes_since_goal is not None and minutes_since_goal <= 25:
        tempo_points = 2
    signal += tempo_points

    return min(signal, 100)


def _safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _future_goal_outcome(record, horizon=None):
    """
    True  = có bàn sau snapshot (trong horizon nếu horizon != None)
    False = đủ dữ liệu theo dõi nhưng không có bàn
    None  = chưa đủ dữ liệu để kết luận âm tính
    """
    fixture_id = record.get("fixture_id")
    minute_now = _safe_float(record.get("minute"))
    goals_now = _safe_float(record.get("total_goals"))
    if fixture_id is None or minute_now is None or goals_now is None:
        return None

    future = []
    for later in history_data:
        if later.get("fixture_id") != fixture_id:
            continue
        lm = _safe_float(later.get("minute"))
        lg = _safe_float(later.get("total_goals"))
        if lm is None or lg is None or lm <= minute_now:
            continue
        future.append((lm, lg))

    if not future:
        return None

    future.sort()
    if horizon is None:
        # Chỉ kết luận False nếu history đã đi đủ xa về cuối trận.
        if any(lg > goals_now for _, lg in future):
            return True
        max_minute = max(m for m, _ in future)
        return False if max_minute >= 88 else None

    target = minute_now + horizon
    for lm, lg in future:
        if lm <= target and lg > goals_now:
            return True

    # Muốn kết luận không có bàn trong N phút thì phải có snapshot
    # ít nhất tới target (cho phép thiếu 1 phút do polling/API delay).
    max_minute = max(m for m, _ in future)
    if max_minute >= target - 1:
        return False
    return None


def _rate_for_horizon(records, horizon):
    outcomes = [_future_goal_outcome(r, horizon) for r in records]
    known = [x for x in outcomes if x is not None]
    if not known:
        return None, 0
    rate = sum(1 for x in known if x) / len(known) * 100
    return round(rate, 1), len(known)


def get_historical_similarity(
    minute, total_goals, total_shots, shots_on_target, corners,
    ou_line=None, current_fixture_id=None, max_matches=50
):
    if not history_data:
        return {
            "sample_size": 0, "goal_rate": None,
            "goal_rate_5": None, "sample_5": 0,
            "goal_rate_10": None, "sample_10": 0,
            "goal_rate_15": None, "sample_15": 0
        }

    candidates = []
    for record in history_data:
        rid = record.get("fixture_id")
        if rid is None or rid == current_fixture_id:
            continue

        rm = _safe_float(record.get("minute"))
        rg = _safe_float(record.get("total_goals"))
        rs = _safe_float(record.get("total_shots"))
        rt = _safe_float(record.get("total_sot"))
        rc = _safe_float(record.get("total_corners"))
        ro = _safe_float(record.get("ou_line"))
        if rm is None or rg is None:
            continue

        # Cổng rộng để loại các trạng thái hoàn toàn khác trước khi xếp hạng.
        if abs(rm - float(minute)) > 12:
            continue
        if abs(rg - float(total_goals)) > 1:
            continue

        # Distance chuẩn hóa. Càng thấp càng giống.
        distance = abs(rm - float(minute)) / 6.0
        distance += abs(rg - float(total_goals)) * 1.5
        if total_shots is not None and rs is not None:
            distance += abs(rs - float(total_shots)) / 6.0
        else:
            distance += 0.75
        if shots_on_target is not None and rt is not None:
            distance += abs(rt - float(shots_on_target)) / 3.0
        else:
            distance += 0.75
        if corners is not None and rc is not None:
            distance += abs(rc - float(corners)) / 3.0
        else:
            distance += 0.5
        if ou_line is not None and ro is not None:
            distance += abs(ro - float(ou_line)) / 0.5

        candidates.append((distance, record))

    # Mỗi fixture lấy snapshot giống trạng thái hiện tại NHẤT.
    best_by_fixture = {}
    for distance, record in candidates:
        rid = record.get("fixture_id")
        old = best_by_fixture.get(rid)
        if old is None or distance < old[0]:
            best_by_fixture[rid] = (distance, record)

    ranked = sorted(best_by_fixture.values(), key=lambda x: x[0])
    selected = [record for _, record in ranked[:max_matches]]

    if not selected:
        return {
            "sample_size": 0, "goal_rate": None,
            "goal_rate_5": None, "sample_5": 0,
            "goal_rate_10": None, "sample_10": 0,
            "goal_rate_15": None, "sample_15": 0
        }

    # Any-next-goal dùng để so với line O/U +0.5. Chỉ lấy outcome đã biết.
    any_outcomes = [_future_goal_outcome(r, None) for r in selected]
    any_known = [x for x in any_outcomes if x is not None]
    goal_rate = None
    if any_known:
        goal_rate = round(sum(1 for x in any_known if x) / len(any_known) * 100, 1)

    rate5, sample5 = _rate_for_horizon(selected, 5)
    rate10, sample10 = _rate_for_horizon(selected, 10)
    rate15, sample15 = _rate_for_horizon(selected, 15)

    result = {
        "sample_size": len(any_known),
        "selected_matches": len(selected),
        "goal_rate": goal_rate,
        "goal_rate_5": rate5, "sample_5": sample5,
        "goal_rate_10": rate10, "sample_10": sample10,
        "goal_rate_15": rate15, "sample_15": sample15
    }
    print("HISTORICAL SIMILAR V4:", result)
    return result


def analyze_match(match):

    fixture = match.get(
        "fixture",
        {}
    )

    league = match.get(
        "league",
        {}
    )

    print(
        "LEAGUE COVERAGE:",
        league
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

    status = fixture.get(
        "status",
        {}
    )

    minute = status.get(
        "elapsed"
    )

    if minute is None:
        minute = 0

    print(
        "MATCH STATUS:",
        status
    )

    total_goals = (
        home_goals
        + away_goals
    )

    print(
        "ANALYZING:",
        home,
        "vs",
        away,
        f"{home_goals}-{away_goals}",
        f"minute={minute}"
    )

    match_status = status.get(
        "short",
        ""
    )

    if match_status == "ET":

        print(
            "SKIP EXTRA TIME:",
            fixture_id,
            "| minute=",
            minute
        )

        return

    if minute < COLLECT_FROM_MINUTE:
        print("SKIP BEFORE COLLECTION WINDOW:", fixture_id, "| minute=", minute)
        return

    alert_eligible_by_time = minute >= ALERT_FROM_MINUTE
    if not alert_eligible_by_time:
        print("COLLECT ONLY - BEFORE ALERT WINDOW:", fixture_id, "| minute=", minute)

    if fixture_id in sent_alerts:

        print(
            "ALREADY ALERTED:",
            fixture_id
        )

        return

    # ==================================================
    # LIVE STATISTICS
    # ==================================================

    stats = get_statistics(
        fixture_id
    )

    # ==================================================
    # LIVE EVENTS
    # ==================================================

    events = get_events(
        fixture_id,
        minute
    )

    # ==================================================
    # GOAL TEMPO
    # ==================================================

    latest_goal_minute = None
    minutes_since_goal = None

    if events:

        latest_goal_minute = events.get(
            "latest_goal_minute"
        )

        if latest_goal_minute is not None:

            minutes_since_goal = (
                minute
                - latest_goal_minute
            )

            print(
                "GOAL TEMPO:",
                "latest_goal=",
                latest_goal_minute,
                "| minutes_since_goal=",
                minutes_since_goal
            )

        else:

            print(
                "GOAL TEMPO: NO GOALS"
            )

    else:

        print(
            "GOAL TEMPO: EVENTS UNAVAILABLE"
        )

    # ==================================================
    # LIVE ODDS
    # ==================================================

    odds = get_live_odds(
        fixture_id
    )

    # ==================================================
    # LIVE STATISTICS PARSE
    # ==================================================

    total_shots = None
    shots_on_target = None
    corners = None

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

        if (
            home_shots is not None
            and away_shots is not None
        ):

            total_shots = (
                home_shots
                + away_shots
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

        if (
            home_sot is not None
            and away_sot is not None
        ):

            shots_on_target = (
                home_sot
                + away_sot
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

        if (
            home_corners is not None
            and away_corners is not None
        ):

            corners = (
                home_corners
                + away_corners
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
            "LIVE STATISTICS UNAVAILABLE:",
            fixture_id
        )

    # ==================================================
    # LIVE O/U KÈO RUNG
    # ==================================================

    main_ou = None

    ou_market = get_live_ou_market(
        odds
    )

    if ou_market:

        print(
            "LIVE O/U READY:",
            ou_market
        )

        main_ou = select_main_ou(
            ou_market,
            total_goals
        )

        if main_ou:

            print(
                "MAIN LIVE O/U:",
                main_ou
            )

        else:

            print(
                "MAIN O/U UNAVAILABLE"
            )

    else:

        print(
            "NO LIVE O/U:",
            fixture_id
        )

    # ==================================================
    # SIGNAL
    # ==================================================

    goals_last_5 = 0
    goals_last_10 = 0
    goals_last_15 = 0
    goals_last_20 = 0

    if events:

        goals_last_5 = events.get(
            "goals_last_5",
            0
        )

        goals_last_10 = events.get(
            "goals_last_10",
            0
        )

        goals_last_15 = events.get(
            "goals_last_15",
            0
        )

        goals_last_20 = events.get(
            "goals_last_20",
            0
        )

    signal = calculate_signal(
        minute=minute,
        total_goals=total_goals,
        total_shots=total_shots,
        shots_on_target=shots_on_target,
        corners=corners,
        minutes_since_goal=minutes_since_goal,
        goals_last_5=goals_last_5,
        goals_last_10=goals_last_10,
        goals_last_15=goals_last_15,
        goals_last_20=goals_last_20
    )

    print(
        "GOAL TEMPO SIGNAL:",
        "5m=",
        goals_last_5,
        "| 10m=",
        goals_last_10,
        "| 15m=",
        goals_last_15,
        "| 20m=",
        goals_last_20
    )

    # ==================================================
    # HISTORICAL SIMILARITY
    # ==================================================

    ou_line = None

    if main_ou:

        ou_line = main_ou.get(
            "handicap"
        )

    historical = get_historical_similarity(
        minute=minute,
        total_goals=total_goals,
        total_shots=total_shots,
        shots_on_target=shots_on_target,
        corners=corners,
        ou_line=ou_line,
        current_fixture_id=fixture_id
    )

    historical_rate = historical.get(
        "goal_rate"
    )

    historical_sample = historical.get(
        "sample_size",
        0
    )

    historical_rate_5 = historical.get("goal_rate_5")
    historical_rate_10 = historical.get("goal_rate_10")
    historical_rate_15 = historical.get("goal_rate_15")
    historical_sample_5 = historical.get("sample_5", 0)
    historical_sample_10 = historical.get("sample_10", 0)
    historical_sample_15 = historical.get("sample_15", 0)

    print(
        "HISTORICAL RATE:",
        historical_rate,
        "% | SAMPLE:",
        historical_sample
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

    # ==================================================
    # SAVE HISTORY SNAPSHOT
    # ==================================================

    data_quality = (
        "FULL"
        if total_shots is not None and shots_on_target is not None and corners is not None
        else "PARTIAL"
    )

    # V4.1: luôn lưu từ phút 30 nếu có trạng thái trận. PARTIAL vẫn hữu ích
    # cho minute/score/events/O-U; similarity sẽ phạt các trường stats bị thiếu.
    save_match_snapshot(
        fixture_id, home, away, minute, home_goals, away_goals,
        total_shots, shots_on_target, corners,
        ou_line=ou_line,
        ou_over=(main_ou.get("over_odd") if main_ou else None),
        ou_under=(main_ou.get("under_odd") if main_ou else None),
        data_quality=data_quality
    )
    print("DATA QUALITY:", data_quality)

    if not alert_eligible_by_time:
        print("COLLECTED - NO ALERT BEFORE", ALERT_FROM_MINUTE, "MIN:", fixture_id)
        return

    # HT là khoảng nghỉ, không phải thời gian bóng đang lăn. Vẫn lưu snapshot
    # để history biết trạng thái 45', nhưng không phát tín hiệu rung tại HT.
    if match_status == "HT":
        print("COLLECTED AT HT - ALERT PAUSED:", fixture_id)
        return

    # Không phát cảnh báo mới từ phút 85 trở đi.
    # Snapshot/history đã được lưu phía trên nên dữ liệu vẫn tiếp tục được thu thập.
    if minute >= 85:
        print(
            "KÈO RUNG REJECT:", fixture_id,
            "| MINUTE >= 85 - NO NEW ALERT"
        )
        return

    # ==================================================
    # FINAL KÈO RUNG FILTER
    # ==================================================

    print(
        "KÈO RUNG FILTER START:",
        fixture_id
    )

    # --------------------------------------------------
    # 1. PHẢI CÓ LIVE STATS ĐẦY ĐỦ
    # --------------------------------------------------

    if (
        total_shots is None
        or shots_on_target is None
        or corners is None
    ):

        print(
            "KÈO RUNG REJECT:",
            fixture_id,
            "| LIVE STATS INCOMPLETE"
        )

        return

    # --------------------------------------------------
    # 2. PHẢI CÓ LINE KÈO RUNG
    # --------------------------------------------------

    if main_ou is None:

        print(
            "KÈO RUNG REJECT:",
            fixture_id,
            "| NO VALID RUNG LINE"
        )

        return

    # Cho phép kèo rung current goals +0.5 hoặc +0.75 theo cấu hình hiện tại.
    # Các line khác vẫn bị loại.
    if not main_ou.get("next_goal_compatible", False):
        print(
            "KÈO RUNG REJECT:", fixture_id,
            "| ASIAN LINE NOT NEXT-GOAL COMPARABLE:",
            main_ou.get("handicap")
        )
        return

    # --------------------------------------------------
    # 3. PHẢI CÓ LỊCH SỬ
    # --------------------------------------------------

    if historical_rate is None:

        print(
            "KÈO RUNG REJECT:",
            fixture_id,
            "| NO HISTORICAL RATE"
        )

        return

    # --------------------------------------------------
    # 4. LỊCH SỬ PHẢI ĐỦ MẪU
    # --------------------------------------------------

    MIN_HISTORY_SAMPLE = 5

    if historical_sample < MIN_HISTORY_SAMPLE:

        print(
            "KÈO RUNG REJECT:",
            fixture_id,
            "| HISTORY SAMPLE TOO SMALL:",
            historical_sample
        )

        return

    # --------------------------------------------------
    # 5. LỊCH SỬ PHẢI CÓ TỶ LỆ BÀN TIẾP THEO
    # --------------------------------------------------

    MIN_HISTORICAL_RATE = 60.0

    if historical_rate < MIN_HISTORICAL_RATE:

        print(
            "KÈO RUNG REJECT:",
            fixture_id,
            "| HISTORICAL RATE LOW:",
            historical_rate
        )

        return

    # --------------------------------------------------
    # 6. KIỂM TRA ODDS
    # --------------------------------------------------

    over_odd = main_ou.get(
        "over_odd"
    )

    under_odd = main_ou.get(
        "under_odd"
    )

    if (
        over_odd is None
        or under_odd is None
    ):

        print(
            "KÈO RUNG REJECT:",
            fixture_id,
            "| INVALID O/U ODDS"
        )

        return

    try:

        over_odd = float(
            over_odd
        )

        under_odd = float(
            under_odd
        )

    except:

        print(
            "KÈO RUNG REJECT:",
            fixture_id,
            "| ODDS PARSE ERROR"
        )

        return

    if over_odd <= 1.0:

        print(
            "KÈO RUNG REJECT:",
            fixture_id,
            "| INVALID OVER ODDS:",
            over_odd
        )

        return

    # --------------------------------------------------
    # 7. XÁC SUẤT NGẦM ĐỊNH CỦA OVER
    # --------------------------------------------------

    if over_odd <= 1.0 or under_odd <= 1.0:
        print("KÈO RUNG REJECT:", fixture_id, "| INVALID TWO-WAY ODDS")
        return

    raw_over = 1.0 / over_odd
    raw_under = 1.0 / under_odd
    market_margin = raw_over + raw_under
    implied_over_probability = raw_over / market_margin * 100

    odds_edge = historical_rate - implied_over_probability

    print(
        "ODDS ANALYSIS:",
        "Over=",
        over_odd,
        "| implied=",
        round(
            implied_over_probability,
            1
        ),
        "%",
        "| historical=",
        historical_rate,
        "%",
        "| edge=",
        round(
            odds_edge,
            1
        ),
        "%"
    )

    # --------------------------------------------------
    # 8. ODDS PHẢI CÓ LỢI THẾ
    # --------------------------------------------------

    MIN_ODDS_EDGE = 5.0

    if odds_edge < MIN_ODDS_EDGE:

        print(
            "KÈO RUNG REJECT:",
            fixture_id,
            "| ODDS EDGE TOO LOW:",
            round(
                odds_edge,
                1
            ),
            "%"
        )

        return

    # --------------------------------------------------
    # 9. KIỂM TRA LIVE STATS
    # --------------------------------------------------

    stats_strength = 0

    if total_shots >= 10:
        stats_strength += 1

    if shots_on_target >= 4:
        stats_strength += 1

    if corners >= 2:
        stats_strength += 1

    if goals_last_10 >= 1:
        stats_strength += 1

    if (
        minutes_since_goal is not None
        and minutes_since_goal <= 10
    ):
        stats_strength += 1

    print(
        "STATS STRENGTH:",
        stats_strength,
        "/5"
    )

    # --------------------------------------------------
    # 10. NHÁNH SIGNAL MẠNH
    # --------------------------------------------------

    strong_signal_path = (
        signal >= 70
        and stats_strength >= 2
        and historical_rate >= 60
        and odds_edge >= 5
    )

    # --------------------------------------------------
    # 11. NHÁNH SIGNAL THẤP NHƯNG CÁC YẾU TỐ KHÁC MẠNH
    # --------------------------------------------------

    combined_path = (
        signal >= 55
        and stats_strength >= 4
        and historical_rate >= 65
        and odds_edge >= 8
    )

    print(
        "SIGNAL PATH:",
        "STRONG="
        , strong_signal_path,
        "| COMBINED="
        , combined_path
    )

    if not (
        strong_signal_path
        or combined_path
    ):

        print(
            "KÈO RUNG REJECT:",
            fixture_id,
            "| COMBINED CONDITIONS NOT STRONG ENOUGH"
        )

        return

    # ==================================================
    # 12. TẠO CẢNH BÁO
    # ==================================================

    handicap = main_ou.get(
        "handicap"
    )

    alert_message = (
        "🚨 BETING · KÈO RUNG\n"
        "\n"
        f"⚽ {home} vs {away}\n"
        f"⏱ {minute}' | "
        f"{home_goals}-{away_goals}\n"
        f"🔥 Signal: {signal}/100\n"
        f"📊 Sút: {int(total_shots)} "
        f"| SOT: {int(shots_on_target)} "
        f"| Góc: {int(corners)}\n"
        f"⚡ Bàn gần nhất: "
        f"{latest_goal_minute}'\n"
        if latest_goal_minute is not None
        else
        f"🚨 BETING · KÈO RUNG\n"
        "\n"
        f"⚽ {home} vs {away}\n"
        f"⏱ {minute}' | "
        f"{home_goals}-{away_goals}\n"
        f"🔥 Signal: {signal}/100\n"
        f"📊 Sút: {int(total_shots)} "
        f"| SOT: {int(shots_on_target)} "
        f"| Góc: {int(corners)}\n"
    )

    alert_message += (
        f"📈 O/U rung: {handicap}\n"
        f"💰 Over {handicap}: {over_odd}\n"
        f"📉 Under {handicap}: {under_odd}\n"
        f"🧠 Có bàn tiếp theo: {historical_rate}% "
        f"({historical_sample} mẫu đủ dữ liệu)\n"
        f"⏳ ≤5 phút: {historical_rate_5 if historical_rate_5 is not None else 'N/A'}% "
        f"({historical_sample_5} mẫu)\n"
        f"⏳ ≤10 phút: {historical_rate_10 if historical_rate_10 is not None else 'N/A'}% "
        f"({historical_sample_10} mẫu)\n"
        f"⏳ ≤15 phút: {historical_rate_15 if historical_rate_15 is not None else 'N/A'}% "
        f"({historical_sample_15} mẫu)\n"
        f"📐 Fair market Over: {round(implied_over_probability, 1)}%\n"
        f"📐 Historical edge: {round(odds_edge, 1):+} điểm %\n"
        "\n"
        "🎯 KẾT LUẬN: CÓ TÍN HIỆU KÈO RUNG"
    )

    print(
        "🚨 KÈO RUNG TRIGGER:",
        fixture_id
    )

    print(
        alert_message
    )

    # ==================================================
    # 13. GỬI TELEGRAM
    # ==================================================

    send_telegram(
        alert_message
    )

    # Lưu tín hiệu để tự chốt WIN / HALF WIN / LOST và thống kê theo ngày.
    alert_results.append({
        "fixture_id": fixture_id,
        "home": home,
        "away": away,
        "alert_at": datetime.now().astimezone().isoformat(),
        "alert_date": datetime.now().astimezone().date().isoformat(),
        "alert_minute": minute,
        "alert_home_goals": home_goals,
        "alert_away_goals": away_goals,
        "handicap": handicap,
        "over_odd": over_odd,
        "signal": signal,
        "historical_rate": historical_rate,
        "historical_sample": historical_sample,
        "odds_edge": round(odds_edge, 1),
        "result": "PENDING"
    })
    save_results()

    # ==================================================
    # 14. MỖI TRẬN CHỈ ALERT 1 LẦN
    # ==================================================

    sent_alerts.add(
        fixture_id
    )

    print(
        "ALERT SENT:",
        fixture_id,
        "| ONE ALERT PER MATCH"
    )
def main():

    print("")
    print("================================")
    print("BETING V4.2 STARTED")
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
        "BETING V4.2 DA KHOI DONG!\n\n"
        "Live football analysis\n"
        "Live statistics\n"
        "Keo rung signal engine V4\n"
        "History 5/10/15m + no-vig odds\n"
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

            process_pending_results(matches)

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
