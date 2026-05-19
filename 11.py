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
st.set_page_config(page_title="ETF 投資戰情室 PRO", layout="wide")

if 'update_success' in st.session_state and st.session_state.update_success:
    st.toast(st.session_state.update_success, icon="✅")
    st.session_state.update_success = False

# 自定義 CSS (PRO 版華麗樣式)
st.markdown("""
    <style>
    [data-testid="stElementToolbar"], 
    [data-testid="stDataFrameToolbar"],
    [data-testid="stToolbar"],
    .stDataFrame [data-testid="stElementToolbar"] { 
        display: none !important; opacity: 0 !important; visibility: hidden !important; pointer-events: none !important;
    }
    [data-testid="stMetricDelta"] svg { fill: red; }
    [data-testid="stMetric"] { background-color: var(--secondary-background-color); padding: 12px; border-radius: 10px; box-shadow: 1px 1px 4px rgba(0,0,0,0.05); }
    .triple-box { background-color: #ffffff; border-radius: 12px; border: 1px solid #e0e0e0; padding: 15px; display: flex; flex-wrap: wrap; justify-content: space-around; align-items: center; margin-bottom: 20px; box-shadow: 2px 2px 8px rgba(0,0,0,0.04); gap: 10px; }
    .triple-col { flex: 1 1 30%; min-width: 140px; text-align: center; padding: 10px 0; }
    .triple-title { font-size: 14px; color: #757575; font-weight: bold; margin-bottom: 5px; }
    .triple-val-r { font-size: 28px; font-weight: 900; color: #b71c1c; font-family: Arial, sans-serif; line-height: 1.1; }
    .triple-val-g { font-size: 28px; font-weight: 900; color: #2e7d32; font-family: Arial, sans-serif; line-height: 1.1; }
    .triple-val-gold { font-size: 28px; font-weight: 900; color: #f39c12; font-family: Arial, sans-serif; line-height: 1.1; text-shadow: 1px 1px 2px rgba(243, 156, 18, 0.3); }
    .triple-pct-r { font-size: 14px; font-weight: bold; color: #b71c1c; margin-top: 5px; }
    .triple-pct-g { font-size: 14px; font-weight: bold; color: #2e7d32; margin-top: 5px; }
    .triple-sub-gold { font-size: 12px; font-weight: bold; color: #7f8c8d; margin-top: 5px; }
    @keyframes lightning-strike { 0% { box-shadow: 0 0 10px rgba(241, 196, 15, 0.5); background-color: #fffdf5; border-color: #f1c40f; transform: scale(1); } 50% { box-shadow: 0 0 40px rgba(255, 235, 59, 1), inset 0 0 25px rgba(255, 235, 59, 0.9); background-color: #ffffe0; border-color: #ffeb3b; transform: scale(1.03); } 100% { box-shadow: 0 0 10px rgba(241, 196, 15, 0.5); background-color: #fffdf5; border-color: #f1c40f; transform: scale(1); } }
    .flash-gold-box { background-color: #fffdf5; border-radius: 12px; padding: 15px; border: 2px solid #f1c40f; animation: lightning-strike 0.1s infinite; }
    .alert-high { background-color: #ffebee; border: 2px solid #ef5350; border-left: 8px solid #d32f2f; padding: 15px; border-radius: 8px; margin-bottom: 15px; color: #b71c1c; font-size: 16px; font-weight: bold; }
    .alert-low { background-color: #e8f5e9; border: 2px solid #66bb6a; border-left: 8px solid #388e3c; padding: 15px; border-radius: 8px; margin-bottom: 15px; color: #1b5e20; font-size: 16px; font-weight: bold; }
    .month-card { background-color: #e9ecef; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 10px; border: 1px solid #ced4da; }
    .month-title { font-size: 20px; font-weight: bold; color: #495057; }
    .month-amount { font-size: 28px; font-weight: bold; color: #d9534f; margin: 10px 0; }
    .month-sources { font-size: 14px; color: #6c757d; }
    div.stButton > button { font-weight: bold; border-radius: 8px; }
    .calc-box { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 15px; margin-bottom: 15px;}
    .calc-result-profit { font-size: 24px; font-weight: bold; color: #d32f2f; margin-top: 10px;}
    .calc-result-loss { font-size: 24px; font-weight: bold; color: #388e3c; margin-top: 10px;}
    .auto-refresh-box { background-color: #f0f7ff; border: 1px solid #cce5ff; border-radius: 8px; padding: 15px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 系統設定與資料庫 ---
SETTINGS_FILE = 'settings.json'

ETF_FULL_DATABASE = {
    "0050": ["元大台灣50", [1, 7], "0.32%", "0.035%"],
    "0056": ["元大高股息", [1, 4, 7, 10], "0.3%", "0.035%"],
    "00878": ["國泰永續ESG高股息", [2, 5, 8, 11], "0.25%", "0.035%"],
    "00891": ["中信關鍵半導體", [2, 5, 8, 11], "0.4%", "0.035%"],
    "00919": ["群益台灣精選高息", [3, 6, 9, 12], "0.3%", "0.035%"],
    "00929": ["復華台灣科技優息", list(range(1, 13)), "0.30%", "0.030%"],
    "00940": ["元大臺灣價值高息", list(range(1, 13)), "0.3%", "0.030%"],
}

EXTRA_ETFS = {
    "2887": "2887 台新金", "2330": "2330 台積電", "2454": "2454 聯發科", "2317": "2317 鴻海"
}

ETF_NAME_DB = {}
DIVIDEND_SCHEDULE = {}
ETF_FEES_DB = {}

for k, v in EXTRA_ETFS.items(): ETF_NAME_DB[k] = v
for k, v in ETF_FULL_DATABASE.items():
    ETF_NAME_DB[k] = f"{k} {v[0]}"
    DIVIDEND_SCHEDULE[f"{k}.TW"] = v[1]
    ETF_FEES_DB[f"{k}.TW"] = {"經理費": v[2], "保管費": v[3]}

ETF_CONSTITUENTS_DB = {
    "0056.TW": [{"name": "鴻海", "weight": 6.5}, {"name": "聯發科", "weight": 5.2}, {"name": "聯詠", "weight": 4.8}, {"name": "其他", "weight": 83.5}],
    "00878.TW": [{"name": "聯發科", "weight": 5.5}, {"name": "國泰金", "weight": 5.1}, {"name": "富邦金", "weight": 4.9}, {"name": "其他", "weight": 84.5}],
    "0050.TW": [{"name": "台積電", "weight": 52.5}, {"name": "鴻海", "weight": 5.5}, {"name": "聯發科", "weight": 4.8}, {"name": "其他", "weight": 37.2}]
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    
    # 💡 這裡已經替換為你朋友的專屬庫存與持股成本
    return {
        "etfs": [
            {"symbol": "0050.TW", "name": "0050 元大台灣50", "holdings": 3.0, "cost": 135.50, "alert_high": 0.0, "alert_low": 0.0, "pledged_shares": 0.0, "ex_div_shares_custom": 3.0},
            {"symbol": "0056.TW", "name": "0056 元大高股息", "holdings": 10.0, "cost": 36.80, "alert_high": 0.0, "alert_low": 0.0, "pledged_shares": 0.0, "ex_div_shares_custom": 10.0},
            {"symbol": "00878.TW", "name": "00878 國泰永續高股息", "holdings": 15.0, "cost": 22.10, "alert_high": 0.0, "alert_low": 0.0, "pledged_shares": 0.0, "ex_div_shares_custom": 15.0},
            {"symbol": "00919.TW", "name": "00919 群益台灣精選高息", "holdings": 25.0, "cost": 25.20, "alert_high": 0.0, "alert_low": 0.0, "pledged_shares": 0.0, "ex_div_shares_custom": 25.0},
            {"symbol": "2330.TW", "name": "2330 台積電", "holdings": 1.0, "cost": 780.00, "alert_high": 0.0, "alert_low": 0.0, "pledged_shares": 0.0, "ex_div_shares_custom": 1.0}
        ], 
        "pledge": {"borrowed_amount": 0},
        "watchlist": [],
        "total_received_divs": 0.0,          # 預設已領取配息歸零
        "view_month": datetime.today().month # 預設顯示當前月份
    }
    
    # 強化防呆機制：如果檔案壞掉、空白、或編碼錯誤，一律直接載入專屬預設值
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f: 
                content = f.read().strip()
                if not content: return default_data
                data = json.loads(content)
                for k, v in default_data.items():
                    if k not in data: data[k] = v
                return data
        except: 
            pass # 發生 JSONDecodeError 直接跳過，不當機！
            
    return default_data

def save_to_json(data):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

if 'my_data' not in st.session_state: 
    st.session_state.my_data = load_settings()

if 'watchlist' not in st.session_state.my_data: st.session_state.my_data['watchlist'] = []
if 'pledge' not in st.session_state.my_data: st.session_state.my_data['pledge'] = {"borrowed_amount": 0}

for etf in st.session_state.my_data['etfs']:
    if 'pledged_shares' not in etf: etf['pledged_shares'] = 0.0
    if 'is_pledged' not in etf: etf['is_pledged'] = False 
save_to_json(st.session_state.my_data)

# --- 3. UI 操作 Callback ---
def auto_fill_etf_name():
    clean_sym = st.session_state.get('add_sym_bot', '').strip().upper().replace(".TW", "")
    st.session_state.add_name_bot = ETF_NAME_DB.get(clean_sym, f"{clean_sym} ETF") if clean_sym else ""

def add_new_etf_bot():
    raw_sym = st.session_state.get('add_sym_bot', '')
    new_name = st.session_state.get('add_name_bot', '')
    new_h = st.session_state.get('add_h_bot', 0.0)
    new_c = st.session_state.get('add_c_bot', 0.0)

    clean_symbol = raw_sym.strip().upper().replace(".TW", "")
    if clean_symbol and new_name:
        final_symbol = f"{clean_symbol}.TW" 
        exists = False
        for e in st.session_state.my_data['etfs']:
            if e['symbol'] == final_symbol:
                e['holdings'] += new_h; exists = True; break
        if not exists:
            st.session_state.my_data['etfs'].append({"symbol": final_symbol, "name": new_name, "holdings": new_h, "cost": new_c})
        save_to_json(st.session_state.my_data)
        st.session_state.add_sym_bot = ""; st.session_state.add_name_bot = ""; st.session_state.add_h_bot = 0.0; st.session_state.add_c_bot = 0.0

def delete_etf(index):
    if 0 <= index < len(st.session_state.my_data['etfs']):
        st.session_state.my_data['etfs'].pop(index)
        save_to_json(st.session_state.my_data)

def save_edits():
    for i, item in enumerate(st.session_state.my_data['etfs']):
        item['holdings'] = st.session_state.get(f"edit_h_{i}", item['holdings'])
        item['cost'] = st.session_state.get(f"edit_c_{i}", item['cost'])
    save_to_json(st.session_state.my_data)

# 初始化按鈕狀態
for key in ['show_calendar', 'show_div_db', 'show_tech', 'show_holdings', 'show_constituents', 'show_daily_price', 'show_pledge']:
    if key not in st.session_state: st.session_state[key] = False 
def toggle_state(key): st.session_state[key] = not st.session_state[key]

# --- 4. 核心數據抓取 ---
@st.cache_data(ttl=10800) 
def fetch_taiwan_upcoming_dividends(): return {} 

@st.cache_data(ttl=43200)
def get_div_data(symbol, custom_div_info=None):
    is_announced, div_amount, ex_date, pay_date, fill_status, status_msg = False, 0.0, "待官方公告", "待官方公告", "-", "⏳ 依前次估算"
    today = datetime.today()
    if custom_div_info and custom_div_info.get('v', 0) > 0:
        return True, custom_div_info['v'], custom_div_info.get('d', ''), custom_div_info.get('p', ''), "-", "✅ 手動設定"
    try: 
        tk = yf.Ticker(symbol)
        divs = tk.dividends
        if not divs.empty:
            latest_div = divs.sort_index(ascending=False).head(1)
            div_amount = float(latest_div.values[0]) 
            last_ex_date_obj = latest_div.index[0].replace(tzinfo=None)
            ex_date = last_ex_date_obj.strftime('%Y-%m-%d')
            status_msg = "✅ 已公告 (近期)" if last_ex_date_obj.date() >= today.date() else "✅ 前次紀錄"
    except: pass
    return is_announced, div_amount, ex_date, pay_date, fill_status, status_msg

@st.cache_data(ttl=10)
def fetch_data(etf_list, custom_divs):
    results, tech_results = [], []
    total_mkt, total_cost, total_div, total_today_pnl = 0, 0, 0, 0
    price_alerts = []
    monthly_calendar = {i: {"amount": 0, "sources": []} for i in range(1, 13)} 

    for item in etf_list:
        curr_p = item['cost'] if item['cost'] > 0 else 10.0 
        prev_close, day_high, day_low, vol, year_high, year_low = curr_p, curr_p, curr_p, 0, curr_p, curr_p
        cap_str = "系統無資料"
        
        try: 
            tk = yf.Ticker(item['symbol'])
            inf = tk.fast_info
            curr_p = inf.get('lastPrice', curr_p)
            prev_close = inf.get('previousClose', curr_p)
            day_high = inf.get('dayHigh', curr_p)
            day_low = inf.get('dayLow', curr_p)
            vol = inf.get('lastVolume', 0)
        except: pass 

        status_light = "🔴" if curr_p > prev_close else "🟢" if curr_p < prev_close else "⚪"
        display_name = f"{status_light} {item['name']}"

        shares = item['holdings'] * 1000
        mkt_val = shares * curr_p
        cost_val = shares * item['cost']
        profit = mkt_val - cost_val
        roi = (profit / cost_val * 100) if cost_val != 0 else 0
        
        today_diff = curr_p - prev_close
        today_profit = shares * today_diff
        today_pct_change = (today_diff / prev_close * 100) if prev_close else 0
        total_today_pnl += today_profit

        is_announced, div_amount, ex_date, pay_date, fill_status, status_msg = get_div_data(item['symbol'], custom_divs.get(item['symbol']))
        est_yield = 0.0
        months_to_pay = DIVIDEND_SCHEDULE.get(item['symbol'], [])
        if len(months_to_pay) > 0 and div_amount > 0 and curr_p > 0:
            est_yield = (div_amount * len(months_to_pay)) / curr_p * 100

        if div_amount > 0 and shares > 0:
            for m in months_to_pay:
                pay_m = m + 1 if m < 12 else 1
                monthly_calendar[pay_m]["amount"] += (shares * div_amount)
                if item['name'] not in monthly_calendar[pay_m]["sources"]: monthly_calendar[pay_m]["sources"].append(item['name'])

        total_mkt += mkt_val; total_cost += cost_val; total_div += (shares * div_amount)
        fee_info = ETF_FEES_DB.get(item['symbol'], {"經理費": "-", "保管費": "-"})

        results.append({
            "代號": item['symbol'], "名稱": item['name'], "現價": curr_p, "均價": item['cost'],
            "張數": item['holdings'], "市值": mkt_val, "損益": profit, "報酬率": roi,
            "經理費": fee_info["經理費"], "保管費": fee_info["保管費"], 
            "單次預估領息": shares * div_amount, "每股配息": div_amount,
            "最新公告除息日": ex_date, "預估發放日": pay_date, "狀態": status_msg
        })
            
        tech_results.append({
            "ETF 名稱": display_name, "股票張數": item['holdings'], "現價": round(curr_p, 2), 
            "今日損益": f"{today_profit:+.0f}", "今日漲跌幅": f"{today_pct_change:+.2f}%", 
            "今日交易量": f"{vol:,.0f}" if vol > 0 else "無資料", "年殖利率": f"{est_yield:.2f}%"
        })
        
    return pd.DataFrame(results), pd.DataFrame(tech_results), total_mkt, total_cost, total_div, total_today_pnl, price_alerts, monthly_calendar

df, df_tech, g_mkt, g_cost, g_div, g_today_pnl, price_alerts, monthly_calendar = fetch_data(st.session_state.my_data['etfs'], st.session_state.my_data.get('custom_divs', {}))

# --- 5. 介面呈現 PRO ---
st.title("📈 實戰資產戰情室 PRO")
st.caption(f"最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (已啟動自動備份還原機制)")

total_net_profit = df['損益'].sum() if not df.empty else 0
r_total = (total_net_profit / g_cost * 100) if g_cost != 0 else 0
prev_mkt = g_mkt - g_today_pnl
today_pct = (g_today_pnl / prev_mkt * 100) if prev_mkt != 0 else 0

current_month_num = datetime.today().month
current_month_div_amount = monthly_calendar[current_month_num]["amount"]
sub_title = f"來自：{'、'.join([s.split(' ')[0] for s in monthly_calendar[current_month_num]['sources']])}" if monthly_calendar[current_month_num]['sources'] else "本月無現金流入預定"

st.markdown(f"""
<div class="triple-box">
    <div class="triple-col">
        <div class="triple-title">今日預估損益</div>
        <div class="{'triple-val-r' if g_today_pnl >= 0 else 'triple-val-g'}">{g_today_pnl:+.0f}</div>
        <div class="{'triple-pct-r' if g_today_pnl >= 0 else 'triple-pct-g'}">{today_pct:+.2f}%</div>
    </div>
    <div class="triple-col">
        <div class="triple-title">累積淨損益</div>
        <div class="{'triple-val-r' if total_net_profit >= 0 else 'triple-val-g'}">{total_net_profit:+.0f}</div>
        <div class="{'triple-pct-r' if total_net_profit >= 0 else 'triple-pct-g'}">{r_total:+.2f}%</div>
    </div>
    <div class="triple-col flash-gold-box">
        <div class="triple-title" style="color: #b48608; margin-bottom: 5px;">⚡ {current_month_num} 月預估領息總額</div>
        <div class="triple-val-gold">${current_month_div_amount:,.0f}</div>
        <div class="triple-sub-gold">{sub_title}</div>
    </div>
</div>
""", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
c1.metric("股票總市值", f"${g_mkt:,.0f}")
c2.metric("投資總成本", f"${g_cost:,.0f}")
c3.metric("全年預估總領息", f"${sum([monthly_calendar[m]['amount'] for m in range(1, 13)]):,.0f}")
st.write("---")

cols_btn_r1 = st.columns(3)
cols_btn_r2 = st.columns(3)
with cols_btn_r1[0]: st.button("📅 每月領息日曆", on_click=toggle_state, args=('show_calendar',), type="primary" if st.session_state.show_calendar else "secondary", use_container_width=True)
with cols_btn_r1[1]: st.button("📂 除權息/手動配息設定", on_click=toggle_state, args=('show_div_db',), type="primary" if st.session_state.show_div_db else "secondary", use_container_width=True)
with cols_btn_r1[2]: st.button("📡 股價區間監控", on_click=toggle_state, args=('show_tech',), type="primary" if st.session_state.show_tech else "secondary", use_container_width=True)
with cols_btn_r2[0]: st.button("📊 詳細持股明細", on_click=toggle_state, args=('show_holdings',), type="primary" if st.session_state.show_holdings else "secondary", use_container_width=True)
with cols_btn_r2[1]: st.button("🧩 ETF 成份股", on_click=toggle_state, args=('show_constituents',), type="primary" if st.session_state.show_constituents else "secondary", use_container_width=True) 
with cols_btn_r2[2]: st.button("🏦 股票質押專區", on_click=toggle_state, args=('show_pledge',), type="primary" if st.session_state.show_pledge else "secondary", use_container_width=True) 
st.write("---")

if st.session_state.show_calendar:
    st.markdown("#### 📅 1~12月 預估領息日曆")
    sm = int(st.selectbox("選擇月份：", [f"{m} 月" for m in range(1, 13)], index=datetime.today().month - 1).replace(" 月", ""))
    st.markdown(f"<div class='month-card'><div class='month-title'>{sm} 月預估領息</div><div class='month-amount'>${monthly_calendar[sm]['amount']:,.0f}</div><div class='month-sources'>來源：{'、'.join(monthly_calendar[sm]['sources']) if monthly_calendar[sm]['sources'] else '無'}</div></div>", unsafe_allow_html=True)
    st.write("---")

if st.session_state.show_div_db:
    with st.expander("🛠️ 手動配息覆蓋面板", expanded=True):
        custom_dict = st.session_state.my_data.get('custom_divs', {})
        display_list = [{"代號": i['symbol'], "名稱": i['name'], "每股配息": custom_dict.get(i['symbol'], {}).get('v', 0.0), "持有張數": i['holdings']} for i in st.session_state.my_data.get('etfs', [])]
        if display_list:
            edited_custom = st.data_editor(pd.DataFrame(display_list), use_container_width=True, hide_index=True, column_config={"代號": st.column_config.TextColumn(disabled=True), "名稱": st.column_config.TextColumn(disabled=True), "每股配息": st.column_config.NumberColumn(format="%.3f"), "持有張數": st.column_config.NumberColumn(format="%.3f", disabled=True)})
            if st.button("💾 儲存配息資料並套用", type="primary"):
                st.session_state.my_data['custom_divs'] = {str(r['代號']): {"v": float(r['每股配息'])} for _, r in edited_custom.iterrows() if pd.notna(r['每股配息']) and float(r['每股配息']) > 0}
                save_to_json(st.session_state.my_data); st.cache_data.clear(); st.rerun()
    st.write("---")

if st.session_state.show_tech:
    st.markdown("#### 📡 庫存價格區間監控與自動更新")
    col_a1, col_a2 = st.columns([8, 2])
    with col_a1: st.dataframe(df_tech.style.applymap(lambda x: 'color: red;' if '+' in str(x) else 'color: green;' if '-' in str(x) else '', subset=['今日損益', '今日漲跌幅']), use_container_width=True, hide_index=True)
    with col_a2:
        st.radio("即時更新(5秒)", ["❌ 關閉", "✅ 開啟"], key="auto_refresh_mode")
    st.write("---")

if st.session_state.show_holdings:
    st.markdown("#### 📊 詳細持股明細")
    st.dataframe(df.style.format({"現價":"{:.2f}", "均價":"{:.2f}", "張數":"{:.3f}", "市值":"{:,.0f}", "損益":"{:,.0f}"}), use_container_width=True, hide_index=True)
    st.write("---")

if st.session_state.show_constituents:
    st.markdown("#### 🧩 專屬庫存 ETF 核心成分股佔比")
    c_cols = st.columns(3)
    for idx, item in enumerate(st.session_state.my_data['etfs']):
        sym = item['symbol']
        if sym in ETF_CONSTITUENTS_DB:
            df_comp = pd.DataFrame(ETF_CONSTITUENTS_DB[sym])
            base = alt.Chart(df_comp).encode(theta=alt.Theta("weight:Q", stack=True), color="name:N")
            chart = base.mark_arc(outerRadius=100, innerRadius=40).properties(height=280)
            with c_cols[idx % 3]:
                st.markdown(f"**🛡️ {item['name']}**")
                st.altair_chart(chart, use_container_width=True)
    st.write("---")

if st.session_state.show_pledge:
    st.markdown("#### 🏦 股票質押專區 (維持率監控)")
    borrowed = st.number_input("💸 輸入已借入總額 (元)", value=int(st.session_state.my_data['pledge'].get('borrowed_amount', 0)), step=10000)
    if borrowed != st.session_state.my_data['pledge'].get('borrowed_amount', 0): st.session_state.my_data['pledge']['borrowed_amount'] = borrowed; save_to_json(st.session_state.my_data); st.rerun()
    
    pledge_list, total_p_mkt, total_limit = [], 0, 0
    for i in st.session_state.my_data['etfs']:
        curr_p = df[df['代號'] == i['symbol']]['現價'].values[0] if not df.empty else 0
        p_mkt = i.get('pledged_shares', 0.0) * 1000 * curr_p if i.get('is_pledged', False) else 0
        p_limit = p_mkt * 0.6 if i.get('is_pledged', False) else 0
        total_p_mkt += p_mkt; total_limit += p_limit
        pledge_list.append({"選取": i.get('is_pledged', False), "名稱": i['name'], "總張數": i['holdings'], "質押張數": i.get('pledged_shares', 0.0), "質押市值": round(p_mkt, 0), "可借上限": round(p_limit, 0)})
        
    m_ratio = (total_p_mkt / borrowed * 100) if borrowed > 0 else 0
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("擔保品總市值", f"${total_p_mkt:,.0f}"); col_m2.metric("總可借款上限", f"${total_limit:,.0f}")
    if borrowed > 0: col_m3.metric("🚨 維持率", f"{m_ratio:.2f}%", "注意" if m_ratio < 160 else "安全")

    edited_p = st.data_editor(pd.DataFrame(pledge_list), column_config={"選取": st.column_config.CheckboxColumn(), "質押張數": st.column_config.NumberColumn(format="%.3f")}, disabled=["名稱", "總張數", "質押市值", "可借上限"], use_container_width=True, hide_index=True)
    has_p_changes = False
    for _, r in edited_p.iterrows():
        for e in st.session_state.my_data['etfs']:
            if e['name'] == r['名稱']:
                if e.get('pledged_shares', 0.0) != r['質押張數'] or e.get('is_pledged', False) != r['選取']:
                    e['pledged_shares'] = min(r['質押張數'], e['holdings']); e['is_pledged'] = r['選取']; has_p_changes = True
    if has_p_changes: save_to_json(st.session_state.my_data); st.rerun()
    st.write("---")

bot_c1, bot_c2 = st.columns([2, 8])
with bot_c1:
    if st.button("🔄 重整股價", use_container_width=True): st.cache_data.clear(); st.rerun()

with bot_c2:
    with st.expander("⚙️ 標的管理 (庫存新增 / 修改 / 刪除)", expanded=True):
        st.markdown("#### ➕ 新增庫存標的")
        col_add1, col_add2, col_add3, col_add4 = st.columns(4)
        with col_add1: st.text_input("代號", key="add_sym_bot", on_change=auto_fill_etf_name)
        with col_add2: st.text_input("名稱", key="add_name_bot")
        with col_add3: st.number_input("張數", step=0.001, format="%.3f", key="add_h_bot")
        with col_add4: st.number_input("均價", step=0.01, key="add_c_bot")
        st.button("確認新增", use_container_width=True, on_click=add_new_etf_bot)

        if st.session_state.my_data['etfs']:
            st.markdown("---"); st.markdown("#### 📝 修改庫存 (支援小數點 3 位)")
            for i, item in enumerate(st.session_state.my_data['etfs']):
                cc1, cc2, cc3 = st.columns([4, 4, 2])
                with cc1: st.number_input(f"{item['name']} 張數", value=float(item['holdings']), step=0.001, format="%.3f", key=f"edit_h_{i}")
                with cc2: st.number_input(f"{item['name']} 均價", value=float(item['cost']), step=0.01, key=f"edit_c_{i}")
                with cc3: 
                    st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
                    st.button(f"🗑️ 刪除", key=f"del_{i}", on_click=delete_etf, args=(i,), use_container_width=True)
            st.button("💾 儲存修改", use_container_width=True, type="primary", on_click=save_edits)

if st.session_state.get('auto_refresh_mode') == "✅ 開啟":
    time.sleep(5); st.cache_data.clear(); st.rerun()
