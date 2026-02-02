import os
import requests
from dotenv import load_dotenv

# .envを読み込む
load_dotenv()

API_KEY = os.getenv("JQUANTS_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

print("--- 診断開始 ---")

# 1. 中身のチェック
if API_KEY:
    print(f"✅ API_KEYの文字数: {len(API_KEY)}")
    print(f"   先頭3文字: {API_KEY[:3]}")
    print(f"   末尾3文字: {API_KEY[-3:]}")
    
    if '"' in API_KEY or "'" in API_KEY:
        print("⚠️ 警告: キーの中にクォーテーション(' または \") が含まれています！.envを確認してください。")
    else:
        print("✅ キーの形式は良さそうです")
else:
    print("❌ API_KEYが空です")

# 2. 実際にAPIを叩いてみる (一番軽い銘柄一覧取得)
print("\n--- API通信テスト ---")
url = "https://api.jquants.com/v2/equities/master?code=7203" # トヨタだけ取得
headers = {"x-api-key": API_KEY}

try:
    res = requests.get(url, headers=headers)
    print(f"Status Code: {res.status_code}")
    
    if res.status_code == 200:
        print("🎉 成功！APIキーは正しいです。")
        print("データサンプル:", res.json()['equities'][0]['Name'])
    else:
        print("💀 失敗...")
        print("エラー内容:", res.text)
except Exception as e:
    print(f"通信エラー: {e}")