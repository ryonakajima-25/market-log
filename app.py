import streamlit as st

# アプリの一番最初に書く必要があります
st.set_page_config(
    page_title="MarketLog | 株式投資分析",
    page_icon="📈",
    layout="wide" # ワイドレイアウトにするとモダンな印象になります
)

# ヘッダー部分
st.title("📊 MarketLog")
st.caption("スマートな投資判断のためのマーケットログ・ダッシュボード")

# センス良く見せるためのカスタムCSS
st.markdown("""
    <style>
    /* メイン背景のカスタマイズ */
    .stApp {
        background-color: #f8f9fa; /* 薄いグレーで目に優しく */
    }
    /* タイトルの文字色変更 */
    h1 {
        color: #1E3A8A; /* 濃いネイビーで信頼感を演出 */
        font-family: 'Helvetica Neue', Arial, sans-serif;
    }
    /* サイドバーのカスタマイズ */
    .css-1d391kg {
        background-color: #1E3A8A;
    }
    </style>
    """, unsafe_allow_html=True)