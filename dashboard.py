import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. 頁面設定 ---
st.set_page_config(layout="wide", page_title="AI 操盤戰情室", page_icon="📊")

# --- 2. 核心視覺：深碳灰 + 美股配色 + 頂部壓縮 ---
st.markdown("""
    <style>
    /* 1. 徹底消滅頂部留白，將內容往上推 */
    .stApp { margin-top: -95px; background-color: #0b0e11; }
    .main .block-container { padding-top: 0rem !important; height: 100vh; overflow: hidden; }

    /* 2. 側邊欄改版：深碳灰專業風格 (取代大橘色) */
    section[data-testid="stSidebar"] {
        background-color: #161a25 !important;
        border-right: 1px solid #2d3139;
    }
    section[data-testid="stSidebar"] label {
        color: #848e9c !important; 
        font-size: 13px !important;
        font-weight: 600 !important;
    }
    section[data-testid="stSidebar"] h3 {
        color: #f39c12 !important;
        font-family: 'Courier New', monospace;
    }

    /* 3. 標題：簡潔高白 */
    .terminal-header {
        color: #ffffff;
        font-family: 'Inter', sans-serif;
        font-size: 24px;
        font-weight: 700;
        margin-bottom: 12px;
        padding-top: 35px;
        text-transform: uppercase;
    }

    /* 4. 指標卡片：黑字橘底 (高級對比) */
    div[data-testid="stMetric"] {
        background-color: #f39c12;
        border: 1px solid #000000;
        padding: 8px 15px !important;
        border-radius: 2px;
        box-shadow: 4px 4px 0px #000000;
    }
    div[data-testid="stMetricValue"] { color: #000000 !important; font-weight: 800 !important; font-size: 24px !important; }
    div[data-testid="stMetricLabel"] { color: #000000 !important; opacity: 0.8; font-size: 12px !important; }

    /* 5. AI 回應區：固定高度與高對比文字 */
    .ai-box {
        background-color: #161a25;
        border-left: 4px solid #f39c12;
        border-radius: 0px 4px 4px 0px;
        padding: 15px;
        height: 420px;
        overflow-y: auto;
        color: #ffffff;
        font-size: 14px;
        line-height: 1.6;
    }

    /* 6. 按鈕：黑底橘字專業按鈕 */
    .stButton>button {
        background-color: #000000 !important;
        color: #f39c12 !important;
        border: 1px solid #f39c12 !important;
        border-radius: 2px;
        font-weight: bold;
        width: 100%;
        text-transform: uppercase;
    }
    .stButton>button:hover {
        background-color: #f39c12 !important;
        color: #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 數據邏輯 (支援美股週期) ---
@st.cache_data(ttl=60)
def get_pro_data(ticker, tf):
    try:
        # 根據 29 歲投資研究員的專業需求，提供足夠的回測長度
        period = "6mo" if tf == "1d" else "1mo"
        df = yf.Ticker(ticker).history(period=period, interval=tf)
        if df.empty: return None
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        return df
    except: return None

# --- 4. 側邊欄設定 ---
with st.sidebar:
    st.markdown("### 🖥️ TERMINAL")
    ticker = st.text_input("TICKER", value="NBIS").upper()
    timeframe = st.selectbox("TIMEFRAME", ["1d", "1h", "15m"])
    st.markdown("---")
    my_cost = st.number_input("COST BASIS", value=0.0, format="%.2f")
    direction = st.radio("POSITION", ["Long", "Short"], horizontal=True)
    st.markdown("---")
    st.caption("AI Model: Gemini-1.5-Flash")

# --- 5. 主畫面佈局 ---
if ticker:
    df = get_pro_data(ticker, timeframe)
    if df is not None:
        last = df.iloc[-1]
        
        # 標題
        st.markdown(f"<div class='terminal-header'>{ticker} // REAL-TIME STRATEGY</div>", unsafe_allow_html=True)
        
        # 指標列
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("LAST PRICE", f"${last['Close']:.2f}")
        c2.metric("VOL (24H)", f"{last['Volume']/1000000:.2f}M")
        c3.metric("EMA 20", f"${last['EMA20']:.2f}")
        c4.metric("POSITION", "IDLE" if my_cost == 0 else f"{direction}")

        col_main, col_ai = st.columns([2.7, 1])

        with col_main:
            # 美股標準 K 線配色 (TradingView 風格)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.8, 0.2])
            
            # K線：綠漲紅跌 (#26a69a / #ef5350)
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                increasing_line_color='#26a69a', increasing_fillcolor='#26a69a',
                decreasing_line_color='#ef5350', decreasing_fillcolor='#ef5350',
                name="Price"
            ), row=1, col=1)
            
            # 均線點綴
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], line=dict(color='#f39c12', width=1), name='EMA20'), row=1, col=1)
            
            # 成交量
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color='#363a45', opacity=0.5), row=2, col=1)

            fig.update_layout(
                template="plotly_dark", height=580,
                margin=dict(l=0, r=0, t=0, b=0),
                xaxis_rangeslider_visible=False,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                showlegend=False
            )
            fig.update_xaxes(gridcolor='#1e222d', zeroline=False)
            fig.update_yaxes(gridcolor='#1e222d', zeroline=False)
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        with col_ai:
            st.markdown("<p style='color:#f39c12; font-weight:bold; font-size:12px; margin-top:10px;'>🤖 AI STRATEGIC ADVISOR</p>", unsafe_allow_html=True)
            if st.button("RUN ANALYSIS"):
                pass
            
            # AI 建議區
            st.markdown(f"""
                <div class="ai-box">
                    <span style="color:#26a69a;">● STATUS: MONITORING</span><br><br>
                    <b>[技術面診斷]</b><br>
                    {ticker} 在 {timeframe} 週期中顯示出強烈的支撐力道。EMA20 目前位於 ${last['EMA20']:.2f}。
                    <br><br>
                    <b>[操作建議]</b><br>
                    考慮到你的專業研究背景，此標的正處於 SMC 結構的修正區。建議觀察成交量是否在支撐位放大。
                    <br><br>
                    <b>[止損警告]</b><br>
                    若價格跌破今日低點，建議立即執行診斷。
                </div>
            """, unsafe_allow_html=True)
    else:
        st.error("TICKER NOT FOUND.")
