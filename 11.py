import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import altair as alt
from streamlit_autorefresh import st_autorefresh

# --- 1. 網頁基礎設定 ---
st.set_page_config(page_title="淑英姐 ETF 隨身戰情室", layout="wide")
st_autorefresh(interval=15 * 1000, key="data_refresh")

# --- 2. 核心數據管理 ---
SETTINGS_FILE = 'settings.json'

def save_to_json(data):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_settings():
    # 嚴格依照淑英姐 2026/05 最新黑底截圖數據
    default_data = {
        "etfs": [
            {"symbol": "0056.TW", "name": "元大高股息", "shares": 3000, "cost": 41.45, "manual_pnl": -1931},
            {"symbol": "00646.TW", "name": "元大S&P500", "shares": 7000, "cost": 44.90, "manual_pnl": 181134},
            {"symbol": "00903.TW", "name": "富邦元宇宙", "shares": 2000, "cost": 14.33, "manual_pnl": 8690},
            {"symbol": "00940.TW", "name": "元大台灣價值高息", "shares": 13000, "cost": 9.88, "manual_pnl": 5645},
            {"symbol": "6142.TW", "name": "聚亨", "shares": 3513, "cost": 34.05, "manual_pnl": -91201},
            {"symbol": "2601.TW", "name": "益航", "shares": 9000, "cost": 21.40, "manual_pnl": -147673},
            {"symbol": "2887.TW", "name": "台新新光金", "shares": 2274, "cost": 17.91, "manual_pnl": 13148}
        ]
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 強制檢查是否包含新標的，若無則重置
                if "6142.TW" not in [item['symbol'] for item in data['etfs']]:
                    return default_data
                return data
        except: return default_data
    return default_data

if 'my_data' not in st.session_state:
    st.session_state.my_data = load_settings()

# --- 3. 數據抓取核心 ---

@st.cache_data(ttl=10)
def fetch_market_data():
    us_tickers = {"^DJI": "道瓊工業", "^IXIC": "那斯達克", "^SOX": "費城半導體", "NVDA": "輝達 NVIDIA", "TSM": "台積電 ADR"}
    tw_tickers = {"^TWII": "台股大盤", "2330.TW": "台積電", "2454.TW": "聯發科"}
    def get_data(tickers, prefix):
        results = []
        for sym, name in tickers.items():
            try:
                tk = yf.Ticker(sym)
                hist = tk.history(period="1d")
                if not hist.empty:
                    curr, prev = float(hist['Close'].iloc[-1]), tk.fast_info.get('regularMarketPreviousClose', float(hist['Close'].iloc[-1]))
                    data_time = hist.index[-1].strftime('%m/%d')
                else:
                    curr = float(tk.fast_info.get('lastPrice', 0))
                    prev = float(tk.fast_info.get('regularMarketPreviousClose', curr))
                    data_time = datetime.now().strftime('%m/%d')
                if curr > 0:
                    diff = curr - prev
                    pct = (diff / prev) * 100 if prev != 0 else 0
                    results.append({"name": name, "icon": prefix, "price": curr, "diff": diff, "pct": pct, "time": data_time})
            except: pass
        return results
    return get_data(us_tickers, "🇺🇸") + get_data(tw_tickers, "🇹🇼")

@st.cache_data(ttl=10)
def fetch_analysis(etf_list):
    if not etf_list: return pd.DataFrame(), 0, 0, 0, 0
    res, t_mkt, t_pnl, t_cost, t_day_change = [], 0, 0, 0, 0
    
    for item in etf_list:
        try:
            tk = yf.Ticker(item['symbol'])
            hist = tk.history(period="2d")
            if not hist.empty:
                curr_p = hist['Close'].iloc[-1]
                prev_p = hist['Close'].iloc[-2] if len(hist) >= 2 else curr_p
            else:
                curr_p = item['cost']
                prev_p = curr_p
            
            day_chg = (curr_p - prev_p) * item['shares']
            status_light = "🔴" if day_chg > 0 else "🟢" if day_chg < 0 else "🔵"
            
            t_mkt += (item['shares'] * curr_p); t_pnl += item['manual_pnl']; t_cost += (item['shares'] * item['cost']); t_day_change += day_chg
            
            res.append({
                "狀態": status_light,
                "名稱": item['name'], 
                "代號": item['symbol'].split('.')[0],
                "買入均價": f"{item['cost']:.2f}",
                "目前現價": round(curr_p, 2), 
                "今日損益": day_chg, 
                "總損益": item['manual_pnl']
            })
        except: continue
    return pd.DataFrame(res), t_mkt, t_pnl, t_cost, t_day_change

# --- 4. 介面渲染 ---
def render_custom_card(data):
    b_color = "#ef4444" if data['diff'] > 0 else "#22c55e" if data['diff'] < 0 else "#3b82f6"
    html = f"""
    <div style="background-color: white; border-radius: 10px; padding: 10px; margin-bottom: 10px; border-left: 5px solid {b_color}; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
        <div style="font-size: 12px; color: #666;">{data['icon']} {data['name']}</div>
        <div style="font-size: 18px; font-weight: bold;">{data['price']:,.2f}</div>
        <div style="font-size: 12px; color: {b_color}; font-weight: bold;">{data['diff']:+,.2f} ({data['pct']:.2f}%)</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

st.title("📱 淑英姐 ETF 隨身戰情室")

# 獲取數據
market_data = fetch_market_data()
df, g_mkt, g_pnl, g_cost, g_day_chg = fetch_analysis(st.session_state.my_data['etfs'])

# 市場指標
with st.container():
    cols = st.columns(len(market_data))
    for i, item in enumerate(market_data):
        with cols[i]: render_custom_card(item)

st.divider()

# 總資產概況
c1, c2 = st.columns(2)
with c1: st.metric("今日估計盈虧", f"{g_day_chg:+,.0f} 元", delta_color="normal")
with c2: st.metric("手動總損益", f"{g_pnl:,.0f} 元")

if not df.empty:
    st.dataframe(df.style.format({"今日損益":"{:+,.0f}","總損益":"{:,.0f}"}).map(lambda x: f'color:{"red" if (isinstance(x, (int,float)) and x>0) or str(x).startswith("+") else "green" if (isinstance(x, (int,float)) and x<0) or str(x).startswith("-") else "black"};font-weight:bold;', subset=['總損益', '今日損益']), use_container_width=True, hide_index=True)

# --- 🛠 資產管理 ---
with st.expander("🛠 管理我的持股 (新增標的/修正中文名)"):
    st.markdown("#### 1. ➕ 新增股票")
    nc1, nc2, nc3 = st.columns([2, 1, 1])
    with nc1: ns = st.text_input("輸入代號 (例: 2330.TW)", key="new_symbol").upper()
    with nc2: nsh = st.number_input("股數", value=1000, step=100)
    with nc3: 
        if st.button("✨ 點我新增"):
            if ns:
                try:
                    tk = yf.Ticker(ns)
                    raw_name = tk.info.get('shortName', tk.info.get('longName', ns))
                    clean_name = raw_name.split(' ETF')[0].split('基金')[0]
                    st.session_state.my_data['etfs'].append({"symbol": ns, "name": clean_name, "shares": nsh, "cost": 0.0, "manual_pnl": 0})
                    st.success(f"已加入「{clean_name}」！請儲存。")
                except: st.error("代號需包含 .TW")

    st.divider()
    st.markdown("#### 2. 📋 修正持股與名稱")
    updated_list = []
    for i, item in enumerate(st.session_state.my_data['etfs']):
        c1, c2, c3, c4, c5 = st.columns([1.5, 1, 1, 1, 0.5])
        with c1: new_n = st.text_input(f"顯示名稱", value=item['name'], key=f"n_{i}")
        with c2: new_s = st.number_input(f"股數", value=int(item['shares']), key=f"s_{i}")
        with c3: new_c = st.number_input(f"買入均價", value=float(item['cost']), key=f"c_{i}")
        with c4: new_p = st.number_input(f"損益修正", value=int(item['manual_pnl']), key=f"p_{i}")
        with c5: 
            if st.button("🗑️", key=f"del_{i}"): continue
        updated_list.append({"symbol": item['symbol'], "name": new_n, "shares": new_s, "cost": new_c, "manual_pnl": new_p})
    
    if st.button("💾 儲存並更新淑英姐數據", type="primary"):
        st.session_state.my_data['etfs'] = updated_list
        save_to_json(st.session_state.my_data)
        st.rerun()