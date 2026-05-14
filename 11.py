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
    [data-testid="stElementToolbar"], 
    [data-testid="stDataFrameToolbar"],
    [data-testid="stToolbar"] { display: none !important; }
    
    [data-testid="stMetricDelta"] svg { fill: red; }
    
    [data-testid="stMetric"] { 
        background-color: var(--secondary-background-color); 
        padding: 12px; 
        border-radius: 10px; 
    }

    .triple-box { background-color: #ffffff; border-radius: 12px; border: 1px solid #e0e0e0; padding: 15px; display: flex; flex-wrap: wrap; justify-content: space-around; align-items: center; margin-bottom: 20px; box-shadow: 2px 2px 8px rgba(0,0,0,0.04); gap: 10px; }
    .triple-col { flex: 1 1 30%; min-width: 140px; text-align: center; padding: 10px 0; }
    .triple-title { font-size: 14px; color: #757575; font-weight: bold; margin-bottom: 5px; }
    .triple-val-r { font-size: 28px; font-weight: 900; color: #b71c1c; font-family: Arial, sans-serif; line-height: 1.1; }
    .triple-val-g { font-size: 28px; font-weight: 900; color: #2e7d32; font-family: Arial, sans-serif; line-height: 1.1; }
    .triple-val-gold { font-size: 28px; font-weight: 900; color: #f39c12; font-family: Arial, sans-serif; line-height: 1.1; text-shadow: 1px 1px 2px rgba(243, 156, 18, 0.3); }
    .triple-pct-r { font-size: 14px; font-weight: bold; color: #b71c1c; margin-top: 5px; }
    .triple-pct-g { font-size: 14px; font-weight: bold; color: #2e7d32; margin-top: 5px; }
    .triple-sub-gold { font-size: 12px; font-weight: bold; color: #7f8c8d; margin-top: 5px; }

    @keyframes lightning-strike {
        0% { box-shadow: 0 0 10px rgba(241, 196, 15, 0.5); background-color: #fffdf5; transform: scale(1); }
        50% { box-shadow: 0 0 40px rgba(255, 235, 59, 1); background-color: #ffffe0; transform: scale(1.03); }
        100% { box-shadow: 0 0 10px rgba(241, 196, 15, 0.5); background-color: #fffdf5; transform: scale(1); }
    }
    .flash-gold-box { background-color: #fffdf5; border-radius: 12px; padding: 15px; border: 2px solid #f1c40f; animation: lightning-strike 0.1s infinite; }

    .month-card { background-color: #e9ecef; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 10px; border: 1px solid #ced4da; }
    .month-title { font-size: 20px; font-weight: bold; color: #495057; }
    .month-amount { font-size: 28px; font-weight: bold; color: #d9534f; margin: 10px 0; }
    
    div.stButton > button { font-weight: bold; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 系統設定與資料庫 ---
SETTINGS_FILE = 'settings.json'

ETF_FULL_DATABASE = {
    "0050": ["元大台灣50", [1, 7], "0.32%", "0.035%"],
    "0056": ["元大高股息", [1, 4, 7, 10], "0.3%", "0.035%"],
    "00878": ["國泰永續ESG高股息", [2, 5, 8, 11], "0.25%", "0.035%"],
    "00919": ["群益台灣精選高息", [3, 6, 9, 12], "0.3%", "0.035%"],
    "00929": ["復華台灣科技優息", list(range(1, 13)), "0.30%", "0.030%"],
    "00927": ["群益台灣半導體收益", [1, 4, 7, 10], "0.4%", "0.035%"],
    "00891": ["中信關鍵半導體", [2, 5, 8, 11], "0.4%", "0.035%"],
}

ETF_NAME_DB = {k: f"{k} {v[0]}" for k, v in ETF_FULL_DATABASE.items()}
DIVIDEND_SCHEDULE = {f"{k}.TW": v[1] for k, v in ETF_FULL_DATABASE.items()}

def load_settings():
    default_data = {"etfs": [], "pledge": {"borrowed_amount": 0}, "watchlist": [], "custom_divs": {}}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f: 
                data = json.load(f)
                return data
        except: pass
    return default_data

def save_to_json(data):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

if 'my_data' not in st.session_state: 
    st.session_state.my_data = load_settings()

# --- 3. 核心函數區 ---
def add_new_etf_bot():
    raw_sym = st.session_state.get('add_sym_bot', '').strip().upper().replace(".TW", "")
    new_name = st.session_state.get('add_name_bot', '')
    new_h = st.session_state.get('add_h_bot', 0.0)
    new_c = st.session_state.get('add_c_bot', 0.0)
    if raw_sym and new_name:
        final_symbol = f"{raw_sym}.TW"
        # 檢查是否已在庫存
        if not any(e['symbol'] == final_symbol for e in st.session_state.my_data['etfs']):
            st.session_state.my_data['etfs'].append({
                "symbol": final_symbol, "name": new_name, "holdings": new_h, "cost": new_c, 
                "alert_high": 0.0, "alert_low": 0.0, "pledged_shares": 0.0, "is_pledged": False
            })
            save_to_json(st.session_state.my_data)
        st.session_state.add_sym_bot = ""; st.session_state.add_name_bot = ""; st.session_state.add_h_bot = 0.0; st.session_state.add_c_bot = 0.0

def delete_etf(index):
    st.session_state.my_data['etfs'].pop(index)
    save_to_json(st.session_state.my_data)

def save_edits():
    for i, item in enumerate(st.session_state.my_data['etfs']):
        item['holdings'] = st.session_state.get(f"edit_h_{i}", item['holdings'])
        item['cost'] = st.session_state.get(f"edit_c_{i}", item['cost'])
    save_to_json(st.session_state.my_data)

# 切換按鈕
if 'show_div_db' not in st.session_state: st.session_state.show_div_db = False
def toggle_div_db(): st.session_state.show_div_db = not st.session_state.show_div_db

# --- 4. 數據抓取 (簡化演示核心邏輯) ---
@st.cache_data(ttl=60)
def fetch_basic_data(etf_list):
    results = []
    for item in etf_list:
        try:
            tk = yf.Ticker(item['symbol'])
            curr_p = tk.fast_info.get('lastPrice', item['cost'])
            results.append({
                "代號": item['symbol'], "名稱": item['name'], "現價": curr_p, 
                "均價": item['cost'], "張數": item['holdings'], "損益": (curr_p - item['cost']) * item['holdings'] * 1000
            })
        except: continue
    return pd.DataFrame(results)

df_stock = fetch_basic_data(st.session_state.my_data['etfs'])

# --- 5. 介面呈現 ---
st.title("📈 實戰資產戰情室")

# 除權息區塊
st.button("📂 展開/收起 除權息總覽", on_click=toggle_div_db)

if st.session_state.show_div_db:
    with st.expander("🛠️ 手動配息覆蓋面板 (領息試算)", expanded=True):
        st.caption("💸 系統已自動對應您的實體庫存，修改後按儲存即可套用！")
        
        custom_dict = st.session_state.my_data.get('custom_divs', {})
        display_list = []
        
        # 🔥 優化核心：只根據目前庫存清單生成表格，避免重覆
        for item in st.session_state.my_data.get('etfs', []):
            sym = item['symbol']
            c_info = custom_dict.get(sym, {})
            display_list.append({
                "代號": sym,
                "名稱": item['name'],
                "每股配息": c_info.get('v', 0.0),
                "除息日": c_info.get('d', ''),
                "發放日": c_info.get('p', ''),
                "持有張數": item['holdings'] # 直接使用庫存張數
            })

        df_custom = pd.DataFrame(display_list)
        edited_custom = st.data_editor(
            df_custom, use_container_width=True, hide_index=True,
            column_config={
                "代號": st.column_config.TextColumn("代號", disabled=True),
                "名稱": st.column_config.TextColumn("名稱", disabled=True),
                "每股配息": st.column_config.NumberColumn("每股配息", format="%.3f"),
                "持有張數": st.column_config.NumberColumn("持有張數", disabled=True, format="%.3f")
            }
        )
        
        if st.button("💾 儲存配息資料並套用"):
            new_db = {}
            for _, row in edited_custom.iterrows():
                if row['每股配息'] > 0:
                    new_db[row['代號']] = {"v": row['每股配息'], "d": row['除息日'], "p": row['發放日']}
            st.session_state.my_data['custom_divs'] = new_db
            save_to_json(st.session_state.my_data)
            st.rerun()

st.write("---")

# 庫存管理區
with st.expander("⚙️ 標的管理 (庫存新增 / 修改 / 刪除)", expanded=True):
    st.markdown("#### ➕ 新增庫存標的")
    c1, c2 = st.columns(2)
    with c1: st.text_input("輸入代碼", key="add_sym_bot", placeholder="例如: 0056")
    with c2: st.text_input("名稱", key="add_name_bot", placeholder="元大高股息")
    
    c3, c4 = st.columns(2)
    with c3: st.number_input("張數", step=0.001, format="%.3f", key="add_h_bot")
    with c4: st.number_input("均價", step=0.01, key="add_c_bot")
    st.button("確認新增庫存", on_click=add_new_etf_bot, use_container_width=True)

    if st.session_state.my_data['etfs']:
        st.write("---")
        for i, item in enumerate(st.session_state.my_data['etfs']):
            with st.expander(f"📍 {item['name']}"):
                cc1, cc2 = st.columns(2)
                with cc1: st.number_input("張數", value=float(item['holdings']), step=0.001, format="%.3f", key=f"edit_h_{i}")
                with cc2: st.number_input("均價", value=float(item['cost']), step=0.01, key=f"edit_c_{i}")
                st.button(f"🗑️ 刪除 {item['name']}", key=f"del_{i}", on_click=delete_etf, args=(i,))
        st.button("💾 儲存所有修改", type="primary", on_click=save_edits, use_container_width=True)
