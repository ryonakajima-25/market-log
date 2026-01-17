import streamlit as st
import jquantsapi
import pandas as pd
from datetime import datetime, timedelta

st.title("📊 market-log")

@st.cache_resource
def get_api_client():
    api_key = st.secrets["JQUANTS_API_KEY"]
    # V2のAPIキーをリフレッシュトークンとして渡す
    cli = jquantsapi.Client(refresh_token=api_key)
    return cli

cli = get_api_client()

# データ取得関数
@st.cache_data(ttl=3600)
def fetch_stock_data(code):
    try:
        # 土日の取得エラーを防ぐため、直近1週間のデータを取得し、その一番新しいものを出す
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        # V2では4桁または5桁。念のため5桁(末尾0)も試せるように
        # まずは4桁でリクエスト
        df = cli.get_prices_daily_quotes(
            code=code, 
            from_str=start_date.strftime("%Y-%m-%d"),
            to_str=end_date.strftime("%Y-%m-%d")
        )
        
        if df.empty:
            return None, "データが空です（市場休業日の可能性があります）"
            
        return df.iloc[-1], None
    except Exception as e:
        return None, str(e)

# 銘柄設定（V2仕様：4桁で試してダメなら5桁に自動変換するロジックをループ内で対応）
target_stocks = {"3350": "メタプラネット", "8058": "三菱商事"}

cols = st.columns(len(target_stocks))

for col, (code, name) in zip(cols, target_stocks.items()):
    # 4桁で試す
    data, err = fetch_stock_data(code)
    
    # 4桁でダメなら5桁（末尾に0）で再トライ
    if data is None:
        data, err = fetch_stock_data(code + "0")
    
    with col:
        if data is not None:
            # 取得成功時の表示
            st.metric(f"{name} ({code})", f"¥{data['Close']:,}")
            st.caption(f"日付: {data['Date']}")
        else:
            # 失敗時の原因表示
            st.error(f"{name}の取得失敗")
            st.caption(f"原因: {err}")

# デバッグ用：生データを確認したい場合
if st.sidebar.checkbox("デバッグ情報を表示"):
    st.sidebar.write("API接続テスト中...")
    try:
        # 試しに日経平均(99840)などのデータを1件だけ取ってみる
        test_df = cli.get_prices_daily_quotes(code="80580")
        st.write(test_df.tail(3))
    except Exception as e:
        st.write(f"APIテストエラー: {e}")