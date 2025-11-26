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
    st.sidebar.warning("⚠️ 尚未偵測到 API Key。請在 Streamlit Secrets 設定 'GEMINI_API_KEY'。")

# --- 功能 1: 列出所有可用模型 ---
def list_available_models():
    if not API_KEY: return ["Error: No API Key"]
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    try:
        # 這裡也把掃描時間拉長到 30 秒，避免網路慢時掃描失敗
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

# --- 功能 2: 狙擊手發問 (120秒超長待機版) ---
def ask_gemini_sniper(prompt, model_name):
    if not API_KEY: return "❌ 請先設定 API Key 才能使用 AI 功能。"

    system_instruction = """
    你是一位華爾街頂級 SMC 交易員。
    請**嚴格依照以下 Markdown 格式**回答，不要改變排版，確保表格可以正常顯示：

    ### ⚡️ 決策：[買進 / 賣出 / 續抱 / 減倉 / 觀望] (選一個)
    
    | 🛑 建議止損 (SL) | 🎯 建議止盈 (TP) | ⚖️ 盈虧比 |
    | :--- | :--- | :--- |
    | **$價格** | **$價格** | **1 : X** |

    ---
    **📝 戰術分析:**
    * **結構:** (一句話判斷多空)
    * **理由:** (結合 RVOL, RSI, 訂單塊分析)
    * **操作:** (具體操作指令，例如：跌破 X 離場，或是在 Y 加碼)
    """
    
    final_prompt = f"{system_instruction}\n\n市場數據與用戶狀況:\n{prompt}"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": final_prompt}]}]}
    
    try:
        # 關鍵修正：timeout 改為 120 秒 (給 AI 足夠時間畫表格)
        response = requests.post(url, headers=headers, json=data, timeout=120)
        
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"❌ API 錯誤 ({response.status_code}): {response.text}"
            
    except requests.exceptions.Timeout:
        return "❌ AI 思考超時 (超過120秒)。請檢查 Google 服務狀態或稍後再試。"
    except Exception as e:
        return f"❌ 網路錯誤: {str(e)}"

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
    st.subheader("部位管理")
    col1, col2 = st.columns(2)
    with col1:
        my_cost = st.number_input("成本價", value=0.0, step=0.1, format="%.2f")
    with col2:
        position_type = st.selectbox("方向", ["多單 (Long)", "空單 (Short)"])
    
    st.markdown("---")
    
    # 模型設定
    default_models = ['gemini-1.5-flash', 'gemini-pro']
    
    if API_KEY:
        if st.button("🔄 重整模型列表"):
            found = list_available_models()
            if found and not found[0].startswith("Error"):
                st.session_state['models'] = found
                st.success("已更新")
    
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
        trend = "多頭排列" if price > last['EMA20'] else "空頭排列"
        
        col_main, col_ai = st.columns([2, 1])

        with col_main:
            # 頂部數據
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("現價", f"${price:.2f}", f"{pct:.2f}%")
            m2.metric("RVOL", f"{rvol:.2f}x", "🔥爆量" if rvol > 2 else "縮量")
            m3.metric("ATR (波動)", f"{atr:.2f}")
            
            pnl_val = 0
            if my_cost > 0:
                if "Long" in position_type:
                    pnl = (price - my_cost) / my_cost * 100
                    pnl_val = price - my_cost
                else:
                    pnl = (my_cost - price) / my_cost * 100
                    pnl_val = my_cost - price
                m4.metric("未實現損益", f"{pnl_val:.2f}", f"{pnl:.2f}%")
            else:
                m4.metric("未實現損益", "-")

            # 圖表
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], line=dict(color='#2962FF', width=1), name='EMA 20'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA50'], line=dict(color='#FF6D00', width=1), name='EMA 50'), row=1, col=1)
            
            if my_cost > 0:
                fig.add_hline(y=my_cost, line_dash="dash", line_color="yellow", annotation_text="COST", row=1, col=1)

            colors = ['#00C853' if c >= o else '#D50000' for c, o in zip(df['Close'], df['Open'])]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='Volume'), row=2, col=1)
            fig.update_layout(height=500, margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with col_ai:
            st.subheader("🤖 AI 策略顧問")
            
            # 按鈕邏輯
            if my_cost > 0:
                btn_text = "🛡️ 分析持倉 (出場建議)"
                prompt_intro = f"我持有 {ticker} 成本 {my_cost} ({position_type})。"
            else:
                btn_text = "🚀 分析進場 (尋找機會)"
                prompt_intro = f"我想進場 {ticker}。"

            if st.button(btn_text, use_container_width=True):
                data_prompt = f"""
                【市場數據】
                標的: {ticker} ({timeframe}) | 現價: {price:.2f}
                結構: {trend} | RVOL: {rvol:.2f} | RSI: {rsi:.1f} | ATR: {atr:.2f}
                前高(PDH): {pdh:.2f} | 前低(PDL): {pdl:.2f}
                
                【用戶狀態】
                {prompt_intro}
                
                請給出專業 SMC 交易計畫。
                """

                # 使用 st.status 顯示漂亮的載入動畫
                with st.status("🧠 AI 正在計算點位與排版...", expanded=True) as status:
                    response_text = ask_gemini_sniper(data_prompt, selected_model)
                    status.update(label="分析完成！", state="complete", expanded=False)
                
                with st.container(border=True):
                    st.markdown(response_text)

            # 簡易聊天框
            if prompt := st.chat_input("手動發問..."):
                with st.chat_message("user"):
                    st.markdown(prompt)
                with st.chat_message("assistant"):
                    with st.spinner("思考中..."):
                        resp = ask_gemini_sniper(f"現價:{price}, 問題:{prompt}", selected_model)
                        st.markdown(resp)

    else:
        st.error("找不到代碼")
