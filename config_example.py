# ============================================================
#  config.py  ―  freee API 接続設定
# ============================================================
#  ★ ここを自分の環境に書き換えてください ★
# ============================================================

# ------ freee 開発者アプリ情報 ------
CLIENT_ID     = "クライアントID"
CLIENT_SECRET = "クライアントシークレット"
### 以上はhttps://app.secure.freee.co.jp/developers/applications/54778 から取得できる

# ------ アクセストークン（最初に取得したもの）------
ACCESS_TOKEN  = "アクセストークン"
### 以上は「開発用テストアプリ」作成中ウィザードで取得できる。
### あるいは更新・再取得の際にはhttps://developer.freee.co.jp/startguide/getting-access-token を参照

# ------ テスト事業所ID（GET /users/me で取得した company_id）------
COMPANY_ID    = 事業所ID   # 数値で入力  例: 1234567
### https://developer.freee.co.jp/reference/hr/reference ページで「GET /api/v1/users/meログインユーザーの取得」
### を参照して取得できる。
# 出力例:
# {
#   "id": 14895509,
#   "companies": [
#     {
#       "id": 12503089,     ← 事業所ID
#       "name": "開発用テスト事業所",
#       "role": "company_admin",
#       "external_cid": "3642531977",
#       "employee_id": null,
#       "display_name": null
#     }
#   ]
# }

# ------ freee API ベースURL ------
#  ※ 人事労務APIは /hr/api/v1 がパスプレフィックス
#     会計APIは /api/v1（別物なので注意）
API_BASE      = "https://api.freee.co.jp/hr"

# ------ MG→freee 従業員番号のプレフィックス ------
#  freee側の従業員番号(num)に付与。MG-001 → "MG-001"
EMPLOYEE_NUM_PREFIX = ""  # 空文字ならMGのIDをそのまま使う（このプロジェクトでは使わない）
