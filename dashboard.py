st.markdown("""
    <style>
    /* 1. 徹底消滅頂部留白 (維持你要求的往上移) */
    .stApp { margin-top: -95px; background-color: #0b0e11; }
    .main .block-container { padding-top: 0rem !important; }

    /* 2. 側邊欄改版：深碳灰 + 橘色細節 (取代原本的大橘色) */
    section[data-testid="stSidebar"] {
        background-color: #161a25 !important; /* 改為深色，不再是橘色 */
        border-right: 1px solid #2d3139;
    }
    
    /* 側邊欄標籤文字：改為明亮灰，確保看得清楚 */
    section[data-testid="stSidebar"] label {
        color: #848e9c !important; 
        font-size: 13px !important;
        font-weight: 500 !important;
    }

    /* 側邊欄標題：保留橘色作為點綴 */
    section[data-testid="stSidebar"] h3 {
        color: #f39c12 !important;
        font-family: 'Courier New', monospace;
    }

    /* 3. 調整中間標題位置 */
    .terminal-header {
        color: #ffffff;
        font-size: 24px;
        font-weight: 700;
        margin-bottom: 15px;
        padding-top: 30px;
    }

    /* 4. 指標卡片 (維持橘色背景，讓數據跳出來) */
    div[data-testid="stMetric"] {
        background-color: #f39c12;
        border: 1px solid #000000;
        padding: 8px 15px !important;
        border-radius: 2px;
    }
    div[data-testid="stMetricValue"] { color: #000000 !important; font-weight: 800 !important; }
    div[data-testid="stMetricLabel"] { color: #000000 !important; opacity: 0.8; }

    /* 5. AI 回應區區塊 */
    .ai-response-box {
        background: #1c202b;
        border-left: 4px solid #f39c12;
        color: #ffffff;
        padding: 15px;
        font-size: 14px;
        height: 400px;
        overflow-y: auto;
    }
    </style>
    """, unsafe_allow_html=True)
