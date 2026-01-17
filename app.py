import streamlit as st
import jquantsapi
import pandas as pd

st.title("📊 market-log")

@st.cache_resource
def get_api_client():
    api_key = st.secrets["JQUANTS_API_KEY"]
    # 1.9.0 以前のライブラリでも V2 認証を通すための標準的な書き方
    # refresh_token 引数に APIキーを渡すことで動作する仕様になっています
    cli = jquantsapi.Client(refresh_token=api_key)
    return cli

cli = get_api_client()

# 以下、以前のデータ取得ロジック
@st.cache_data(ttl=3600)
def fetch_stock_data(code):
    try:
        # V2 では銘柄コードは 4 桁で取得可能
        df = cli.get_prices_daily_quotes(code=code)
        if df.empty:
            return None
        return df.iloc[-1]
    except Exception:
        return None

# 銘柄表示
target_stocks = {"3350": "メタプラネット", "8058": "三菱商事"}
cols = st.columns(len(target_stocks))

for col, (code, name) in zip(cols, target_stocks.items()):
    data = fetch_stock_data(code)
    if data is not None:
        with col:
            st.metric(f"{name} ({code})", f"¥{data['Close']:,}")
    else:
        col.error(f"{name}の取得失敗")