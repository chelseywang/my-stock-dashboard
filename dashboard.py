import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

# --- 1. 頁面設定 ---
st.set_page_config(layout="wide", page_title="AI 操盤戰情室", page_icon="🟡")

# --- 注入亮黃色調 CSS ---
st.markdown("""
    <style>
    /* 全域背景 */
    .main {
        background-color: #0b0d11;
        color: #e0e0e0;
    }
    
    /* 側邊欄改為亮黃色點綴 */
    section[data-testid="stSidebar"] {
        background-color: #14171c;
        border-right: 2px solid #fee75c;
    }
    
    /* 卡片設計：亮黃邊框 + 玻璃效果 */
    div[data-testid="stMetric"] {
        background: rgba(254, 231, 92, 0.05);
        border: 1px solid rgba(254, 231, 92, 0.3);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8);
        transition: transform 0.2s ease-in-out;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        border: 1px solid #fee75c;
    }

    /* 指標標題顏色 */
    div[data-testid="stMetricLabel"] {
        color: #fee75c !important;
        font-weight: bold !important;
        letter-spacing: 1px;
    }

    /* 按鈕：亮黃滿版感 */
    .stButton>button {
        width: 100%;
        background-color: #fee75c;
        color: #000000;
        font-weight: bold;
        border: none;
        border-radius: 10px;
        padding: 0.6rem;
        box-shadow: 0 4px 15px rgba(254, 231, 92, 0.2);
    }
    .stButton>button:hover {
        background-color: #fff1a8;
        box-shadow: 0 0 20px rgba(254, 231, 92, 0.5);
        color: #000000;
    }

    /* 文字輸入與下拉選單 */
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        background-color: #1c2026 !important;
        color: white !important;
        border: 1px solid #3d444d !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 數據抓取 (延用邏輯) ---
def get_stock_data(ticker, timeframe):
    try:
        period = "6mo" if timeframe == "1d" else "1mo"
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=timeframe)
        if df.empty: return None, None
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        tr = pd.concat([df['High']-df['Low'], (df['High']-df['Close'].shift()).abs(), (df['Low']-df['Close'].shift()).abs()], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        df['AvgVol'] = df['Volume'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['AvgVol']
        return df, stock
    except: return None, None

# --- 側邊欄控制 ---
with st.sidebar:
    st.markdown("<h1 style='color: #fee75c;'>COMMAND</h1>", unsafe_allow_html=True)
    ticker = st.text_input("標的代碼", value="NBIS").upper()
    timeframe = st.selectbox("圖表週期", ["1d", "1h", "15m"])
    st.markdown("---")
    my_cost = st.number_input("成本價", value=0.0, format="%.2f")
    position_type = st.radio("倉位方向", ["Long", "Short"], horizontal=True)
    selected_model = st.selectbox("AI 核心", ["gemini-1.5-flash", "gemini-pro"])

# --- 主畫面顯示 ---
if ticker:
    df, _ = get_stock_data(ticker, timeframe)
    
    if df is not None:
        last = df.iloc[-1]
        pct_change = ((last['Close'] - df.iloc[-2]['Close']) / df.iloc[-2]['Close']) * 100

        # 頂部大標與指標
        st.markdown(f"<h1 style='color: white;'>{ticker} <span style='color: #fee75c;'>TERMINAL</span></h1>", unsafe_allow_html=True)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("CURRENT PRICE", f"${last['Close']:.2f}", f"{pct_change:.2f}%")
        c2.metric("VOL RATIO (RVOL)", f"{last['RVOL']:.2f}x")
        c3.metric("ATR VOLATILITY", f"{last['ATR']:.2f}")
        
        if my_cost > 0:
            pnl = (last['Close'] - my_cost) / my_cost * 100 if position_type == "Long" else (my_cost - last['Close']) / my_cost * 100
            c4.metric("UNREALIZED P/L", f"{pnl:.2f}%")
        else:
            c4.metric("POSITION", "IDLE")

        col_main, col_ai = st.columns([2.5, 1])

        with col_main:
            # 圖表美化：配合黃色調
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.75, 0.25])
            
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                increasing_line_color='#fee75c', increasing_fillcolor='#fee75c',
                decreasing_line_color='#404040', decreasing_fillcolor='#404040',
                name="Price"
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], line=dict(color='#ffffff', width=1.5), name='EMA20'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA50'], line=dict(color='#fee75c', width=1.5, dash='dash'), name='EMA50'), row=1, col=1)
            
            # 成交量
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color='#333333', name='Vol', opacity=0.8), row=2, col=1)
            
            fig.update_layout(
                template="plotly_dark",
                height=650,
                margin=dict(l=0, r=0, t=0, b=0),
                xaxis_rangeslider_visible=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color="#fee75c")
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_ai:
            st.markdown("<h3 style='color: #fee75c;'>AI ADVISOR</h3>", unsafe_allow_html=True)
            if st.button("EXECUTE ANALYSIS"):
                st.info("💡 正在生成亮黃色調的精簡策略建議...")
                # 這裡調用原有的 ask_gemini_strategy 邏輯即可
            
            with st.container(border=True):
                st.caption("Chat with AI")
                st.chat_input("Ask a question...")

    else:
        st.error("Invalid Ticker.")
