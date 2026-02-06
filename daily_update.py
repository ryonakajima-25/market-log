import pandas as pd
import requests
from datetime import datetime
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# .envファイルを読み込む（ローカル実行用。GitHub ActionsではSecretsから読まれます）
load_dotenv()

# --- 設定 ---
API_KEY = os.getenv("JQUANTS_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
BASE_URL_V2 = "https://api.jquants.com/v2"

def get_db_engine():
    return create_engine(DATABASE_URL)

def fetch_daily_data(date_str):
    """当日の全銘柄データを取得"""
    headers = {"x-api-key": API_KEY}
    url = f"{BASE_URL_V2}/equities/bars/daily?date={date_str}"
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            res_json = res.json()
            data = res_json.get("daily_quotes", []) or res_json.get("data", [])
            if len(data) > 0:
                return pd.DataFrame(data)
        else:
            print(f"  ⚠️ API Status: {res.status_code} {res.text[:50]}")
    except Exception as e:
        print(f"  Fetch Error: {e}")
    return None

def fetch_company_list(date_str):
    """当日の銘柄一覧を取得"""
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
    # 1. 今日の日付を取得 (JST前提)
    # GitHub ActionsのサーバーはUTCなので、日本時間に合わせるために9時間足す処理が必要ですが、
    # 実行タイミング（17:00 JST）でスクリプトが動くなら、その時点の日付を使えばOKです。
    # ※厳密にJSTにするため、ここでは timezone を意識したほうが安全ですが、
    # 簡易的に UTC+9時間 を意識して実装します。
    
    from datetime import timezone, timedelta
    JST = timezone(timedelta(hours=9))
    now = datetime.now(JST)

    # 2. 土日チェック (月=0, ..., 金=4, 土=5, 日=6)
    if now.weekday() >= 5:
        print("☕ 今日は土日なので処理をスキップします")
        return

    date_str = now.strftime("%Y%m%d")
    print(f"🚀 デイリー処理開始: {date_str}")
    
    # DB接続チェック
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            pass
    except Exception as e:
        print(f"❌ DB接続エラー: {e}")
        return

    # 3. データ取得
    df_quotes = fetch_daily_data(date_str)
    if df_quotes is None or df_quotes.empty:
        print("❌ 本日のデータはまだ配信されていないか、休場日です。")
        return

    # 4. 銘柄リスト取得
    df_list = fetch_company_list(date_str)
    if df_list.empty:
        print("⚠️ 銘柄リスト取得失敗")
        return

    # 5. 結合・整形
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

    # 6. DBへ保存
    try:
        with engine.connect() as conn:
            # 重複防止のため、一旦その日のデータを消す
            conn.execute(text(f"DELETE FROM market_history WHERE \"Date\" = '{now.strftime('%Y-%m-%d')}'"))
            conn.commit()

        # 保存
        market_summary = df.groupby(['Date', 'NormMarket'])['TradingValue'].sum().reset_index()
        market_summary.to_sql('market_history', engine, if_exists='append', index=False)
        print("✅ 本日のデータ保存完了！")
        
    except Exception as e:
        print(f"❌ 保存エラー: {e}")

if __name__ == "__main__":
    main()