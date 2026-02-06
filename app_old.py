import streamlit as st
import os
from views import stock_analysis, market_analysis

# CSS読み込み
def local_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        pass

st.set_page_config(page_title="market-log", layout="wide")
local_css("style.css")

# サイドバー (ここを入れ替えました)
st.sidebar.title("MENU")
page = st.sidebar.radio("機能を選択", ["市場分析 (Light)", "銘柄分析"])

# APIキー
# APIキー読み込み（Renderの環境変数 または ローカルのsecrets.toml）
API_KEY = os.getenv("JQUANTS_API_KEY")
if not API_KEY and "JQUANTS_API_KEY" in st.secrets:
    API_KEY = st.secrets["JQUANTS_API_KEY"]

if not API_KEY:
    st.error("APIキーが設定されていません。RenderのEnvironment Variablesを設定してください。")
    st.stop()
# ルーティング
if page == "市場分析 (Light)":
    market_analysis.render(API_KEY)
elif page == "銘柄分析":
    stock_analysis.render(API_KEY)