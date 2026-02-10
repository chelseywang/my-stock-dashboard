import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json

# --- 1. 頁面設定 ---
st.set_page_config(layout="wide", page_title="AI 操盤戰情室", page_icon="💎")

# --- 注入自定義 CSS (提升精緻度) ---
st.markdown("""
    <style>
    /* 全域背景優化 */
    .main {
        background-color: #0e1117;
    }
    /* 卡片式容器 */
    div[data-testid="stMetric"] {
        background-color: #1e2130;
        border: 1px solid #31333f;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    /* 調整按鈕樣式 */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        border: 1px solid #4a90e2;
        background-color: rgba(74, 144, 226, 0.1);
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #4a90e2;
        color: white;
        box-shadow: 0 0 15px rgba(74, 144, 226, 0.4);
    }
    /* 側邊欄美化 */
    section[data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 0. 設定 Gemini API ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    API_KEY = ""
    st.sidebar.warning("⚠️ 請設定 Streamlit Secrets 'GEMINI_API_KEY'")

# --- 模型列表與策略函數 (保持原邏輯) ---
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
        # ATR
        tr = pd.concat([df['High']-df['Low'], (df['High']-df['Close'].shift()).abs(), (df['Low']-df['Close'].shift()).abs()], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        return df, stock
    except: return None, None

# --- 3. 側邊欄 ---
with st.sidebar:
    st.title("💎 戰情控制台")
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
        
        # 頁面標題區
        st.markdown(f"## {ticker} 實時戰情分析 <span style='font-size:16px; color:gray;'>{timeframe} 週期</span>", unsafe_allow_html=True)

        # 頂部指標區
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("當前市價", f"${last['Close']:.2f}", f"{change_pct:.2f}%")
        c2.metric("RVOL 成交量比", f"{last['RVOL']:.2f}x", "爆量" if last['RVOL'] > 2 else "平穩", delta_color="inverse" if last['RVOL'] < 1 else "normal")
        c3.metric("ATR 波動率", f"{last['ATR']:.2f}")
        
        if my_cost > 0:
            pnl = (last['Close'] - my_cost) / my_cost * 100 if position_type == "Long" else (my_cost - last['Close']) / my_cost * 100
            c4.metric("目前損益", f"{pnl:.2f}%", "獲利中" if pnl > 0 else "虧損中")
        else:
            c4.metric("持倉狀態", "觀望中")

        st.markdown("<br>", unsafe_allow_html=True)
        
        col_main, col_ai = st.columns([2.2, 1])

        with col_main:
            # 專業 K 線圖
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            
            # K線
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                name="行情", increasing_line_color='#00ff88', decreasing_line_color='#ff4b4b'
            ), row=1, col=1)
            
            # 均線
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], line=dict(color='#4a90e2', width=1.5), name='EMA20'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA50'], line=dict(color='#f39c12', width=1.5), name='EMA50'), row=1, col=1)
            
            # 量能
            colors = ['#00ff88' if c >= o else '#ff4b4b' for c, o in zip(df['Close'], df['Open'])]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='成交量', opacity=0.5), row=2, col=1)
            
            fig.update_layout(
                template="plotly_dark",
                height=600,
                margin=dict(l=10, r=10, t=0, b=0),
                xaxis_rangeslider_visible=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        with col_ai:
            st.markdown("### 🤖 AI 決策顧問")
            
            btn_label = "🛡️ 執行持倉診斷" if my_cost > 0 else "🚀 尋找進場機會"
            if st.button(btn_label):
                ctx = f"標的:{ticker}, 現價:{last['Close']:.2f}, 成本:{my_cost}, 方向:{position_type}, ATR:{last['ATR']:.2f}"
                with st.spinner("正在計算最優期望值..."):
                    res = ask_gemini_strategy(ctx, selected_model)
                    st.markdown(f"<div style='background-color: #1e2130; padding: 20px; border-radius: 10px; border-left: 5px solid #4a90e2;'>{res}</div>", unsafe_allow_html=True)

            # 聊天對話框
            st.markdown("---")
            if chat_q := st.chat_input("詢問 AI 關於此標的的細節..."):
                with st.chat_message("user"): st.write(chat_q)
                with st.chat_message("assistant"):
                    st.write(ask_gemini_strategy(f"現價:{last['Close']}, 問題:{chat_q}", selected_model))

    else:
        st.error("❌ 無法獲取股票數據，請檢查代碼是否正確。")
