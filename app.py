import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
import datetime

# .envファイルを読み込む
load_dotenv()

# --- 設定 ---
DATABASE_URL = os.getenv("DATABASE_URL")

# ページ設定
st.set_page_config(
    page_title="Market Log",
    page_icon="📊",
    layout="wide"
)

# --- データベース接続関数 ---
@st.cache_data(ttl=600)
def load_market_data():
    try:
        engine = create_engine(DATABASE_URL)
        query = 'SELECT * FROM market_history ORDER BY "Date"'
        df = pd.read_sql(query, engine)
        return df
    except Exception as e:
        st.error(f"データの読み込みに失敗しました: {e}")
        return pd.DataFrame()

# --- メイン画面 ---
def main():
    st.title("📊 市場別 売買代金推移")
    
    # 1. データ読み込み
    df = load_market_data()

    if df.empty:
        st.warning("📉 データが見つかりません。batch_save.py を実行してデータを蓄積してください。")
        return

    # 日付整形と単位変換
    df['Date'] = pd.to_datetime(df['Date'])
    df['Value_Oku'] = df['TradingValue'] / 100_000_000
    
    min_date = df['Date'].min().date()
    max_date = df['Date'].max().date()

    # --- 2. 表示設定エリア（画面上部） ---
    # 少し背景色をつけるなど区切りが明確になるよう container を使用
    with st.container():
        col1, col2 = st.columns([3, 1]) # 設定と再読み込みボタンを横に並べる
        
        with col1:
            # モード選択（横並びで表示）
            mode = st.radio(
                "📅 表示モード",
                ["直近10営業日 (デフォルト)", "日付で範囲指定"],
                index=0,
                horizontal=True
            )
            
            # フィルタリング処理
            filtered_df = pd.DataFrame()

            if mode == "直近10営業日 (デフォルト)":
                unique_dates = sorted(df['Date'].unique())
                if len(unique_dates) >= 10:
                    start_date = unique_dates[-10]
                    filtered_df = df[df['Date'] >= start_date]
                else:
                    filtered_df = df
            
            else: # "日付で範囲指定"
                default_start = max_date - datetime.timedelta(days=30)
                # 日付選択を下に出す
                date_range = st.date_input(
                    "期間を選択してください",
                    value=(default_start, max_date),
                    min_value=min_date,
                    max_value=max_date,
                    format="YYYY/MM/DD"
                )
                
                if len(date_range) == 2:
                    start_sel, end_sel = date_range
                    filtered_df = df[
                        (df['Date'].dt.date >= start_sel) & 
                        (df['Date'].dt.date <= end_sel)
                    ]
                else:
                    st.warning("終了日も選択してください")
                    filtered_df = df.tail(10 * 4)

        with col2:
            # 右端に再読み込みボタンを配置（少し余白をあけて下に下げる）
            st.write("") 
            st.write("")
            if st.button("🔄 データを更新"):
                st.cache_data.clear()
                st.rerun()

    st.divider() # 設定とグラフの間に区切り線

    # --- 3. グラフ表示エリア ---
    
    if filtered_df.empty:
        st.error("指定された期間のデータがありません。")
        return

    # グラフ用に日付を文字列化 (YYYY-MM-DD)
    filtered_df['DisplayDate'] = filtered_df['Date'].dt.strftime('%Y-%m-%d')

    chart_data = filtered_df.pivot(index='DisplayDate', columns='NormMarket', values='Value_Oku')

    market_colors = {
        "Prime": "#3366CC",    # 青
        "Standard": "#336633", # 緑
        "Growth": "#CC6633",   # オレンジ
        "Others": "#808080"    # グレー
    }

    markets_to_show = ["Prime", "Standard", "Growth", "Others"]
    available_markets = [m for m in markets_to_show if m in chart_data.columns]

    for market in available_markets:
        # 市場名タイトル
        st.subheader(f"■ {market}市場")
        
        # --- HTMLカスタム表示（前日比・色分け） ---
        market_series = chart_data[market]
        latest_val = market_series.iloc[-1]
        latest_date_str = market_series.index[-1]
        
        if len(market_series) >= 2:
            prev_val = market_series.iloc[-2]
            diff_pct = ((latest_val - prev_val) / prev_val) * 100
        else:
            diff_pct = 0.0

        if diff_pct > 0:
            diff_color = "#FF4B4B" # 赤
            diff_text = f"（前日比 +{diff_pct:.1f}%）"
        elif diff_pct < 0:
            diff_color = "#33CCFF" # 蛍光青
            diff_text = f"（前日比 {diff_pct:.1f}%）"
        else:
            diff_color = "#CCCCCC"
            diff_text = f"（前日比 ±0.0%）"

        st.markdown(f"""
        <div style="font-size: 14px; color: #888888; margin-bottom: -5px;">
            {latest_date_str} の売買代金
        </div>
        <div style="font-size: 32px; font-weight: bold;">
            {latest_val:,.0f} 億円
            <span style="font-size: 20px; color: {diff_color}; margin-left: 10px;">
                {diff_text}
            </span>
        </div>
        """, unsafe_allow_html=True)
        # ------------------------
        
        st.bar_chart(
            market_series,
            color=market_colors.get(market, "#808080"),
            height=250
        )
        st.divider()

    # 詳細データテーブル（一番下）
    with st.expander("📅 表示期間のデータ一覧を見る"):
        table_df = chart_data.sort_index(ascending=False)
        st.dataframe(
            table_df.style.format("{:,.0f}"),
            use_container_width=True
        )

if __name__ == "__main__":
    main()