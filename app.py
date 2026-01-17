import streamlit as st
import jquantsapi
import pandas as pd
from datetime import datetime

# ページ設定
st.set_page_config(page_title="market-log", page_icon="📈", layout="wide")

st.title("📊 market-log (V2)")

# J-Quants API ログイン (V2対応)
@st.cache_resource
def get_api_client():
    # V2では mail/password ではなく api_key のみで初期化
    api_key = st.secrets["JQUANTS_API_KEY"]
    cli = jquantsapi.Client(api_key=api_key)
    return cli

cli = get_api_client()

# データ取得関数 (V2対応)
@st.cache_data(ttl=3600)
def fetch_stock_data(code):
    # V2のエンドポイントを使用して日足データを取得
    # codeは "8058" のような4桁でOKになりました（以前の5桁指定が不要に）
    df = cli.get_prices_daily_quotes(code=code)
    
    if df.empty:
        return None
        
    # 最新の1行を取得
    latest = df.iloc[-1]
    return latest

# 表示する銘柄の設定
target_stocks = {
    "3350": "メタプラネット",
    "8058": "三菱商事"
}

# ダッシュボード表示
cols = st.columns(len(target_stocks))

for col, (code, name) in zip(cols, target_stocks.items()):
    try:
        data = fetch_stock_data(code)
        
        if data is not None:
            with col:
                st.subheader(f"{name} ({code})")
                m_col1, m_col2 = st.columns(2)
                # V2ではカラム名が分かりやすくなっている場合があります
                # (以前の 'Close' はそのまま維持されています)
                m_col1.metric("終値", f"¥{data['Close']:,}")
                m_col2.metric("始値", f"¥{data['Open']:,}")
                
                with st.expander("詳細データ"):
                    st.write(f"**高値:** ¥{data['High']:,}")
                    st.write(f"**安値:** ¥{data['Low']:,}")
                    st.write(f"**出来高:** {data['Volume']:,} 株")
        else:
            col.warning(f"{name}のデータが見つかりませんでした")
                
    except Exception as e:
        col.error(f"{name}の取得エラー")
        st.sidebar.error(f"Error ({code}): {e}")

st.sidebar.caption(f"API V2 Connection: Active")