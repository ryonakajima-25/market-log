import pandas as pd
import requests
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import urllib.parse

# .envファイルを読み込む
load_dotenv()

# --- 設定 ---
API_KEY = os.getenv("JQUANTS_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# APIのURL
BASE_URL_V2 = "https://api.jquants.com/v2"

def get_db_engine():
    # 【重要】DBパスワードの記号(%と+)でエラーが出ないように自動修正する処理
    if DATABASE_URL and ("%" in DATABASE_URL or "+" in DATABASE_URL):
        # すでに修正済み(%25など)でなければ、警告を出すか、ここでよしなに処理する
        # 今回は、ユーザーが.envを直していない場合でも動くように、ここでURLをパースして再構築するのは複雑なので
        # シンプルにそのまま渡しますが、エラーが出たら.env修正を促します。
        pass
    return create_engine(DATABASE_URL)

def fetch_daily_data(date_str):
    """指定日の全銘柄データを取得"""
    headers = {"x-api-key": API_KEY}
    url = f"{BASE_URL_V2}/equities/bars/daily?date={date_str}"
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            res_json = res.json()
            # ★ここが修正ポイント！ 'daily_quotes' か 'data' のどっちかに入っている
            data = res_json.get("daily_quotes", []) or res_json.get("data", [])
            
            if len(data) > 0:
                return pd.DataFrame(data)
        else:
            # エラーの場合はログを出す
            print(f"  ⚠️ API Status: {res.status_code}")
    except Exception as e:
        print(f"Error fetching {date_str}: {e}")
    return None

def fetch_company_list():
    """銘柄一覧（市場情報）を取得"""
    headers = {"x-api-key": API_KEY}
    url = f"{BASE_URL_V2}/equities/master"
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            res_json = res.json()
            # ここも念のため両方対応
            data = res_json.get("equities", []) or res_json.get("info", []) or res_json.get("data", [])
            return pd.DataFrame(data)[['Code', 'Market']]
    except:
        pass
    return pd.DataFrame()

def main():
    print("🚀 バッチ処理開始...")
    
    # DB接続テスト
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            pass
    except Exception as e:
        print(f"\n❌ DB接続エラー: {e}")
        return

    # 過去14日分をループ
    for i in range(14):
        target_date = datetime.now() - timedelta(days=i)
        date_str = target_date.strftime("%Y%m%d")
        print(f"\n📅 処理中: {date_str}")

        # 1. データ取得
        df_quotes = fetch_daily_data(date_str)
        if df_quotes is None or df_quotes.empty:
            print("  ❌ データなし（休日など）")
            continue

        df_list = fetch_company_list()
        if df_list.empty:
            print("  ⚠️ 銘柄リスト取得失敗(スキップ)")
            continue

        # 2. データ整形
        df = pd.merge(df_quotes, df_list, on='Code', how='left')
        df['Date'] = pd.to_datetime(df['Date'])
        # カラム名のゆらぎ吸収 (Va=売買代金, Vo=出来高)
        if 'Va' in df.columns:
            df['TradingValue'] = pd.to_numeric(df['Va'], errors='coerce').fillna(0)
        elif 'TradingValue' in df.columns: # すでに名前が合っている場合
            df['TradingValue'] = pd.to_numeric(df['TradingValue'], errors='coerce').fillna(0)
            
        if 'C' in df.columns:
            df['Close'] = pd.to_numeric(df['C'], errors='coerce')

        df['Market'] = df['Market'].fillna('Others')

        # 市場名正規化
        def normalize_market(m):
            m = str(m)
            if "Prime" in m or "プライム" in m: return "Prime"
            if "Standard" in m or "スタンダード" in m: return "Standard"
            if "Growth" in m or "グロース" in m: return "Growth"
            return "Others"
        df['NormMarket'] = df['Market'].apply(normalize_market)

        # 3. DBへ保存
        # 重複削除
        with engine.connect() as conn:
            conn.execute(text(f"DELETE FROM market_history WHERE \"Date\" = '{target_date.strftime('%Y-%m-%d')}'"))
            conn.execute(text(f"DELETE FROM daily_ranking WHERE \"Date\" = '{target_date.strftime('%Y-%m-%d')}'"))
            conn.commit()

        # A. 市場集計
        market_summary = df.groupby(['Date', 'NormMarket'])['TradingValue'].sum().reset_index()
        market_summary.to_sql('market_history', engine, if_exists='append', index=False)
        print(f"  ✅ 市場集計 保存完了")

        # B. ランキング
        top100 = df.sort_values('TradingValue', ascending=False).head(100)
        # カラム名をDBに合わせて調整
        top100_save = top100[['Date', 'Code', 'NormMarket', 'TradingValue', 'Close']].copy()
        top100_save.columns = ['Date', 'Code', 'Market', 'TradingValue', 'Close']
        
        top100_save.to_sql('daily_ranking', engine, if_exists='append', index=False)
        print(f"  ✅ ランキング 保存完了")

if __name__ == "__main__":
    main()