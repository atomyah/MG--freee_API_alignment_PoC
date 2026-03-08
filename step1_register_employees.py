#!/usr/bin/env python3
"""
Step 1: MachinGood ダミーデータから freee人事労務へ従業員を登録する

使い方:
  1. config.py を自分の環境に書き換える
  2. python step1_register_employees.py
  3. 実効は一回しかできない。再度実行すると、従業員が重複して登録される。

前提条件:
  - freee人事労務のテスト事業所に「締め日支払い日グループ」が
    少なくとも1つ設定済みであること（Web画面 → 設定 → 締め日支払い日）
  - 「勤務・賃金設定」が少なくとも1つ設定済みであること
    （Web画面 → 設定 → 勤務・賃金）

※ テスト事業所を作成した直後は、デフォルトで1つずつ存在するはずです。
"""

import json
import sys
import requests
from config import ACCESS_TOKEN, COMPANY_ID, API_BASE

# ============================================================
#  共通ヘッダ
# ============================================================
HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def api_get(path, params=None):
    """GETリクエスト"""
    url = f"{API_BASE}{path}"
    resp = requests.get(url, headers=HEADERS, params=params)
    if resp.status_code != 200:
        print(f"  [ERROR] GET {path} → {resp.status_code}")
        print(f"  {resp.text[:500]}")
        return None
    return resp.json()


def api_post(path, body):
    """POSTリクエスト"""
    url = f"{API_BASE}{path}"
    resp = requests.post(url, headers=HEADERS, json=body)
    if resp.status_code not in (200, 201):
        print(f"  [ERROR] POST {path} → {resp.status_code}")
        print(f"  {resp.text[:500]}")
        return None
    return resp.json()


# ============================================================
#  事前チェック: 締め日支払い日 & 勤務・賃金設定 を取得
# ============================================================
def get_company_settings():
    """テスト事業所の基本設定を取得"""
    print("=" * 60)
    print("  freee テスト事業所の設定を確認中...")
    print("=" * 60)

    # --- 締め日支払い日グループ ---
    data = api_get(f"/api/v1/companies/{COMPANY_ID}/pay_periods")
    if not data:
        print("\n[FATAL] 締め日支払い日グループを取得できません。")
        print("  → freee Web画面で [設定] → [締め日支払い日] を確認してください。")
        sys.exit(1)

    # レスポンス形式に応じて取得
    if isinstance(data, list):
        groups = data
    elif isinstance(data, dict):
        groups = data.get("pay_period_groups", data.get("pay_periods", [data]))
    else:
        groups = [data]

    if not groups:
        print("\n[FATAL] 締め日支払い日グループが0件です。Web画面で作成してください。")
        sys.exit(1)

    # 最初のグループを使用
    pay_period = groups[0]
    pay_period_id = pay_period.get("id") or pay_period.get("group_id")
    print(f"  締め日支払い日グループ: id={pay_period_id}")
    print(f"    {json.dumps(pay_period, ensure_ascii=False)[:200]}")

    # --- 勤務・賃金設定 ---
    data2 = api_get(f"/api/v1/companies/{COMPANY_ID}/work_rule_sets")
    if not data2:
        print("\n[WARN] 勤務・賃金設定を取得できませんでした（エンドポイントが異なる可能性）")
        work_rule_id = None
    else:
        if isinstance(data2, list):
            rules = data2
        elif isinstance(data2, dict):
            rules = data2.get("work_rule_sets", [data2])
        else:
            rules = [data2]
        work_rule_id = rules[0].get("id") if rules else None
        if work_rule_id:
            print(f"  勤務・賃金設定: id={work_rule_id}")

    return pay_period_id, work_rule_id


# ============================================================
#  従業員を登録
# ============================================================
def register_employee(emp, pay_period_id):
    """
    1名の従業員をfreee人事労務に登録する。

    POST /api/v1/employees
    """
    print(f"\n--- {emp['last_name']} {emp['first_name']} ({emp['mg_employee_id']}) ---")

    # MG の gender → freee の gender
    gender_map = {"male": "male", "female": "female"}

    # MG の employment_type → freee の pay_calc_type
    #   monthly → monthly (月給)
    #   hourly  → hourly  (時給)
    pay_calc = "monthly" if emp["employment_type"] == "monthly" else "hourly"

    emp_data = {
        "last_name": emp["last_name"],
        "first_name": emp["first_name"],
        "last_name_kana": emp["last_name_kana"],
        "first_name_kana": emp["first_name_kana"],
        "gender": gender_map.get(emp["gender"], "male"),
        "birth_date": emp["birth_date"],
        "entry_date": emp["entry_date"],
        "num": emp["mg_employee_id"],           # 従業員番号（MG IDをそのまま使用）
        "pay_calc_type": pay_calc,
        "pay_amount": emp["base_salary"],        # 月給額 or 0
    }

    # 時給の場合
    if pay_calc == "hourly" and emp.get("hourly_rate"):
        emp_data["pay_amount"] = emp["hourly_rate"]

    body = {
        "company_id": COMPANY_ID,
        "employee": emp_data,
    }

    result = api_post("/api/v1/employees", body)

    if result:
        emp_data = result.get("employee", result)
        freee_id = emp_data.get("id")
        print(f"  ✅ 登録成功! freee employee_id = {freee_id}")
        return freee_id
    else:
        print(f"  ❌ 登録失敗")
        return None


# ============================================================
#  メイン
# ============================================================
def main():
    # 設定チェック
    if COMPANY_ID == 0:
        print("[ERROR] config.py の COMPANY_ID を設定してください。")
        sys.exit(1)
    if ACCESS_TOKEN == "ここにアクセストークンを貼る":
        print("[ERROR] config.py の ACCESS_TOKEN を設定してください。")
        sys.exit(1)

    # ダミーデータ読み込み
    with open("mg_dummy_data.json", "r", encoding="utf-8") as f:
        mg_data = json.load(f)

    # 従業員登録
    print("\n" + "=" * 60)
    print("  従業員を登録します（5名）")
    print("=" * 60)

    # まず接続テスト: GET /users/me
    me = api_get("/api/v1/users/me")
    if not me:
        print("\n[FATAL] API接続に失敗しました。")
        print("  → ACCESS_TOKEN が正しいか、期限切れでないか確認してください。")
        sys.exit(1)
    print(f"  ✅ API接続OK（ユーザーID: {me.get('id', '?')}）\n")

    mapping = {}  # mg_employee_id → freee employee_id

    for emp in mg_data["employees"]:
        freee_id = register_employee(emp, None)
        if freee_id:
            mapping[emp["mg_employee_id"]] = freee_id

    # マッピング結果を保存
    with open("employee_mapping.json", "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"  完了！ {len(mapping)}/{len(mg_data['employees'])} 名の登録に成功")
    print("=" * 60)
    print(f"\n  マッピングファイル: employee_mapping.json")
    print(f"  {json.dumps(mapping, ensure_ascii=False, indent=2)}")

    if len(mapping) < len(mg_data["employees"]):
        print("\n[TIPS] 登録失敗した場合:")
        print("  1. freee Web画面で「締め日支払い日」「勤務・賃金」の設定を確認")
        print("  2. アクセストークンの有効期限が切れていないか確認")
        print("  3. アプリの権限に「従業員情報の参照・更新」が含まれているか確認")
        print("     → アプリ管理 > 権限設定 で確認・変更後、トークン再取得")

    print("\n次のステップ: python step2_input_attendance.py")


if __name__ == "__main__":
    main()
