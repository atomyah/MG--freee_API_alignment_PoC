#!/usr/bin/env python3
"""
freee アクセストークン自動リフレッシュ

使い方:
  python refresh_token.py

config.py の ACCESS_TOKEN を自動更新します。
初回のみ REFRESH_TOKEN の設定が必要です。
"""

import json
import sys
import requests
from config import CLIENT_ID, CLIENT_SECRET, API_BASE

# ============================================================
#  トークンファイル（config.pyとは別に管理）
# ============================================================
TOKEN_FILE = "token.json"


def load_tokens():
    """保存済みトークンを読み込み"""
    try:
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def save_tokens(data):
    """トークンをファイルに保存"""
    with open(TOKEN_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  トークンを {TOKEN_FILE} に保存しました")


def refresh_access_token(refresh_token):
    """リフレッシュトークンで新しいアクセストークンを取得"""
    print("  アクセストークンをリフレッシュ中...")

    resp = requests.post(
        "https://accounts.secure.freee.co.jp/public_api/token",
        data={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": refresh_token,
        },
    )

    if resp.status_code != 200:
        print(f"  [ERROR] トークンリフレッシュ失敗: {resp.status_code}")
        print(f"  {resp.text[:500]}")
        return None

    data = resp.json()
    print(f"  ✅ 新しいアクセストークンを取得しました")
    print(f"     有効期限: {data.get('expires_in', '?')} 秒")
    return data


def get_valid_token():
    """
    有効なアクセストークンを返す。
    期限切れの場合は自動リフレッシュ。
    """
    tokens = load_tokens()

    if not tokens:
        print("[ERROR] token.json が見つかりません。")
        print("  → まず python refresh_token.py を実行してください。")
        sys.exit(1)

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    # テスト: 現在のトークンが有効か確認
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    resp = requests.get(f"{API_BASE}/api/v1/users/me", headers=headers)

    if resp.status_code == 200:
        return access_token

    # 期限切れ → リフレッシュ
    print("  アクセストークンが期限切れです。リフレッシュします...")
    new_data = refresh_access_token(refresh_token)

    if not new_data:
        print("[FATAL] リフレッシュに失敗しました。")
        print("  → 認可コードから取り直してください。")
        sys.exit(1)

    save_tokens(new_data)
    return new_data["access_token"]


def main():
    """
    初回セットアップ or 手動リフレッシュ
    """
    tokens = load_tokens()

    if tokens and tokens.get("refresh_token"):
        # 既存のリフレッシュトークンで更新
        new_data = refresh_access_token(tokens["refresh_token"])
        if new_data:
            save_tokens(new_data)
            print(f"\n  config.py を以下のように更新してください:")
            print(f'  ACCESS_TOKEN = "{new_data["access_token"]}"')
            return
        else:
            print("  リフレッシュに失敗しました。")

    # 初回: リフレッシュトークンを入力
    print("=" * 60)
    print("  freee トークン初期設定")
    print("=" * 60)
    print()
    print("  curl でトークン取得した際のレスポンスから")
    print("  refresh_token の値を入力してください。")
    print()
    rt = input("  refresh_token: ").strip()

    if not rt:
        print("  キャンセルしました。")
        return

    new_data = refresh_access_token(rt)
    if new_data:
        save_tokens(new_data)
        print(f"\n  config.py を以下のように更新してください:")
        print(f'  ACCESS_TOKEN = "{new_data["access_token"]}"')
    else:
        print("  失敗しました。refresh_token が正しいか確認してください。")


if __name__ == "__main__":
    main()
