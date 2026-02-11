import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. 頁面設定 ---
st.set_page_config(layout="wide", page_title="AI 操盤戰情室", page_icon="🍊")

# --- 注入「橘黃背景 + 黑字」強對比 CSS ---
st.markdown("""
    <style>
    /* 全域背景 */
    .main {
        background-color: #111111;
    }
    
    /* 側邊欄：滿版橘黃 + 黑字 */
    section[data-testid="stSidebar"] {
        background-color: #FFB800 !important;
        border-right: 2px solid #000000;
    }
    section[data-testid="stSidebar"] * {
        color: #000000 !important;
        font-weight: 600 !important;
    }
    
    /* 指標卡片：亮橘黃背景 + 黑字 */
    div[data-testid="stMetric"] {
        background-color: #FFB800;
        border: 2px solid #000000;
        padding: 20px;
        border-radius: 0px; /* 方正風格更硬核 */
        box-shadow: 8px 8px 0px #000000; /* 復古陰影 */
    }
    
    /* 強制指標文字為黑色 */
    div[data-testid="stMetric"] * {
        color: #000000 !important;
    }

    /* 按鈕：黑底黃字 */
    .stButton>button {
        width: 100%;
        background-color: #000000 !important;
        color: #FFB800 !important;
        border: 2px solid #000000;
        border-radius: 0px;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    .stButton>button:hover {
        background-color: #333333 !important;
        box-shadow: 4px 4px 0px #FFB800;
    }

    /* 標題樣式 */
    h1, h2, h3 {
        color: #FFB800 !important;
        text-transform: uppercase;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 數據函數 ---
def get_stock_data(ticker, timeframe):
    try:
        period = "6mo" if timeframe == "1d" else "1mo"
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=timeframe)
        if df.empty: return None
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        tr = pd.concat([df['High']-df['Low'], (df['High']-df['Close'].shift()).abs(), (df['Low']-df['Close'].shift()).abs()], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        df['AvgVol'] = df['Volume'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['AvgVol']
        return df
    except: return None

# --- 側邊欄 ---
with st.sidebar:
    st.markdown("# ☢️ COMMAND")
    ticker = st.text_input("TICKER", value="NBIS").upper()
    timeframe = st.selectbox("TIMEFRAME", ["1d", "1h", "15m"])
    st.markdown("---")
    my_cost = st.number_input("COST BASIS", value=0.0, format="%.2f")
    position_type = st.radio("SIDE", ["Long", "Short"], horizontal=True)

# --- 主畫面 ---
if ticker:
    df = get_stock_data(ticker, timeframe)
    
    if df is not None:
        last = df.iloc[-1]
        pct = ((last['Close'] - df.iloc[-2]['Close']) / df.iloc[-2]['Close']) * 100

        st.markdown(f"<h1>{ticker} // SIGNAL TERMINAL</h1>", unsafe_allow_html=True)
        
        # 指標區
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("PRICE", f"${last['Close']:.2f}", f"{pct:.2f}%")
        c2.metric("RVOL", f"{last['RVOL']:.2f}x")
        c3.metric("ATR", f"{last['ATR']:.2f}")
        
        if my_cost > 0:
            pnl = (last['Close'] - my_cost) / my_cost * 100 if position_type == "Long" else (my_cost - last['Close']) / my_cost * 100
            c4.metric("P/L %", f"{pnl:.2f}%")
        else:
            c4.metric("STATUS", "NO POS")

        col_left, col_right = st.columns([2.5, 1])

        with col_left:
            # 圖表：黃黑配色
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.8, 0.2])
            
            # K線：上漲橘黃，下跌深灰/黑
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                increasing_line_color='#FFB800', increasing_fillcolor='#FFB800',
                decreasing_line_color='#555555', decreasing_fillcolor='#111111',
                name="Market"
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], line=dict(color='#FFFFFF', width=1), name='EMA20'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA50'], line=dict(color='#FFB800', width=1.5, dash='dot'), name='EMA50'), row=1, col=1)
            
            fig.update_layout(
                template="plotly_dark",
                height=600,
                margin=dict(l=0, r=0, t=0, b=0),
                xaxis_rangeslider_visible=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color="#FFB800")
            )
            fig.update_yaxes(gridcolor='#222222', zerolinecolor='#222222')
            fig.update_xaxes(gridcolor='#222222')
            
            st.plotly_chart(fig, use_container_width=True)

        with col_right:
            st.markdown("### 🤖 ANALYST BOT")
            if st.button("RUN DIAGNOSTIC"):
                st.warning("正在生成戰術分析...")
            
            st.markdown("<br>" * 2, unsafe_allow_html=True)
            st.text_area("NOTES", value="趨勢跟蹤中...", height=150)

    else:
        st.error("TICKER NOT FOUND.")
