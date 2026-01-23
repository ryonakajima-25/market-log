import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import data_manager
from datetime import datetime, timedelta

def calculate_technical_indicators(df):
    """テクニカル指標（移動平均、RSI）を計算する"""
    df = df.copy()
    
    # 移動平均線 (SMA)
    df['SMA_Short'] = df['Close'].rolling(window=5).mean()
    df['SMA_Mid'] = df['Close'].rolling(window=25).mean()
    df['SMA_Long'] = df['Close'].rolling(window=75).mean()
    
    # RSI (14日)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df

def plot_candlestick_chart(df, name, code):
    """Plotlyを使って高機能チャートを描画する"""
    
    # 1. 表示期間を「半年前〜今日」にフィルタリング
    end_date = df['Date'].max()
    start_date = end_date - pd.DateOffset(months=6) # 厳密に6ヶ月前
    
    display_df = df[df['Date'] >= start_date].copy()
    
    # データが空の場合のガード
    if display_df.empty:
        st.warning("表示期間内のデータがありません")
        return

    # 日付を文字列に変換（土日詰め表示のため）
    display_df['DateStr'] = display_df['Date'].dt.strftime('%Y-%m-%d')
    
    # 2. 「毎月最初の営業日」を特定する（X軸の目盛り用）
    display_df['YM'] = display_df['Date'].dt.to_period('M')
    first_biz_days = display_df.groupby('YM')['DateStr'].min().tolist()
    
    # 【修正】目盛りのラベルを作成（最初の月だけ空文字にする）
    tick_text_labels = []
    for i, date_val in enumerate(first_biz_days):
        if i == 0:
            tick_text_labels.append("") # 左端（一番古い月）は文字を表示しない
        else:
            # 日付文字列 (YYYY-MM-DD) から MM/DD だけ抽出して短く表示しても良いが
            # ここではYYYY-MM-DDのまま（または好みで短縮可）
            tick_text_labels.append(date_val)
    
    # 3段構成のサブプロット
    fig = make_subplots(
        rows=3, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.05, 
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=("", "出来高", "RSI(14)")
    )

    # --- 1段目: ローソク足と移動平均線 ---
    fig.add_trace(go.Candlestick(
        x=display_df['DateStr'],
        open=display_df['Open'], high=display_df['High'],
        low=display_df['Low'], close=display_df['Close'],
        name="株価",
        increasing_line_color='#FF4136',
        decreasing_line_color='#2ECC40'
    ), row=1, col=1)

    # 移動平均線
    fig.add_trace(go.Scatter(x=display_df['DateStr'], y=display_df['SMA_Short'], name="短期(5日)", line=dict(color='yellow', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=display_df['DateStr'], y=display_df['SMA_Mid'], name="中期(25日)", line=dict(color='orange', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=display_df['DateStr'], y=display_df['SMA_Long'], name="長期(75日)", line=dict(color='cyan', width=1)), row=1, col=1)

    # --- 2段目: 出来高 ---
    colors = ['#FF4136' if row['Open'] < row['Close'] else '#2ECC40' for i, row in display_df.iterrows()]
    fig.add_trace(go.Bar(
        x=display_df['DateStr'], y=display_df['TradingValue'],
        name="売買代金",
        marker_color=colors
    ), row=2, col=1)

    # --- 3段目: RSI ---
    fig.add_trace(go.Scatter(x=display_df['DateStr'], y=display_df['RSI'], name="RSI", line=dict(color='#BA68C8', width=2)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#888888", row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#888888", row=3, col=1)

    # --- レイアウト調整 ---
    fig.update_layout(
        title=dict(text=f"{name} ({code}) 日足チャート", font=dict(size=20, color="#F0F0F0")),
        height=800,
        xaxis_rangeslider_visible=False,
        showlegend=True,
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor='#1e1e1e',
        paper_bgcolor='#1e1e1e',
        font=dict(color='#F0F0F0'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    # 3. X軸の設定（グリッド線は維持しつつ、最初の文字だけ消す）
    fig.update_xaxes(
        type='category', 
        tickmode='array',        
        tickvals=first_biz_days,   # グリッド線を引きたい場所（全月）
        ticktext=tick_text_labels, # 表示したい文字（最初は空文字）
        gridcolor='#444444',
        showgrid=True,           
        tickangle=0              
    )
    
    # Y軸の設定
    fig.update_yaxes(gridcolor='#444444', showgrid=True, zerolinecolor='#666666')
    fig.update_yaxes(title_text="株価", row=1, col=1)
    fig.update_yaxes(title_text="売買代金", showticklabels=False, row=2, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=3, col=1)

    st.plotly_chart(fig, use_container_width=True)


def render(api_key):
    st.title("📊 銘柄分析")
    
    df_list = data_manager.fetch_company_list(api_key)
    options = []
    
    if not df_list.empty:
        for index, row in df_list.iterrows():
            code = str(row.get('Code', ''))
            name = str(row.get('CompanyName', ''))
            d_code = code[:-1] if len(code)==5 and code.endswith('0') else code
            options.append(f"{d_code}: {name}")
    else:
        st.warning("銘柄リストの取得に失敗しました。リロードしてください。")
    
    st.markdown("##### 🔍 銘柄検索")
    selected = st.selectbox("銘柄選択", [""] + options, index=0, placeholder="コードまたは名称...", label_visibility="collapsed")

    if selected:
        try:
            code_str, name = selected.split(": ", 1)
        except:
            return
        
        df_price, err_p = data_manager.fetch_real_data(code_str, api_key)
        
        tab1, tab2, tab3 = st.tabs(["📈 チャート・業績", "📋 財務詳細", "🏦 投資家動向"])
        
        with tab1:
            st.markdown(f"### {name} ({code_str})")
            
            if df_price is not None:
                latest = df_price.iloc[-1]
                close = int(latest['Close'])
                val = int(latest.get('TradingValue', 0))
                
                diff = 0
                diff_pct = 0.0
                if len(df_price) >= 2:
                    prev = df_price.iloc[-2]
                    diff = close - int(prev['Close'])
                    if prev.get('TradingValue', 0) > 0:
                        diff_pct = ((val - prev['TradingValue']) / prev['TradingValue']) * 100
                
                c1, c2 = st.columns([1, 1.5])
                c1.metric("終値", f"¥{close:,}", f"{diff:+,} 円")
                
                col = "#D32F2F" if diff_pct >= 0 else "#1976D2"
                arr = "↑" if diff_pct >= 0 else "↓"
                c2.markdown(f"<div style='font-size:1.8em; font-weight:bold'>¥{val:,}</div>", unsafe_allow_html=True)
                c2.markdown(f"<span style='color:{col}'>{arr} 前日比 {diff_pct:+.1f}%</span>", unsafe_allow_html=True)
                
                st.divider()
                
                df_calc = calculate_technical_indicators(df_price)
                plot_candlestick_chart(df_calc, name, code_str)
                
            else:
                st.warning("株価データがありません")

        with tab2:
            df_fin, err_f = data_manager.fetch_financial_data(code_str, api_key)
            if df_fin is not None and df_price is not None:
                fin = df_fin.copy()
                fin['PER'] = None
                fin['PBR'] = None
                prices = df_price.set_index('Date')['Close']
                
                for i, r in fin.iterrows():
                    try: p = prices.asof(r['開示日'])
                    except: p = None
                    if pd.notna(p):
                        if r.get('EPS',0) > 0: fin.at[i,'PER'] = p / r['EPS']
                        if r.get('BPS',0) > 0: fin.at[i,'PBR'] = p / r['BPS']
                
                fin['開示日'] = fin['開示日'].dt.strftime('%Y-%m-%d')
                view = fin[['開示日','売上高','営業利益','経常利益','PER','PBR']]
                
                st.dataframe(
                    view.style.format({
                        '売上高': "¥{:,.0f}", '営業利益': "¥{:,.0f}", '経常利益': "¥{:,.0f}",
                        'PER': "{:.1f}倍", 'PBR': "{:.2f}倍"
                    }, na_rep="-"),
                    hide_index=True, width='stretch'
                )
            elif err_f:
                st.warning(f"財務データエラー: {err_f}")
            elif df_fin is not None:
                st.dataframe(df_fin, width='stretch')
        
        with tab3:
            st.subheader("🏦 投資家動向 (週次)")
            df_inv, err_i = data_manager.fetch_investor_type_data(code_str, api_key)
            if df_inv is not None:
                def get_val(row, keys):
                    for k in keys: 
                        if k in row: return float(row[k])
                    return 0.0
                
                plot_data = []
                for _, row in df_inv.iterrows():
                    d = row.get('Date') or row.get('PublishedDate')
                    f_net = get_val(row, ['BrokerageForeignersPurchases', 'ForeignPurchases']) - get_val(row, ['BrokerageForeignersSales', 'ForeignSales'])
                    i_net = get_val(row, ['BrokerageIndividualsPurchases', 'IndividualPurchases']) - get_val(row, ['BrokerageIndividualsSales', 'IndividualSales'])
                    plot_data.append({'Date':d, '海外(差引)': f_net/100000000, '個人(差引)': i_net/100000000})
            
                df_plot = pd.DataFrame(plot_data).set_index('Date').sort_index()
                st.bar_chart(df_plot, color=["#FF4B4B", "#1f77b4"])
                st.caption("※ 単位: 億円")
            else:
                st.info("この銘柄の投資部門別データはありません")