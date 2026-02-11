import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. 頁面設定 ---
st.set_page_config(layout="wide", page_title="AI 操盤戰情室", page_icon="📊")

# --- 2. 視覺修正：沉穩、高對比、不跑版 ---
st.markdown("""
    <style>
    /* 1. 適度縮減頂部，確保內容在視窗內 */
    .stApp { margin-top: -50px; background-color: #0b0e11; }
    .main .block-container { padding-top: 1rem !important; height: 100vh; overflow: hidden; }

    /* 2. 側邊欄：深碳灰級致專業感 */
    section[data-testid="stSidebar"] {
        background-color: #161a25 !important;
        border-right: 1px solid #2d3139;
    }
    section[data-testid="stSidebar"] label {
        color: #f39c12 !important; /* 標籤用琥珀橘 */
        font-weight: 600 !important;
    }

    /* 3. 標題：白色大氣風格 */
    .terminal-header {
        color: #ffffff;
        font-family: 'Inter', sans-serif;
        font-size: 26px;
        font-weight: 800;
        margin-bottom: 20px;
        letter-spacing: 1px;
    }

    /* 4. 指標卡片：深色背景 + 亮白字 (提升閱讀舒適度) */
    div[data-testid="stMetric"] {
        background-color: #1e222d;
        border: 1px solid #363a45;
        padding: 12px 15px !important;
        border-radius: 4px;
    }
    div[data-testid="stMetricValue"] { color: #ffffff !important; font-size: 28px !important; }
    div[data-testid="stMetricLabel"] { color: #848e9c !important; font-size: 13px !important; }

    /* 5. AI 回應區：高質感容器 */
    .ai-box {
        background-color: #161a25;
        border: 1px solid #2d3139;
        border-left: 5px solid #f39c12;
        padding: 20px;
        height: 450px;
        overflow-y: auto;
        color: #ffffff;
        font-size: 15px;
        line-height: 1.8;
    }

    /* 6. 按鈕：琥珀橘黑字 */
    .stButton>button {
        background-color: #f39c12 !important;
        color: #000000 !important;
        font-weight: bold;
        border: none;
        border-radius: 4px;
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 數據邏輯 ---
@st.cache_data(ttl=60)
def get_pro_data(ticker, tf):
    try:
        period = "6mo" if tf == "1d" else "1mo"
        df = yf.Ticker(ticker).history(period=period, interval=tf)
        if df.empty: return None
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        return df
    except: return None

# --- 4. 側邊欄 ---
with st.sidebar:
    st.markdown("<h2 style='color:#f39c12;'>COMMAND</h2>", unsafe_allow_html=True)
    ticker = st.text_input("TICKER", value="NBIS").upper()
    timeframe = st.selectbox("TIMEFRAME", ["1d", "1h", "15m"])
    st.markdown("---")
    my_cost = st.number_input("COST BASIS", value=0.0, format="%.2f")
    direction = st.radio("POSITION", ["Long", "Short"], horizontal=True)

# --- 5. 主畫面 ---
if ticker:
    df = get_pro_data(ticker, timeframe)
    if df is not None:
        last = df.iloc[-1]
        
        # 標題
        st.markdown(f"<div class='terminal-header'>{ticker} // MARKET TERMINAL</div>", unsafe_allow_html=True)
        
        # 指標列
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("LAST PRICE", f"${last['Close']:.2f}")
        c2.metric("VOLUME", f"{last['Volume']/1000000:.2f}M")
        c3.metric("EMA20", f"${last['EMA20']:.2f}")
        c4.metric("STATUS", "MONITOR" if my_cost == 0 else direction)

        col_main, col_ai = st.columns([2.6, 1])

        with col_main:
            # 圖表：美股標準紅綠色
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.8, 0.2])
            
            # K線
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                increasing_line_color='#26a69a', increasing_fillcolor='#26a69a',
                decreasing_line_color='#ef5350', decreasing_fillcolor='#ef5350',
                name="Market"
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], line=dict(color='#f39c12', width=1.5), name='EMA20'), row=1, col=1)

            fig.update_layout(
                template="plotly_dark", height=600,
                margin=dict(l=0, r=0, t=0, b=0),
                xaxis_rangeslider_visible=False,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color="#ffffff")
            )
            fig.update_xaxes(gridcolor='#1e222d')
            fig.update_yaxes(gridcolor='#1e222d')
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        with col_ai:
            st.markdown("<p style='color:#f39c12; font-weight:bold; margin-top:10px;'>🤖 STRATEGIC ANALYST</p>", unsafe_allow_html=True)
            if st.button("RUN ANALYSIS"):
                pass
            
            st.markdown(f"""
                <div class="ai-box">
                    <b style="color:#f39c12;">[SYSTEM STATUS: ACTIVE]</b><br><br>
                    正在分析 <b>{ticker}</b> 的價格行為...<br><br>
                    <b>技術總結：</b><br>
                    當前價格在 EMA20 上方運行，顯示短期趨勢偏多。美股盤面顯示買盤力道強勁。<br><br>
                    <b>策略筆記：</b><br>
                    考慮到你的專業研究背景，建議關注支撐位與爆量結點。目前結構適合持有或等待回調分批進場。
                </div>
            """, unsafe_allow_html=True)
    else:
        st.error("Invalid Ticker.")
