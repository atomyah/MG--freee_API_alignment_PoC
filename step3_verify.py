#!/usr/bin/env python3
"""
Step 3: freee人事労務に登録した従業員・勤怠データを確認する

使い方:
  python step3_verify.py
"""

import json
import sys
import requests
from config import ACCESS_TOKEN, COMPANY_ID, API_BASE

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def api_get(path, params=None):
    url = f"{API_BASE}{path}"
    resp = requests.get(url, headers=HEADERS, params=params)
    if resp.status_code != 200:
        print(f"  [ERROR] GET {path} → {resp.status_code}")
        print(f"  {resp.text[:500]}")
        return None
    return resp.json()


def verify_employees():
    """従業員一覧を取得して表示"""
    print("=" * 60)
    print("  1. 登録済み従業員の確認")
    print("=" * 60)

    data = api_get(f"/api/v1/companies/{COMPANY_ID}/employees")
    if not data:
        print("  従業員一覧を取得できませんでした。")
        return []

    employees = data if isinstance(data, list) else data.get("employees", [data])

    print(f"  従業員数: {len(employees)}名\n")
    for emp in employees:
        eid = emp.get("id", "?")
        num = emp.get("num", "")
        name = f"{emp.get('last_name', '')} {emp.get('first_name', '')}"
        entry = emp.get("entry_date", "?")
        print(f"  [{num:>6}] {name:<12} (freee_id={eid}, 入社日={entry})")

    return employees


def verify_attendance(employees):
    """各従業員の2025年2月の月次勤怠サマリを取得"""
    print(f"\n{'=' * 60}")
    print("  2. 勤怠データの確認（2025年2月）")
    print("=" * 60)

    # マッピングがあれば読み込み
    try:
        with open("employee_mapping.json", "r", encoding="utf-8") as f:
            mapping = json.load(f)
        # 逆引き: freee_id → mg_id
        reverse_map = {str(v): k for k, v in mapping.items()}
    except FileNotFoundError:
        reverse_map = {}

    for emp in employees:
        eid = emp.get("id")
        name = f"{emp.get('last_name', '')} {emp.get('first_name', '')}"
        mg_id = reverse_map.get(str(eid), "?")

        print(f"\n  --- {name} ({mg_id} → freee:{eid}) ---")

        # 月次サマリ取得
        data = api_get(
            f"/api/v1/employees/{eid}/work_record_summaries/2025/2",
            params={"company_id": COMPANY_ID}
        )

        if not data:
            print("    月次サマリを取得できませんでした。")
            continue

        summary = data.get("work_record_summary", data)

        # よく使うフィールドを表示
        fields = {
            "出勤日数":     "work_days",
            "有給取得日数":  "paid_holiday",
            "欠勤日数":     "absence_days",
            "総労働時間(分)": "total_work_mins",
            "残業時間(分)":  "total_overtime_work_mins",
            "深夜残業(分)":  "total_midnight_work_mins",
        }

        for label, key in fields.items():
            val = summary.get(key, "-")
            if val is not None and val != "-":
                print(f"    {label}: {val}")
            else:
                print(f"    {label}: (データなし)")


def main():
    if COMPANY_ID == 0:
        print("[ERROR] config.py の COMPANY_ID を設定してください。")
        sys.exit(1)

    employees = verify_employees()

    if employees:
        verify_attendance(employees)

    print(f"\n{'=' * 60}")
    print("  確認完了！")
    print("=" * 60)
    print("\n  freee Web画面でも確認できます:")
    print("    → [従業員] タブ: 従業員一覧")
    print("    → [勤怠] タブ: 勤怠データ")
    print("    → [給与明細] タブ: 給与計算の実行")


if __name__ == "__main__":
    main()
