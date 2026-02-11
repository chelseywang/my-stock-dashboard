import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. 頁面設定 ---
st.set_page_config(layout="wide", page_title="AI 操盤戰情室", page_icon="📈")

# --- 2. 高度鎖定與極簡化 CSS ---
st.markdown("""
    <style>
    /* 1. 極大化縮減頂部空白 */
    .stApp {
        margin-top: -60px; /* 強制將整體內容往上拉 */
    }
    .main .block-container {
        padding-top: 0rem !important; /* 移除容器上方內距 */
        padding-bottom: 0rem !important;
        height: 100vh;
        overflow: hidden;
    }
    
    /* 2. 標題區塊高度優化 */
    .terminal-header {
        margin-top: 10px;
        margin-bottom: -15px; /* 縮減與下方指標的距離 */
        color: #FF9800;
        font-family: 'Courier New', Courier, monospace;
        font-weight: bold;
    }

    /* 3. 背景與側邊欄 (專業琥珀橘) */
    .main { background-color: #0F0F0F; }
    section[data-testid="stSidebar"] {
        background-color: #FF9800 !important;
        border-right: 1px solid #000000;
    }
    section[data-testid="stSidebar"] * { color: #000000 !important; }

    /* 4. 指標卡片 (緊湊型) */
    div[data-testid="stMetric"] {
        background-color: #FF9800;
        border: 1px solid #000000;
        padding: 5px 12px !important;
        border-radius: 2px;
        box-shadow: 3px 3px 0px #000000;
    }
    div[data-testid="stMetric"] * { color: #000000 !important; }

    /* 5. AI 回應區 (固定高度捲軸) */
    .ai-response-box {
        height: 380px;
        overflow-y: auto;
        background: #1A1A1A;
        border: 1px solid #333;
        border-left: 4px solid #FF9800;
        padding: 15px;
        color: #E0E0E0;
        font-size: 0.85rem;
        line-height: 1.6;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 側邊欄 ---
with st.sidebar:
    st.markdown("### 🖥️ COMMAND")
    ticker = st.text_input("TICKER", value="NBIS").upper()
    timeframe = st.selectbox("TIMEFRAME", ["1d", "1h", "15m"])
    st.markdown("---")
    my_cost = st.number_input("COST", value=0.0, format="%.2f")
    pos_direction = st.radio("SIDE", ["Long", "Short"], horizontal=True)

# --- 4. 數據抓取 ---
@st.cache_data(ttl=300)
def get_data(ticker, tf):
    try:
        df = yf.Ticker(ticker).history(period="6mo" if tf=="1d" else "1mo", interval=tf)
        if df.empty: return None
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        return df
    except: return None

# --- 5. 主畫面 ---
if ticker:
    df = get_data(ticker, timeframe)
    if df is not None:
        last = df.iloc[-1]
        
        # 使用自定義 Class 將標題往上拉
        st.markdown(f"<h2 class='terminal-header'>{ticker} // TERMINAL ANALYTICS</h2>", unsafe_allow_html=True)
        
        # 指標列
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("PRICE", f"${last['Close']:.2f}")
        m2.metric("VOL", f"{last['Volume']/1000000:.1f}M")
        m3.metric("EMA20", f"${last['EMA20']:.2f}")
        m4.metric("POSITION", "MONITOR" if my_cost == 0 else f"{pos_direction}")

        col_left, col_right = st.columns([2.6, 1])

        with col_left:
            # 圖表高度固定在 550，確保不超出視窗
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.8, 0.2])
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                increasing_line_color='#FF9800', increasing_fillcolor='#FF9800',
                decreasing_line_color='#555555', decreasing_fillcolor='#121212'
            ), row=1, col=1)
            
            fig.update_layout(
                template="plotly_dark", height=550,
                margin=dict(l=0, r=0, t=0, b=0),
                xaxis_rangeslider_visible=False,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        with col_right:
            st.markdown("<p style='color:#FF9800; font-weight:bold; margin-top:10px;'>🤖 AI ANALYST</p>", unsafe_allow_html=True)
            if st.button("EXECUTE ANALYSIS", use_container_width=True):
                pass
            
            # AI 文本區塊
            st.markdown("""
                <div class="ai-response-box">
                    <strong>[READY]</strong> 終端已連線。正在監控 <strong>{ticker}</strong> 價格行為。<br><br>
                    <strong>策略建議：</strong><br>
                    目前的支撐位在 ${support}。如果價格維持在 EMA20 之上，多頭動能將持續。<br><br>
                    <strong>風險提示：</strong><br>
                    近期波動率 (ATR) 增加，建議縮小倉位或調寬止損。
                </div>
            """.format(ticker=ticker, support=round(last['Close']*0.95, 2)), unsafe_allow_html=True)

    else:
        st.error("Ticker not found.")
