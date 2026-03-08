#!/usr/bin/env python3
"""
Step 2: MachinGood ダミー勤怠データを freee人事労務へ投入する

使い方:
  1. step1_register_employees.py を先に実行して employee_mapping.json を作成
  2. python step2_input_attendance.py
  3. 何回実行してもよい。（勤怠データが更新されることはない。ただfreeeの設定変更に合わせて（有給休暇を入力するなど）、
     再度実行すると、それに合わせて表示結果が変わる。

変換レイヤーの役割:
  - MGの時刻文字列（"09:00"）→ freee APIのISO 8601形式へ変換
  - 有給・欠勤・半休の勤怠区分マッピング
  - 休憩時間の変換
"""

import json
import sys
import time
import requests
from config import ACCESS_TOKEN, COMPANY_ID, API_BASE

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


# ============================================================
#  変換レイヤー：MG形式 → freee形式
# ============================================================

def time_to_minutes(time_str):
    """
    "09:00" → 540 (分)
    """
    if not time_str:
        return None
    h, m = time_str.split(":")
    return int(h) * 60 + int(m)


def to_iso_datetime(date_str, time_str):
    """
    "2025-02-03", "09:00" → "2025-02-03T09:00:00.000+09:00"
    """
    if not time_str:
        return None
    return f"{date_str}T{time_str}:00.000+09:00"


def classify_day_type(record):
    """
    MGの勤怠レコードからfreeeの日区分を判定する。
    """
    note = record.get("note", "")

    if "有給休暇" in note and "半休" not in note:
        return "paid_holiday"
    if "欠勤" in note:
        return "absence"
    if "祝日" in note:
        return None  # freeeの自動判定に任せる

    if record["clock_in"] is None:
        return None

    return "normal_day"


def _break_start_time(clock_in):
    """休憩開始時刻を推定（12:00固定、ただし出勤が12時以降なら4時間後）"""
    mins = time_to_minutes(clock_in)
    if mins >= 720:  # 12:00以降の出勤
        start = mins + 240
    else:
        start = 720  # 12:00
    return f"{start // 60:02d}:{start % 60:02d}"


def _break_end_time(clock_in, break_mins):
    """休憩終了時刻"""
    start = time_to_minutes(_break_start_time(clock_in))
    end = start + break_mins
    return f"{end // 60:02d}:{end % 60:02d}"


def convert_to_freee_work_record(record):
    """
    MGの1日分の勤怠レコードを、freee APIのリクエストボディに変換する。

    PUT /api/v1/employees/{employee_id}/work_records/{date}
    """
    date = record["date"]
    day_type = classify_day_type(record)

    if day_type is None:
        return None  # スキップ対象

    if day_type == "paid_holiday":
        return {
            "company_id": COMPANY_ID,
            "break_records": [],
            "clock_in_at": None,
            "clock_out_at": None,
            "day_pattern": "normal_day",
            "is_absence": False,
            "paid_holiday": 1.0,
            "use_default_work_pattern": True,
            "use_attendance_deduction": True,
        }

    if day_type == "absence":
        return {
            "company_id": COMPANY_ID,
            "break_records": [],
            "clock_in_at": None,
            "clock_out_at": None,
            "day_pattern": "normal_day",
            "is_absence": True,
            "paid_holiday": 0.0,
            "use_default_work_pattern": True,
            "use_attendance_deduction": True,
        }

    # --- 通常出勤 ---
    break_mins = record.get("break_mins", 60)
    break_start = _break_start_time(record["clock_in"])
    break_end = _break_end_time(record["clock_in"], break_mins)

    body = {
        "company_id": COMPANY_ID,
        "clock_in_at": to_iso_datetime(date, record["clock_in"]),
        "clock_out_at": to_iso_datetime(date, record["clock_out"]),
        "break_records": [
            {
                "clock_in_at": to_iso_datetime(date, break_start),
                "clock_out_at": to_iso_datetime(date, break_end),
            }
        ],
        "day_pattern": "normal_day",
        "is_absence": False,
        "paid_holiday": 0.0,
        "use_default_work_pattern": False,
        "use_attendance_deduction": True,
    }

    # 半休対応
    note = record.get("note", "")
    if "午前半休" in note or "午後半休" in note:
        body["paid_holiday"] = 0.5

    return body


# ============================================================
#  API 呼び出し
# ============================================================

def put_work_record(employee_id, date, body):
    """
    PUT /api/v1/employees/{employee_id}/work_records/{date}
    """
    url = f"{API_BASE}/api/v1/employees/{employee_id}/work_records/{date}"

    request_body = {
        "company_id": COMPANY_ID,
        "work_record": {k: v for k, v in body.items() if k != "company_id"},
        ###　body の各キー・値をループして、company_id 以外を work_record に入れる。ody に company_id が含まれていても、work_record の中には入れない
        ### work_record には、convert_to_freee_work_record が返す body から company_id を除いたものが入れられる。
    }
    # company_id: 会社ID（トップレベル）
    # work_record: 勤怠レコード本体（出退勤時刻など
    
    ### work_record中身例（通常勤務）
    # {
    # "clock_in_at": "2025-02-03T09:00:00.000+09:00",
    # "clock_out_at": "2025-02-03T18:00:00.000+09:00",
    # "break_records": [
    #     {
    #     "clock_in_at": "2025-02-03T12:00:00.000+09:00",
    #     "clock_out_at": "2025-02-03T13:00:00.000+09:00"
    #     }
    # ],
    # "day_pattern": "normal_day",
    # "is_absence": false,
    # "paid_holiday": 0.0,
    # "use_default_work_pattern": false,
    # "use_attendance_deduction": true
    # }
    
    ### work_record中身例（有給休暇）
    # {
    # "break_records": [],
    # "clock_in_at": null,
    # "clock_out_at": null,
    # "day_pattern": "normal_day",
    # "is_absence": false,
    # "paid_holiday": 1.0,
    # "use_default_work_pattern": true,
    # "use_attendance_deduction": true
    # } 
    
    # フィールドの意味
    # clock_in_at / clock_out_at	出勤・退勤時刻（ISO 8601）
    # break_records	休憩の開始・終了時刻の配列
    # day_pattern	日区分（normal_day など）
    # is_absence	欠勤フラグ
    # paid_holiday	有給日数（0.0 / 0.5 / 1.0）
    # use_default_work_pattern	所定労働パターンを使用するか
    # use_attendance_deduction	勤怠控除を適用するか
    
    resp = requests.put(url, headers=HEADERS, json=request_body)

    if resp.status_code in (200, 201):
        return True
    else:
        print(f"    [ERROR] {resp.status_code}: {resp.text[:500]}")
        return False


# ============================================================
#  メイン
# ============================================================
def main():
    if COMPANY_ID == 0:
        print("[ERROR] config.py の COMPANY_ID を設定してください。")
        sys.exit(1)

    # マッピング読み込み
    try:
        with open("employee_mapping.json", "r", encoding="utf-8") as f:
            mapping = json.load(f)
    except FileNotFoundError:
        print("[ERROR] employee_mapping.json が見つかりません。")
        print("  → 先に step1_register_employees.py を実行してください。")
        sys.exit(1)

    # ダミーデータ読み込み
    with open("mg_dummy_data.json", "r", encoding="utf-8") as f:
        mg_data = json.load(f)

    attendance = mg_data["attendance_2025_02"]

    print("=" * 60)
    print(f"  勤怠データを投入します（{attendance['year']}年{attendance['month']}月）")
    print("=" * 60)

    total_ok = 0
    total_skip = 0
    total_err = 0

    for emp_record in attendance["records"]:
        mg_id = emp_record["mg_employee_id"]
        freee_id = mapping.get(mg_id)

        if not freee_id:
            print(f"\n[SKIP] {mg_id}: マッピングが見つかりません")
            continue

        emp_info = next(
            (e for e in mg_data["employees"] if e["mg_employee_id"] == mg_id),
            None
        )
        name = f"{emp_info['last_name']} {emp_info['first_name']}" if emp_info else mg_id

        print(f"\n--- {name} ({mg_id} → freee:{freee_id}) ---")

        for day in emp_record["daily"]:
            date = day["date"]
            note = day.get("note", "")

            body = convert_to_freee_work_record(day)

            if body is None:
                print(f"  {date}: スキップ ({note})")
                total_skip += 1
                continue

            ok = put_work_record(freee_id, date, body)

            if ok:
                work_hours = ""
                if day["clock_in"] and day["clock_out"]:
                    mins = time_to_minutes(day["clock_out"]) - time_to_minutes(day["clock_in"]) - day["break_mins"]
                    work_hours = f" ({mins // 60}h{mins % 60:02d}m)"
                print(f"  {date}: ✅{work_hours} {note}")
                total_ok += 1
            else:
                print(f"  {date}: ❌ {note}")
                total_err += 1

            # レートリミット対策
            time.sleep(0.3)

    print("\n" + "=" * 60)
    print(f"  完了！")
    print(f"    成功: {total_ok}件")
    print(f"    スキップ: {total_skip}件（祝日等）")
    print(f"    失敗: {total_err}件")
    print("=" * 60)

    if total_err > 0:
        print("\n[TIPS] 失敗した場合:")
        print("  1. freee Web画面で従業員が正しく登録されているか確認")
        print("  2. 「勤務・賃金設定」で所定労働時間が設定されているか確認")
        print("  3. アプリの権限に「勤怠情報の参照・更新」が含まれているか確認")

    print("\n次のステップ:")
    print("  python step3_verify.py  (投入結果の確認)")
    print("  または freee Web画面で [勤怠] タブを確認してください")


if __name__ == "__main__":
    main()
