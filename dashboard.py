import streamlit as st
import yfinance as yf
import pandas as pd 
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json

# --- 1. 頁面設定 ---
st.set_page_config(layout="wide", page_title="AI 操盤戰情室", page_icon="💎")

# --- 2. 注入最新參考圖示配色 CSS (深藍側邊欄 + 專業白底報告風) ---
st.markdown("""
    <style>
    /* 1. 頂部空間與整體背景 */
    .stApp { 
        margin-top: -70px; 
        background-color: #f1f4f9; /* 右側背景改為極淺灰藍，提升報告質感 */
    }
    .main .block-container { 
        padding-top: 0rem !important; 
        height: 100vh; 
        overflow: hidden; 
    }

    /* 2. 側邊欄：參考圖示的深藍色 (#213d91) + 純白文字 */
    section[data-testid="stSidebar"] {
        background-color: #213d91 !important; 
        border-right: 1px solid #1a3073;
    }
    /* 強制側邊欄所有文字與標籤改為純白 */
    section[data-testid="stSidebar"] * {
        color: #ffffff !important;
    }
    section[data-testid="stSidebar"] label {
        font-size: 14px !important;
        font-weight: 500 !important;
    }

    /* 3. 標題：深藍色調文字 */
    .terminal-title {
        color: #213d91;
        font-family: 'Inter', 'Noto Sans TC', sans-serif;
        font-size: 28px;
        font-weight: 800;
        margin-bottom: 15px;
        padding-top: 35px;
        letter-spacing: -0.5px;
    }

    /* 4. 指標卡片：參考圖示的白底藍框風格 */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e0e6ed;
        padding: 18px !important;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(33, 61, 145, 0.05);
    }
    div[data-testid="stMetricValue"] { 
        color: #213d91 !important; 
        font-size: 30px !important; 
        font-weight: 700 !important; 
    }
    div[data-testid="stMetricLabel"] { 
        color: #5c6b89 !important; 
        font-size: 14px !important; 
    }

    /* 5. AI 回應區：純白底色報告格式 */
    .ai-box {
        background-color: #ffffff;
        border: 1px solid #e0e6ed;
        border-left: 6px solid #213d91;
        padding: 25px;
        height: 480px;
        overflow-y: auto;
        color: #334155;
        font-size: 15px;
        line-height: 1.8;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    }

    /* 6. 按鈕：深藍配色優化 */
    .stButton>button {
        background-color: #213d91 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px;
        font-weight: 600;
        width: 100%;
        padding: 0.6rem;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #1a3073 !important;
        box-shadow: 0 4px 12px rgba(33, 61, 145, 0.3);
    }

    /* 分隔線顏色優化 */
    hr {
        border: 0;
        border-top: 1px solid #d1d9e6;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 核心功能邏輯 (維持原設定不改動) ---
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
    if not API_KEY: return "❌ 請設定 API Key"
    system_instruction = "你現在是專業資深交易員。請用冷靜、專業的方式回答：### 🐢 中長線策略、### ⚡️ 短線佈局、### 💡 總結建議。"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": f"{system_instruction}\n\n{prompt}"}]}]}, timeout=60)
        return res.json()['candidates'][0]['content']['parts'][0]['text']
    except: return "❌ 分析失敗。"

def get_stock_data(ticker, timeframe):
    try:
        df = yf.Ticker(ticker).history(period="6mo" if timeframe == "1d" else "1mo", interval=timeframe)
        if df.empty: return None, None
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        df['AvgVol'] = df['Volume'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['AvgVol']
        tr = pd.concat([df['High']-df['Low'], (df['High']-df['Close'].shift()).abs(), (df['Low']-df['Close'].shift()).abs()], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        return df, yf.Ticker(ticker)
    except: return None, None

# --- 3. 側邊欄 (深藍背景邏輯) ---
with st.sidebar:
    st.markdown("<h2 style='color:#ffffff; margin-bottom:0;'>⚙️ 操盤參數設定</h2>", unsafe_allow_html=True)
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
        change_pct = ((last['Close'] - df.iloc[-2]['Close']) / df.iloc[-2]['Close']) * 100
        
        st.markdown(f"<div class='terminal-title'>{ticker} 實時戰情分析 <span style='font-size:16px; font-weight:400; color:#5c6b89;'>{timeframe} 週期數據匯總</span></div>", unsafe_allow_html=True)

        # 指標區 (Metric Cards)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("當前市價", f"${last['Close']:.2f}", f"{change_pct:.2f}%")
        c2.metric("RVOL 成交量比", f"{last['RVOL']:.2f}x")
        c3.metric("ATR 波動率", f"{last['ATR']:.2f}")
        c4.metric("目前損益", f"{((last['Close']-my_cost)/my_cost*100 if position_type=='Long' else (my_cost-last['Close'])/my_cost*100):.2f}%" if my_cost>0 else "觀望中")

        st.markdown("<br>", unsafe_allow_html=True)

        col_main, col_ai = st.columns([2.8, 1])

        with col_main:
            # 圖表：專業白底配色 (Plotly White)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                name="行情", increasing_line_color='#26a69a', increasing_fillcolor='#26a69a',
                decreasing_line_color='#ef5350', decreasing_fillcolor='#ef5350'
            ), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], line=dict(color='#213d91', width=1.5), name='EMA20'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA50'], line=dict(color='#fa8c16', width=1.5, dash='dot'), name='EMA50'), row=1, col=1)
            
            vol_colors = ['#26a69a' if c >= o else '#ef5350' for c, o in zip(df['Close'], df['Open'])]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=vol_colors, opacity=0.4, name='成交量'), row=2, col=1)
            
            fig.update_layout(
                template="plotly_white", 
                height=600, margin=dict(l=0, r=0, t=0, b=0),
                xaxis_rangeslider_visible=False, 
                showlegend=False
            )
            fig.update_xaxes(gridcolor='#eef2f6', zeroline=False)
            fig.update_yaxes(gridcolor='#eef2f6', zeroline=False)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        with col_ai:
            st.markdown("<p style='color:#213d91; font-weight:bold; font-size:16px; margin-top:5px;'>📊 AI 策略報告生成</p>", unsafe_allow_html=True)
            btn_label = "🛡️ 執行持倉診斷" if my_cost > 0 else "🚀 執行 AI 策略分析"
            if st.button(btn_label):
                with st.spinner("正在產生深度分析報告..."):
                    res = ask_gemini_strategy(f"標:{ticker}, 價:{last['Close']:.2f}, 本:{my_cost}, 向:{position_type}", selected_model)
                    st.markdown(f"<div class='ai-box'>{res}</div>", unsafe_allow_html=True)

            st.markdown("<hr>", unsafe_allow_html=True)
            if chat_q := st.chat_input("詢問 AI 標的細節或產業展望..."):
                with st.chat_message("user"): st.write(chat_q)
                with st.chat_message("assistant"): st.write(ask_gemini_strategy(f"現價:{last['Close']}, 問題:{chat_q}", selected_model))
    else:
        st.error("❌ 無法獲取數據，請檢查標的代碼是否正確。")
