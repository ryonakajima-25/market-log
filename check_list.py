import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("JQUANTS_API_KEY")

def test_url(url_name, url):
    print(f"\n📡 {url_name} をテスト中: {url}")
    headers = {"x-api-key": API_KEY}
    try:
        res = requests.get(url, headers=headers)
        print(f"   Status Code: {res.status_code}")
        
        if res.status_code == 200:
            data = res.json()
            # データの箱の名前を探す
            keys = list(data.keys())
            print(f"   🎉 成功！データのキー: {keys}")
            
            # 中身を少し見る
            content = data.get('info', []) or data.get('equities', []) or data.get('data', [])
            if len(content) > 0:
                print(f"   ✅ データ件数: {len(content)} 件")
                print(f"   👀 データの例: {content[0]}")
                return True
            else:
                print("   ⚠️ データが空っぽです")
        else:
            print(f"   ❌ エラー: {res.text[:100]}")
    except Exception as e:
        print(f"   ❌ 通信エラー: {e}")
    return False

print("--- 銘柄一覧API 探索ツアー ---")

# 1. V1のアドレス（こっちが本命）
url_v1 = "https://api.jquants.com/v1/listed/info"
test_url("V1 (Listed Info)", url_v1)

# 2. V2のアドレス（さっき失敗したやつ）
url_v2 = "https://api.jquants.com/v2/equities/master" 
test_url("V2 (Equities Master)", url_v2)