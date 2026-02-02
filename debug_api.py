import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("JQUANTS_API_KEY")

print(f"🔑 API_KEY (先頭3文字): {API_KEY[:3] if API_KEY else 'None'}")

# 確実にデータがあるはずの「先週の金曜日 (2026-01-30)」を指定
target_date = "20260130"
url = f"https://api.jquants.com/v2/equities/bars/daily?date={target_date}"
headers = {"x-api-key": API_KEY}

print(f"\n📡 通信テスト: {target_date} のデータを取得中...")

try:
    res = requests.get(url, headers=headers)
    print(f"📊 ステータスコード: {res.status_code}")
    print(f"📄 レスポンス内容:\n{res.text[:500]}") # エラーの詳細を表示
except Exception as e:
    print(f"❌ 通信エラー: {e}")