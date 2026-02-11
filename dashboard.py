import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json

# --- 1. 頁面設定 ---
st.set_page_config(layout="wide", page_title="AI 操盤戰情室", page_icon="💎")

# --- 注入高級感 CSS (解決跑版與字體清晰度問題) ---
st.markdown("""
    <style>
    /* 1. 徹底消滅頂部留白，確保不捲動 */
    .stApp { margin-top: -85px; background-color: #0b0e11; }
    .main .block-container { padding-top: 0rem !important; height: 100vh; overflow: hidden; }

    /* 2. 側邊欄：深碳灰級致專業感 */
    section[data-testid="stSidebar"] {
        background-color: #161a25 !important;
        border-right: 1px solid #2d3139;
    }
    section[data-testid="stSidebar"] label {
        color: #f39c12 !important; 
        font-weight: 600 !important;
    }

    /* 3. 標題區：高亮白字，不撞頂 */
    .terminal-title {
        color: #ffffff;
        font-family: 'Inter', sans-serif;
        font-size: 24px;
        font-weight: 800;
        margin-bottom: 10px;
        padding-top: 30px;
        text-transform: uppercase;
    }

    /* 4. 指標卡片：琥珀橘背景 + 黑字 (高讀取度) */
    div[data-testid="stMetric"] {
        background-color: #f39c12;
        border: 1px solid #000000;
        padding: 8px 15px !important;
        border-radius: 4px;
        box-shadow: 3px 3px 0px #000000;
    }
    div[data-testid="stMetricValue"] { color: #000000 !important; font-size: 24px !important; font-weight: 800 !important; }
    div[data-testid="stMetricLabel"] { color: #000000 !important; opacity: 0.8; font-size: 12px !important; }

    /* 5. AI 回應區：深色容器 + 亮白字 */
    .ai-box {
        background-color: #161a25;
        border: 1px solid #2d3139;
        border-left: 5px solid #f39c12;
        padding: 15px;
        height: 400px;
        overflow-y: auto;
        color: #ffffff;
        font-size: 15px;
        line-height: 1.7;
    }

    /* 6. 按鈕：黑底橘字專業風格 */
    .stButton>button {
        background-color: #000000 !important;
        color: #f39c12 !important;
        border: 1px solid #f39c12 !important;
        border-radius: 4px;
        font-weight: 800;
        width: 100%;
        text-transform: uppercase;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #f39c12 !important;
        color: #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 模型與策略函數 (保持原邏輯) ---
def list_available_models():
    if not API_KEY: return ["Error: No API Key"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            valid_models = [m['name'].replace('models/', '') for m in data.get('models', []) 
                           if 'generateContent' in m.get('supportedGenerationMethods', [])]
            return valid_models
        return [f"Error: {response.status_code}"]
    except: return ["Error: Connection Failed"]

def ask_gemini_strategy(prompt, model_name):
    if not API_KEY: return "❌ 請先設定 API Key"
    system_instruction = """你現在是專業資深交易員。請用冷靜、專業、直白的方式回答。
    必須包含：### 🐢 中長線策略、### ⚡️ 短線佈局、### 💡 總結建議。"""
    final_prompt = f"{system_instruction}\n\n{prompt}"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": final_prompt}]}]}, timeout=60)
        return res.json()['candidates'][0]['content']['parts'][0]['text']
    except: return "❌ 分析失敗，請稍後再試。"

def get_stock_data(ticker, timeframe):
    try:
        period = "6mo" if timeframe == "1d" else "1mo"
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=timeframe)
        if df.empty: return None, None
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        df['AvgVol'] = df['Volume'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['AvgVol']
        tr = pd.concat([df['High']-df['Low'], (df['High']-df['Close'].shift()).abs(), (df['Low']-df['Close'].shift()).abs()], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        return df, stock
    except: return None, None

# --- 3. 側邊欄 ---
with st.sidebar:
    st.markdown("<h2 style='color:#f39c12; font-family:monospace;'>COMMAND</h2>", unsafe_allow_html=True)
    ticker = st.text_input("輸入標的代碼", value="NBIS").upper()
    timeframe = st.selectbox("圖表週期", ["1d", "1h", "15m"])
    st.markdown("---")
    st.subheader("🛡️ 持倉診斷")
    my_cost = st.number_input("成本價", value=0.0, format="%.2f")
    position_type = st.radio("倉位方向", ["Long", "Short"], horizontal=True)
    st.markdown("---")
    model_list = st.session_state.get('models', ['gemini-1.5-flash', 'gemini-pro'])
    selected_model = st.selectbox("AI 核心引擎", model_list)

# --- 4. 主畫面 ---
if ticker:
    df, stock_info = get_stock_data(ticker, timeframe)
    if df is not None:
        last = df.iloc[-1]
        prev = df.iloc[-2]
        change_pct = ((last['Close'] - prev['Close']) / prev['Close']) * 100
        
        # 標題
        st.markdown(f"<div class='terminal-title'>{ticker} // MARKET TERMINAL ANALYTICS</div>", unsafe_allow_html=True)

        # 指標列
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("當前市價", f"${last['Close']:.2f}", f"{change_pct:.2f}%")
        c2.metric("RVOL 成交量比", f"{last['RVOL']:.2f}x")
        c3.metric("ATR 波動率", f"{last['ATR']:.2f}")
        if my_cost > 0:
            pnl = (last['Close'] - my_cost) / my_cost * 100 if position_type == "Long" else (my_cost - last['Close']) / my_cost * 100
            c4.metric("目前損益", f"{pnl:.2f}%")
        else:
            c4.metric("持倉狀態", "觀望中")

        col_main, col_ai = st.columns([2.6, 1])

        with col_main:
            # 圖表：美股標準綠漲紅跌配色
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.8, 0.2])
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                name="行情", increasing_line_color='#26a69a', increasing_fillcolor='#26a69a',
                decreasing_line_color='#ef5350', decreasing_fillcolor='#ef5350'
            ), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], line=dict(color='#ffffff', width=1), name='EMA20'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA50'], line=dict(color='#f39c12', width=1, dash='dot'), name='EMA50'), row=1, col=1)
            
            # 成交量
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color='#363a45', opacity=0.5, name='成交量'), row=2, col=1)
            
            fig.update_layout(
                template="plotly_dark", height=580, margin=dict(l=0, r=0, t=0, b=0),
                xaxis_rangeslider_visible=False, paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)', showlegend=False
            )
            fig.update_xaxes(gridcolor='#1e222d', zeroline=False)
            fig.update_yaxes(gridcolor='#1e222d', zeroline=False)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        with col_ai:
            st.markdown("<p style='color:#f39c12; font-weight:bold; font-size:12px; margin-top:10px;'>🤖 AI STRATEGIC ADVISOR</p>", unsafe_allow_html=True)
            btn_label = "🛡️ 執行持倉診斷" if my_cost > 0 else "🚀 尋找進場機會"
            if st.button(btn_label):
                ctx = f"標的:{ticker}, 現價:{last['Close']:.2f}, 成本:{my_cost}, 方向:{position_type}, ATR:{last['ATR']:.2f}"
                with st.spinner("正在生成戰術建議..."):
                    res = ask_gemini_strategy(ctx, selected_model)
                    st.markdown(f"<div class='ai-box'>{res}</div>", unsafe_allow_html=True)

            st.markdown("---")
            if chat_q := st.chat_input("詢問 AI 關於此標的的細節..."):
                with st.chat_message("user"): st.write(chat_q)
                with st.chat_message("assistant"):
                    st.write(ask_gemini_strategy(f"現價:{last['Close']}, 問題:{chat_q}", selected_model))
    else:
        st.error("❌ 無法獲取數據，請檢查代碼。")
