import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. 頁面設定 ---
st.set_page_config(layout="wide", page_title="AI 操盤戰情室", page_icon="📈")

# --- 2. 注入專業高度鎖定與配色 CSS ---
st.markdown("""
    <style>
    /* 移除多餘間距，鎖定 100vh 高度 */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        height: 100vh;
        overflow: hidden;
    }
    
    /* 背景配色：深碳黑 */
    .main {
        background-color: #121212;
    }
    
    /* 側邊欄：專業橘黃 + 黑字 */
    section[data-testid="stSidebar"] {
        background-color: #FF9800 !important;
        border-right: 1px solid #222222;
    }
    section[data-testid="stSidebar"] * {
        color: #000000 !important;
    }

    /* 指標卡片：縮小尺寸以適應一頁佈局 */
    div[data-testid="stMetric"] {
        background-color: #FF9800;
        border: 1px solid #000000;
        padding: 5px 15px !important;
        border-radius: 4px;
        box-shadow: 4px 4px 0px #000000;
    }
    div[data-testid="stMetric"] * {
        color: #000000 !important;
    }
    
    /* AI 回應區：限制高度並允許滾動 */
    .ai-response-container {
        height: 350px;
        overflow-y: auto;
        background: #1e1e1e;
        border-left: 3px solid #FF9800;
        padding: 15px;
        font-size: 0.9rem;
    }

    /* 按鈕：黑底橘字 */
    .stButton>button {
        background-color: #000000 !important;
        color: #FF9800 !important;
        border: 1px solid #000000;
        border-radius: 2px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 側邊欄控制 ---
with st.sidebar:
    st.markdown("### 🛠️ SYSTEM COMMAND")
    ticker = st.text_input("TICKER", value="NBIS").upper()
    timeframe = st.selectbox("TIMEFRAME", ["1d", "1h", "15m"])
    st.markdown("---")
    my_cost = st.number_input("COST", value=0.0, format="%.2f")
    pos_direction = st.radio("SIDE", ["Long", "Short"], horizontal=True)

# --- 4. 數據與主畫面 ---
def get_data(ticker, tf):
    try:
        df = yf.Ticker(ticker).history(period="6mo" if tf=="1d" else "1mo", interval=tf)
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        return df
    except: return None

if ticker:
    df = get_data(ticker, timeframe)
    if df is not None:
        last = df.iloc[-1]
        
        # 標題區
        st.markdown(f"<h2 style='color: #FF9800; margin: 0;'>{ticker} // TERMINAL ANALYTICS</h2>", unsafe_allow_html=True)
        
        # 頂部指標區 (縮小間距)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("PRICE", f"${last['Close']:.2f}")
        m2.metric("VOLATILITY", f"{last['High']-last['Low']:.2f}")
        m3.metric("RVOL", "1.24x") # 範例數據
        m4.metric("STATUS", "MONITORING")

        col_chart, col_ai = st.columns([2.5, 1])

        with col_chart:
            # 調整圖表高度，確保不產生捲軸
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.8, 0.2])
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                increasing_line_color='#FF9800', increasing_fillcolor='#FF9800',
                decreasing_line_color='#444444', decreasing_fillcolor='#121212'
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], line=dict(color='#FFFFFF', width=1), name='EMA20'), row=1, col=1)
            
            fig.update_layout(
                template="plotly_dark", height=500, # 固定高度
                margin=dict(l=0, r=0, t=0, b=0),
                xaxis_rangeslider_visible=False,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        with col_ai:
            st.markdown("<p style='color: #FF9800; margin-bottom: 5px;'>🤖 AI STRATEGY</p>", unsafe_allow_html=True)
            if st.button("RUN DIAGNOSTIC"):
                pass
            
            # 使用自定義容器讓回應區可滾動，不撐開視窗
            st.markdown("""
                <div class="ai-response-container">
                    <strong>[系統提示]</strong> 正在掃描市場結構...<br><br>
                    <strong>🐢 中長線策略:</strong><br>
                    目前的趨勢維持在 EMA50 之上，屬於健康回測。建議在 $88.5 附近分批佈局。絕對防守位設於 $85.2。<br><br>
                    <strong>⚡️ 短線佈局:</strong><br>
                    RSI 顯示超賣，短期有反彈需求。關注前高壓力和日內爆量結點。
                </div>
            """, unsafe_allow_html=True)

    else:
        st.error("Invalid Ticker.")
