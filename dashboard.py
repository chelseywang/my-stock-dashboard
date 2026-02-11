import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json

# --- 1. 頁面設定 ---
st.set_page_config(layout="wide", page_title="AI 操盤戰情室", page_icon="💎")

# --- 2. 注入視覺優化 CSS ---
st.markdown("""
    <style>
    /* 1. 全域空間優化 */
    .stApp { margin-top: -70px; background-color: #f1f4f9; }
    .main .block-container { padding-top: 0rem !important; height: 100vh; overflow: hidden; }

    /* 2. 側邊欄：深藍雙色分層 */
    section[data-testid="stSidebar"] {
        background-color: #1a237e !important;
        border-right: 1px solid #0d1240;
    }
    
    /* 3. 強制輸入框文字為黑色 (解決填寫字體不清晰問題) */
    input, div[data-baseweb="select"] > div {
        color: #000000 !important;
        background-color: #ffffff !important;
    }

    /* 4. 側邊欄文字優化 */
    section[data-testid="stSidebar"] label { color: #ffffff !important; font-weight: 500 !important; }
    section[data-testid="stSidebar"] h2 { color: #ffffff !important; margin-bottom: 5px; }

    /* 5. 擴大後的 AI 診斷容器 */
    .ai-response-box {
        background-color: #ffffff;
        border-left: 6px solid #1a237e;
        padding: 25px;
        height: 580px; /* 增加高度以對齊圖表 */
        overflow-y: auto;
        color: #334155;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
        font-size: 16px; /* 稍微放大字體更易讀 */
    }
    
    .stButton>button {
        background-color: #1a237e !important;
        color: #ffffff !important;
        border-radius: 8px;
        width: 100%;
        font-weight: 600;
        padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 核心邏輯 (維持原功能不變) ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    API_KEY = ""
    st.sidebar.warning("⚠️ 請設定 API_KEY")

def list_available_models():
    if not API_KEY: return ["Error: No API Key"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return [m['name'].replace('models/', '') for m in data.get('models', []) 
                    if 'generateContent' in m.get('supportedGenerationMethods', [])]
        return [f"Error: {response.status_code}"]
    except: return ["Error: Connection"]

def ask_gemini_strategy(prompt, model_name):
    if not API_KEY: return "❌ 請先設定 API Key"
    system_instruction = """你現在是我的專屬投資顧問。請用最直白的方式回答：### 🐢 中長線策略、### ⚡️ 短線佈局、--- 💡 總結建議。"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": f"{system_instruction}\n\n數據:\n{prompt}"}]}]}, timeout=120)
        return res.json()['candidates'][0]['content']['parts'][0]['text']
    except: return "❌ 分析失敗。"

def get_stock_data(ticker, timeframe):
    try:
        df = yf.Ticker(ticker).history(period="6mo" if timeframe == "1d" else "1mo", interval=timeframe)
        if df.empty: return None, None
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['AvgVol'] = df['Volume'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['AvgVol']
        tr = pd.concat([df['High']-df['Low'], (df['High']-df['Close'].shift()).abs(), (df['Low']-df['Close'].shift()).abs()], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        return df, yf.Ticker(ticker)
    except: return None, None

# --- 3. 側邊欄 ---
with st.sidebar:
    st.markdown("## ⚙️ 系統設定")
    ticker = st.text_input("TICKER", value="NBIS").upper()
    timeframe = st.selectbox("圖表週期", ["1d", "1h", "15m"])
    
    if API_KEY and st.button("🔄 重整可用模型"):
        found = list_available_models()
        if found and not found[0].startswith("Error"):
            st.session_state['models'] = found
    model_list = st.session_state.get('models', ['gemini-1.5-flash', 'gemini-pro'])
    selected_model = st.selectbox("AI 核心引擎", model_list)

    st.markdown("<br><div style='border-top: 1px solid rgba(255,255,255,0.2);'></div><br>", unsafe_allow_html=True)
    st.markdown("## 🛡️ 持倉診斷")
    c1, c2 = st.columns(2)
    with c1:
        my_cost = st.number_input("成本價", value=0.0, format="%.2f")
    with c2:
        position_type = st.selectbox("方向", ["Long", "Short"])

# --- 4. 主畫面佈局優化 ---
if ticker:
    df, _ = get_stock_data(ticker, timeframe)
    if df is not None:
        last = df.iloc[-1]
        change_pct = ((last['Close'] - df.iloc[-2]['Close']) / df.iloc[-2]['Close']) * 100
        
        st.markdown(f"<h1 style='color: #1a237e; padding-top: 30px;'>{ticker} / 操盤實時戰情</h1>", unsafe_allow_html=True)

        # 指標卡片
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("當前市價", f"${last['Close']:.2f}", f"{change_pct:.2f}%")
        m2.metric("RVOL", f"{last['RVOL']:.2f}x")
        m3.metric("ATR", f"{last['ATR']:.2f}")
        m4.metric("損益狀態", f"{((last['Close']-my_cost)/my_cost*100 if position_type=='Long' else (my_cost-last['Close'])/my_cost*100):.2f}%" if my_cost>0 else "觀望")

        st.markdown("<br>", unsafe_allow_html=True)
        
        # 重新分配欄位比例：增加右側寬度
        col_main, col_ai = st.columns([1.8, 1])

        with col_main:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線",
                                         increasing_line_color='#26a69a', decreasing_line_color='#ef5350'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], line=dict(color='#1a237e', width=1.5), name='EMA20'), row=1, col=1)
            vol_colors = ['#26a69a' if c >= o else '#ef5350' for c, o in zip(df['Close'], df['Open'])]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=vol_colors, opacity=0.4), row=2, col=1)
            fig.update_layout(template="plotly_white", height=600, margin=dict(l=0, r=0, t=0, b=0), xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        with col_ai:
            st.markdown("<p style='color:#1a237e; font-weight:bold; font-size:18px;'>🤖 AI 顧問戰術報告</p>", unsafe_allow_html=True)
            if st.button("🚀 生成即時分析報告"):
                with st.spinner("正在進行深度結構分析..."):
                    res = ask_gemini_strategy(f"標的:{ticker}, 價:{last['Close']:.2f}, 本:{my_cost}, 向:{position_type}", selected_model)
                    st.markdown(f"<div class='ai-response-box'>{res}</div>", unsafe_allow_html=True)
    else:
        st.error("代碼錯誤，無法抓取數據。")

