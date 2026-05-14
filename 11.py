import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import time
import altair as alt
import requests

# --- 1. 網頁基礎設定 ---
st.set_page_config(page_title="ETF 投資戰情室", layout="wide")

# 全局提示訊息狀態
if 'update_success' in st.session_state and st.session_state.update_success:
    st.toast(st.session_state.update_success, icon="✅")
    st.session_state.update_success = False

# 自定義 CSS
st.markdown("""
    <style>
    /* 🔥 終極暴力隱藏表格右上角浮動工具列 */
    [data-testid="stElementToolbar"], 
    [data-testid="stDataFrameToolbar"],
    [data-testid="stToolbar"],
    .stDataFrame [data-testid="stElementToolbar"] { 
        display: none !important; 
        opacity: 0 !important; 
        visibility: hidden !important; 
        pointer-events: none !important;
    }
    
    [data-testid="stMetricDelta"] svg { fill: red; }
    
    /* 修正深色模式下白底白字的問題，改用系統自適應變數 */
    [data-testid="stMetric"] { 
        background-color: var(--secondary-background-color); 
        padding: 12px; 
        border-radius: 10px; 
        box-shadow: 1px 1px 4px rgba(0,0,0,0.05);
    }

    /* 三拼損益與領息橫列大看板樣式 */
    .triple-box { background-color: #ffffff; border-radius: 12px; border: 1px solid #e0e0e0; padding: 15px; display: flex; flex-wrap: wrap; justify-content: space-around; align-items: center; margin-bottom: 20px; box-shadow: 2px 2px 8px rgba(0,0,0,0.04); gap: 10px; }
    .triple-col { flex: 1 1 30%; min-width: 140px; text-align: center; padding: 10px 0; }
    .triple-title { font-size: 14px; color: #757575; font-weight: bold; margin-bottom: 5px; }
    .triple-val-r { font-size: 28px; font-weight: 900; color: #b71c1c; font-family: Arial, sans-serif; line-height: 1.1; }
    .triple-val-g { font-size: 28px; font-weight: 900; color: #2e7d32; font-family: Arial, sans-serif; line-height: 1.1; }
    .triple-val-gold { font-size: 28px; font-weight: 900; color: #f39c12; font-family: Arial, sans-serif; line-height: 1.1; text-shadow: 1px 1px 2px rgba(243, 156, 18, 0.3); }
    .triple-pct-r { font-size: 14px; font-weight: bold; color: #b71c1c; margin-top: 5px; }
    .triple-pct-g { font-size: 14px; font-weight: bold; color: #2e7d32; margin-top: 5px; }
    .triple-sub-gold { font-size: 12px; font-weight: bold; color: #7f8c8d; margin-top: 5px; }

    /* 閃電特效 */
    @keyframes lightning-strike {
        0% { box-shadow: 0 0 10px rgba(241, 196, 15, 0.5); background-color: #fffdf5; border-color: #f1c40f; transform: scale(1); }
        50% { box-shadow: 0 0 40px rgba(255, 235, 59, 1), inset 0 0 25px rgba(255, 235, 59, 0.9); background-color: #ffffe0; border-color: #ffeb3b; transform: scale(1.03); }
        100% { box-shadow: 0 0 10px rgba(241, 196, 15, 0.5); background-color: #fffdf5; border-color: #f1c40f; transform: scale(1); }
    }
    .flash-gold-box { background-color: #fffdf5; border-radius: 12px; padding: 15px; border: 2px solid #f1c40f; animation: lightning-strike 0.1s infinite; }

    .alert-high { background-color: #ffebee; border: 2px solid #ef5350; border-left: 8px solid #d32f2f; padding: 15px; border-radius: 8px; margin-bottom: 15px; color: #b71c1c; font-size: 16px; font-weight: bold; }
    .alert-low { background-color: #e8f5e9; border: 2px solid #66bb6a; border-left: 8px solid #388e3c; padding: 15px; border-radius: 8px; margin-bottom: 15px; color: #1b5e20; font-size: 16px; font-weight: bold; }

    .month-card { background-color: #e9ecef; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 10px; border: 1px solid #ced4da; }
    .month-title { font-size: 20px; font-weight: bold; color: #495057; }
    .month-amount { font-size: 28px; font-weight: bold; color: #d9534f; margin: 10px 0; }
    .month-sources { font-size: 14px; color: #6c757d; }
    
    div.stButton > button { font-weight: bold; border-radius: 8px; }
    
    .calc-box { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 15px; margin-bottom: 15px;}
    .calc-title { color: #495057; font-weight: bold; font-size: 16px; margin-bottom: 10px; }
    .calc-result-profit { font-size: 24px; font-weight: bold; color: #d32f2f; margin-top: 10px;}
    .calc-result-loss { font-size: 24px; font-weight: bold; color: #388e3c; margin-top: 10px;}
    .calc-result-info { font-size: 14px; color: #6c757d; margin-top: 5px;}
    
    /* 自動更新控制區樣式 */
    .auto-refresh-box { background-color: #f0f7ff; border: 1px solid #cce5ff; border-radius: 8px; padding: 15px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 系統設定與資料庫 ---
SETTINGS_FILE = 'settings.json'

ETF_FULL_DATABASE = {
    "0050": ["元大台灣50", [1, 7], "0.32%", "0.035%"],
    "0051": ["元大中型100", [11], "0.4%", "0.035%"],
    "0052": ["富邦台灣科技指數", [4], "0.15%", "0.035%"],
    "0053": ["元大台灣電子科技", [11], "0.3%", "0.035%"],
    "0055": ["元大MSCI金融", [11], "0.3%", "0.035%"],
    "0056": ["元大台灣高股息", [1, 4, 7, 10], "0.3%", "0.035%"],
    "0057": ["富邦摩台", [6], "0.15%", "0.035%"],
    "006201": ["元大富櫃50", [12], "0.4%", "0.035%"],
    "006203": ["元大摩臺台灣", [1, 7], "0.3%", "0.035%"],
    "006204": ["永豐臺灣加權", [10], "0.32%", "0.035%"],
    "006208": ["富邦台50", [7, 11], "0.15%", "0.035%"],
    "00690": ["兆豐藍籌30", [2, 5, 8, 11], "0.32%", "0.035%"],
    "00692": ["富邦臺灣公司治理", [7, 11], "0.15%", "0.035%"],
    "00701": ["國泰股利精選30", [1, 8], "0.3%", "0.035%"],
    "00713": ["元大台灣高息低波", [3, 6, 9, 12], "0.3%", "0.035%"],
    "00728": ["第一金工業30", [3, 6, 9, 12], "0.4%", "0.035%"],
    "00730": ["富邦臺灣優質高息", list(range(1, 13)), "0.45%", "0.035%"],
    "00731": ["復華富時高息低波", [2, 5, 8, 11], "0.3%", "0.035%"],
    "00733": ["富邦臺灣中小", [5, 10], "0.4%", "0.035%"],
    "00850": ["元大臺灣ESG永續", [2, 5, 8, 11], "0.3%", "0.035%"],
    "00878": ["國泰永續ESG高股息", [2, 5, 8, 11], "0.25%", "0.035%"],
    "00881": ["國泰台灣5G+", [1, 8], "0.4%", "0.035%"],
    "00888": ["永豐台灣ESG永續優質", [1, 4, 7, 10], "0.25%", "0.03%"],
    "00891": ["中信關鍵半導體", [2, 5, 8, 11], "0.4%", "0.035%"],
    "00892": ["富邦台灣核心半導體", [], "0.4%", "0.035%"],
    "00894": ["中信特選小資高價30", [2, 5, 8, 11], "0.4%", "0.035%"],
    "00896": ["中信綠能及電動車", [3, 6, 9, 12], "0.4%", "0.035%"],
    "00900": ["富邦特選高股息30", [2, 5, 8, 11], "0.3%", "0.035%"],
    "00901": ["永豐台灣智能車供應鏈", [10], "0.4%", "0.04%"],
    "00904": ["新光臺灣半導體30", [1, 4, 7, 10], "0.4%", "0.035%"],
    "00905": ["FT臺灣Smart", [1, 4, 7, 10], "0.4%", "0.035%"],
    "00907": ["永豐優選存股", [2, 4, 6, 8, 10, 12], "0.4%", "0.03%"],
    "00912": ["中信台灣智慧50", [1, 4, 7, 10], "0.3%", "0.035%"],
    "00913": ["兆豐晶圓製造", [1, 7], "0.4%", "0.03%"],
    "00915": ["凱基優選高股息30", [3, 6, 9, 12], "0.3%", "0.035%"],
    "00918": ["大華優利高填息30", [3, 6, 9, 12], "0.35%", "0.035%"],
    "00919": ["群益台灣精選高息", [3, 6, 9, 12], "0.3%", "0.035%"],
    "00921": ["兆豐龍頭等權重", [3, 6, 9, 12], "0.45%", "0.030%"],
    "00922": ["國泰台灣領袖50", [3, 10], "0.20%", "0.035%"],
    "00923": ["群益台灣ESG低碳50", [2, 8], "0.32%", "0.035%"],
    "00927": ["群益台灣半導體收益", [1, 4, 7, 10], "0.4%", "0.035%"],
    "00928": ["中信上櫃ESG30", [1, 7], "0.4%", "0.035%"],
    "00929": ["復華台灣科技優息", list(range(1, 13)), "0.30%", "0.030%"],
    "00930": ["永豐ESG低碳高息", [1, 3, 5, 7, 9, 11], "0.35%", "0.035%"],
    "00932": ["兆豐永續高息等權", [2, 5, 8, 11], "0.15%", "0.030%"],
    "00934": ["中信成長高股息", list(range(1, 13)), "0.3%", "0.035%"],
    "00935": ["野村臺灣創新科技50", [3, 9], "0.4%", "0.035%"],
    "00936": ["台新永續高息中小", list(range(1, 13)), "0.4%", "0.035%"],
    "00938": ["凱基優選30", [2, 5, 8, 11], "0.3%", "0.35%"],
    "00939": ["統一台灣高息動力", list(range(1, 13)), "0.3%", "0.035%"],
    "00940": ["元大臺灣價值高息", list(range(1, 13)), "0.3%", "0.030%"],
    "00943": ["兆豐電子高息等權", list(range(1, 13)), "0.25%", "0.03%"],
    "00944": ["野村臺灣趨勢動能高股息", list(range(1, 13)), "0.4%", "0.035%"],
    "00946": ["群益台灣科技高息成長", list(range(1, 13)), "0.3%", "0.030%"],
    "00947": ["台新臺灣IC設計動能", [1, 4, 7, 10], "0.40%", "0.030%"],
    "00952": ["凱基台灣AI 50", list(range(1, 13)), "0.40%", "0.030%"],
    "00961": ["FT臺灣永續高息", list(range(1, 13)), "0.30%", "0.035%"],
    "00962": ["台新臺灣AI優息動能", list(range(1, 13)), "0.40%", "0.035%"],
    "009802": ["富邦旗艦50", [3, 6, 9, 12], "0.15%", "0.03%"],
    "009803": ["保德信市值動能50", [3, 6, 9, 12], "0.25%", "0.035%"],
    "009804": ["聯邦台灣精彩50", [4, 7], "0.15%", "0.035%"],
    "009808": ["華南永昌台灣優選50", [2, 5, 8, 11], "0.05%", "0.035%"],
    "009809": ["富邦台灣淨零轉型 ESG 50", [3, 6, 9, 12], "0.30%", "0.035%"],
    "00980A": ["野村臺灣智慧優選主動式", [2, 5, 8, 11], "0.75%", "0.035%"],
    "00981A": ["統一台股增長主動式", [3, 6, 9, 12], "1.0%", "0.10%"],
    "00982A": ["群益台灣精選強棒主動式", [2, 5, 8, 11], "0.8%", "0.035%"],
    "00984A": ["安聯台灣高息成長主動式", [1, 4, 7, 10], "0.7%", "0.04%"],
    "00985A": ["野村台灣增強50主動式", [1], "0.45%", "0.035%"],
    "00981T": ["平衡凱基雙核收息", [], "0.60%", "0.10%"]
}

EXTRA_ETFS = {
    "00631L": "00631L 元大台灣50正2", "00673R": "00673R 期元大S&P原油反1", 
    "00632R": "00632R 元大台灣50反1", "009819": "009819 中信數據及電力", 
    "00712": "00712 復華富時不動產", "00992A": "00992A 主動群益科技創新",
    "00400A": "00400A 主動國泰動能高息", "00997A": "00997A 主動群益美國增長",
    "00988A": "00988A 主動統一全球創新", "00994A": "00994A 主動第一金台股優",
    "00646": "00646 元大S&P500", "00662": "00662 富邦NASDAQ", 
    "00830": "00830 國泰費城半導體", "00757": "00757 統一FANG+", 
    "00882": "00882 中信中國高股息", "00963": "00963 中信全球高股息", 
    "00964": "00964 中信亞太高股息", "00679B": "00679B 元大美債20年", 
    "00687B": "00687B 國泰20年美債", "00720B": "00720B 元大投資級公司債",
    "00751B": "00751B 元大AAA至A公司債", "00937B": "00937B 群益ESG投等債20+", 
    "00772B": "00772B 中信高評級公司債", "00773B": "00773B 中信優先金融債", 
    "00780B": "00780B 國泰A級金融債", "00795B": "00795B 中信美國公債20年",
    "2330": "2330 台積電", "2454": "2454 聯發科", "2317": "2317 鴻海"
}

ETF_NAME_DB = {}
DIVIDEND_SCHEDULE = {}
ETF_FEES_DB = {}

for k, v in EXTRA_ETFS.items():
    ETF_NAME_DB[k] = v

for k, v in ETF_FULL_DATABASE.items():
    ETF_NAME_DB[k] = f"{k} {v[0]}"
    DIVIDEND_SCHEDULE[f"{k}.TW"] = v[1]
    ETF_FEES_DB[f"{k}.TW"] = {"經理費": v[2], "保管費": v[3]}

ETF_CONSTITUENTS_DB = {
    "0056.TW": [{"name": "鴻海", "weight": 6.5}, {"name": "聯發科", "weight": 5.2}, {"name": "聯詠", "weight": 4.8}, {"name": "中信金", "weight": 4.5}, {"name": "聯電", "weight": 4.1}, {"name": "其他", "weight": 74.9}],
    "00878.TW": [{"name": "聯發科", "weight": 5.5}, {"name": "國泰金", "weight": 5.1}, {"name": "富邦金", "weight": 4.9}, {"name": "廣達", "weight": 4.5}, {"name": "聯電", "weight": 4.2}, {"name": "其他", "weight": 75.8}],
    "00919.TW": [{"name": "長榮", "weight": 11.5}, {"name": "聯電", "weight": 6.2}, {"name": "瑞昱", "weight": 5.8}, {"name": "聯發科", "weight": 5.1}, {"name": "聯詠", "weight": 4.8}, {"name": "其他", "weight": 66.6}],
    "00927.TW": [{"name": "台積電", "weight": 31.2}, {"name": "聯發科", "weight": 15.5}, {"name": "聯電", "weight": 6.5}, {"name": "日月光投控", "weight": 5.8}, {"name": "瑞昱", "weight": 5.2}, {"name": "其他", "weight": 35.8}],
    "00891.TW": [{"name": "台積電", "weight": 30.5}, {"name": "聯發科", "weight": 14.2}, {"name": "聯電", "weight": 6.1}, {"name": "日月光投控", "weight": 5.5}, {"name": "瑞昱", "weight": 5.0}, {"name": "其他", "weight": 38.7}],
    "00929.TW": [{"name": "聯發科", "weight": 9.5}, {"name": "聯電", "weight": 7.2}, {"name": "日月光投控", "weight": 6.8}, {"name": "瑞昱", "weight": 6.5}, {"name": "聯詠", "weight": 6.1}, {"name": "其他", "weight": 63.9}],
    "0050.TW": [{"name": "台積電", "weight": 52.5}, {"name": "鴻海", "weight": 5.5}, {"name": "聯發科", "weight": 4.8}, {"name": "廣達", "weight": 2.1}, {"name": "台達電", "weight": 1.9}, {"name": "其他", "weight": 33.2}],
    "006208.TW": [{"name": "台積電", "weight": 52.6}, {"name": "鴻海", "weight": 5.4}, {"name": "聯發科", "weight": 4.9}, {"name": "廣達", "weight": 2.0}, {"name": "台達電", "weight": 1.8}, {"name": "其他", "weight": 33.3}],
    "00713.TW": [{"name": "統一", "weight": 8.5}, {"name": "台灣大", "weight": 7.2}, {"name": "遠傳", "weight": 6.8}, {"name": "華碩", "weight": 6.1}, {"name": "仁寶", "weight": 5.5}, {"name": "其他", "weight": 65.9}],
    "00940.TW": [{"name": "長榮", "weight": 9.5}, {"name": "聯電", "weight": 6.5}, {"name": "聯發科", "weight": 5.8}, {"name": "中美晶", "weight": 5.2}, {"name": "神基", "weight": 4.8}, {"name": "其他", "weight": 68.2}],
    "00981A.TW": [{"name": "台積電", "weight": 18.5}, {"name": "聯發科", "weight": 8.2}, {"name": "奇鋐", "weight": 6.5}, {"name": "台光電", "weight": 5.8}, {"name": "雙鴻", "weight": 5.2}, {"name": "其他", "weight": 55.8}],
    "00982A.TW": [{"name": "台積電", "weight": 15.0}, {"name": "鴻海", "weight": 9.5}, {"name": "聯發科", "weight": 7.5}, {"name": "富邦金", "weight": 5.5}, {"name": "廣達", "weight": 4.8}, {"name": "其他", "weight": 57.7}]
}

def load_settings():
    default_data = {
        "etfs": [], 
        "pledge": {"borrowed_amount": 0},
        "watchlist": [],
        "custom_divs": {}
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f: 
                data = json.load(f)
                for k, v in default_data.items():
                    if k not in data: data[k] = v
                return data
        except: pass
    return default_data

def save_to_json(data):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

if 'my_data' not in st.session_state: 
    st.session_state.my_data = load_settings()

if 'watchlist' not in st.session_state.my_data:
    st.session_state.my_data['watchlist'] = []

now_str = datetime.now().strftime("%Y-%m")

if 'pledge' not in st.session_state.my_data: st.session_state.my_data['pledge'] = {"borrowed_amount": 0}

for etf in st.session_state.my_data['etfs']:
    if 'pledged_shares' not in etf: etf['pledged_shares'] = 0.0
    if 'is_pledged' not in etf: etf['is_pledged'] = False 
save_to_json(st.session_state.my_data)

# --- 🚀 Callback 函數區 ---
def auto_fill_etf_name():
    raw_sym = st.session_state.get('add_sym_bot', '')
    clean_sym = raw_sym.strip().upper().replace(".TW", "")
    if clean_sym: st.session_state.add_name_bot = ETF_NAME_DB.get(clean_sym, f"{clean_sym} ETF")
    else: st.session_state.add_name_bot = ""

def add_new_etf_bot():
    raw_sym = st.session_state.get('add_sym_bot', '')
    new_name = st.session_state.get('add_name_bot', '')
    new_h = st.session_state.get('add_h_bot', 0.0)
    new_c = st.session_state.get('add_c_bot', 0.0)

    clean_symbol = raw_sym.strip().upper().replace(".TW", "")
    if clean_symbol and new_name:
        final_symbol = f"{clean_symbol}.TW" 
        st.session_state.my_data['etfs'].append({
            "symbol": final_symbol, "name": new_name, "holdings": new_h, "cost": new_c, "alert_high": 0.0, "alert_low": 0.0, "pledged_shares": 0.0, "is_pledged": False
        })
        save_to_json(st.session_state.my_data)
        st.session_state.add_sym_bot = ""; st.session_state.add_name_bot = ""; st.session_state.add_h_bot = 0.0; st.session_state.add_c_bot = 0.0

def delete_etf(index):
    if 0 <= index < len(st.session_state.my_data['etfs']):
        st.session_state.my_data['etfs'].pop(index)
        save_to_json(st.session_state.my_data)

def save_edits():
    temp_list = []
    for i, item in enumerate(st.session_state.my_data['etfs']):
        h_val = st.session_state.get(f"edit_h_{i}", item['holdings'])
        c_val = st.session_state.get(f"edit_c_{i}", item['cost'])
        temp_list.append({
            "symbol": item['symbol'], "name": item['name'], "holdings": h_val, "cost": c_val,
            "alert_high": item.get('alert_high', 0.0), "alert_low": item.get('alert_low', 0.0), 
            "pledged_shares": item.get('pledged_shares', 0.0), "is_pledged": item.get('is_pledged', False)
        })
    st.session_state.my_data['etfs'] = temp_list
    save_to_json(st.session_state.my_data)

def auto_fill_wl_name():
    raw_sym = st.session_state.get('add_sym_wl', '')
    clean_sym = raw_sym.strip().upper().replace(".TW", "")
    if clean_sym: st.session_state.add_name_wl = ETF_NAME_DB.get(clean_sym, f"{clean_sym}")
    else: st.session_state.add_name_wl = ""

def add_new_wl():
    raw_sym = st.session_state.get('add_sym_wl', '')
    new_name = st.session_state.get('add_name_wl', '')
    clean_symbol = raw_sym.strip().upper().replace(".TW", "")
    if clean_symbol and new_name:
        final_symbol = f"{clean_symbol}.TW"
        if any(x['symbol'] == final_symbol for x in st.session_state.my_data['watchlist']):
            st.warning("該標的已在自選名單中！")
            return
        st.session_state.my_data['watchlist'].append({"symbol": final_symbol, "name": new_name})
        save_to_json(st.session_state.my_data)
        st.session_state.add_sym_wl = ""; st.session_state.add_name_wl = ""

def delete_wl(index):
    if 0 <= index < len(st.session_state.my_data['watchlist']):
        st.session_state.my_data['watchlist'].pop(index)
        save_to_json(st.session_state.my_data)

def execute_trade():
    trade_etf_name = st.session_state.calc_selected_etf
    trade_type = st.session_state.calc_trade_type
    trade_shares = st.session_state.calc_trade_shares
    
    for i, item in enumerate(st.session_state.my_data['etfs']):
        if item['name'] == trade_etf_name:
            current_holdings = item['holdings']
            current_cost = item['cost']
            current_price = df[df['名稱'] == trade_etf_name].iloc[0]['現價']
            
            if trade_type == "賣出 (計算已實現損益)":
                actual_sell_shares = min(trade_shares, current_holdings)
                new_holdings = current_holdings - actual_sell_shares
                if new_holdings <= 0:
                    st.session_state.my_data['etfs'].pop(i)
                    st.success(f"已全數賣出 {trade_etf_name}，並從庫存中移除！")
                else:
                    item['holdings'] = new_holdings
                    st.success(f"成功賣出 {actual_sell_shares} 張 {trade_etf_name}！庫存剩餘 {new_holdings} 張。")
            elif trade_type == "買進 (計算買入成本與新均價)":
                buy_cost_total = current_price * trade_shares * 1000
                new_total_shares = current_holdings + trade_shares
                new_total_cost_val = (current_cost * current_holdings * 1000) + buy_cost_total
                new_avg_cost = new_total_cost_val / (new_total_shares * 1000) if new_total_shares > 0 else 0
                item['holdings'] = new_total_shares
                item['cost'] = round(new_avg_cost, 2)
                st.success(f"成功買進 {trade_shares} 張 {trade_etf_name}！最新均價更新為 ${item['cost']}。")
            save_to_json(st.session_state.my_data)
            break

# 初始化按鈕狀態
if 'show_calendar' not in st.session_state: st.session_state.show_calendar = False
if 'show_div_db' not in st.session_state: st.session_state.show_div_db = False
if 'show_tech' not in st.session_state: st.session_state.show_tech = False
if 'show_holdings' not in st.session_state: st.session_state.show_holdings = False
if 'show_constituents' not in st.session_state: st.session_state.show_constituents = False 
if 'show_daily_price' not in st.session_state: st.session_state.show_daily_price = False 
if 'show_pledge' not in st.session_state: st.session_state.show_pledge = False 

def toggle_calendar(): st.session_state.show_calendar = not st.session_state.show_calendar
def toggle_div_db(): st.session_state.show_div_db = not st.session_state.show_div_db
def toggle_tech(): st.session_state.show_tech = not st.session_state.show_tech
def toggle_holdings(): st.session_state.show_holdings = not st.session_state.show_holdings
def toggle_constituents(): st.session_state.show_constituents = not st.session_state.show_constituents
def toggle_daily_price(): st.session_state.show_daily_price = not st.session_state.show_daily_price 
def toggle_pledge(): st.session_state.show_pledge = not st.session_state.show_pledge 

# ==============================================================================
# 🔥 [升級版] 台灣證券交易所 (TWSE) + 櫃買中心 (TPEx) 官方除權息預告
# ==============================================================================
@st.cache_data(ttl=10800) 
def fetch_taiwan_upcoming_dividends():
    tw_div_data = {}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    # 1. 抓取 TWSE (上市)
    try:
        url_twse = "https://www.twse.com.tw/exchangeReport/TWT49U?response=json"
        res = requests.get(url_twse, headers=headers, timeout=5)
        data = res.json()
        
        if data.get('stat') == 'OK':
            import re
            for row in data.get('data', []):
                if len(row) >= 8: 
                    date_str = str(row[0])      
                    symbol = str(row[1]).strip() 
                    
                    match = re.search(r'(\d+)年(\d+)月(\d+)日', date_str)
                    if match:
                        tw_year, month, day = match.groups()
                        ex_date = f"{int(tw_year) + 1911}-{month.zfill(2)}-{day.zfill(2)}"
                        
                        amount = 0.0
                        cash_div_str = str(row[7]).replace(',', '').strip()
                        if cash_div_str and cash_div_str.replace('.', '', 1).isdigit():
                            amount = float(cash_div_str)
                        
                        pay_date_obj = datetime.strptime(ex_date, '%Y-%m-%d') + timedelta(days=28)
                        pay_date = pay_date_obj.strftime('%Y-%m-%d')
                        
                        tw_div_data[symbol] = {
                            "ex_date": ex_date,
                            "pay_date": pay_date,
                            "amount": amount
                        }
    except Exception as e:
        pass

    # 2. 抓取 TPEx (上櫃)
    try:
        url_tpex = "https://www.tpex.org.tw/web/stock/exright/preAnnounce/PrePost_result.php?l=zh-tw&o=json"
        res_tpex = requests.get(url_tpex, headers=headers, timeout=5)
        data_tpex = res_tpex.json()
        if 'aaData' in data_tpex:
            for row in data_tpex['aaData']:
                if len(row) >= 6:
                    date_str = str(row[0]) 
                    symbol = str(row[1]).strip()
                    
                    parts = date_str.split('/')
                    if len(parts) == 3:
                        tw_year, month, day = parts
                        ex_date = f"{int(tw_year) + 1911}-{month.zfill(2)}-{day.zfill(2)}"
                        
                        amount = 0.0
                        cash_div_str = str(row[5]).replace(',', '').strip()
                        if cash_div_str and cash_div_str.replace('.', '', 1).isdigit():
                            amount = float(cash_div_str)
                            
                        pay_date_obj = datetime.strptime(ex_date, '%Y-%m-%d') + timedelta(days=28)
                        pay_date = pay_date_obj.strftime('%Y-%m-%d')
                        
                        tw_div_data[symbol] = {
                            "ex_date": ex_date,
                            "pay_date": pay_date,
                            "amount": amount
                        }
    except Exception as e:
        pass
        
    return tw_div_data

# ==============================================================================
# 🔥 獨立快取的「基金規模探測器」
# ==============================================================================
@st.cache_data(ttl=86400) 
def get_fund_size(symbol):
    try:
        tk = yf.Ticker(symbol)
        cap = tk.fast_info.get('marketCap')
        if cap and cap > 0: return cap
        shares = tk.fast_info.get('shares')
        price = tk.fast_info.get('lastPrice') or tk.fast_info.get('previousClose')
        if shares and price: return shares * price
        info = tk.info
        cap = info.get('totalAssets') or info.get('marketCap')
        if cap and cap > 0: return cap
    except Exception:
        pass
    return None

# --- 🎯 抓取除權息資料 ---
@st.cache_data(ttl=43200)
def get_div_data(symbol, custom_div_info=None):
    is_announced = False
    div_amount = 0.0
    ex_date = "待官方公告"
    pay_date = "待官方公告"
    fill_status = "-"
    status_msg = "⏳ 依前次估算"
    
    clean_sym = symbol.replace('.TW', '')
    taiwan_div_data = fetch_taiwan_upcoming_dividends()
    
    try:
        tk = yf.Ticker(symbol)
        today = datetime.today()
        
        if custom_div_info and custom_div_info.get('v', 0) > 0:
            div_amount = custom_div_info['v']
            ex_date = custom_div_info['d']
            pay_date = custom_div_info['p']
            is_announced = True
            
            ex_date_obj = datetime.strptime(ex_date, '%Y-%m-%d')
            if ex_date_obj.date() >= today.date():
                status_msg = "✅ 已公告 (手動)"
            else:
                status_msg = "✅ 前次紀錄 (手動)"
            
        elif clean_sym in taiwan_div_data:
            is_announced = True
            ex_date = taiwan_div_data[clean_sym]['ex_date']
            pay_date = taiwan_div_data[clean_sym]['pay_date']
            official_amount = taiwan_div_data[clean_sym]['amount']
            
            if official_amount > 0:
                div_amount = official_amount
            else:
                actions = tk.actions
                if not actions.empty:
                    latest = actions.sort_index(ascending=False).head(1)
                    div_amount = float(latest['Dividends'].values[0])
                    
            ex_date_obj = datetime.strptime(ex_date, '%Y-%m-%d')
            if ex_date_obj.date() >= today.date():
                status_msg = "✅ 已公告 (台灣官方)"
            else:
                status_msg = "✅ 前次配息 (台灣官方)"
                    
        else:
            divs = tk.dividends
            if not divs.empty:
                latest_div = divs.sort_index(ascending=False).head(1)
                div_amount = float(latest_div.values[0]) 
                last_ex_date_obj = latest_div.index[0].replace(tzinfo=None)
                
                ex_date = last_ex_date_obj.strftime('%Y-%m-%d')
                pay_date = (last_ex_date_obj + timedelta(days=28)).strftime('%Y-%m-%d') 
                is_announced = True
                
                if last_ex_date_obj.date() >= today.date():
                    status_msg = "✅ 已公告 (近期)"
                else:
                    status_msg = "✅ 前次配息紀錄"

        hist = tk.history(period='1y')
        divs = tk.dividends
        if not divs.empty and not hist.empty:
            now_ts = pd.Timestamp.now(tz=divs.index.tzinfo) if divs.index.tzinfo else pd.Timestamp.now()
            past_divs = divs[divs.index < now_ts].sort_index(ascending=False)
            
            if not past_divs.empty:
                last_ex_date = past_divs.index[0]
                pre_ex = hist[hist.index < last_ex_date]
                post_ex = hist[hist.index >= last_ex_date]
                
                if not pre_ex.empty and not post_ex.empty:
                    target_price = pre_ex['Close'].iloc[-1]
                    filled = False
                    t_days = 0
                    for d, r in post_ex.iterrows():
                        t_days += 1
                        if r['High'] >= target_price:
                            fill_status = f"{d.month}/{d.day} 填息完成 ({t_days}天)"
                            filled = True
                            break
                    if not filled:
                        fill_status = f"未填息 ({t_days}天)"
    except Exception:
        pass
    
    return is_announced, div_amount, ex_date, pay_date, fill_status, status_msg

# --- 🎯 抓取自選股資料 ---
@st.cache_data(ttl=10)
def fetch_watchlist_data(wl_list):
    if not wl_list: return pd.DataFrame()
    results = []
    for item in wl_list:
        try:
            tk = yf.Ticker(item['symbol'])
            hist = tk.history(period="2d")
            if hist.empty: continue
            
            rt_curr = tk.fast_info.get('lastPrice')
            curr_p = rt_curr if rt_curr is not None else hist['Close'].iloc[-1]
            
            rt_prev = tk.fast_info.get('previousClose')
            prev_close = rt_prev if rt_prev is not None else (hist['Close'].iloc[-2] if len(hist) >= 2 else curr_p)
            
            diff = curr_p - prev_close
            pct = (diff / prev_close * 100) if prev_close else 0
            status_light = "🔴" if diff > 0 else "🟢" if diff < 0 else "⚪"
            
            results.append({
                "代號": item['symbol'].replace('.TW', ''), "名稱": item['name'],
                "現價": round(curr_p, 2), "漲跌": round(diff, 2), "漲跌幅": f"{pct:+.2f}%", "狀態": status_light
            })
        except Exception: continue
    return pd.DataFrame(results)

# --- 🎯 抓取自選股除權息資料 ---
@st.cache_data(ttl=43200)
def fetch_watchlist_dividend(wl_list, custom_divs):
    if not wl_list: return pd.DataFrame()
    results = []
    for item in wl_list:
        sym = item['symbol']
        try:
            cap_raw = get_fund_size(sym)
            cap_str = f"{cap_raw / 100000000:.2f} 億" if cap_raw else "系統無資料"

            custom_info = custom_divs.get(sym)
            is_announced, div_amount, ex_date, pay_date, fill_status, status_msg = get_div_data(sym, custom_info)
            
            months = DIVIDEND_SCHEDULE.get(sym, [])
            freq = "月配息" if len(months)==12 else "季配息" if len(months)==4 else "半年配" if len(months)==2 else "年配息" if len(months)==1 else "未知"

            results.append({
                "類別": "👀 自選", "ETF 名稱": item['name'], "基金規模": cap_str,  
                "配息頻率": freq, "配息月份": "、".join(map(str, months)) + " 月" if months else "未設定",
                "狀態": status_msg, 
                "除息日": ex_date, "發放日": pay_date, "每股金額": f"${div_amount:.3f}", "最新填息紀錄": fill_status
            })
        except Exception:
            continue
    return pd.DataFrame(results)

# --- 4. 核心數據計算 ---
@st.cache_data(ttl=10)
def fetch_data(etf_list, custom_divs):
    if not etf_list: return pd.DataFrame(), pd.DataFrame(), 0, 0, 0, 0, [], {i: {"amount": 0, "sources": []} for i in range(1, 13)}
    results, tech_results = [], []
    total_mkt, total_cost, total_div, total_today_pnl = 0, 0, 0, 0
    price_alerts = []
    monthly_calendar = {i: {"amount": 0, "sources": []} for i in range(1, 13)} 
    today = datetime.today()

    for item in etf_list:
        try:
            tk = yf.Ticker(item['symbol'])
            
            cap_raw = get_fund_size(item['symbol'])
            cap_str = f"{cap_raw / 100000000:.2f} 億" if cap_raw else "系統無資料"

            hist = tk.history(period='5d') 
            if hist.empty: continue
            
            rt_curr = tk.fast_info.get('lastPrice')
            curr_p = rt_curr if rt_curr is not None else hist['Close'].iloc[-1]
            
            rt_prev = tk.fast_info.get('previousClose')
            prev_close = rt_prev if rt_prev is not None else (hist['Close'].iloc[-2] if len(hist) >= 2 else curr_p)
            
            rt_dh = tk.fast_info.get('dayHigh')
            day_high = rt_dh if rt_dh is not None else hist['High'].iloc[-1]
            
            rt_dl = tk.fast_info.get('dayLow')
            day_low = rt_dl if rt_dl is not None else hist['Low'].iloc[-1]
            
            rt_vol = tk.fast_info.get('lastVolume')
            vol = rt_vol if rt_vol is not None else hist['Volume'].iloc[-1]
            
            year_high = tk.fast_info.get('yearHigh', 0)
            year_low = tk.fast_info.get('yearLow', 0)

            if curr_p > prev_close: status_light = "🔴"
            elif curr_p < prev_close: status_light = "🟢"
            else: status_light = "⚪"
            display_name = f"{status_light} {item['name']}"

            shares = item['holdings'] * 1000
            mkt_val = shares * curr_p
            cost_val = shares * item['cost']
            
            sell_cost_estimate = mkt_val * 0.00235
            profit = mkt_val - cost_val - sell_cost_estimate
            roi = (profit / cost_val * 100) if cost_val != 0 else 0
            
            today_diff = curr_p - prev_close
            today_profit = shares * today_diff
            today_pct_change = (today_diff / prev_close * 100) if prev_close else 0
            
            total_today_pnl += today_profit
            today_pnl_str = f"+${today_profit:,.0f}" if today_profit >= 0 else f"-${abs(today_profit):,.0f}"
            today_pct_str = f"+{today_pct_change:.2f}%" if today_pct_change >= 0 else f"{today_pct_change:.2f}%"

            a_high = float(item.get('alert_high', 0.0))
            a_low = float(item.get('alert_low', 0.0))
            if a_high > 0 and curr_p >= a_high: price_alerts.append({"name": item['name'], "price": curr_p, "target": a_high, "type": "high"})
            if a_low > 0 and curr_p <= a_low: price_alerts.append({"name": item['name'], "price": curr_p, "target": a_low, "type": "low"})

            custom_info = custom_divs.get(item['symbol'])
            is_announced, div_amount, ex_date, pay_date, fill_status, status_msg = get_div_data(item['symbol'], custom_info)

            est_yield = 0.0
            months_to_pay = DIVIDEND_SCHEDULE.get(item['symbol'], [])
            if len(months_to_pay) > 0 and div_amount > 0 and curr_p > 0:
                est_yield = (div_amount * len(months_to_pay)) / curr_p * 100

            if div_amount > 0 and shares > 0:
                explicit_pay_month = None
                if is_announced and pay_date != "待官方公告":
                    explicit_pay_month = datetime.strptime(pay_date, '%Y-%m-%d').month
                    monthly_calendar[explicit_pay_month]["amount"] += (shares * div_amount)
                    if item['name'] not in monthly_calendar[explicit_pay_month]["sources"]:
                        monthly_calendar[explicit_pay_month]["sources"].append(item['name'])

                for m in months_to_pay:
                    pay_m = m + 1 if m < 12 else 1
                    if pay_m != explicit_pay_month:
                        monthly_calendar[pay_m]["amount"] += (shares * div_amount)
                        if item['name'] not in monthly_calendar[pay_m]["sources"]:
                            monthly_calendar[pay_m]["sources"].append(item['name'])

            total_mkt += mkt_val; total_cost += cost_val; total_div += (shares * div_amount)
            
            fee_info = ETF_FEES_DB.get(item['symbol'], {"經理費": "-", "保管費": "-"})

            results.append({
                "代號": item['symbol'], "名稱": item['name'], "現價": curr_p, "均價": item['cost'],
                "張數": item['holdings'], "市值": mkt_val, "損益": profit, "報酬率": roi,
                "經理費": fee_info["經理費"], "保管費": fee_info["保管費"], 
                "單次預估領息": shares * div_amount, "每股配息": div_amount,
                "最新公告除息日": ex_date, "預估發放日": pay_date, "已公告": is_announced,
                "狀態": status_msg,
                "最新填息紀錄": fill_status, "基金規模": cap_str
            })
            
            months_to_pay = DIVIDEND_SCHEDULE.get(item['symbol'], [])
            if months_to_pay:
                if len(months_to_pay) == 12: month_tag = "月配息"
                else: month_tag = ",".join(map(str, months_to_pay)) + "月"
            else:
                month_tag = "-"
                
            tech_results.append({
                "ETF 名稱": display_name, 
                "配息月份": month_tag, 
                "股票張數": item['holdings'], 
                "現價": round(curr_p, 2),
                "今日損益": today_pnl_str, 
                "今日漲跌幅": today_pct_str, 
                "今日交易量": f"{vol:,.0f}" if vol > 0 else "無資料",
                "年殖利率": f"{est_yield:.2f}%", 
                "今日最高/最低": f"${day_high:.2f} / ${day_low:.2f}",
                "52週最高/最低": f"${year_high:.2f} / ${year_low:.2f}", 
                "設定高標(停利)": a_high, 
                "設定低標(停損)": a_low
            })
            
        except Exception as e: continue
        
    return pd.DataFrame(results), pd.DataFrame(tech_results), total_mkt, total_cost, total_div, total_today_pnl, price_alerts, monthly_calendar

df, df_tech, g_mkt, g_cost, g_div, g_today_pnl, price_alerts, monthly_calendar = fetch_data(st.session_state.my_data['etfs'], st.session_state.my_data.get('custom_divs', {}))

# --- 5. 介面呈現 ---
st.title("📈 實戰資產戰情室")
st.caption(f"最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if price_alerts:
    for alert in price_alerts:
        if alert['type'] == "high":
            st.markdown(f"<div class='alert-high'>🚨 突破停利高標：【{alert['name']}】 現價 ${alert['price']:.2f} 已突破您設定的 ${alert['target']}！</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='alert-low'>⚠️ 跌破停損低標：【{alert['name']}】 現價 ${alert['price']:.2f} 已跌破您設定的 ${alert['target']}！</div>", unsafe_allow_html=True)

# 重新計算總損益
total_net_profit = df['損益'].sum() if not df.empty else 0
r_total = (total_net_profit / g_cost * 100) if g_cost != 0 else 0
prev_mkt = g_mkt - g_today_pnl
today_pct = (g_today_pnl / prev_mkt * 100) if prev_mkt != 0 else 0

today_val_str = f"+{g_today_pnl:,.0f}" if g_today_pnl >= 0 else f"{g_today_pnl:,.0f}"
today_pct_str = f"+{today_pct:.2f}%" if today_pct >= 0 else f"{today_pct:.2f}%"
today_c_val = "triple-val-r" if g_today_pnl >= 0 else "triple-val-g"
today_c_pct = "triple-pct-r" if g_today_pnl >= 0 else "triple-pct-g"

total_val_str = f"+{total_net_profit:,.0f}" if total_net_profit >= 0 else f"{total_net_profit:,.0f}"
total_pct_str = f"+{r_total:.2f}%" if r_total >= 0 else f"{r_total:.2f}%"
total_c_val = "triple-val-r" if total_net_profit >= 0 else "triple-val-g"
total_c_pct = "triple-pct-r" if total_net_profit >= 0 else "triple-pct-g"

current_month_num = datetime.today().month
current_month_div_amount = monthly_calendar[current_month_num]["amount"]
current_month_div_str = f"${current_month_div_amount:,.0f}"
div_sources = monthly_calendar[current_month_num]["sources"]
if div_sources:
    sources_str = "、".join([s.split(' ')[0] for s in div_sources]) 
    sub_title = f"來自：{sources_str}"
else:
    sub_title = "本月無現金流入預定"

html_triple_pnl = f"""
<div class="triple-box">
    <div class="triple-col">
        <div class="triple-title">今日損益</div>
        <div class="{today_c_val}">{today_val_str}</div>
        <div class="{today_c_pct}">{today_pct_str}</div>
    </div>
    <div class="triple-col">
        <div class="triple-title">累積預估淨損益 (已扣手續費/稅)</div>
        <div class="{total_c_val}">{total_val_str}</div>
        <div class="{total_c_pct}">{total_pct_str}</div>
    </div>
    <div class="triple-col flash-gold-box">
        <div class="triple-title" style="color: #b48608; margin-bottom: 5px;">⚡ {current_month_num} 月預估領息總額</div>
        <div class="triple-val-gold">{current_month_div_str}</div>
        <div class="triple-sub-gold">{sub_title}</div>
    </div>
</div>
"""
st.markdown(html_triple_pnl, unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
c1.metric("股票總市值", f"${g_mkt:,.0f}")
c2.metric("投資總成本", f"${g_cost:,.0f}")
c3.metric("全年預估總領息", f"${sum([monthly_calendar[m]['amount'] for m in range(1, 13)]):,.0f}")
st.write("---")

cols_btn_r1 = st.columns(3)
cols_btn_r2 = st.columns(3)
cols_btn_r3 = st.columns(3)

b3_lbl, b3_typ = ("🔽 收起每月領息", "primary") if st.session_state.show_calendar else ("📅 展開每月領息", "secondary")
b4_lbl, b4_typ = ("🔽 收起除權息", "primary") if st.session_state.show_div_db else ("📂 展開除權息", "secondary")
b5_lbl, b5_typ = ("🔽 收起股價監控", "primary") if st.session_state.show_tech else ("📡 展開股價監控", "secondary")
b6_lbl, b6_typ = ("🔽 收起持股明細", "primary") if st.session_state.show_holdings else ("📊 展開持股明細", "secondary")
b7_lbl, b7_typ = ("🔽 收起ETF成份股", "primary") if st.session_state.show_constituents else ("🧩 展開ETF成份股", "secondary")
b8_lbl, b8_typ = ("🔽 收起質押專區", "primary") if st.session_state.show_pledge else ("🏦 展開質押專區", "secondary") 
b10_lbl, b10_typ = ("🔽 收起每日股價", "primary") if st.session_state.show_daily_price else ("🗓️ 展開每日股價", "secondary") 

with cols_btn_r1[0]: st.button(b3_lbl, on_click=toggle_calendar, type=b3_typ, use_container_width=True)
with cols_btn_r1[1]: st.button(b4_lbl, on_click=toggle_div_db, type=b4_typ, use_container_width=True)
with cols_btn_r1[2]: st.button(b5_lbl, on_click=toggle_tech, type=b5_typ, use_container_width=True)

with cols_btn_r2[0]: st.button(b6_lbl, on_click=toggle_holdings, type=b6_typ, use_container_width=True)
with cols_btn_r2[1]: st.button(b7_lbl, on_click=toggle_constituents, type=b7_typ, use_container_width=True) 
with cols_btn_r2[2]: st.button(b8_lbl, on_click=toggle_pledge, type=b8_typ, use_container_width=True) 

with cols_btn_r3[0]: st.button(b10_lbl, on_click=toggle_daily_price, type=b10_typ, use_container_width=True) 

st.write("---")

if st.session_state.show_calendar:
    st.markdown("#### 📅 1~12月 預估領息日曆")
    month_options = [f"{m} 月" for m in range(1, 13)]
    default_index = datetime.today().month - 1
    selected_month_str = st.selectbox("請選擇您想查詢的月份：", month_options, index=default_index)
    selected_month = int(selected_month_str.replace(" 月", ""))
    data = monthly_calendar[selected_month]
    sources_text = "、".join(data["sources"]) if data["sources"] else "本月無除息預定"
    amount_text = f"${data['amount']:,.0f}" if data["amount"] > 0 else "$0"
    col_space1, col_center, col_space2 = st.columns([1, 2, 1])
    with col_center:
        st.markdown(f"""
        <div class='month-card'>
            <div class='month-title'>{selected_month} 月預估領息</div>
            <div class='month-amount'>{amount_text}</div>
            <div class='month-sources'>ETF 來源：{sources_text}</div>
        </div>
        """, unsafe_allow_html=True)
    st.write("---")

if st.session_state.show_div_db:
    col_d1, col_d2 = st.columns([7, 3])
    with col_d1:
        st.markdown("#### 📚 專屬 ETF 與自選股 除權息時程總覽")
    with col_d2:
        if st.button("🔄 強制抓取最新公告", type="primary", use_container_width=True):
            with st.spinner("🚀 強制清洗快取並重新連線抓取中..."):
                time.sleep(0.6)
                st.cache_data.clear() 
            st.session_state.update_success = "已強制重新抓取最新資料！"
            st.rerun()

    db_list = []
    
    if not df.empty:
        for _, row in df.iterrows():
            sym = row['代號']; months = DIVIDEND_SCHEDULE.get(sym, [])
            freq = "月配息" if len(months)==12 else "季配息" if len(months)==4 else "半年配" if len(months)==2 else "年配息" if len(months)==1 else "未知"
            db_list.append({
                "類別": "💼 庫存",
                "ETF 名稱": row['名稱'], 
                "基金規模": row.get('基金規模', '系統無資料'),
                "配息頻率": freq, 
                "配息月份": "、".join(map(str, months)) + " 月" if months else "未設定",
                "狀態": row['狀態'],
                "除息日": row['最新公告除息日'], 
                "發放日": row['預估發放日'], 
                "每股金額": f"${row['每股配息']:.3f}",
                "最新填息紀錄": row['最新填息紀錄']
            })
            
    df_port_div = pd.DataFrame(db_list)
    df_wl_div = fetch_watchlist_dividend(st.session_state.my_data.get('watchlist', []), st.session_state.my_data.get('custom_divs', {}))
    
    final_div_df = pd.DataFrame()
    if not df_port_div.empty and not df_wl_div.empty:
        final_div_df = pd.concat([df_port_div, df_wl_div], ignore_index=True)
    elif not df_wl_div.empty:
        final_div_df = df_wl_div
    elif not df_port_div.empty:
        final_div_df = df_port_div
        
    if not final_div_df.empty:
        st.dataframe(final_div_df, use_container_width=True, hide_index=True)
    else:
        st.info("目前尚無庫存或自選股，因此無除權息資料可顯示。")
        
    with st.expander("🛠️ 手動配息覆蓋面板 (修正 Yahoo 資料庫延遲與領息試算)", expanded=False):
        st.caption("💡 投信剛公告但系統尚未抓到時，可直接在下方表格雙擊修改，按下儲存即可全站套用！(代號務必加上 .TW)")
        st.caption("💸 系統已自動帶入您的庫存資料與張數！您可以直接試算除息領取的總金額！")
        
        # 🔥 全新邏輯：自動抓取庫存清單，並與已儲存的手動配息資料結合
        custom_dict = st.session_state.my_data.get('custom_divs', {})
        display_list = []
        added_syms = set()

        # 1. 自動列出所有當前庫存 ETF
        for item in st.session_state.my_data.get('etfs', []):
            sym = item['symbol']
            name = item['name']
            c_info = custom_dict.get(sym, {})
            
            # 如果使用者沒有特別儲存覆蓋的張數，就自動帶入目前庫存的張數
            shares = c_info.get('s', 0.0)
            if shares == 0.0: 
                shares = item.get('holdings', 0.0)
                
            display_list.append({
                "代號": sym,
                "名稱": name,  # 🔥 新增名稱欄位
                "每股配息": c_info.get('v', 0.0),
                "除息日": c_info.get('d', ''),
                "發放日": c_info.get('p', ''),
                "持有張數": shares
            })
            added_syms.add(sym)

        # 2. 列出曾經手動設定，但目前不在庫存中的 ETF（例如自選股）
        for sym, c_info in custom_dict.items():
            if sym not in added_syms:
                clean_sym = sym.replace(".TW", "")
                name = ETF_NAME_DB.get(clean_sym, "自訂標的")
                display_list.append({
                    "代號": sym,
                    "名稱": name,
                    "每股配息": c_info.get('v', 0.0),
                    "除息日": c_info.get('d', ''),
                    "發放日": c_info.get('p', ''),
                    "持有張數": c_info.get('s', 0.0)
                })

        # 如果連一筆都沒有，給個預設空欄位
        if not display_list:
            display_list.append({"代號": "00878.TW", "名稱": "國泰永續高股息", "每股配息": 0.0, "除息日": "", "發放日": "", "持有張數": 0.0})

        df_custom = pd.DataFrame(display_list)
            
        edited_custom = st.data_editor(
            df_custom, 
            num_rows="dynamic", 
            use_container_width=True, 
            key="custom_div_editor",
            column_config={
                "代號": st.column_config.TextColumn("代號 (.TW)"),
                "名稱": st.column_config.TextColumn("名稱", disabled=True), # 🔥 設定名稱欄位防呆（禁止編輯）
                "每股配息": st.column_config.NumberColumn("每股配息 ($)", format="%.3f", min_value=0.0),
                "除息日": st.column_config.TextColumn("除息日 (YYYY-MM-DD)"),
                "發放日": st.column_config.TextColumn("發放日 (YYYY-MM-DD)"),
                "持有張數": st.column_config.NumberColumn("持有張數", format="%.1f", min_value=0.0)
            }
        )
        
        if st.button("💾 儲存手動覆蓋資料並套用", type="primary"):
            new_db = {}
            for _, row in edited_custom.iterrows():
                sym = str(row['代號']).strip()
                if sym and sym != "nan":
                    if not sym.endswith(".TW"): sym += ".TW"
                    
                    v_val = float(row['每股配息']) if pd.notna(row['每股配息']) else 0.0
                    d_val = str(row['除息日']) if pd.notna(row['除息日']) else ""
                    p_val = str(row['發放日']) if pd.notna(row['發放日']) else ""
                    s_val = float(row['持有張數']) if pd.notna(row['持有張數']) else 0.0
                    
                    # 只有當設定了大於 0 的配息或張數時，才真的寫入覆蓋資料庫
                    if v_val > 0 or s_val > 0:
                        new_db[sym] = {
                            "v": v_val,
                            "d": d_val,
                            "p": p_val,
                            "s": s_val
                        }
            st.session_state.my_data['custom_divs'] = new_db
            save_to_json(st.session_state.my_data)
            st.cache_data.clear() 
            st.session_state.update_success = "手動覆蓋資料已儲存並成功套用！"
            st.rerun()
            
        # --- 領息試算結果區塊 ---
        st.markdown("##### 💸 此次手動配息預估領息結果")
        calc_results = []
        for _, row in edited_custom.iterrows():
            sym = str(row['代號']).strip()
            name = str(row['名稱']).strip()
            if sym and sym != "nan":
                div_val = float(row['每股配息']) if pd.notna(row['每股配息']) else 0.0
                shares = float(row['持有張數']) if pd.notna(row['持有張數']) else 0.0
                if div_val > 0 and shares > 0:
                    total_div = div_val * shares * 1000
                    calc_results.append({
                        "標的": f"{sym} {name}",
                        "預估領息總額": f"${total_div:,.0f}"
                    })
        
        if calc_results:
            st.dataframe(pd.DataFrame(calc_results), hide_index=True, use_container_width=True)
        else:
            st.info("請於上方表格輸入大於 0 的「每股配息」，系統將根據您的張數自動為您試算。")

    st.write("---")

if st.session_state.show_tech:
    if not df.empty:
        st.markdown("#### 📡 庫存價格區間監控與技術分析")
        tech_col, auto_tech_col = st.columns([8.5, 1.5])
        
        with tech_col:
            if '配息月份' in df_tech.columns:
                df_tech = df_tech.sort_values(by='配息月份', ascending=True)
                
            def color_profit_loss(val):
                if isinstance(val, str):
                    if val.startswith('+'): return 'color: #d32f2f; font-weight: bold;' 
                    elif val.startswith('-'): return 'color: #388e3c; font-weight: bold;' 
                return ''
                
            def color_months(val):
                if not isinstance(val, str): return ''
                if val == '1,4,7,10月': return 'background-color: #e3f2fd; color: #1565c0; font-weight: bold; text-align: center;' 
                if val == '2,5,8,11月': return 'background-color: #f3e5f5; color: #6a1b9a; font-weight: bold; text-align: center;' 
                if val == '3,6,9,12月': return 'background-color: #e8f5e9; color: #2e7d32; font-weight: bold; text-align: center;' 
                if val == '月配息': return 'background-color: #fff8e1; color: #f57f17; font-weight: bold; text-align: center;' 
                return 'color: #555; text-align: center;'

            if "設定高標(停利)" in df_tech.columns and "設定低標(停損)" in df_tech.columns:
                df_tech_display = df_tech.drop(columns=["設定高標(停利)", "設定低標(停損)"])
            else:
                df_tech_display = df_tech

            try:
                styled_df_tech = df_tech_display.style.map(color_profit_loss, subset=['今日損益', '今日漲跌幅']).map(color_months, subset=['配息月份'])
            except AttributeError:
                styled_df_tech = df_tech_display.style.applymap(color_profit_loss, subset=['今日損益', '今日漲跌幅']).applymap(color_months, subset=['配息月份'])

            st.dataframe(
                styled_df_tech,
                column_config={
                    "現價": st.column_config.NumberColumn("現價", format="%.2f"),
                    "股票張數": st.column_config.NumberColumn("股票張數", format="%.1f") 
                },
                use_container_width=True, hide_index=True
            )
                
        with auto_tech_col:
            st.markdown("<div style='background-color: #f0f7ff; border: 1px solid #cce5ff; border-radius: 8px; padding: 10px 8px; text-align: center; box-shadow: 1px 1px 3px rgba(0,0,0,0.05);'>", unsafe_allow_html=True)
            st.markdown("<div style='font-size: 15px; font-weight: bold; color: #1e3c72; margin-bottom: 4px;'>⚡ 自動更新</div>", unsafe_allow_html=True)
            st.markdown("<div style='font-size: 11px; color: #6c757d; margin-bottom: 10px; line-height: 1.2;'>每 5 秒即時重整</div>", unsafe_allow_html=True)
            
            if 'auto_refresh_mode' not in st.session_state:
                st.session_state.auto_refresh_mode = "❌ NO USE (關閉)"
                
            auto_update = st.radio(
                "即時更新", 
                ["❌ NO USE (關閉)", "✅ USE (開啟)"], 
                key="auto_refresh_mode",
                horizontal=False,
                label_visibility="collapsed"
            )
            st.markdown("</div>", unsafe_allow_html=True)

        st.write("")
        st.markdown("#### 📊 詳細持股清單與內扣費率")
        st.dataframe(df.style.format({"現價":"{:.2f}", "均價":"{:.2f}", "市值":"{:,.0f}", "損益":"{:,.0f}"}), use_container_width=True, hide_index=True)

    else:
        st.markdown("#### 📡 庫存價格區間監控")
        st.info("目前無庫存標的。")
        
    st.write("---")
    
    st.markdown("#### 👀 自選股觀察清單")
    st.caption("追蹤您尚未入手、正在觀察的標的")
    
    col_w1, col_w2, col_w3 = st.columns([2, 2, 1])
    with col_w1:
        st.text_input("輸入代碼 (不需手打 .TW)", placeholder="例如: 2330", key="add_sym_wl", on_change=auto_fill_wl_name)
    with col_w2:
        st.text_input("自定義名稱", placeholder="例如: 2330 台積電", key="add_name_wl")
    with col_w3:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        st.button("➕ 加入名單", key="btn_add_wl", on_click=add_new_wl, use_container_width=True)

    wl_df = fetch_watchlist_data(st.session_state.my_data.get('watchlist', []))
    if not wl_df.empty:
        def color_diff(val):
            if isinstance(val, str) and '%' in val:
                if val.startswith('+'): return 'color: #d32f2f; font-weight: bold;'
                elif val.startswith('-'): return 'color: #388e3c; font-weight: bold;'
            elif isinstance(val, (int, float)):
                if val > 0: return 'color: #d32f2f; font-weight: bold;'
                elif val < 0: return 'color: #388e3c; font-weight: bold;'
            return ''
        
        try:
            styled_wl = wl_df.style.map(color_diff, subset=['漲跌', '漲跌幅'])
        except AttributeError:
            styled_wl = wl_df.style.applymap(color_diff, subset=['漲跌', '漲跌幅'])
            
        st.dataframe(styled_wl, use_container_width=True, hide_index=True)
        
        with st.expander("🗑️ 管理與刪除自選股"):
            for i, item in enumerate(st.session_state.my_data['watchlist']):
                cols_wl_del = st.columns([3, 1, 6])
                cols_wl_del[0].markdown(f"📍 **{item['name']}**")
                cols_wl_del[1].button("刪除", key=f"del_wl_{i}", on_click=delete_wl, args=(i,), use_container_width=True)
    else:
        st.info("目前尚無自選股。請在上方輸入代碼新增您的觀察名單！")

    st.write("---")

if st.session_state.show_holdings:
    if not df.empty:
        st.markdown("#### 📊 持股動態明細")
        for _, row in df.iterrows():
            p_color = "red" if row['損益'] >= 0 else "green"; roi_str = f"{row['報酬率']:+.2f}%"
            status_badge = row['狀態']
            with st.expander(f"💎 {row['名稱']} | 預估淨報酬: :{p_color}[{roi_str}]", expanded=True):
                col_l, col_m, col_r = st.columns(3)
                with col_l: st.write(f"張數: **{row['張數']}**"); st.write(f"現價: **{row['現價']:.2f}**"); st.caption(f"均價: {row['均價']:.2f}")
                with col_m: st.markdown(f"市值: **${row['市值']:,.0f}**"); st.markdown(f"預估淨利: :{p_color}[**${row['損益']:,.0f}**]")
                with col_r: st.markdown(f"單次領息估算: :orange[**${row['單次預估領息']:,.0f}**]"); st.caption(f"📅 最新除息日: {row['最新公告除息日']} ({status_badge})")
    else:
        st.info("⚠️ 目前尚無持股資料。請至下方「⚙️ 標的管理」新增您的庫存！")
    st.write("---")

if st.session_state.show_constituents:
    if not df.empty:
        st.markdown("#### 🧩 專屬庫存 ETF 核心成分股佔比")
        st.caption("已開啟「直接顯示比例」模式。透過圓餅圖檢視成分股，可協助您避免資金過度集中於單一個股，降低系統性風險。")
        
        c_cols = st.columns(3)
        for idx, item in enumerate(st.session_state.my_data['etfs']):
            sym = item['symbol']
            name = item['name']
            
            comp_data = ETF_CONSTITUENTS_DB.get(sym, [{"name": "其他成分股", "weight": 100.0}])
            df_comp = pd.DataFrame(comp_data)
            
            df_comp['label'] = df_comp['weight'].apply(lambda w: f"{w:.1f}%" if w >= 2.0 else "")
            
            base = alt.Chart(df_comp).encode(
                theta=alt.Theta("weight:Q", stack=True),
                color=alt.Color("name:N", 
                                sort=alt.EncodingSortField(field="weight", op="sum", order="descending"), 
                                legend=alt.Legend(title=None, orient="right", labelFontSize=12)),
                tooltip=[
                    alt.Tooltip("name:N", title="成分股"),
                    alt.Tooltip("weight:Q", title="權重 (%)", format=".2f")
                ]
            )
            
            pie = base.mark_arc(outerRadius=100, innerRadius=0)
            
            text = base.mark_text(radius=125, size=13, fontWeight="bold", color="#333333").encode(
                text="label:N"
            )
            
            chart = alt.layer(pie, text).properties(
                height=280
            ).configure_view(strokeWidth=0)
            
            with c_cols[idx % 3]:
                st.markdown(f"<div style='font-weight:900; color:#1e3c72; font-size:16px; margin-bottom:5px; margin-top:15px;'>🛡️ {name}</div>", unsafe_allow_html=True)
                st.altair_chart(chart, use_container_width=True)
    else:
        st.info("⚠️ 目前尚無持股資料。請至下方「⚙️ 標的管理」新增您的庫存！")
    st.write("---")

if st.session_state.show_daily_price:
    st.markdown("#### 🗓️ 庫存 ETF 每日統計數據 (近 30 個交易日)")
    
    port_map = {item['symbol']: f"💼 {item['name']}" for item in st.session_state.my_data.get('etfs', [])}
    current_symbols = list(port_map.keys())
    
    if current_symbols:
        with st.spinner("📡 正在向資料庫調閱歷史數據... (啟用強制補正機制)"):
            try:
                hist_data = yf.download(current_symbols, period="2mo")['Close']
                
                if len(current_symbols) == 1:
                    hist_data = hist_data.to_frame()
                    hist_data.columns = [port_map[current_symbols[0]]]
                else:
                    hist_data = hist_data.rename(columns=port_map)
                
                hist_data = hist_data.dropna(how='all')
                
                today_str = datetime.now().strftime('%Y-%m-%d')
                today_dt = pd.to_datetime(today_str)
                
                if today_dt not in hist_data.index:
                    hist_data.loc[today_dt] = [None] * len(hist_data.columns)
                
                hist_data = hist_data.sort_index()
                
                for sym in current_symbols:
                    mapped_name = port_map[sym]
                    try:
                        live_price = df[df['代號'] == sym]['現價'].values[0]
                        hist_data.loc[hist_data.index[-1], mapped_name] = live_price
                    except:
                        pass
                        
                hist_data = hist_data.ffill()
                
                diff_data = hist_data.diff()
                
                hist_data = hist_data.tail(30)
                diff_data = diff_data.tail(30)
                
                hist_data.index = hist_data.index.strftime('%m/%d')
                diff_data.index = diff_data.index.strftime('%m/%d')
                
                h_display = hist_data.iloc[::-1].T
                d_display = diff_data.iloc[::-1].T
                
                valid_port_names = [name for name in port_map.values() if name in h_display.index]
                
                if valid_port_names:
                    st.markdown("##### 📉 每日收盤價與漲跌 (庫存)")
                    
                    combined_df = pd.DataFrame(index=valid_port_names, columns=h_display.columns)
                    
                    for etf_name in valid_port_names:
                        for col in h_display.columns:
                            price = h_display.loc[etf_name, col]
                            diff = d_display.loc[etf_name, col]
                            
                            if pd.isna(price) or pd.isna(diff):
                                combined_df.loc[etf_name, col] = "-"
                            else:
                                sign = "+" if diff > 0 else ""
                                combined_df.loc[etf_name, col] = f"{price:.2f} ({sign}{diff:.2f})"

                    def color_price_diff(df_to_style):
                        css = pd.DataFrame('', index=df_to_style.index, columns=df_to_style.columns)
                        for idx in df_to_style.index:
                            for col in df_to_style.columns:
                                val_str = str(df_to_style.loc[idx, col])
                                if "(+" in val_str:
                                    css.loc[idx, col] = 'color: #d32f2f; font-weight: bold;'
                                elif "(-" in val_str:
                                    css.loc[idx, col] = 'color: #388e3c; font-weight: bold;'
                                elif "-" not in val_str:
                                    css.loc[idx, col] = 'color: #555;'
                        return css

                    st.dataframe(combined_df.style.apply(color_price_diff, axis=None), use_container_width=True)
                    st.caption("💡 提示：數值格式為 `收盤價 (漲跌)`。紅色代表上漲，綠色代表下跌。系統已啟動強效補正機制，確保不再有缺漏。")
                else:
                    st.info("⚠️ 目前無有效庫存數據。")
            except Exception as e:
                st.error(f"無法抓取每日數據：{e}")
    else:
        st.info("⚠️ 目前無庫存資料。")
    st.write("---")

if st.session_state.show_pledge:
    if not df.empty:
        st.markdown("#### 🏦 股票質押專區 (維持率監控)")
        st.info("💡 股票質押後會從一般券商庫存消失。一般券商最高可借出擔保品市值的 60%。請先「打勾選取」欲質押標的，再輸入已借款項！")
        
        pledge_data = st.session_state.my_data['pledge']
        borrowed = st.number_input("💸 輸入已向券商借入款項總額 (元)", min_value=0, value=int(pledge_data.get('borrowed_amount', 0)), step=10000)
        
        if borrowed != pledge_data.get('borrowed_amount', 0):
            st.session_state.my_data['pledge']['borrowed_amount'] = borrowed
            save_to_json(st.session_state.my_data)
            st.rerun()

        pledge_df_list = []
        total_pledge_mkt = 0
        total_borrowable = 0
        for item in st.session_state.my_data['etfs']:
            sym = item['symbol']
            name = item['name']
            h_total = item['holdings']
            p_shares = item.get('pledged_shares', 0.0)
            is_pledged = item.get('is_pledged', False) # 讀取打勾狀態
            
            try:
                curr_p = df[df['代號'] == sym]['現價'].values[0]
            except:
                curr_p = 0
                
            original_mkt = h_total * 1000 * curr_p
                
            p_mkt = p_shares * 1000 * curr_p if is_pledged else 0
            p_limit = p_mkt * 0.6 if is_pledged else 0
            total_pledge_mkt += p_mkt
            total_borrowable += p_limit
            
            pledge_df_list.append({
                "✓ 選取": is_pledged,
                "ETF 名稱": name,
                "總庫存 (張)": h_total,
                "庫存市值 (元)": round(original_mkt, 0),
                "質押張數": p_shares,
                "現價": round(curr_p, 2),
                "質押市值 (元)": round(p_mkt, 0),
                "可借上限 (60%)": round(p_limit, 0) 
            })
            
        pledge_df = pd.DataFrame(pledge_df_list)
        margin_ratio = (total_pledge_mkt / borrowed * 100) if borrowed > 0 else 0
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("擔保品總市值", f"${total_pledge_mkt:,.0f}")
        col_m2.metric("🎯 總可借款上限 (60%)", f"${total_borrowable:,.0f}")
        col_m3.metric("💸 已借入總額", f"${borrowed:,.0f}")
        
        if borrowed > 0:
            if margin_ratio < 130:
                col_m4.metric("🚨 目前維持率", f"{margin_ratio:.2f}%", "危險：低於 130% 將面臨斷頭", delta_color="inverse")
                st.error("🚨 警告：您的維持率已跌破 130%，請盡速補繳保證金或償還部分借款！")
            elif margin_ratio < 160:
                col_m4.metric("⚠️ 目前維持率", f"{margin_ratio:.2f}%", "注意：市場波動可能導致風險", delta_color="off")
            else:
                col_m4.metric("✅ 目前維持率", f"{margin_ratio:.2f}%", "安全：維持率處於健康水平", delta_color="normal")
        else:
            col_m4.metric("目前維持率", "0.00%")

        st.write("👇 **請勾選欲質押的標的，並雙擊「質押張數」欄位設定數量：**")
        edited_pledge = st.data_editor(
            pledge_df,
            column_config={
                "✓ 選取": st.column_config.CheckboxColumn("✓ 選取質押", help="勾選後才會計入擔保品總市值"),
                "質押張數": st.column_config.NumberColumn("質押張數 (雙擊編輯)", min_value=0.0, step=1.0, format="%.1f"),
                "庫存市值 (元)": st.column_config.NumberColumn("庫存市值 (元)", format="%.0f"),
                "現價": st.column_config.NumberColumn("現價", format="%.2f"),
                "質押市值 (元)": st.column_config.NumberColumn("質押市值 (元)", format="%.0f"),
                "可借上限 (60%)": st.column_config.NumberColumn("可借上限 (60%)", format="%.0f") 
            },
            disabled=["ETF 名稱", "總庫存 (張)", "庫存市值 (元)", "現價", "質押市值 (元)", "可借上限 (60%)"],
            use_container_width=True, hide_index=True
        )
        
        has_p_changes = False
        for _, row in edited_pledge.iterrows():
            p_name = row['ETF 名稱']
            new_is_pledged = row['✓ 選取']
            new_p_shares = row['質押張數']
            
            for etf in st.session_state.my_data['etfs']:
                if etf['name'] == p_name:
                    if new_p_shares > etf['holdings']:
                        new_p_shares = etf['holdings']
                        
                    if etf.get('pledged_shares', 0.0) != new_p_shares or etf.get('is_pledged', False) != new_is_pledged:
                        etf['pledged_shares'] = new_p_shares
                        etf['is_pledged'] = new_is_pledged
                        has_p_changes = True
                    break
        if has_p_changes:
            save_to_json(st.session_state.my_data)
            st.rerun()
    else:
        st.info("⚠️ 目前尚無持股資料，無法進行質押計算。")
    st.write("---")

with st.expander("💰 買賣損益試算器", expanded=False):
    st.markdown("<div class='calc-title'>依照即時現價，試算買進或賣出後的損益狀況，並可直接寫入庫存！</div>", unsafe_allow_html=True)
    
    if not df.empty:
        calc_options = [row['名稱'] for _, row in df.iterrows()]
        
        if 'calc_selected_etf' not in st.session_state: st.session_state.calc_selected_etf = calc_options[0]
        if 'calc_trade_type' not in st.session_state: st.session_state.calc_trade_type = "賣出 (計算已實現損益)"
        if 'calc_trade_shares' not in st.session_state: st.session_state.calc_trade_shares = 1.0
        
        st.selectbox("選擇要操作的庫存標的：", calc_options, key="calc_selected_etf")
        
        target_row = df[df['名稱'] == st.session_state.calc_selected_etf].iloc[0]
        current_price = target_row['現價']
        current_cost = target_row['均價']
        current_holdings = target_row['張數']
        
        st.info(f"📍 **{st.session_state.calc_selected_etf}** | 目前庫存：{current_holdings} 張 | 庫存均價：${current_cost:.2f} | 系統即時現價：${current_price:.2f}")
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.radio("交易動作：", ["賣出 (計算已實現損益)", "買進 (計算買入成本與新均價)"], key="calc_trade_type")
        with col_c2:
            st.number_input("輸入交易張數", min_value=0.1, step=1.0, key="calc_trade_shares")
            
        if st.session_state.calc_trade_type == "賣出 (計算已實現損益)":
            trade_shares_display = st.session_state.calc_trade_shares
            if trade_shares_display > current_holdings:
                st.warning(f"⚠️ 賣出張數 ({trade_shares_display}) 大於目前庫存 ({current_holdings})，將以全數出清試算並執行。")
                trade_shares_display = current_holdings
                
            realized_profit = (current_price - current_cost) * trade_shares_display * 1000
            
            st.markdown("<div class='calc-box'>", unsafe_allow_html=True)
            st.write(f"📝 試算賣出 **{trade_shares_display}** 張")
            if realized_profit > 0:
                st.markdown(f"🎉 預估已實現損益 (賺)：<div class='calc-result-profit'>+${realized_profit:,.0f}</div>", unsafe_allow_html=True)
            elif realized_profit < 0:
                st.markdown(f"📉 預估已實現損益 (賠)：<div class='calc-result-loss'>-${abs(realized_profit):,.0f}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"⚖️ 預估已實現損益：<div style='font-size: 24px; font-weight: bold; margin-top: 10px;'>$0</div>", unsafe_allow_html=True)
                
            st.markdown(f"<div class='calc-result-info'>*不含手續費與證交稅，成交價以系統抓取之現價 ${current_price:.2f} 計算</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.button("💾 確認賣出並更新庫存", type="primary", use_container_width=True, on_click=execute_trade)
            
        else:
            trade_shares_display = st.session_state.calc_trade_shares
            buy_cost_total = current_price * trade_shares_display * 1000
            new_total_shares = current_holdings + trade_shares_display
            new_total_cost_val = (current_cost * current_holdings * 1000) + buy_cost_total
            new_avg_cost = new_total_cost_val / (new_total_shares * 1000) if new_total_shares > 0 else 0
            
            st.markdown("<div class='calc-box'>", unsafe_allow_html=True)
            st.write(f"📝 試算買進 **{trade_shares_display}** 張")
            st.markdown(f"💸 預估買入總花費：<div style='font-size: 24px; font-weight: bold; margin-top: 10px;'>${buy_cost_total:,.0f}</div>", unsafe_allow_html=True)
            st.markdown(f"🎯 買入後全新均價：<div style='font-size: 20px; font-weight: bold; color: #1e3c72; margin-top: 10px;'>${new_avg_cost:.2f}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='calc-result-info'>*總庫存將變為 {new_total_shares} 張。不含手續費，成交價以系統抓取之現價 ${current_price:.2f} 計算</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.button("💾 確認買進並更新庫存", type="primary", use_container_width=True, on_click=execute_trade)
            
    else:
        st.warning("請先在下方「標的管理」新增庫存，才能進行試算喔！")

st.write("---")

bot_c1, bot_c2 = st.columns([3, 7])

with bot_c1:
    if st.button("🔄 手動重新整理股價", use_container_width=True):
        fetch_data.clear()
        fetch_watchlist_dividend.clear()
        fetch_taiwan_upcoming_dividends.clear()
        st.rerun()

with bot_c2:
    with st.expander("⚙️ 標的管理 (庫存新增 / 修改 / 刪除)", expanded=True):
        st.markdown("#### ➕ 新增庫存標的 (股票/ETF)")
        
        if "add_name_bot" not in st.session_state: st.session_state.add_name_bot = ""
        if "add_sym_bot" not in st.session_state: st.session_state.add_sym_bot = ""
        if "add_h_bot" not in st.session_state: st.session_state.add_h_bot = 0.0
        if "add_c_bot" not in st.session_state: st.session_state.add_c_bot = 0.0

        st.text_input("輸入代碼 (不需手打 .TW)", placeholder="例如: 00878 或 00981A", key="add_sym_bot", on_change=auto_fill_etf_name)
        st.text_input("自定義名稱", placeholder="例如: 00878 國泰永續高股息", key="add_name_bot")
        
        col_add1, col_add2 = st.columns(2)
        with col_add1:
            st.number_input("張數", step=1.0, key="add_h_bot")
        with col_add2:
            st.number_input("均價", step=0.1, key="add_c_bot")
        
        st.button("確認新增庫存", key="btn_add_bot", use_container_width=True, on_click=add_new_etf_bot)

        if st.session_state.my_data['etfs']:
            st.write("---")
            st.markdown("#### 📝 庫存修改與刪除")
            
            for i, item in enumerate(st.session_state.my_data['etfs']):
                with st.expander(f"📍 {item['name']}"):
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        st.number_input("張數", value=float(item['holdings']), step=1.0, key=f"edit_h_{i}")
                    with col_e2:
                        st.number_input("均價", value=float(item['cost']), step=0.1, key=f"edit_c_{i}")

                    st.button(f"🗑️ 刪除 {item['name']}", key=f"del_{i}", on_click=delete_etf, args=(i,), use_container_width=True)

            st.button("💾 儲存所有修改", use_container_width=True, type="primary", on_click=save_edits)

if st.session_state.get('auto_refresh_mode') == "✅ USE (開啟)":
    time.sleep(5)
    st.cache_data.clear() 
    st.rerun()
