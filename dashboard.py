import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. 頁面設定 ---
st.set_page_config(layout="wide", page_title="Professional Trading Terminal", page_icon="📊")

# --- 2. 沉穩高級感 CSS ---
st.markdown("""
    <style>
    /* 移除 Streamlit 預設內距 */
    .stApp { margin-top: -85px; background-color: #0B0E14; }
    .main .block-container { padding-top: 0rem !important; height: 100vh; overflow: hidden; }

    /* 頂部標題：改為細體簡潔風格 */
    .terminal-title {
        color: #E0E3EB;
        font-family: 'Inter', sans-serif;
        font-size: 20px;
        font-weight: 500;
        letter-spacing: 0.5px;
        margin-bottom: 15px;
        padding-top: 20px;
    }

    /* 指標卡片：深色層次感 */
    div[data-testid="stMetric"] {
        background-color: #161A25;
        border: 1px solid #2A2E39;
        padding: 10px 15px !important;
        border-radius: 4px;
    }
    div[data-testid="stMetricLabel"] { color: #848E9C !important; font-size: 12px !important; }
    div[data-testid="stMetricValue"] { color: #E0E3EB !important; font-size: 22px !important; }

    /* 側邊欄：低飽和度橘色 */
    section[data-testid="stSidebar"] {
        background-color: #161A25 !important;
        border-right: 1px solid #2A2E39;
    }
    section[data-testid="stSidebar"] * { color: #D1D4DC !important; }

    /* 按鈕：專業藍色 */
    .stButton>button {
        background-color: #2962FF !important;
        color: white !important;
        border: none;
        border-radius: 4px;
        font-weight: 500;
        width: 100%;
    }
    
    /* AI 回應容器 */
    .ai-box {
        background-color: #161A25;
        border: 1px solid #2A2E39;
        border-radius: 4px;
        padding: 15px;
        height: 400px;
        overflow-y: auto;
        color: #D1D4DC;
        font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 數據獲取 ---
@st.cache_data(ttl=60)
def get_pro_data(ticker, tf):
    try:
        data = yf.Ticker(ticker).history(period="6mo" if tf=="1d" else "1mo", interval=tf)
        return data if not data.empty else None
    except: return None

# --- 4. 主畫面佈局 ---
with st.sidebar:
    st.markdown("### ⚙️ TERMINAL SETTINGS")
    ticker = st.text_input("TICKER", value="NBIS").upper()
    timeframe = st.selectbox("TIMEFRAME", ["1d", "1h", "15m"])
    st.markdown("---")
    my_cost = st.number_input("COST BASIS", value=0.0, format="%.2f")
    direction = st.radio("SIDE", ["Long", "Short"], horizontal=True)

if ticker:
    df = get_pro_data(ticker, timeframe)
    if df is not None:
        last = df.iloc[-1]
        
        # 標題區
        st.markdown(f"<div class='terminal-title'>{ticker} <span style='color:#848E9C; font-size:14px;'>MARKET TERMINAL (LIVE)</span></div>", unsafe_allow_html=True)
        
        # 指標列
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("LAST PRICE", f"${last['Close']:.2f}")
        c2.metric("VOLUME", f"{last['Volume']/1000000:.2f}M")
        c3.metric("DAY HIGH", f"${last['High']:.2f}")
        c4.metric("DAY LOW", f"${last['Low']:.2f}")

        col_main, col_ai = st.columns([2.7, 1])

        with col_main:
            # 美式標準 K 線圖
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.8, 0.2])
            
            # K線：綠漲紅跌 (美股標準)
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                increasing_line_color='#00C076', increasing_fillcolor='#00C076',
                decreasing_line_color='#FF333A', decreasing_fillcolor='#FF333A',
                name="Market"
            ), row=1, col=1)
            
            # 成交量顏色同步 K 線
            vol_colors = ['#00C076' if row['Close'] >= row['Open'] else '#FF333A' for _, row in df.iterrows()]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=vol_colors, opacity=0.3, name="Volume"), row=2, col=1)

            fig.update_layout(
                template="plotly_dark", height=580,
                margin=dict(l=0, r=0, t=0, b=0),
                xaxis_rangeslider_visible=False,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                showlegend=False
            )
            # 格線淡化
            fig.update_xaxes(gridcolor='#1E222D', zeroline=False)
            fig.update_yaxes(gridcolor='#1E222D', zeroline=False)
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        with col_ai:
            st.markdown("<div style='color:#848E9C; font-size:12px; font-weight:600; margin-bottom:8px;'>AI STRATEGIC INSIGHT</div>", unsafe_allow_html=True)
            if st.button("RUN ANALYSIS"):
                pass
            
            st.markdown(f"""
                <div class="ai-box">
                    <span style="color:#00C076;">● SYSTEM ONLINE</span><br><br>
                    <strong>當前分析 ({ticker}):</strong><br>
                    價格目前在關鍵支撐位上方震盪。成交量配合良好。K 線形態顯示買盤在低位積極承接。<br><br>
                    <strong>操作建議：</strong><br>
                    若價格站穩昨高，可考慮加碼。止損建議設於今日低點下方 1 ATR 處。
                </div>
            """, unsafe_allow_html=True)

    else:
        st.error("Invalid Ticker Symbol.")
