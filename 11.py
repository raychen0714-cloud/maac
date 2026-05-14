import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os
import numpy as np
from datetime import datetime, timedelta
import altair as alt
import requests
import time  # 引入原生時間套件，處理自動更新

# --- 1. 網頁基礎設定 ---
st.set_page_config(page_title="ETF 投資戰情室", layout="wide", page_icon="📈")

# 全局提示訊息狀態
if 'update_success' in st.session_state and st.session_state.update_success:
    st.toast(st.session_state.update_success, icon="✅")
    st.session_state.update_success = False

# 自定義 CSS
st.markdown("""
    <style>
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
    
    [data-testid="stMetric"] { 
        background-color: var(--secondary-background-color); 
        padding: 12px; 
        border-radius: 10px; 
        box-shadow: 1px 1px 4px rgba(0,0,0,0.05);
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
    </style>
    """, unsafe_allow_html=True)

st.markdown("### 📈 ETF 投資戰情室")

# --- 2. 系統設定與資料庫 ---
SETTINGS_FILE = 'settings.json'

ETF_FULL_DATABASE = {
    "0050": ["元大台灣50", [1, 7], "0.32%", "0.035%"],
    "0056": ["元大台灣高股息", [1, 4, 7, 10], "0.3%", "0.035%"],
    "00713": ["元大台灣高息低波", [3, 6, 9, 12], "0.3%", "0.035%"],
    "00878": ["國泰永續ESG高股息", [2, 5, 8, 11], "0.25%", "0.035%"],
    "00891": ["中信關鍵半導體", [1, 4, 7, 10], "0.4%", "0.035%"],
    "00919": ["群益台灣精選高息", [3, 6, 9, 12], "0.3%", "0.035%"],
    "00927": ["群益台灣半導體收益", [1, 4, 7, 10], "0.4%", "0.035%"],
    "00929": ["復華台灣科技優息", list(range(1, 13)), "0.30%", "0.030%"],
    "00940": ["元大臺灣價值高息", list(range(1, 13)), "0.3%", "0.030%"],
    "00981A": ["統一台股增長主動式", [3, 6, 9, 12], "1.0%", "0.10%"],
    "00982A": ["群益台灣精選強棒主動式", [2, 5, 8, 11], "0.8%", "0.035%"]
}

EXTRA_ETFS = {
    "00631L": "00631L 元大台灣50正2", "00632R": "00632R 元大台灣50反1", 
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
    "00929.TW": [{"name": "聯發科", "weight": 9.5}, {"name": "聯電", "weight": 7.2}, {"name": "日月光投控", "weight": 6.8}, {"name": "瑞昱", "weight": 6.5}, {"name": "聯詠", "weight": 6.1}, {"name": "其他", "weight": 63.9}],
    "0050.TW": [{"name": "台積電", "weight": 52.5}, {"name": "鴻海", "weight": 5.5}, {"name": "聯發科", "weight": 4.8}, {"name": "廣達", "weight": 2.1}, {"name": "台達電", "weight": 1.9}, {"name": "其他", "weight": 33.2}],
    "00981A.TW": [{"name": "台積電", "weight": 18.5}, {"name": "聯發科", "weight": 8.2}, {"name": "奇鋐", "weight": 6.5}, {"name": "台光電", "weight": 5.8}, {"name": "雙鴻", "weight": 5.2}, {"name": "其他", "weight": 55.8}]
}

def load_settings():
    default_data = {
        "etfs": [], 
        "pledge": {"borrowed_amount": 0},
        "watchlist": [],
        "custom_divs": {},
        "manual_monthly_divs": {str(i): -1.0 for i in range(1, 13)}
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f: 
                data = json.load(f)
                for k, v in default_data.items():
                    if k not in data: data[k] = v
                for etf in data.get('etfs', []):
                    if 'div_shares' not in etf:
                        etf['div_shares'] = etf.get('holdings', 0.0)
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

if 'pledge' not in st.session_state.my_data: 
    st.session_state.my_data['pledge'] = {"borrowed_amount": 0}

if 'manual_monthly_divs' not in st.session_state.my_data:
    st.session_state.my_data['manual_monthly_divs'] = {str(i): -1.0 for i in range(1, 13)}

# 確保所有庫存 ETF 都有相關欄位
for etf in st.session_state.my_data['etfs']:
    if 'pledged_shares' not in etf: etf['pledged_shares'] = 0.0
    if 'is_pledged' not in etf: etf['is_pledged'] = False 
    if 'div_shares' not in etf: etf['div_shares'] = etf.get('holdings', 0.0)
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
            "symbol": final_symbol, "name": new_name, "holdings": new_h, "cost": new_c, "div_shares": new_h, "alert_high": 0.0, "alert_low": 0.0, "pledged_shares": 0.0, "is_pledged": False
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
        ds_val = st.session_state.get(f"edit_ds_{i}", item.get('div_shares', h_val))
        temp_list.append({
            "symbol": item['symbol'], "name": item['name'], "holdings": h_val, "cost": c_val, "div_shares": ds_val,
            "alert_high": item.get('alert_high', 0.0), "alert_low": item.get('alert_low', 0.0), 
            "pledged_shares": item.get('pledged_shares', 0.0), "is_pledged": item.get('is_pledged', False)
        })
    st.session_state.my_data['etfs'] = temp_list
    save_to_json(st.session_state.my_data)

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

@st.cache_data(ttl=10) 
def fetch_taiwan_upcoming_dividends():
    tw_div_data = {}
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        url_twse = "https://www.twse.com.tw/exchangeReport/TWT49U?response=json"
        res = requests.get(url_twse, headers=headers, timeout=5).json()
        if res.get('stat') == 'OK':
            import re
            for row in res.get('data', []):
                if len(row) >= 8: 
                    date_str, symbol = str(row[0]), str(row[1]).strip() 
                    match = re.search(r'(\d+)年(\d+)月(\d+)日', date_str)
                    if match:
                        tw_year, month, day = match.groups()
                        ex_date = f"{int(tw_year) + 1911}-{month.zfill(2)}-{day.zfill(2)}"
                        amount = 0.0
                        cash_div_str = str(row[7]).replace(',', '').strip()
                        if cash_div_str and cash_div_str.replace('.', '', 1).isdigit(): amount = float(cash_div_str)
                        pay_date = (datetime.strptime(ex_date, '%Y-%m-%d') + timedelta(days=28)).strftime('%Y-%m-%d')
                        tw_div_data[symbol] = {"ex_date": ex_date, "pay_date": pay_date, "amount": amount}
    except Exception: pass
    return tw_div_data

@st.cache_data(ttl=86400) 
def get_fund_size(symbol):
    try:
        tk = yf.Ticker(symbol)
        cap = tk.fast_info.get('marketCap')
        if cap and cap > 0: return cap
        shares = tk.fast_info.get('shares')
        price = tk.fast_info.get('lastPrice') or tk.fast_info.get('previousClose')
        if shares and price: return shares * price
    except Exception: pass
    return None

@st.cache_data(ttl=43200)
def get_div_data(symbol, custom_div_info=None):
    is_announced, div_amount, ex_date, pay_date, fill_status, status_msg = False, 0.0, "待官方公告", "待官方公告", "-", "⏳ 依前次估算"
    clean_sym = symbol.replace('.TW', '')
    taiwan_div_data = fetch_taiwan_upcoming_dividends()
    
    try:
        tk = yf.Ticker(symbol)
        today = datetime.today()
        
        if custom_div_info and custom_div_info.get('v', 0) > 0:
            div_amount, ex_date, pay_date = custom_div_info['v'], custom_div_info['d'], custom_div_info['p']
            is_announced = True
            status_msg = "✅ 已公告 (手動)" if datetime.strptime(ex_date, '%Y-%m-%d').date() >= today.date() else "✅ 前次紀錄 (手動)"
        elif clean_sym in taiwan_div_data:
            is_announced = True
            ex_date, pay_date, official_amount = taiwan_div_data[clean_sym]['ex_date'], taiwan_div_data[clean_sym]['pay_date'], taiwan_div_data[clean_sym]['amount']
            if official_amount > 0: div_amount = official_amount
            else:
                actions = tk.actions
                if not actions.empty: div_amount = float(actions.sort_index(ascending=False).head(1)['Dividends'].values[0])
            status_msg = "✅ 已公告 (台灣官方)" if datetime.strptime(ex_date, '%Y-%m-%d').date() >= today.date() else "✅ 前次配息 (台灣官方)"
        else:
            divs = tk.dividends
            if not divs.empty:
                latest_div = divs.sort_index(ascending=False).head(1)
                div_amount = float(latest_div.values[0]) 
                last_ex_date_obj = latest_div.index[0].replace(tzinfo=None)
                ex_date = last_ex_date_obj.strftime('%Y-%m-%d')
                pay_date = (last_ex_date_obj + timedelta(days=28)).strftime('%Y-%m-%d') 
                is_announced = True
                status_msg = "✅ 已公告 (近期)" if last_ex_date_obj.date() >= today.date() else "✅ 前次配息紀錄"

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
                    t_days, filled = 0, False
                    for d, r in post_ex.iterrows():
                        t_days += 1
                        if r['High'] >= target_price:
                            fill_status = f"{d.month}/{d.day} 填息完成 ({t_days}天)"
                            filled = True
                            break
                    if not filled: fill_status = f"未填息 ({t_days}天)"
    except Exception: pass
    return is_announced, div_amount, ex_date, pay_date, fill_status, status_msg

@st.cache_data(ttl=10)
def fetch_data(etf_list, custom_divs):
    if not etf_list: return pd.DataFrame(), pd.DataFrame(), 0, 0, 0, 0, [], {i: {"amount": 0, "sources": []} for i in range(1, 13)}
    results, tech_results, price_alerts = [], [], []
    total_mkt, total_cost, total_div, total_today_pnl = 0, 0, 0, 0
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

            status_light = "🔴" if curr_p > prev_close else "🟢" if curr_p < prev_close else "⚪"
            display_name = f"{status_light} {item['name']}"

            shares = item['holdings'] * 1000
            mkt_val = shares * curr_p
            cost_val = shares * item['cost']
            div_shares_val = item.get('div_shares', item['holdings']) * 1000
            
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

            is_announced, div_amount, ex_date, pay_date, fill_status, status_msg = get_div_data(item['symbol'], custom_divs.get(item['symbol']))
            
            clean_sym_only = item['symbol'].replace('.TW', '')
            months_to_pay = DIVIDEND_SCHEDULE.get(item['symbol'], [])
            if not months_to_pay and clean_sym_only in ETF_FULL_DATABASE:
                months_to_pay = ETF_FULL_DATABASE[clean_sym_only][1]
            
            est_yield = (div_amount * len(months_to_pay)) / curr_p * 100 if len(months_to_pay) > 0 and div_amount > 0 and curr_p > 0 else 0.0

            if div_amount > 0 and div_shares_val > 0:
                explicit_pay_month = None
                if is_announced and pay_date != "待官方公告":
                    try:
                        explicit_pay_month = datetime.strptime(pay_date, '%Y-%m-%d').month
                        monthly_calendar[explicit_pay_month]["amount"] += (div_shares_val * div_amount)
                        if item['name'] not in monthly_calendar[explicit_pay_month]["sources"]:
                            monthly_calendar[explicit_pay_month]["sources"].append(item['name'])
                    except: pass

                for m in months_to_pay:
                    pay_m = m + 1 if m < 12 else 1
                    if pay_m != explicit_pay_month:
                        monthly_calendar[pay_m]["amount"] += (div_shares_val * div_amount)
                        if item['name'] not in monthly_calendar[pay_m]["sources"]:
                            monthly_calendar[pay_m]["sources"].append(item['name'])

            total_mkt += mkt_val; total_cost += cost_val; total_div += (div_shares_val * div_amount)
            fee_info = ETF_FEES_DB.get(item['symbol'], {"經理費": "-", "保管費": "-"})

            results.append({
                "代號": item['symbol'], "名稱": item['name'], "現價": curr_p, "均價": item['cost'],
                "張數": item['holdings'], "市值": mkt_val, "損益": profit, "報酬率": roi,
                "參與配息張數": item.get('div_shares', item['holdings']),
                "經理費": fee_info["經理費"], "保管費": fee_info["保管費"], 
                "單次預估領息": div_shares_val * div_amount, "每股配息": div_amount,
                "最新公告除息日": ex_date, "預估發放日": pay_date, "已公告": is_announced,
                "狀態": status_msg, "最新填息紀錄": fill_status, "基金規模": cap_str
            })
            
            month_tag = "月配息" if len(months_to_pay) == 12 else ",".join(map(str, months_to_pay)) + "月" if months_to_pay else "-"
            tech_results.append({
                "ETF 名稱": display_name, "配息月份": month_tag, "股票張數": item['holdings'], 
                "現價": round(curr_p, 2), "今日損益": today_pnl_str, "今日漲跌幅": today_pct_str, 
                "今日交易量": f"{vol:,.0f}" if vol > 0 else "無資料", "年殖利率": f"{est_yield:.2f}%", 
                "今日最高/最低": f"${day_high:.2f} / ${day_low:.2f}", "52週最高/最低": f"${year_high:.2f} / ${year_low:.2f}", 
                "設定高標(停利)": a_high, "設定低標(停損)": a_low
            })
        except Exception: continue
        
    return pd.DataFrame(results), pd.DataFrame(tech_results), total_mkt, total_cost, total_div, total_today_pnl, price_alerts, monthly_calendar

df, df_tech, g_mkt, g_cost, g_div, g_today_pnl, price_alerts, monthly_calendar = fetch_data(st.session_state.my_data['etfs'], st.session_state.my_data.get('custom_divs', {}))

# --- 5. 介面呈現 ---
st.write("<div style='height: 20px;'></div>", unsafe_allow_html=True) 

if price_alerts:
    for alert in price_alerts:
        if alert['type'] == "high": st.markdown(f"<div class='alert-high'>🚨 突破停利高標：【{alert['name']}】 現價 ${alert['price']:.2f} 已突破您設定的 ${alert['target']}！</div>", unsafe_allow_html=True)
        else: st.markdown(f"<div class='alert-low'>⚠️ 跌破停損低標：【{alert['name']}】 現價 ${alert['price']:.2f} 已跌破您設定的 ${alert['target']}！</div>", unsafe_allow_html=True)

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
sys_current_month_amt = monthly_calendar[current_month_num]["amount"]
manual_amt = st.session_state.my_data['manual_monthly_divs'].get(str(current_month_num), -1.0)
final_current_month_amt = manual_amt if manual_amt >= 0 else sys_current_month_amt

current_month_div_str = f"${final_current_month_amt:,.0f}"
div_sources = monthly_calendar[current_month_num]["sources"]
sub_title = f"來自：{'、'.join([s.split(' ')[0] for s in div_sources])}" if div_sources else "本月無除息預定"
if manual_amt >= 0: sub_title = "✍️ 已套用您手動修改的金額"

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
    <div class="triple-col" style="background-color: #fffdf5; border: 2px solid #f1c40f;">
        <div class="triple-title" style="color: #b48608; margin-bottom: 5px;">⚡ {current_month_num} 月預估領息總額</div>
        <div class="triple-val-gold">{current_month_div_str}</div>
        <div class="triple-sub-gold">{sub_title}</div>
    </div>
</div>
"""
st.markdown(html_triple_pnl, unsafe_allow_html=True)

total_yearly_div = 0
for m in range(1, 13):
    m_val = st.session_state.my_data['manual_monthly_divs'].get(str(m), -1.0)
    total_yearly_div += m_val if m_val >= 0 else monthly_calendar[m]['amount']

c1, c2, c3 = st.columns(3)
c1.metric("股票總市值", f"${g_mkt:,.0f}")
c2.metric("投資總成本", f"${g_cost:,.0f}")
c3.metric("全年預估總領息", f"${total_yearly_div:,.0f}")
st.write("---")

cols_btn_r1 = st.columns(3)
cols_btn_r2 = st.columns(3)
cols_btn_r3 = st.columns(3)

b3_lbl, b3_typ = ("🔽 收起每月領息", "primary") if st.session_state.show_calendar else ("📅 展開每月領息", "secondary")
b4_lbl, b4_typ = ("🔽 收起除權息", "primary") if st.session_state.show_div_db else ("📂 展開除權息", "secondary")
b5_lbl, b5_typ = ("🔽 收起股價監控", "primary") if st.session_state.show_tech else ("📡 展開股價監控", "secondary")
b6_lbl, b6_typ = ("🔽 收起持股明細", "primary") if st.session_state.show_holdings else ("📊 展開持股明細", "secondary")
b7_lbl, b7_typ = ("🔽 收起ETF成份股", "primary") if st.session_state.show_constituents else ("🧩 展開ETF成份股", "secondary")
b8_lbl, b8_typ = ("🔽 收起每日股價", "primary") if st.session_state.show_daily_price else ("🗓️ 展開每日股價", "secondary") 
b9_lbl, b9_typ = ("🔽 收起質押專區", "primary") if st.session_state.show_pledge else ("🏦 展開質押專區", "secondary") 

with cols_btn_r1[0]: st.button(b3_lbl, on_click=toggle_calendar, type=b3_typ, use_container_width=True)
with cols_btn_r1[1]: st.button(b4_lbl, on_click=toggle_div_db, type=b4_typ, use_container_width=True)
with cols_btn_r1[2]: st.button(b5_lbl, on_click=toggle_tech, type=b5_typ, use_container_width=True)

with cols_btn_r2[0]: st.button(b6_lbl, on_click=toggle_holdings, type=b6_typ, use_container_width=True)
with cols_btn_r2[1]: st.button(b7_lbl, on_click=toggle_constituents, type=b7_typ, use_container_width=True) 
with cols_btn_r2[2]: st.button(b8_lbl, on_click=toggle_daily_price, type=b8_typ, use_container_width=True) 

# --- 修改這裡：把更新控制功能塞進這排 ---
with cols_btn_r3[0]: 
    st.button(b9_lbl, on_click=toggle_pledge, type=b9_typ, use_container_width=True) 

with cols_btn_r3[1]: 
    # 正是你畫圈的位子！使用原生 Checkbox 最穩定
    st.checkbox("⏱️ 5秒自動更新", key="auto_refresh_toggle")

with cols_btn_r3[2]:
    # 手動重整按鈕移來這，對齊滿版
    if st.button("🔄 手動重整股價", use_container_width=True):
        st.cache_data.clear()
        try:
            st.rerun()
        except AttributeError:
            st.experimental_rerun()

st.write("---")

if st.session_state.show_calendar:
    st.markdown("#### 📅 1~12月 預估領息日曆與手動微調")
    cal_data = []
    for m in range(1, 13):
        sys_amt = monthly_calendar[m]['amount']
        manual_amt = st.session_state.my_data['manual_monthly_divs'].get(str(m), -1.0)
        cal_data.append({
            "月份": f"{m} 月",
            "系統自動預估 (元)": round(sys_amt, 0),
            "手動確認金額 (元)": manual_amt,
            "ETF 來源": "、".join([s.split(' ')[0] for s in monthly_calendar[m]['sources']]) if monthly_calendar[m]['sources'] else "-"
        })
    cal_df = pd.DataFrame(cal_data)
    edited_cal = st.data_editor(cal_df, column_config={"手動確認金額 (元)": st.column_config.NumberColumn("手動確認金額 (雙擊修改，-1為自動)", step=100.0, format="%.0f")}, disabled=["月份", "系統自動預估 (元)", "ETF 來源"], use_container_width=True, hide_index=True)
    if st.button("💾 儲存修改好的每月領息金額", type="primary"):
        for index, row in edited_cal.iterrows():
            m_str = str(index + 1)
            st.session_state.my_data['manual_monthly_divs'][m_str] = float(row["手動確認金額 (元)"])
        save_to_json(st.session_state.my_data)
        st.session_state.update_success = "每月領息金額已成功覆蓋儲存！"
        st.rerun()
    st.write("---")

if st.session_state.show_div_db:
    col_d1, col_d2 = st.columns([7, 3])
    with col_d1: st.markdown("#### 📚 專屬 ETF 與自選股 除權息時程總覽")
    with col_d2:
        if st.button("🔄 強制抓取最新公告", type="primary", use_container_width=True):
            st.cache_data.clear() 
            st.rerun()
    db_list = []
    if not df.empty:
        for _, row in df.iterrows():
            sym = row['代號']; months = DIVIDEND_SCHEDULE.get(sym, [])
            freq = "月配息" if len(months)==12 else "季配息" if len(months)==4 else "半年配" if len(months)==2 else "年配息" if len(months)==1 else "未知"
            db_list.append({
                "類別": "💼 庫存", "ETF 名稱": row['名稱'], "基金規模": row.get('基金規模', '系統無資料'),
                "配息頻率": freq, "配息月份": "、".join(map(str, months)) + " 月" if months else "未設定",
                "狀態": row['狀態'], "除息日": row['最新公告除息日'], "發放日": row['預估發放日'], 
                "每股金額": f"${row['每股配息']:.3f}", "最新填息紀錄": row['最新填息紀錄']
            })
    df_port_div = pd.DataFrame(db_list)
    df_wl_div = fetch_watchlist_dividend(st.session_state.my_data.get('watchlist', []), st.session_state.my_data.get('custom_divs', {}))
    final_div_df = pd.concat([df_port_div, df_wl_div], ignore_index=True) if not df_port_div.empty or not df_wl_div.empty else pd.DataFrame()
    if not final_div_df.empty: st.dataframe(final_div_df, use_container_width=True, hide_index=True)
    st.write("---")

if st.session_state.show_tech:
    if not df.empty:
        st.markdown("#### 📡 庫存價格區間監控與技術分析")
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
        
        df_tech_display = df_tech.drop(columns=["設定高標(停利)", "設定低標(停損)"]) if "設定高標(停利)" in df_tech.columns else df_tech
        try: styled_df_tech = df_tech_display.style.map(color_profit_loss, subset=['今日損益', '今日漲跌幅']).map(color_months, subset=['配息月份'])
        except: styled_df_tech = df_tech_display.style.applymap(color_profit_loss, subset=['今日損益', '今日漲跌幅']).applymap(color_months, subset=['配息月份'])

        st.dataframe(styled_df_tech, column_config={"現價": st.column_config.NumberColumn("現價", format="%.2f"), "股票張數": st.column_config.NumberColumn("股票張數", format="%.3f")}, use_container_width=True, hide_index=True)

        st.write("")
        st.markdown("#### 📊 詳細持股清單與內扣費率")
        format_dict = {"現價": "{:.3f}", "均價": "{:.3f}", "張數": "{:.3f}", "市值": "{:,.3f}", "損益": "{:,.3f}", "報酬率": "{:.3f}", "參與配息張數": "{:.3f}", "單次預估領息": "{:,.3f}", "每股配息": "{:.3f}"}
        st.dataframe(df.style.format(format_dict), use_container_width=True, hide_index=True)
    st.write("---")

if st.session_state.show_daily_price:
    st.markdown("#### 🗓️ 庫存與自選 ETF 近期每日收盤價")
    col_date1, col_date2 = st.columns(2)
    with col_date1: start_date = st.date_input("選擇開始日期", datetime.today() - timedelta(days=15))
    with col_date2: end_date = st.date_input("選擇結束日期", datetime.today())
    port_map = {item['symbol']: f"💼 {item['name']}" for item in st.session_state.my_data.get('etfs', [])}
    wl_map = {item['symbol']: f"👀 {item['name']}" for item in st.session_state.my_data.get('watchlist', [])}
    all_symbols_map = {**port_map, **wl_map}
    current_symbols = list(all_symbols_map.keys())
    
    if current_symbols and start_date <= end_date:
        try:
            hist_data = yf.download(current_symbols, start=start_date, end=end_date + timedelta(days=1))['Close']
            
            if len(current_symbols) == 1: 
                hist_data = hist_data.to_frame().rename(columns={current_symbols[0]: all_symbols_map[current_symbols[0]]})
            else: 
                hist_data = hist_data.rename(columns=all_symbols_map)
                
            diff_data = hist_data.diff()
            
            str_index = hist_data.index.strftime('%Y/%m/%d')
            hist_data.index = str_index
            diff_data.index = str_index
            
            display_hist = hist_data.sort_index(ascending=False).T
            display_diff = diff_data.sort_index(ascending=False).T
            
            def color_prices(df_to_style):
                css_df = pd.DataFrame('', index=df_to_style.index, columns=df_to_style.columns)
                for c in df_to_style.columns:
                    for r in df_to_style.index:
                        val_diff = display_diff.loc[r, c]
                        if pd.notna(val_diff):
                            if val_diff > 0:
                                css_df.loc[r, c] = 'color: #d32f2f; font-weight: bold;'
                            elif val_diff < 0:
                                css_df.loc[r, c] = 'color: #388e3c; font-weight: bold;'
                return css_df

            formatter_dict = {col: lambda x: f"{x:.2f}" if pd.notna(x) else "-" for col in display_hist.columns}
                
            st.dataframe(display_hist.style.format(formatter_dict).apply(color_prices, axis=None), use_container_width=True)
        except Exception as e: 
            st.info(f"暫時無法抓取歷史股價：{e}")
    st.write("---")

if st.session_state.show_holdings:
    if not df.empty:
        st.markdown("#### 📊 持股動態明細")
        for _, row in df.iterrows():
            p_color = "red" if row['損益'] >= 0 else "green"
            with st.expander(f"💎 {row['名稱']} | 預估淨報酬: :{p_color}[{row['報酬率']:+.2f}%]", expanded=True):
                col_l, col_m, col_r = st.columns(3)
                with col_l: st.write(f"張數: **{row['張數']:.3f}**"); st.write(f"現價: **{row['現價']:.2f}**")
                with col_m: st.markdown(f"市值: **${row['市值']:,.0f}**"); st.markdown(f"預估淨利: :{p_color}[**${row['損益']:,.0f}**]")
                with col_r: st.markdown(f"單次領息估算: :orange[**${row['單次預估領息']:,.0f}**]")
    st.write("---")

if st.session_state.show_constituents:
    if not df.empty:
        st.markdown("#### 🧩 專屬庫存 ETF 核心成分股佔比")
        c_cols = st.columns(3)
        for idx, item in enumerate(st.session_state.my_data['etfs']):
            sym, name = item['symbol'], item['name']
            comp_data = ETF_CONSTITUENTS_DB.get(sym, [{"name": "其他成分股", "weight": 100.0}])
            df_comp = pd.DataFrame(comp_data)
            base = alt.Chart(df_comp).encode(theta=alt.Theta("weight:Q", stack=True), color=alt.Color("name:N", legend=alt.Legend(orient="right")), tooltip=["name", "weight"])
            chart = base.mark_arc().properties(height=280)
            with c_cols[idx % 3]: st.markdown(f"🛡️ **{name}**"); st.altair_chart(chart, use_container_width=True)
    st.write("---")

if st.session_state.show_pledge:
    if not df.empty:
        st.markdown("#### 🏦 股票質押專區 (維持率監控)")
        borrowed = st.number_input("💸 輸入已向券商借入款項總額 (元)", min_value=0, value=int(st.session_state.my_data['pledge'].get('borrowed_amount', 0)), step=10000)
        if borrowed != st.session_state.my_data['pledge'].get('borrowed_amount', 0):
            st.session_state.my_data['pledge']['borrowed_amount'] = borrowed
            save_to_json(st.session_state.my_data)
            st.rerun()
        pledge_df_list = []
        total_pledge_mkt = 0
        for item in st.session_state.my_data['etfs']:
            curr_p = df[df['代號'] == item['symbol']]['現價'].values[0] if item['symbol'] in df['代號'].values else 0
            p_mkt = item.get('pledged_shares', 0.0) * 1000 * curr_p if item.get('is_pledged', False) else 0
            total_pledge_mkt += p_mkt
            pledge_df_list.append({"✓ 選取": item.get('is_pledged', False), "ETF 名稱": item['name'], "質押張數": item.get('pledged_shares', 0.0), "現價": round(curr_p, 2), "質押市值 (元)": round(p_mkt, 0)})
        margin_ratio = (total_pledge_mkt / borrowed * 100) if borrowed > 0 else 0
        st.metric("目前維持率", f"{margin_ratio:.2f}%", delta=f"{margin_ratio-130:.2f}%" if borrowed > 0 else "0", delta_color="normal" if margin_ratio > 160 else "inverse")
        st.data_editor(pd.DataFrame(pledge_df_list), use_container_width=True, hide_index=True)
    st.write("---")

# 底部管理區
with st.expander("⚙️ 標的管理 (庫存新增 / 修改 / 刪除)", expanded=True):
    st.text_input("輸入代碼 (不需手打 .TW)", key="add_sym_bot", on_change=auto_fill_etf_name)
    st.text_input("自定義名稱", key="add_name_bot")
    st.button("確認新增庫存", use_container_width=True, on_click=add_new_etf_bot)
    if st.session_state.my_data['etfs']:
        for i, item in enumerate(st.session_state.my_data['etfs']):
            with st.expander(f"📍 {item['name']}"):
                st.number_input("張數", value=float(item['holdings']), key=f"edit_h_{i}", step=0.001, format="%.3f")
                st.button(f"🗑️ 刪除", key=f"del_{i}", on_click=delete_etf, args=(i,))
        st.button("💾 儲存修改", use_container_width=True, type="primary", on_click=save_edits)

# --- 原生自動更新邏輯 (放在程式最底部執行) ---
if st.session_state.get("auto_refresh_toggle", False):
    time.sleep(5)
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()
