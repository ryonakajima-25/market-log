import pandas as pd
import requests
from datetime import datetime, timedelta
import time
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

# --- 設定 ---
API_KEY = os.getenv("JQUANTS_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
BASE_URL_V2 = "https://api.jquants.com/v2"

# ▼▼▼ 今回の変更点：取得する期間を日付で指定 ▼▼▼
# 20250811まで完了しているので、その前日「20250810」からスタート
START_DATE_STR = "20250810" 
# どこまで遡るか（5年前の目安）
END_DATE_STR   = "20210101"
# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

def get_db_engine():
    return create_engine(DATABASE_URL)

def fetch_daily_data(date_str):
    """指定日の全銘柄データを取得"""
    headers = {"x-api-key": API_KEY}
    url = f"{BASE_URL_V2}/equities/bars/daily?date={date_str}"
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            res_json = res.json()
            data = res_json.get("daily_quotes", []) or res_json.get("data", [])
            if len(data) > 0:
                return pd.DataFrame(data)
        elif res.status_code in [400, 404]:
            return None
    except Exception as e:
        print(f"  DailyFetch Error: {e}")
    return None

def fetch_company_list(date_str):
    """その時点の銘柄一覧を取得"""
    headers = {"x-api-key": API_KEY}
    url = f"{BASE_URL_V2}/equities/master?date={date_str}"
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            res_json = res.json()
            data = res_json.get("equities", []) or res_json.get("info", []) or res_json.get("data", [])
            
            if len(data) > 0:
                df = pd.DataFrame(data)
                # 列名の読み替え
                if 'MktNm' in df.columns:
                    df = df.rename(columns={'MktNm': 'Market'})
                elif 'MarketCodeName' in df.columns:
                    df = df.rename(columns={'MarketCodeName': 'Market'})
                elif 'Section' in df.columns:
                    df = df.rename(columns={'Section': 'Market'})
                
                if 'Code' in df.columns and 'Market' in df.columns:
                    return df[['Code', 'Market']]
    except:
        pass
    return pd.DataFrame()

def main():
    # 日付計算
    try:
        start_dt = datetime.strptime(START_DATE_STR, "%Y%m%d")
        end_dt = datetime.strptime(END_DATE_STR, "%Y%m%d")
        today = datetime.now()
        
        # 今日から見て「何日前から」「何日前まで」やるかを計算
        start_offset = (today - start_dt).days
        end_offset = (today - end_dt).days
        
        if start_offset < 0:
            print("⚠️ 開始日が未来になっています。設定を確認してください。")
            return
            
    except ValueError as e:
        print(f"❌ 日付の形式が間違っています (YYYYMMDDで指定してください): {e}")
        return

    print(f"🚀 バッチ処理再開: {START_DATE_STR} から {END_DATE_STR} まで遡ります")
    print("⏳ API制限(60req/min)を守るため、ゆっくり実行します...")
    
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            pass
    except Exception as e:
        print(f"\n❌ DB接続エラー: {e}")
        return

    # 指定期間ループ（start_offset から end_offset まで）
    for i in range(start_offset, end_offset + 1):
        target_date = today - timedelta(days=i)
        
        # 土日スキップ
        if target_date.weekday() >= 5:
            continue

        date_str = target_date.strftime("%Y%m%d")
        print(f"\n📅 処理中: {date_str}", end=" ", flush=True)

        # 1. データ取得
        df_quotes = fetch_daily_data(date_str)
        if df_quotes is None or df_quotes.empty:
            print("→ ❌ データなし", end="", flush=True)
            time.sleep(1.0) 
            continue

        # 2. 銘柄リスト取得
        df_list = fetch_company_list(date_str)
        if df_list.empty:
            print("→ ⚠️ 銘柄リストなし(スキップ)", end="", flush=True)
            time.sleep(1.0)
            continue

        # 3. データ結合・整形
        df = pd.merge(df_quotes, df_list, on='Code', how='left')
        df['Date'] = pd.to_datetime(df['Date'])
        
        if 'Va' in df.columns:
            df['TradingValue'] = pd.to_numeric(df['Va'], errors='coerce').fillna(0)
        elif 'TradingValue' in df.columns:
            df['TradingValue'] = pd.to_numeric(df['TradingValue'], errors='coerce').fillna(0)

        df['Market'] = df['Market'].fillna('Others')
        def normalize_market(m):
            m = str(m)
            if "Prime" in m or "プライム" in m: return "Prime"
            if "Standard" in m or "スタンダード" in m: return "Standard"
            if "Growth" in m or "グロース" in m: return "Growth"
            return "Others"
        df['NormMarket'] = df['Market'].apply(normalize_market)

        # 4. DBへ保存
        try:
            with engine.connect() as conn:
                conn.execute(text(f"DELETE FROM market_history WHERE \"Date\" = '{target_date.strftime('%Y-%m-%d')}'"))
                conn.commit()

            market_summary = df.groupby(['Date', 'NormMarket'])['TradingValue'].sum().reset_index()
            market_summary.to_sql('market_history', engine, if_exists='append', index=False)
            print("→ ✅ 保存完了", end="", flush=True)
            
        except Exception as e:
            print(f"→ ❌ 保存エラー: {e}", end="", flush=True)

        # API制限対策ウェイト
        time.sleep(2.2)

if __name__ == "__main__":
    main()