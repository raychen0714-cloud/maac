import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time
import altair as alt
import requests  

# --- 1. 網頁基礎設定 ---
st.set_page_config(page_title="ETF 投資戰情室", layout="wide")

# 自定義 CSS
st.markdown("""
    <style>
    [data-testid="stMetricDelta"] svg { fill: red; }
    .stMetric { background-color: #f8f9fa; padding: 10px; border-radius: 10px; }
    
    .news-box { background-color: #f0f7ff; border-left: 6px solid #4a90e2; padding: 20px; border-radius: 8px; margin-bottom: 25px; box-shadow: 1px 1px 4px rgba(0,0,0,0.05); }
    .news-title { font-size: 20px; font-weight: bold; color: #1e3c72; margin-bottom: 15px; display: flex; align-items: center; }
    .news-item { font-size: 16px; color: #333; margin-bottom: 12px; line-height: 1.5; font-weight: 500;}
    .news-item a { text-decoration: none; color: #1e3c72; transition: color 0.2s;}
    .news-item a:hover { text-decoration: underline; color: #d32f2f; }

    /* 雙重雷達 */
    .ex-div-box { background-color: #ffeaea; border: 1.5px solid #e06666; border-radius: 8px; padding: 10px; text-align: center; margin-bottom: 15px; height: 115px; display: flex; flex-direction: column; justify-content: center; box-shadow: 1px 1px 3px rgba(0,0,0,0.05); overflow-y: auto;}
    .ex-div-title { color: #cc0000; font-weight: bold; font-size: 13px; margin-bottom: 4px; }
    .ex-div-text { color: #783f04; font-size: 12px; font-weight: bold; line-height: 1.4; }
    
    .pay-div-box { background-color: #fff2cc; border: 1.5px solid #f6b26b; border-radius: 8px; padding: 10px; text-align: center; margin-bottom: 15px; height: 115px; display: flex; flex-direction: column; justify-content: center; box-shadow: 1px 1px 3px rgba(0,0,0,0.05); overflow-y: auto;}
    .pay-div-title { color: #b45f06; font-weight: bold; font-size: 13px; margin-bottom: 4px; }
    .pay-div-text { color: #783f04; font-size: 12px; font-weight: bold; line-height: 1.4; }

    /* 三拼損益與領息橫列大看板樣式 (升級為四拼) */
    .triple-box { background-color: #ffffff; border-radius: 12px; border: 1px solid #e0e0e0; padding: 15px; display: flex; flex-wrap: wrap; justify-content: space-around; align-items: center; margin-bottom: 10px; box-shadow: 2px 2px 8px rgba(0,0,0,0.04); gap: 10px; }
    .triple-col { flex: 1 1 22%; min-width: 140px; text-align: center; padding: 10px 0; }
    .triple-title { font-size: 14px; color: #757575; font-weight: bold; margin-bottom: 5px; }
    .triple-val-r { font-size: 28px; font-weight: 900; color: #b71c1c; font-family: Arial, sans-serif; line-height: 1.1; }
    .triple-val-g { font-size: 28px; font-weight: 900; color: #2e7d32; font-family: Arial, sans-serif; line-height: 1.1; }
    .triple-val-gold { font-size: 28px; font-weight: 900; color: #f39c12; font-family: Arial, sans-serif; line-height: 1.1; text-shadow: 1px 1px 2px rgba(243, 156, 18, 0.3); }
    .triple-pct-r { font-size: 14px; font-weight: bold; color: #b71c1c; margin-top: 5px; }
    .triple-pct-g { font-size: 14px; font-weight: bold; color: #2e7d32; margin-top: 5px; }
    .triple-sub-gold { font-size: 12px; font-weight: bold; color: #7f8c8d; margin-top: 5px; }

    .blue-box { background-color: #f0f8ff; border-radius: 12px; padding: 15px; border: 2px solid #90caf9; }
    .triple-val-blue { font-size: 28px; font-weight: 900; color: #1565c0; font-family: Arial, sans-serif; line-height: 1.1; text-shadow: 1px 1px 2px rgba(21, 101, 192, 0.2); }
    .triple-sub-blue { font-size: 12px; font-weight: bold; color: #546e7a; margin-top: 5px; }

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

    .upcoming-box { background-color: #fff4e6; border: 1px solid #ffd8a8; border-radius: 8px; padding: 8px 10px; text-align: center; margin-bottom: 15px; box-shadow: 1px 1px 3px rgba(0,0,0,0.05); }
    .upcoming-title { color: #d9480f; font-weight: bold; font-size: 13px; margin-bottom: 4px; }
    .upcoming-item { color: #862e01; font-size: 13px; font-weight: bold; margin-bottom: 2px; }
    .upcoming-price { font-size: 11px; color: #888; }
    
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

PASSIVE_ETFS = {
    "0050": "0050 元大台灣50", "006208": "006208 富邦台50", "00692": "00692 富邦公司治理", 
    "00850": "00850 元大台灣ESG永續", "00922": "00922 國泰台灣領袖50", "00923": "00923 群益台ESG低碳50",
    "0056": "0056 元大高股息", "00878": "00878 國泰永續高股息", "00713": "00713 元大台灣高息低波",
    "00900": "00900 富邦特選高股息30", "00915": "00915 凱基優選高股息30", "00918": "00918 大華優利高填息30",
    "00919": "00919 群益台灣精選高息", "00929": "00929 復華台灣科技優息", "00936": "00936 台新永續高息中小",
    "00939": "00939 統一台灣高息動能", "00940": "00940 元大台灣價值高息", "00944": "00944 野村趨勢動能高息", 
    "00946": "00946 群益科技高息成長", "0052": "0052 富邦科技", "00881": "00881 國泰台灣5G+", 
    "00891": "00891 中信關鍵半導體", "00892": "00892 富邦台灣半導體", "00927": "00927 群益半導體收益", 
    "00935": "00935 野村臺灣新科技50", "00941": "00941 中信上游半導體", "00893": "00893 國泰智能電動車", 
    "00895": "00895 富邦未來車", "00646": "00646 元大S&P500", "00662": "00662 富邦NASDAQ", 
    "00830": "00830 國泰費城半導體", "00757": "00757 統一FANG+", "00882": "00882 中信中國高股息", 
    "00962": "00962 洲際美國大型龍頭", "00963": "00963 中信全球高股息", "00964": "00964 中信亞太高股息",
    "00679B": "00679B 元大美債20年", "00687B": "00687B 國泰20年美債", "00720B": "00720B 元大投資級公司債",
    "00751B": "00751B 元大AAA至A公司債", "00937B": "00937B 群益ESG投等債20+", "00772B": "00772B 中信高評級公司債",
    "00773B": "00773B 中信優先金融債", "00780B": "00780B 國泰A級金融債", "00795B": "00795B 中信美國公債20年",
    "2330": "2330 台積電", "2454": "2454 聯發科", "2317": "2317 鴻海",
    "00631L": "00631L 元大台灣50正2", "00673R": "00673R 期元大S&P原油反1", 
    "00632R": "00632R 元大台灣50反1", "009819": "009819 中信數據及電力", 
    "00712": "00712 復華富時不動產"
}

ACTIVE_ETFS = {
    "00981A": "00981A 主動統一台股增長",
    "00403A": "00403A 主動統一台股升級50",
    "00999A": "00999A 主動野村臺灣動能",
    "00401A": "00401A 主動摩根台灣鑫收",
    "00992A": "00992A 主動群益科技創新",
    "00400A": "00400A 主動國泰動能高息",
    "00997A": "00997A 主動群益美國增長",
    "00988A": "00988A 主動統一全球創新",
    "00994A": "00994A 主動第一金台股優",
}

ETF_NAME_DB = {**PASSIVE_ETFS, **ACTIVE_ETFS}

DIVIDEND_SCHEDULE = {
    "0050.TW": [1, 7], "0056.TW": [1, 4, 7, 10], "00878.TW": [2, 5, 8, 11],
    "00891.TW": [2, 5, 8, 11], "00919.TW": [3, 6, 9, 12], "00927.TW": [1, 4, 7, 10],
    "00929.TW": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], "00940.TW": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
}

DIVIDEND_DB = {
    "0056.TW": {"v": 1.00, "d": "2026-04-16", "p": "2026-05-15"}, 
    "00927.TW": {"v": 0.94, "d": "2026-04-18", "p": "2026-05-15"},  
    "00878.TW": {"v": 0.66, "d": "2026-05-19", "p": "2026-06-16"},   
    "00891.TW": {"v": 1.25, "d": "2026-05-19", "p": "2026-06-16"},   
    "00982A.TW": {"v": 0.64, "d": "2026-05-19", "p": "2026-06-16"},  
}

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
    "00940.TW": [{"name": "長榮", "weight": 9.5}, {"name": "聯電", "weight": 6.5}, {"name": "聯發科", "weight": 5.8}, {"name": "中美晶", "weight": 5.2}, {"name": "神基", "weight": 4.8}, {"name": "其他", "weight": 68.2}]
}

# --- 2. 系統設定與資料庫 ---
# 💡 將朋友的存檔獨立出來，才不會蓋掉你自己的 settings.json！
SETTINGS_FILE = 'friend_settings.json' 

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    
    # 這裡已經幫你把截圖裡的持股全部換算成初始設定檔了！
    return {
        "etfs": [
            {"symbol": "0050.TW", "name": "0050 元大台灣50", "holdings": 40.0, "cost": 140.09, "alert_high": 0.0, "alert_low": 0.0, "pledged_shares": 0.0},
            {"symbol": "006208.TW", "name": "006208 富邦台50", "holdings": 10.0, "cost": 89.04, "alert_high": 0.0, "alert_low": 0.0, "pledged_shares": 0.0},
            {"symbol": "00757.TW", "name": "00757 統一FANG+", "holdings": 15.0, "cost": 60.27, "alert_high": 0.0, "alert_low": 0.0, "pledged_shares": 0.0},
            {"symbol": "00878.TW", "name": "00878 國泰永續高股息", "holdings": 50.0, "cost": 20.53, "alert_high": 0.0, "alert_low": 0.0, "pledged_shares": 0.0},
            {"symbol": "00919.TW", "name": "00919 群益台灣精選高息", "holdings": 60.0, "cost": 23.14, "alert_high": 0.0, "alert_low": 0.0, "pledged_shares": 0.0},
            {"symbol": "2330.TW", "name": "2330 台積電", "holdings": 3.0, "cost": 683.47, "alert_high": 0.0, "alert_low": 0.0, "pledged_shares": 0.0},
            {"symbol": "2454.TW", "name": "2454 聯發科", "holdings": 2.0, "cost": 879.43, "alert_high": 0.0, "alert_low": 0.0, "pledged_shares": 0.0}
        ], 
        "pledge": {"borrowed_amount": 0},
        "watchlist": [] 
    }

def save_to_json(data):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

if 'my_data' not in st.session_state: 
    st.session_state.my_data = load_settings()

if 'watchlist' not in st.session_state.my_data:
    st.session_state.my_data['watchlist'] = []

if 'pledge' not in st.session_state.my_data:
    st.session_state.my_data['pledge'] = {"borrowed_amount": 0}

if 'total_received_divs' not in st.session_state.my_data:
    st.session_state.my_data['total_received_divs'] = 0.0

for etf in st.session_state.my_data['etfs']:
    if 'pledged_shares' not in etf:
        etf['pledged_shares'] = 0.0
save_to_json(st.session_state.my_data)

# --- 🚀 Callback 函數區 ---
def auto_fill_etf_name():
    raw_sym = st.session_state.get('add_sym_bot', '')
    clean_sym = raw_sym.strip().upper().replace(".TW", "")
    if clean_sym:
        st.session_state.add_name_bot = ETF_NAME_DB.get(clean_sym, f"{clean_sym} ETF")
    else:
        st.session_state.add_name_bot = ""

def add_new_etf_bot():
    raw_sym = st.session_state.get('add_sym_bot', '')
    new_name = st.session_state.get('add_name_bot', '')
    new_h = st.session_state.get('add_h_bot', 0.0)
    new_c = st.session_state.get('add_c_bot', 0.0)

    clean_symbol = raw_sym.strip().upper().replace(".TW", "")
    if clean_symbol and new_name:
        final_symbol = f"{clean_symbol}.TW" 
        
        st.session_state.my_data['etfs'].append({
            "symbol": final_symbol, "name": new_name, 
            "holdings": new_h, "cost": new_c, "alert_high": 0.0, "alert_low": 0.0, "pledged_shares": 0.0
        })
        save_to_json(st.session_state.my_data)
        
        st.session_state.add_sym_bot = ""
        st.session_state.add_name_bot = ""
        st.session_state.add_h_bot = 0.0
        st.session_state.add_c_bot = 0.0

def delete_etf(index):
    if 0 <= index < len(st.session_state.my_data['etfs']):
        st.session_state.my_data['etfs'].pop(index)
        save_to_json(st.session_state.my_data)

def move_etf_up(index):
    if index > 0:
        st.session_state.my_data['etfs'][index - 1], st.session_state.my_data['etfs'][index] = \
        st.session_state.my_data['etfs'][index], st.session_state.my_data['etfs'][index - 1]
        save_to_json(st.session_state.my_data)

def move_etf_down(index):
    if index < len(st.session_state.my_data['etfs']) - 1:
        st.session_state.my_data['etfs'][index + 1], st.session_state.my_data['etfs'][index] = \
        st.session_state.my_data['etfs'][index], st.session_state.my_data['etfs'][index + 1]
        save_to_json(st.session_state.my_data)

def save_edits():
    temp_list = []
    # 這裡將綁定的 key 改為 symbol，避免上下移動時數字殘留
    for item in st.session_state.my_data['etfs']:
        sym = item['symbol']
        h_val = st.session_state.get(f"edit_h_{sym}", item['holdings'])
        c_val = st.session_state.get(f"edit_c_{sym}", item['cost'])
        temp_list.append({
            "symbol": item['symbol'],
            "name": item['name'],
            "holdings": h_val,
            "cost": c_val,
            "alert_high": item.get('alert_high', 0.0),
            "alert_low": item.get('alert_low', 0.0),
            "pledged_shares": item.get('pledged_shares', 0.0),
            "ex_div_shares_custom": item.get('ex_div_shares_custom', h_val)
        })
    st.session_state.my_data['etfs'] = temp_list
    save_to_json(st.session_state.my_data)

# --- 自選股 Callback ---
def auto_fill_wl_name():
    raw_sym = st.session_state.get('add_sym_wl', '')
    clean_sym = raw_sym.strip().upper().replace(".TW", "")
    if clean_sym:
        st.session_state.add_name_wl = ETF_NAME_DB.get(clean_sym, f"{clean_sym}")
    else:
        st.session_state.add_name_wl = ""

def add_new_wl():
    raw_sym = st.session_state.get('add_sym_wl', '')
    new_name = st.session_state.get('add_name_wl', '')
    clean_symbol = raw_sym.strip().upper().replace(".TW", "")
    if clean_symbol and new_name:
        final_symbol = f"{clean_symbol}.TW"
        if any(x['symbol'] == final_symbol for x in st.session_state.my_data['watchlist']):
            st.warning("該標的已在自選名單中！")
            return
        st.session_state.my_data['watchlist'].append({
            "symbol": final_symbol, "name": new_name
        })
        save_to_json(st.session_state.my_data)
        st.session_state.add_sym_wl = ""
        st.session_state.add_name_wl = ""

def delete_wl(index):
    if 0 <= index < len(st.session_state.my_data['watchlist']):
        st.session_state.my_data['watchlist'].pop(index)
        save_to_json(st.session_state.my_data)

# 初始化按鈕狀態
if 'show_us' not in st.session_state: st.session_state.show_us = False
if 'show_tw' not in st.session_state: st.session_state.show_tw = False
if 'show_calendar' not in st.session_state: st.session_state.show_calendar = False
if 'show_div_db' not in st.session_state: st.session_state.show_div_db = False
if 'show_tech' not in st.session_state: st.session_state.show_tech = False
if 'show_holdings' not in st.session_state: st.session_state.show_holdings = False
if 'show_constituents' not in st.session_state: st.session_state.show_constituents = False 
if 'show_pledge' not in st.session_state: st.session_state.show_pledge = False 
if 'show_history' not in st.session_state: st.session_state.show_history = False 

def toggle_history(): st.session_state.show_history = not st.session_state.show_history
def toggle_us(): st.session_state.show_us = not st.session_state.show_us
def toggle_tw(): st.session_state.show_tw = not st.session_state.show_tw
def toggle_calendar(): st.session_state.show_calendar = not st.session_state.show_calendar
def toggle_div_db(): st.session_state.show_div_db = not st.session_state.show_div_db
def toggle_tech(): st.session_state.show_tech = not st.session_state.show_tech
def toggle_holdings(): st.session_state.show_holdings = not st.session_state.show_holdings
def toggle_constituents(): st.session_state.show_constituents = not st.session_state.show_constituents
def toggle_pledge(): st.session_state.show_pledge = not st.session_state.show_pledge 

# --- 📈 抓取美台股大盤指標 ---
@st.cache_data(ttl=60) 
def fetch_macro_data():
    tickers = {
        "us": {"道瓊工業": "^DJI", "那斯達克": "^IXIC", "費城半導體": "^SOX", "輝達 NVIDIA": "NVDA", "台積電 ADR": "TSM"},
        "tw": {"台股加權 (大盤)": "^TWII", "台積電 (台股)": "2330.TW", "聯發科 (台股)": "2454.TW", "台指期 (近月)": "WTX&P"}
    }
    res = {"us": {}, "tw": {}}
    for region, t_dict in tickers.items():
        for name, symbol in t_dict.items():
            try:
                tk = yf.Ticker(symbol)
                hist = tk.history(period="5d")
                if len(hist) >= 2:
                    curr = hist['Close'].iloc[-1]
                    prev = hist['Close'].iloc[-2]
                    res[region][name] = {"price": curr, "diff": curr - prev, "pct": ((curr - prev)/prev)*100, "date": hist.index[-1].strftime("%m/%d")}
            except: pass

    # 🚀 突破證交所封鎖機制 (修正大盤代號辨識)
    try:
        # 改用乾淨的核心代號 (c) 來做配對
        twse_targets_map = {"t00": "台股加權 (大盤)", "2330": "台積電 (台股)", "2454": "聯發科 (台股)"}
        twse_query = "tse_t00.tw|tse_2330.tw|tse_2454.tw"
        headers = {"User-Agent": "Mozilla/5.0"}
        
        session = requests.Session()
        session.get("https://mis.twse.com.tw/stock/index.jsp", headers=headers, timeout=5)
        
        ts = int(time.time() * 1000)
        twse_url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={twse_query}&json=1&delay=0&_={ts}"
        req = session.get(twse_url, headers=headers, timeout=5)
        msg_array = req.json().get('msgArray', [])
        
        today_str = datetime.today().strftime("%m/%d")
        for msg in msg_array:
            c = msg.get('c', '') # 直接抓取代號：t00, 2330, 2454
            
            if c in twse_targets_map:
                name = twse_targets_map[c]
                p = msg.get('z', '-')
                y = msg.get('y', '0')
                
                if p != '-' and float(p) > 0 and float(y) > 0:
                    curr = float(p)
                    prev = float(y)
                    res["tw"][name] = {"price": curr, "diff": curr - prev, "pct": ((curr - prev)/prev)*100, "date": f"{today_str} (TWSE即時)"}
    except Exception as e:
        pass
    return res

def render_macro_cards(data_dict, region_prefix):
    cols = st.columns(3)
    idx = 0
    for name, data in data_dict.items():
        is_up = data['diff'] >= 0
        color_hex = "#e74c3c" if is_up else "#2ecc71" 
        sign = "+" if is_up else ""
        
        html = f"""
        <div style="border:1px solid #e0e0e0; border-radius:8px; border-left:6px solid {color_hex}; padding:15px; margin-bottom:15px; background:#fff; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <div style="color:{color_hex}; font-size:15px; display:flex; align-items:center;">
                    <div style="width:10px; height:10px; border-radius:50%; background-color:{color_hex}; margin-right:6px;"></div>
                    <span style="font-weight:900; margin-right:4px;">{region_prefix}</span> <span style="font-weight:bold;">{name}</span>
                </div>
                <div style="color:#888; font-size:12px;">🕒 {data['date']}</div>
            </div>
            <div style="font-size:26px; font-weight:900; color:#111; margin-bottom:5px;">{data['price']:,.2f}</div>
            <div style="font-size:14px; font-weight:bold; color:{color_hex};">{sign}{data['diff']:,.2f} ({sign}{data['pct']:.2f}%)</div>
        </div>
        """
        with cols[idx % 3]:
            st.markdown(html, unsafe_allow_html=True)
        idx += 1

# --- 4. 核心數據計算 ---
def fetch_data(etf_list):
    if not etf_list: return pd.DataFrame(), pd.DataFrame(), 0, 0, 0, 0, [], [], [], {i: {"amount": 0, "sources": []} for i in range(1, 13)}
    results, tech_results = [], []
    total_mkt, total_cost, total_div, total_today_pnl = 0, 0, 0, 0
    radar_ex, radar_pay, price_alerts = [], [], []
    monthly_calendar = {i: {"amount": 0, "sources": []} for i in range(1, 13)} 
    today = datetime.today()

    if 'ex_div_shares_v2' not in st.session_state:
        st.session_state['ex_div_shares_v2'] = {}

    # 🚀 【重大安全升級】修正 TWSE API 批次對應邏輯，精準切分上市與上櫃/主動型標的
    twse_rt_data = {}
    try:
        tw_symbols = [item['symbol'].replace('.TW', '') for item in etf_list if '.TW' in item['symbol']]
        if tw_symbols:
            channels = []
            for sym in tw_symbols:
                # 採用雙向並行策略：一律同時查詢 tse 與 otc，再根據回傳進行精準解析
                channels.append(f"tse_{sym}.tw")
                channels.append(f"otc_{sym}.tw")
            ts = int(time.time() * 1000)
            twse_url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={'|'.join(channels)}&json=1&delay=0&_={ts}"
            headers = {"User-Agent": "Mozilla/5.0"}
            req = requests.get(twse_url, headers=headers, timeout=5)
            msg_array = req.json().get('msgArray', [])
            for msg in msg_array:
                sym_key = msg['c'] + ".TW"
                p = msg.get('z', '-') # z 是最新成交價
                y = msg.get('y', '0') # y 是昨日收盤價
                try:
                    # 💡 關鍵修正：如果證交所瞬間沒傳回成交價 (p 是 '-')，我們就不強迫覆蓋，
                    # 讓它乖乖退回去用 Yahoo 財經的報價，才不會讓漲跌變成 0！
                    if p != '-' and float(p) > 0:
                        twse_rt_data[sym_key] = {
                            'price': float(p),
                            'prev_close': float(y),
                            'volume': int(msg.get('v', 0)) * 1000 
                        }
                except: pass
    except Exception as e:
        pass 

    for item in etf_list:
        try:
            tk = yf.Ticker(item['symbol'])
            hist = tk.history(period='1y') 
            if hist.empty: continue
            
            rt_curr = tk.fast_info.get('lastPrice')
            curr_p = rt_curr if rt_curr is not None else hist['Close'].iloc[-1]
            
            rt_prev = tk.fast_info.get('previousClose')
            prev_close = rt_prev if rt_prev is not None else (hist['Close'].iloc[-2] if len(hist) >= 2 else curr_p)
            
            rt_vol = tk.fast_info.get('lastVolume')
            vol = rt_vol if rt_vol is not None else hist['Volume'].iloc[-1]
            
            # 🚀 【神級覆蓋】：若證交所官方回傳資料完全合法且大於 0，強制蓋掉 Yahoo
            if item['symbol'] in twse_rt_data and twse_rt_data[item['symbol']]['price'] > 0:
                curr_p = twse_rt_data[item['symbol']]['price']
                prev_close = twse_rt_data[item['symbol']]['prev_close']
                vol = twse_rt_data[item['symbol']]['volume']

            if curr_p > prev_close:
                status_light = "🔴"
            elif curr_p < prev_close:
                status_light = "🟢"
            else:
                status_light = "⚪"
            display_name = f"{status_light} {item['name']}"

            shares = item['holdings'] * 1000
            mkt_val = shares * curr_p
            cost_val = shares * item['cost']
            
            # 🚀 【對齊券商損益】：移除賣出手續費預扣，讓獲利與券商 App 一模一樣
            # 依照你的券商邏輯：預扣約 0.2425% 的交易稅與手續費 (ETF 0.1% 稅 + 0.1425% 手續費)
            sell_cost_estimate = mkt_val * 0.002425
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
            if a_high > 0 and curr_p >= a_high:
                price_alerts.append({"name": item['name'], "price": curr_p, "target": a_high, "type": "high"})
            if a_low > 0 and curr_p <= a_low:
                price_alerts.append({"name": item['name'], "price": curr_p, "target": a_low, "type": "low"})

            is_announced, div_amount, ex_date, pay_date = False, 0, "待官方公告", "待官方公告"
            
            cfg = DIVIDEND_DB.get(item['symbol'])
            if cfg:
                div_amount = cfg['v']
                ex_date = cfg['d']
                pay_date = cfg['p']
                is_announced = True
            else:
                actions = tk.actions
                if not actions.empty:
                    latest = actions.sort_index(ascending=False).head(1)
                    div_amount = float(latest['Dividends'].values[0]) 
                    last_ex_date_obj = latest.index[0].replace(tzinfo=None)
                    
                    ex_date = last_ex_date_obj.strftime('%Y-%m-%d')
                    pay_date = (last_ex_date_obj + timedelta(days=28)).strftime('%Y-%m-%d') 
                    
                    if last_ex_date_obj.date() >= today.date():
                        is_announced = True 

            est_yield = 0.0
            months_to_pay = DIVIDEND_SCHEDULE.get(item['symbol'], [])
            if len(months_to_pay) > 0 and div_amount > 0 and curr_p > 0:
                est_yield = (div_amount * len(months_to_pay)) / curr_p * 100

            ex_shares_setting = float(item.get('ex_div_shares_custom', item['holdings']))
            calc_div_shares = ex_shares_setting * 1000  

            if is_announced:
                ex_date_obj = datetime.strptime(ex_date, '%Y-%m-%d')
                days_diff_ex = (ex_date_obj.date() - today.date()).days
                if 0 <= days_diff_ex <= 20: radar_ex.append({"symbol": item['symbol'].split('.')[0], "date": ex_date, "days": days_diff_ex})
                
                pay_date_obj = datetime.strptime(pay_date, '%Y-%m-%d')
                days_diff_pay = (pay_date_obj.date() - today.date()).days
                if 0 <= days_diff_pay <= 20: radar_pay.append({"symbol": item['symbol'].split('.')[0], "date": pay_date, "amount": calc_div_shares * div_amount, "days": days_diff_pay})

            if div_amount > 0 and calc_div_shares > 0:
                explicit_pay_month = None
                if is_announced and pay_date != "待官方公告":
                    explicit_pay_month = datetime.strptime(pay_date, '%Y-%m-%d').month
                    monthly_calendar[explicit_pay_month]["amount"] += (calc_div_shares * div_amount)
                    if item['name'] not in monthly_calendar[explicit_pay_month]["sources"]:
                        monthly_calendar[explicit_pay_month]["sources"].append(item['name'])

                for m in months_to_pay:
                    pay_m = m + 1 if m < 12 else 1
                    if pay_m != explicit_pay_month:
                        monthly_calendar[pay_m]["amount"] += (calc_div_shares * div_amount)
                        if item['name'] not in monthly_calendar[pay_m]["sources"]:
                            monthly_calendar[pay_m]["sources"].append(item['name'])

            fill_status = "-"
            try:
                divs = tk.dividends
                if not divs.empty:
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

            total_mkt += mkt_val; total_cost += cost_val; total_div += (calc_div_shares * div_amount)
            
            results.append({
                "代號": item['symbol'], "名稱": item['name'], "現價": curr_p, "均價": item['cost'],
                "張數": item['holdings'], "市值": mkt_val, "損益": profit, "報酬率": roi,
                "單次預估領息": calc_div_shares * div_amount, "每股配息": div_amount,
                "最新公告除息日": ex_date, "預估發放日": pay_date, "已公告": is_announced,
                "最新填息紀錄": fill_status 
            })
            
            today_diff_str = f"+{today_diff:.2f}" if today_diff >= 0 else f"{today_diff:.2f}"
            vol_wan_str = f"{vol / 10000000:.2f} 萬" if vol > 0 else "無資料"

            tech_results.append({
                "ETF 名仙": display_name,
                "股票張數": item['holdings'], 
                "現價": round(curr_p, 2),
                "均價": item['cost'],
                "今日損益": today_pnl_str,
                "今日漲跌(點)": today_diff_str,
                "今日漲跌幅": today_pct_str, 
                "今日交易量(萬張)": vol_wan_str
            })
            
        except Exception as e: continue
        
    return pd.DataFrame(results), pd.DataFrame(tech_results), total_mkt, total_cost, total_div, total_today_pnl, radar_ex, radar_pay, price_alerts, monthly_calendar

df, df_tech, g_mkt, g_cost, g_div, g_today_pnl, radar_ex, radar_pay, price_alerts, monthly_calendar = fetch_data(st.session_state.my_data['etfs'])
macro_data = fetch_macro_data()

# --- 5. 介面呈現 ---
st.title("📈 實戰資產戰情室")
st.caption(f"最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if price_alerts:
    for alert in price_alerts:
        if alert['type'] == "high":
            st.markdown(f"<div class='alert-high'>🚨 突破停利高標：【{alert['name']}】 現價 ${alert['price']:.2f} 已突破您設定的 ${alert['target']}！</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='alert-low'>⚠️ 跌破停損低標：【{alert['name']}】 現價 ${alert['price']:.2f} 已跌破您設定的 ${alert['target']}！</div>", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
c1.metric("股票總市值", f"${g_mkt:,.0f}")
c2.metric("投資總成本", f"${g_cost:,.0f}")
c3.metric("全年預估總領息", f"${sum([monthly_calendar[m]['amount'] for m in range(1, 13)]):,.0f}")
st.write("---") 

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

if 'view_month' not in st.session_state.my_data:
    st.session_state.my_data['view_month'] = datetime.today().month
    save_to_json(st.session_state.my_data)

current_month_num = int(st.session_state.my_data['view_month'])
current_month_div_amount = monthly_calendar[current_month_num]["amount"]
current_month_div_str = f"${current_month_div_amount:,.0f}"
div_sources = monthly_calendar[current_month_num]["sources"]

if div_sources:
    sources_str = "、".join([s.split(' ')[0] for s in div_sources]) 
    sub_title = f"來自：{sources_str}"
else:
    sub_title = f"({current_month_num}月無配息入帳預定)"

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
    <div class="triple-col blue-box">
        <div class="triple-title" style="color: #1565c0; margin-bottom: 5px;">💰 總共領到配息金額</div>
        <div class="triple-val-blue">${st.session_state.my_data.get('total_received_divs', 0):,.0f}</div>
        <div class="triple-sub-blue">實際現金入帳總額</div>
    </div>
</div>
"""
st.markdown(html_triple_pnl, unsafe_allow_html=True)

_, col_m1, col_m2, col_m3, _ = st.columns([1.5, 1, 1, 1, 1.5])
with col_m1:
    if st.button("◀️ 上月", use_container_width=True):
        curr = st.session_state.my_data['view_month']
        st.session_state.my_data['view_month'] = curr - 1 if curr > 1 else 12
        save_to_json(st.session_state.my_data)
        st.rerun()
with col_m2:
    if st.button("🔄 本月", use_container_width=True):
        st.session_state.my_data['view_month'] = datetime.today().month
        save_to_json(st.session_state.my_data)
        st.rerun()
with col_m3:
    if st.button("下月 ▶️", use_container_width=True):
        curr = st.session_state.my_data['view_month']
        st.session_state.my_data['view_month'] = curr + 1 if curr < 12 else 1
        save_to_json(st.session_state.my_data)
        st.rerun()

st.write("") 

_, col_action, _ = st.columns([1, 2, 1])
with col_action:
    if current_month_div_amount > 0:
        if st.button(f"📥 一鍵將 {current_month_num} 月預估配息 (${current_month_div_amount:,.0f}) 存入總額", type="primary", use_container_width=True):
            current_total = float(st.session_state.my_data.get('total_received_divs', 0.0))
            st.session_state.my_data['total_received_divs'] = current_total + float(current_month_div_amount)
            save_to_json(st.session_state.my_data)
            st.rerun()
    else:
        st.button(f"🚫 {current_month_num} 月無配息可存入", disabled=True, use_container_width=True)

with st.expander("✏️ 手動記錄 / 修正「總共領到配息金額」"):
    col_adj1, col_adj2 = st.columns([3, 1])
    with col_adj1:
        new_total_divs = st.number_input(
            "請輸入您目前實際已領取的配息總額 (元)：", 
            min_value=0.0, 
            value=float(st.session_state.my_data.get('total_received_divs', 0)), 
            step=100.0
        )
    with col_adj2:
        st.write("") 
        st.write("")
        if st.button("💾 更新總額", type="secondary", use_container_width=True):
            st.session_state.my_data['total_received_divs'] = new_total_divs
            save_to_json(st.session_state.my_data)
            st.rerun()

st.write("---")

us_icon = "🌏"
if "us" in macro_data and macro_data["us"]:
    us_up = sum(1 for v in macro_data["us"].values() if v['diff'] >= 0)
    us_down = len(macro_data["us"]) - us_up
    us_icon = "🔴" if us_up >= us_down else "🟢"

tw_icon = "🇹🇼"
if "tw" in macro_data and macro_data["tw"]:
    tw_up = sum(1 for v in macro_data["tw"].values() if v['diff'] >= 0)
    tw_down = len(macro_data["tw"]) - tw_up
    tw_icon = "🔴" if tw_up >= tw_down else "🟢"

cols_btn_r1 = st.columns(3)
cols_btn_r2 = st.columns(3)
cols_btn_r3 = st.columns(3)

b1_lbl, b1_typ = (f"🔽 收起美股指數 {us_icon}", "primary") if st.session_state.show_us else (f"{us_icon} 展開美股指數", "secondary")
b2_lbl, b2_typ = (f"🔽 收起台股指數 {tw_icon}", "primary") if st.session_state.show_tw else (f"{tw_icon} 展開台股指數", "secondary")
b3_lbl, b3_typ = ("🔽 收起每月領息", "primary") if st.session_state.show_calendar else ("📅 展開每月領息", "secondary")

b4_lbl, b4_typ = ("🔽 收起除權息", "primary") if st.session_state.show_div_db else ("📂 展開除權息", "secondary")
b5_lbl, b5_typ = ("🔽 收起股價監控", "primary") if st.session_state.show_tech else ("📡 展開股價監控", "secondary")
b6_lbl, b6_typ = ("🔽 收起持股明細", "primary") if st.session_state.show_holdings else ("📊 展開持股明細", "secondary")

b7_lbl, b7_typ = ("🔽 收起ETF成份股", "primary") if st.session_state.show_constituents else ("🧩 展開ETF成份股", "secondary")
b8_lbl, b8_typ = ("🔽 收起質押專區", "primary") if st.session_state.show_pledge else ("🏦 展開質押專區", "secondary") 
b9_lbl, b9_typ = ("🔽 收起歷史情報", "primary") if st.session_state.show_history else ("📜 展開歷史情報", "secondary")

with cols_btn_r1[0]: st.button(b1_lbl, on_click=toggle_us, type=b1_typ, use_container_width=True)
with cols_btn_r1[1]: st.button(b2_lbl, on_click=toggle_tw, type=b2_typ, use_container_width=True)
with cols_btn_r1[2]: st.button(b3_lbl, on_click=toggle_calendar, type=b3_typ, use_container_width=True)

with cols_btn_r2[0]: st.button(b4_lbl, on_click=toggle_div_db, type=b4_typ, use_container_width=True)
with cols_btn_r2[1]: st.button(b5_lbl, on_click=toggle_tech, type=b5_typ, use_container_width=True)
with cols_btn_r2[2]: st.button(b6_lbl, on_click=toggle_holdings, type=b6_typ, use_container_width=True)

with cols_btn_r3[0]: st.button(b7_lbl, on_click=toggle_constituents, type=b7_typ, use_container_width=True) 
with cols_btn_r3[1]: st.button(b8_lbl, on_click=toggle_pledge, type=b8_typ, use_container_width=True) 
with cols_btn_r3[2]: st.button(b9_lbl, on_click=toggle_history, type=b9_typ, use_container_width=True)
st.write("---")

if st.session_state.show_us and "us" in macro_data and macro_data["us"]:
    st.markdown("#### 🌏 關鍵美股指標")
    render_macro_cards(macro_data["us"], "us")
    st.write("")

if st.session_state.show_tw and "tw" in macro_data and macro_data["tw"]:
    st.markdown("#### 🇹🇼 關鍵台股點數")
    render_macro_cards(macro_data["tw"], "tw")
    st.write("---")

# --- 📅 展開每月領息 ---
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
        
        if data["sources"]:
            st.markdown("<div style='text-align:center; font-weight:bold; color:#555; margin-top:10px;'>✏️ 微調此月份領息標的張數</div>", unsafe_allow_html=True)
            for item in st.session_state.my_data['etfs']:
                if item['name'] in data["sources"]:
                    saved_val = float(item.get('ex_div_shares_custom', item['holdings']))
                    
                    new_val = st.number_input(
                        f"🎯 修正【{item['name']}】本次領息張數", 
                        min_value=0.0, 
                        value=float(saved_val), 
                        step=0.001, 
                        format="%.3f",
                        key=f"edit_shares_{item['symbol']}"
                    )
                    
                    if new_val != saved_val:
                        for original_etf in st.session_state.my_data['etfs']:
                            if original_etf['symbol'] == item['symbol']:
                                original_etf['ex_div_shares_custom'] = new_val
                                break
                        
                        st.session_state['ex_div_shares_v2'][item['symbol']] = new_val
                        save_to_json(st.session_state.my_data)
                        st.cache_data.clear()
                        st.rerun()
    st.write("---")

# --- 📂 展開除權息 ---
if st.session_state.show_div_db:
    st.markdown("#### 📚 專屬 ETF 除權息時程總覽")
    
    if st.button("🔄 強制抓取最新官方公告", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    db_list = []
    if not df.empty:
        for _, row in df.iterrows():
            sym = row['代號']; months = DIVIDEND_SCHEDULE.get(sym, [])
            freq = "月配" if len(months)==12 else "季配" if len(months)==4 else "半年配" if len(months)==2 else "年配" if len(months)==1 else "未知"
            
            ex_d = row['最新公告除息日']
            if ex_d != "待官方公告":
                try:
                    if datetime.strptime(ex_d, '%Y-%m-%d').date() >= datetime.today().date():
                        status_badge = "✅ 即將除息"
                    else:
                        status_badge = "📅 上期紀錄"
                except:
                    status_badge = "未知"
            else:
                status_badge = "待官方公告"

            db_list.append({
                "ETF 名稱": row['名稱'], 
                "配息頻率": freq, 
                "配息月份": "、".join(map(str, months)) + " 月" if months else "未設定",
                "狀態": status_badge, 
                "除息日": ex_d, 
                "發放日": row['預估發放日'], 
                "每股金額": f"${row['每股配息']:.3f}",
                "填息紀錄": row['最新填息紀錄']
            })
            
    df_port_div = pd.DataFrame(db_list)
    if not df_port_div.empty:
        st.dataframe(df_port_div, use_container_width=True, hide_index=True)
    else:
        st.info("目前尚無庫存資料可顯示。")
        
    st.write("---")

# --- 📡 展開股價監控 ---
if st.session_state.show_tech:
    if not df.empty:
        st.markdown("#### 📡 庫存即時股價監控")
        
        def style_tech_dataframe(row):
            styles = [''] * len(row)
            
            for i, col in enumerate(row.index):
                val = row[col]
                if isinstance(val, str):
                    if val.startswith('+'):
                        styles[i] = 'color: #d32f2f; font-weight: bold;'
                    elif val.startswith('-'):
                        styles[i] = 'color: #388e3c; font-weight: bold;'
            
            try:
                price_idx = row.index.get_loc('現價')
                curr_price = float(row['現價'])
                avg_cost = float(row['均價'])
                
                if curr_price >= avg_cost:
                    styles[price_idx] = 'color: #d32f2f; font-weight: bold;'  
                else:
                    styles[price_idx] = 'color: #388e3c; font-weight: bold;'  
            except:
                pass
                
            return styles

        styled_df_tech = df_tech.style.apply(style_tech_dataframe, axis=1)

        st.dataframe(
            styled_df_tech,
            column_config={
                "現價": st.column_config.NumberColumn("現價", format="%.2f"),
                "均價": st.column_config.NumberColumn("均價", format="%.2f"),
                "股票張數": st.column_config.NumberColumn("股票張數", format="%.3f") 
            },
            use_container_width=True, hide_index=True
        )
    else:
        st.markdown("#### 📡 庫存即時股價監控")
        st.info("目前無庫存標的。")
        
    st.write("---")
    
   
# --- 📊 展開持股明細 ---
if st.session_state.show_holdings:
    if not df.empty:
        st.markdown("#### 📊 持股動態明細")
        for idx, item in enumerate(st.session_state.my_data['etfs']):
            row = df[df['代號'] == item['symbol']].iloc[0]
            
            p_color = "red" if float(row['現價']) >= float(item['cost']) else "green"
            
            roi_str = f"{row['報酬率']:+.2f}%"
            status_badge = "✅ 已公告" if row['已公告'] else "⏳ 依前次估算"
            
            with st.expander(f"💎 {row['名稱']} | 預估投資狀態: {roi_str}", expanded=True):
                col_l, col_m, col_r = st.columns(3)
                with col_l: 
                    st.write(f"當前持有總庫存: **{row['張數']} 張**")
                    
                    try:
                        curr_price_val = float(row['現價'])
                        my_cost_val = float(item['cost'])
                    except:
                        curr_price_val = 0.0
                        my_cost_val = 0.0
                    
                    if curr_price_val > my_cost_val:
                        st.markdown(f"系統現價: <span style='color: #b71c1c; font-weight: bold; font-size: 18px;'>{row['現價']:.2f}</span>", unsafe_allow_html=True)
                    elif curr_price_val < my_cost_val:
                        st.markdown(f"系統現價: <span style='color: #2e7d32; font-weight: bold; font-size: 18px;'>{row['現價']:.2f}</span>", unsafe_allow_html=True)
                    else:
                        st.write(f"系統現價: **{row['現價']:.2f}**")
                        
                    st.caption(f"持倉均價: {row['均價']:.2f}")
                    
                    saved_val = st.session_state['ex_div_shares_v2'].get(item['symbol'], float(item.get('ex_div_shares_custom', item['holdings'])))
                    new_val = st.number_input(
                        f"✏️ 修正本期領息張數 (目前設定: {saved_val} 張)",
                        min_value=0.0,
                        value=float(saved_val),
                        step=0.001,
                        format="%.3f",
                        key=f"detail_mod_{item['symbol']}"
                    )
                    if new_val != saved_val:
                        st.session_state['ex_div_shares_v2'][item['symbol']] = new_val
                        
                        for original_etf in st.session_state.my_data['etfs']:
                            if original_etf['symbol'] == item['symbol']:
                                original_etf['ex_div_shares_custom'] = new_val
                                break
                        save_to_json(st.session_state.my_data)
                        
                        st.cache_data.clear()
                        st.rerun()
                        
                with col_m: 
                    st.markdown(f"市值: **${row['市值']:,.0f}**")
                    st.markdown(f"預估淨利: :{p_color}[**${row['損益']:,.0f}**]")
                with col_r: 
                    st.markdown(f"本期預估領息金額: :orange[**${row['單次預估領息']:,.0f}**]")
                    st.caption(f"📅 除息日期: {row['最新公告除息日']} ({status_badge})")
    else:
        st.info("⚠️ 目前尚無持股資料。請至下方「⚙️ 標的管理」新增您的庫存！")
    st.write("---")

# --- 🧩 展開ETF成份股 ---
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

# --- 🏦 展開質押專區 ---
if st.session_state.show_pledge:
    if not df.empty:
        st.markdown("#### 🏦 股票質押專區 (維持率監控)")
        st.info("💡 股票質押後會從一般券商庫存消失。一般券商（如元大）最高可借出擔保品市值的 60%。請輸入已借入款項，系統將即時監控維持率！")
        
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
            
            try:
                curr_p = df[df['代號'] == sym]['現價'].values[0]
            except:
                curr_p = 0
                
            p_mkt = p_shares * 1000 * curr_p
            p_limit = p_mkt * 0.6  
            total_pledge_mkt += p_mkt
            total_borrowable += p_limit
            
            pledge_df_list.append({
                "ETF 名稱": name,
                "總庫存 (張)": h_total,
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

        st.write("👇 **請雙擊下方表格的「質押張數」欄位，設定您已向券商質押的庫存：**")
        edited_pledge = st.data_editor(
            pledge_df,
            column_config={
                "質押張數": st.column_config.NumberColumn("質押張數 (雙擊編輯)", min_value=0.0, step=0.001, format="%.3f"),
                "現價": st.column_config.NumberColumn("現價", format="%.2f"),
                "質押市值 (元)": st.column_config.NumberColumn("質押市值 (元)", format="%.0f"),
                "可借上限 (60%)": st.column_config.NumberColumn("可借上限 (60%)", format="%.0f") 
            },
            disabled=["ETF 名稱", "總庫存 (張)", "現價", "質押市值 (元)", "可借上限 (60%)"],
            use_container_width=True, hide_index=True
        )
        
        has_p_changes = False
        for _, row in edited_pledge.iterrows():
            p_name = row['ETF 名稱']
            new_p_shares = row['質押張數']
            for etf in st.session_state.my_data['etfs']:
                if etf['name'] == p_name and etf.get('pledged_shares', 0.0) != new_p_shares:
                    etf['pledged_shares'] = new_p_shares
                    has_p_changes = True
                    break
        if has_p_changes:
            save_to_json(st.session_state.my_data)
            st.rerun()
    else:
        st.info("⚠️ 目前尚無持股資料，無法進行質押計算。")
    st.write("---")
# --- 📜 展開持股歷史情報 ---

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_daily_history_masterpiece(symbol, days):
    try:
        if not symbol: return pd.DataFrame()
        
        data = yf.download(symbol, period="6mo", progress=False)
        if data.empty: return pd.DataFrame()
        
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        data.columns = [str(c).strip().capitalize() for c in data.columns]
        if 'Close' not in data.columns: return pd.DataFrame()
        
        df_clean = data[['Close']].copy()
        if 'Volume' in data.columns:
            df_clean['Volume'] = data['Volume']
            
        df_clean = df_clean.reset_index()
        df_clean.rename(columns={df_clean.columns[0]: 'Date'}, inplace=True)
        
        df_clean['Date'] = pd.to_datetime(df_clean['Date'], utc=True).dt.tz_convert('Asia/Taipei').dt.tz_localize(None).dt.normalize()
        
        df_clean = df_clean[df_clean['Date'].dt.weekday < 5]
        
        if 'Volume' in df_clean.columns:
            df_clean['Volume'] = pd.to_numeric(df_clean['Volume'], errors='coerce').fillna(0)
            df_clean = df_clean[df_clean['Volume'] > 0]
            
        df_clean = df_clean.drop_duplicates(subset=['Date'], keep='last')
        df_clean = df_clean.sort_values('Date')
        
        df_clean['漲跌'] = df_clean['Close'].diff()
        df_clean['漲跌幅'] = df_clean['Close'].pct_change() * 100
        
        df_clean.set_index('Date', inplace=True)
        return df_clean.dropna(subset=['漲跌']).tail(days)
    except Exception as e:
        return pd.DataFrame()

if st.session_state.show_history:
    st.markdown("#### 📜 專屬持股每日漲跌情報")
    
    if st.session_state.my_data['etfs']:
        col_sel1, col_sel2 = st.columns([2, 1])
        with col_sel1:
            history_options = [item['name'] for item in st.session_state.my_data['etfs']]
            selected_history_etf = st.selectbox("🔍 選擇要查看的標的：", history_options, key="history_select")
        with col_sel2:
            lookback_days = st.number_input("📅 設定顯示天數：", min_value=1, max_value=100, value=10, step=1)
        
        selected_symbol = next((item['symbol'] for item in st.session_state.my_data['etfs'] if item['name'] == selected_history_etf), "")
        
        if selected_symbol:
            with st.spinner("載入中..."):
                hist_data = fetch_daily_history_masterpiece(selected_symbol, lookback_days)
                
                if not hist_data.empty:
                    html_cards = "<div style='display: flex; flex-wrap: nowrap; overflow-x: auto; overflow-y: hidden; gap: 10px; padding: 10px 5px 15px 5px; -webkit-overflow-scrolling: touch;'>"
                    week_dict = {0: "一", 1: "二", 2: "三", 3: "四", 4: "五", 5: "六", 6: "日"}
                    
                    for date, row in hist_data.iloc[::-1].iterrows():
                        date_str = f"{date.strftime('%m/%d')} ({week_dict[date.weekday()]})" 
                        diff_val = row['漲跌']
                        pct_val = row['漲跌幅']
                        
                        if diff_val > 0:
                            color, bg_color, sign = "#d32f2f", "#fff5f5", "+"
                        elif diff_val < 0:
                            color, bg_color, sign = "#2e7d32", "#f0fff0", ""
                        else:
                            color, bg_color, sign = "#555555", "#f8f9fa", ""
                            
                        html_cards += f"<div style='flex: 0 0 auto; min-width: 90px; background-color: {bg_color}; border: 1.5px solid {color}; border-radius: 8px; padding: 8px 4px; text-align: center; box-shadow: 1px 1px 4px rgba(0,0,0,0.08);'><div style='font-size: 12px; color: #555; font-weight: bold; border-bottom: 1px solid #e0e0e0; padding-bottom: 4px; margin-bottom: 6px;'>{date_str}</div><div style='font-size: 14px; color: #111; font-weight: bold; margin-bottom: 4px;'>{row['Close']:.2f}</div><div style='font-size: 15px; font-weight: 900; color: {color}; line-height: 1.2;'>{sign}{diff_val:.2f}</div><div style='font-size: 12px; font-weight: bold; color: {color}; margin-top: 2px;'>{sign}{pct_val:.2f}%</div></div>"
                        
                    html_cards += "</div>"
                    st.markdown(html_cards, unsafe_allow_html=True)

# 🎯 最底層操作列 (手動更新 + 標的管理 + 自動更新開關)
bot_c1, bot_c2, bot_c3 = st.columns([2, 5, 3])

with bot_c1:
    if st.button("🔄 手動重新整理股價", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with bot_c2:
    with st.expander("⚙️ 標的管理 (庫存新增 / 修改 / 刪除)", expanded=False):
        st.markdown("#### ➕ 新增庫存標的 (股票/ETF)")
        
        if "add_name_bot" not in st.session_state: st.session_state.add_name_bot = ""
        if "add_sym_bot" not in st.session_state: st.session_state.add_sym_bot = ""
        if "add_h_bot" not in st.session_state: st.session_state.add_h_bot = 0.0
        if "add_c_bot" not in st.session_state: st.session_state.add_c_bot = 0.0

        st.text_input("輸入代碼 (不需手打 .TW)", placeholder="例如: 00878 或 00981A", key="add_sym_bot", on_change=auto_fill_etf_name)
        st.text_input("自定義名稱", placeholder="例如: 00878 國泰永續高股息", key="add_name_bot")
        
        col_add1, col_add2 = st.columns(2)
        with col_add1:
            st.number_input("張數", step=0.001, format="%.3f", key="add_h_bot")
        with col_add2:
            st.number_input("均價", step=0.1, key="add_c_bot")
        
        st.button("確認新增庫存", key="btn_add_bot", use_container_width=True, on_click=add_new_etf_bot)

        if st.session_state.my_data['etfs']:
            st.write("---")
            st.markdown("#### 📝 庫存修改與自訂排序")
            
            for i, item in enumerate(st.session_state.my_data['etfs']):
                sym = item['symbol']
                with st.expander(f"📍 {i+1}. {item['name']}"):
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        st.number_input("張數", value=float(item['holdings']), step=0.001, format="%.3f", key=f"edit_h_{sym}")
                    with col_e2:
                        st.number_input("均價", value=float(item['cost']), step=0.1, key=f"edit_c_{sym}")

                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    with col_btn1:
                        if st.button("⬆️ 上移", key=f"up_{sym}", disabled=(i == 0), use_container_width=True):
                            # 移動前，先自動把當前輸入框的最新數字存起來，避免移動後數字遺失
                            for tmp in st.session_state.my_data['etfs']:
                                t_sym = tmp['symbol']
                                if f"edit_h_{t_sym}" in st.session_state: tmp['holdings'] = float(st.session_state[f"edit_h_{t_sym}"])
                                if f"edit_c_{t_sym}" in st.session_state: tmp['cost'] = float(st.session_state[f"edit_c_{t_sym}"])
                            
                            # 執行排序交換
                            st.session_state.my_data['etfs'][i - 1], st.session_state.my_data['etfs'][i] = \
                            st.session_state.my_data['etfs'][i], st.session_state.my_data['etfs'][i - 1]
                            save_to_json(st.session_state.my_data)
                            st.rerun() # 強制整個網頁重新讀取，讓上面的監控表立刻更新！

                    with col_btn2:
                        if st.button("⬇️ 下移", key=f"down_{sym}", disabled=(i == len(st.session_state.my_data['etfs']) - 1), use_container_width=True):
                            for tmp in st.session_state.my_data['etfs']:
                                t_sym = tmp['symbol']
                                if f"edit_h_{t_sym}" in st.session_state: tmp['holdings'] = float(st.session_state[f"edit_h_{t_sym}"])
                                if f"edit_c_{t_sym}" in st.session_state: tmp['cost'] = float(st.session_state[f"edit_c_{t_sym}"])

                            st.session_state.my_data['etfs'][i + 1], st.session_state.my_data['etfs'][i] = \
                            st.session_state.my_data['etfs'][i], st.session_state.my_data['etfs'][i + 1]
                            save_to_json(st.session_state.my_data)
                            st.rerun()

                    with col_btn3:
                        if st.button("🗑️ 刪除", key=f"del_{sym}", use_container_width=True):
                            st.session_state.my_data['etfs'].pop(i)
                            save_to_json(st.session_state.my_data)
                            st.rerun()

            # 獨立的儲存按鈕，強制重整
            if st.button("💾 儲存所有修改", use_container_width=True, type="primary"):
                for item in st.session_state.my_data['etfs']:
                    sym = item['symbol']
                    if f"edit_h_{sym}" in st.session_state:
                        item['holdings'] = float(st.session_state[f"edit_h_{sym}"])
                    if f"edit_c_{sym}" in st.session_state:
                        item['cost'] = float(st.session_state[f"edit_c_{sym}"])
                save_to_json(st.session_state.my_data)
                st.rerun()

with bot_c3:
    st.markdown("<div class='auto-refresh-box'>", unsafe_allow_html=True)
    st.markdown("#### ⚡ 系統自動更新")
    st.caption("開啟後每 30 秒自動重整抓取最新即時股價")
    
    if 'auto_refresh_mode' not in st.session_state:
        st.session_state.auto_refresh_mode = "❌ NO USE (關閉)"
        
    auto_update = st.radio(
        "即時更新 (每 30 秒)", 
        ["❌ NO USE (關閉)", "✅ USE (開啟)"], 
        key="auto_refresh_mode",
        horizontal=True,
        label_visibility="collapsed"
    )
    st.markdown("</div>", unsafe_allow_html=True)

# 🚀 放在腳本最底層的自動更新執行邏輯 (已升級 30 秒)
if st.session_state.auto_refresh_mode == "✅ USE (開啟)":
    time.sleep(30)
    st.cache_data.clear()
    st.rerun()
