import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json

# --- 1. 頁面設定 ---
st.set_page_config(layout="wide", page_title="AI 操盤戰情室", page_icon="💎")

# --- 0. 設定 Gemini API (安全模式) ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    API_KEY = ""
    st.sidebar.warning("⚠️ 請設定 Streamlit Secrets 'GEMINI_API_KEY'")

# --- 功能 1: 列出可用模型 ---
def list_available_models():
    if not API_KEY: return ["Error: No API Key"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            valid_models = []
            if 'models' in data:
                for m in data['models']:
                    if 'generateContent' in m.get('supportedGenerationMethods', []):
                        simple_name = m['name'].replace('models/', '')
                        valid_models.append(simple_name)
            return valid_models
        else:
            return [f"Error: {response.status_code}"]
    except Exception as e:
        return [f"Error: {str(e)}"]

# --- 功能 2: 策略顧問發問 (邏輯重構版) ---
def ask_gemini_strategy(prompt, model_name):
    if not API_KEY: return "❌ 請先設定 API Key"

    # 新的人設：專注於長短線分流與防掃單
    system_instruction = """
    你現在是我的專屬投資顧問。請不要使用複雜術語，用最直白的方式給我操作建議。
    請嚴格依照以下結構回答：

    ### 🐢 中長線策略 (持有 2-3 個月以上)
    * **趨勢判斷:** (目前是大趨勢多頭還是空頭？)
    * **絕對防守價 (Hard Stop):** $價格 (請預留 ATR 緩衝，確保不被插針掃出場)
    * **分批獲利點:** 建議在 $價格 附近減碼一部分。

    ### ⚡️ 短線佈局 (1-2 週內)
    * **關注點位:** (最近的支撐與壓力)
    * **操作建議:** (例如：拉回 $X 接多，或是反彈 $Y 做空)

    ---
    **💡 總結建議:** (一句話告訴我現在該做什麼)
    """
    
    final_prompt = f"{system_instruction}\n\n我的狀況與數據:\n{prompt}"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": final_prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=120)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"❌ API 錯誤 ({response.status_code})"
    except Exception as e:
        return f"❌ 錯誤: {str(e)}"

# --- 2. 核心數據函數 ---
def get_stock_data(ticker, timeframe):
    try:
        period = "6mo" if timeframe == "1d" else "1mo"
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=timeframe)
        if df.empty: return None, None

        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['AvgVol'] = df['Volume'].rolling(window=20).mean()
        df['RVOL'] = df['Volume'] / df['AvgVol']
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # ATR 計算 (用於防掃止損)
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['ATR'] = true_range.rolling(window=14).mean()
        return df, stock
    except: return None, None

# --- 3. 側邊欄 ---
with st.sidebar:
    st.header("💎 交易設定")
    ticker = st.text_input("股票代碼", value="NBIS").upper()
    timeframe = st.selectbox("級別", ["1d", "1h", "15m"], index=0)
    
    st.markdown("---")
    st.subheader("我的持倉 (選填)")
    col1, col2 = st.columns(2)
    with col1:
        my_cost = st.number_input("成本價", value=0.0, step=0.1, format="%.2f")
    with col2:
        position_type = st.selectbox("方向", ["多單 (Long)", "空單 (Short)"])
    
    st.caption("填寫成本後，AI 會切換為「持倉診斷模式」。")
    st.markdown("---")
    
    # 模型設定
    default_models = ['gemini-1.5-flash', 'gemini-pro']
    if API_KEY and st.button("🔄 重整模型"):
        found = list_available_models()
        if found and not found[0].startswith("Error"):
            st.session_state['models'] = found
    
    model_list = st.session_state.get('models', default_models)
    selected_model = st.selectbox("AI 核心:", model_list)

# --- 4. 主畫面 ---
if ticker:
    df, stock_info = get_stock_data(ticker, timeframe)
    
    if df is not None:
        last = df.iloc[-1]
        price = last['Close']
        rvol = last.get('RVOL', 0)
        rsi = last.get('RSI', 50)
        atr = last.get('ATR', 0)
        pct = ((price - df.iloc[-2]['Close']) / df.iloc[-2]['Close']) * 100
        
        pdh = df['High'].iloc[-2]
        pdl = df['Low'].iloc[-2]
        trend = "多頭趨勢" if price > last['EMA20'] else "空頭趨勢"
        
        col_main, col_ai = st.columns([2, 1])

        with col_main:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("現價", f"${price:.2f}", f"{pct:.2f}%")
            m2.metric("RVOL", f"{rvol:.2f}x", "🔥爆量" if rvol > 2 else "縮量")
            m3.metric("ATR (波動)", f"{atr:.2f}")
            
            if my_cost > 0:
                pnl = (price - my_cost) / my_cost * 100 if "Long" in position_type else (my_cost - price) / my_cost * 100
                m4.metric("未實現損益", f"{pnl:.2f}%")
            else:
                m4.metric("持倉狀態", "空手")

            # 圖表
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], line=dict(color='#2962FF', width=1), name='EMA 20'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA50'], line=dict(color='#FF6D00', width=1), name='EMA 50'), row=1, col=1)
            
            if my_cost > 0:
                fig.add_hline(y=my_cost, line_dash="dash", line_color="yellow", annotation_text="成本", row=1, col=1)

            colors = ['#00C853' if c >= o else '#D50000' for c, o in zip(df['Close'], df['Open'])]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='Volume'), row=2, col=1)
            fig.update_layout(height=500, margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with col_ai:
            st.subheader("🤖 策略顧問")
            
            # 根據是否有成本，決定 Prompt 的內容
            if my_cost > 0:
                btn_label = "🛡️ 分析我的持倉 (長短線策略)"
                user_context = f"我持有 {ticker}，成本 {my_cost}，方向 {position_type}。請告訴我長線該怎麼抱，短線該怎麼做，還有絕對止損在哪裡。"
            else:
                btn_label = "🚀 空手分析 (尋找進場點)"
                user_context = f"我目前空手 {ticker}。請告訴我哪裡可以進場？止損設哪裡比較不容易被掃？"

            if st.button(btn_label, use_container_width=True):
                data_prompt = f"""
                【市場數據】
                標的: {ticker} | 現價: {price:.2f} | 趨勢: {trend}
                ATR (日波動): {atr:.2f} | RVOL: {rvol:.2f} | RSI: {rsi:.1f}
                前高: {pdh:.2f} | 前低: {pdl:.2f}
                
                【用戶需求】
                {user_context}
                """

                with st.status("🧠 正在規劃長短線策略...", expanded=True) as status:
                    response_text = ask_gemini_strategy(data_prompt, selected_model)
                    status.update(label="策略規劃完成", state="complete", expanded=False)
                
                with st.container(border=True):
                    st.markdown(response_text)

            # 簡易聊天
            if prompt := st.chat_input("有其他問題嗎？"):
                with st.chat_message("user"):
                    st.markdown(prompt)
                with st.chat_message("assistant"):
                    with st.spinner("思考中..."):
                        resp = ask_gemini_strategy(f"現價:{price}, 問題:{prompt}", selected_model)
                        st.markdown(resp)

    else:
        st.error("找不到代碼")
