import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. 頁面設定 ---
st.set_page_config(layout="wide", page_title="AI 操盤戰情室", page_icon="📈")

# --- 2. 修正後的「清晰終端」CSS ---
st.markdown("""
    <style>
    /* 1. 徹底消除頂部大留白 */
    .stApp { margin-top: -95px; background-color: #0b0e11; }
    .main .block-container { padding-top: 0rem !important; height: 100vh; overflow: hidden; }

    /* 2. 側邊欄：深橘色調 (不刺眼但清晰) */
    section[data-testid="stSidebar"] {
        background-color: #1a1c22 !important;
        border-right: 2px solid #f39c12;
    }
    section[data-testid="stSidebar"] * { color: #f39c12 !important; font-weight: 500; }
    
    /* 3. 標題：高亮橘黃色，位置極致往上 */
    .terminal-header {
        color: #f39c12;
        font-family: 'Inter', sans-serif;
        font-size: 24px;
        font-weight: 800;
        margin-bottom: 10px;
        padding-top: 25px;
        text-transform: uppercase;
    }

    /* 4. 指標卡片：深色背景 + 明亮文字 */
    div[data-testid="stMetric"] {
        background-color: #1e222d;
        border: 1px solid #363a45;
        padding: 10px 15px !important;
        border-radius: 4px;
    }
    div[data-testid="stMetricLabel"] { color: #848e9c !important; font-size: 13px !important; }
    div[data-testid="stMetricValue"] { color: #ffffff !important; font-size: 26px !important; font-weight: 700 !important; }

    /* 5. AI 回應區：高對比白字 */
    .ai-response-box {
        height: 400px;
        overflow-y: auto;
        background: #161a25;
        border-left: 4px solid #f39c12;
        padding: 15px;
        color: #ffffff; /* 確保字體是全白 */
        font-size: 15px;
        line-height: 1.6;
    }

    /* 6. 按鈕：琥珀色黑字 */
    .stButton>button {
        background-color: #f39c12 !important;
        color: #000000 !important;
        border: none;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 側邊欄控制 ---
with st.sidebar:
    st.markdown("### 🖥️ SYSTEM COMMAND")
    ticker = st.text_input("TICKER", value="NBIS").upper()
    timeframe = st.selectbox("TIMEFRAME", ["1d", "1h", "15m"])
    st.markdown("---")
    my_cost = st.number_input("COST", value=0.0, format="%.2f")
    direction = st.radio("SIDE", ["Long", "Short"], horizontal=True)

# --- 4. 數據抓取 ---
@st.cache_data(ttl=60)
def get_clean_data(ticker, tf):
    try:
        df = yf.Ticker(ticker).history(period="6mo" if tf=="1d" else "1mo", interval=tf)
        if df.empty: return None
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        return df
    except: return None

# --- 5. 主畫面佈局 ---
if ticker:
    df = get_clean_data(ticker, timeframe)
    if df is not None:
        last = df.iloc[-1]
        
        # 標題
        st.markdown(f"<div class='terminal-header'>{ticker} // TERMINAL ANALYTICS</div>", unsafe_allow_html=True)
        
        # 指標
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("LAST PRICE", f"${last['Close']:.2f}")
        c2.metric("VOLUME", f"{last['Volume']/1000000:.1f}M")
        c3.metric("EMA20", f"${last['EMA20']:.2f}")
        c4.metric("POSITION", "IDLE" if my_cost == 0 else direction)

        col_l, col_r = st.columns([2.6, 1])

        with col_l:
            # 圖表：美股標準綠漲紅跌
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.8, 0.2])
            
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                increasing_line_color='#26a69a', increasing_fillcolor='#26a69a', # 美股綠
                decreasing_line_color='#ef5350', decreasing_fillcolor='#ef5350', # 美股紅
                name="Market"
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], line=dict(color='#f39c12', width=1.5), name='EMA20'), row=1, col=1)

            fig.update_layout(
                template="plotly_dark", height=580,
                margin=dict(l=0, r=0, t=0, b=0),
                xaxis_rangeslider_visible=False,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color="#ffffff") # 圖表字體全白
            )
            fig.update_xaxes(gridcolor='#1e222d')
            fig.update_yaxes(gridcolor='#1e222d')
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        with col_r:
            st.markdown("<p style='color:#f39c12; font-weight:bold; margin-top:15px;'>🤖 STRATEGIC INSIGHT</p>", unsafe_allow_html=True)
            if st.button("RUN AI DIAGNOSIS"):
                pass
            
            # AI 文本容器 (高對比白字)
            st.markdown(f"""
                <div class="ai-response-box">
                    <b style="color:#f39c12;">[SYSTEM READY]</b> 正在監控 <b>{ticker}</b>...<br><br>
                    目前的 K 線形態呈現標準美式分佈。
                    <br><br>
                    <b>● 技術指標：</b><br>
                    EMA20 目前位於 ${last['EMA20']:.2f}。
                    <br><br>
                    <b>● 策略核心：</b><br>
                    趨勢仍屬強勁，若價格守住支撐位，建議繼續抱緊處理。
                </div>
            """, unsafe_allow_html=True)
    else:
        st.error("TICKER NOT FOUND.")
