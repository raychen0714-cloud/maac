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
                return json.load(f)
        except: return default_data
    return default_data

if 'my_data' not in st.session_state:
    st.session_state.my_data = load_settings()

# --- 3. 數據抓取核心 ---

@st.cache_data(ttl=15)
def fetch_tw_night_session():
    name = "台指期 (夜盤)"
    icon = "🌙"
    try:
        url = "https://tw.stock.yahoo.com/quote/WTX%26"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        price_tag = soup.select_one('span[class*="Fz(32px)"]')
        change_tag = soup.select_one('span[class*="Fz(20px)"]')
        up_time = datetime.now().strftime('%m/%d %H:%M')
        if price_tag and change_tag:
            curr = float(price_tag.text.replace(',', ''))
            change_text = change_tag.text.replace(',', '').strip()
            is_down = "▼" in change_text or "-" in change_text
            clean_val = change_text.replace('▼', '').replace('▲', '').replace('+', '').replace('-', '').strip()
            val_part = clean_val.split(' ')[0]
            diff = -float(val_part) if is_down else float(val_part)
            prev = curr - diff
            pct = (diff / prev) * 100 if prev != 0 else 0
            return {"name": name, "icon": icon, "price": curr, "diff": diff, "pct": pct, "time": up_time, "error": False}
    except: pass
    return {"name": name, "icon": icon, "price": 0, "diff": 0, "pct": 0, "time": "--", "error": True}

@st.cache_data(ttl=10)
def fetch_market_data():
    us_tickers = {"^DJI": "道瓊工業", "^IXIC": "那斯達克", "^SOX": "費城半導體", "NVDA": "輝達 NVIDIA", "TSM": "台積電 ADR"}
    tw_tickers = {"^TWII": "台股加權 (大盤)", "2330.TW": "台積電 (台股)", "2454.TW": "聯發科 (台股)"}
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
                    results.append({"name": name, "icon": prefix, "price": curr, "diff": diff, "pct": pct, "time": data_time, "error": False})
                else: results.append({"name": name, "icon": prefix, "price": 0, "diff": 0, "pct": 0, "time": "--", "error": True})
            except: results.append({"name": name, "icon": prefix, "price": 0, "diff": 0, "pct": 0, "time": "--", "error": True})
        return results
    us_data = get_data(us_tickers, "🇺🇸")
    tw_data = get_data(tw_tickers, "🇹🇼")
    tw_data.append(fetch_tw_night_session())
    return us_data, tw_data

@st.cache_data(ttl=10)
def fetch_analysis(etf_list):
    if not etf_list: return pd.DataFrame(), 0, 0, 0, {}, 0, [], 0
    res, t_mkt, t_pnl, t_cost, t_day_change, annual_total = [], 0, 0, 0, 0, 0
    m_stats = {f"{m}月": {"total": 0, "detail": []} for m in range(1, 13)}
    reminders, today = [], datetime.now()
    
    div_cfg = {
        "0056.TW": {"m": [1, 4, 7, 10], "d": "2026-04-21", "v": 1.00}, 
        "00646.TW": {"m": [10], "d": "2026-10-20", "v": 0.80},
        "00903.TW": {"m": [2, 8], "d": "2026-08-15", "v": 0.15},
        "00940.TW": {"m": [1,2,3,4,5,6,7,8,9,10,11,12], "d": "2026-05-08", "v": 0.05},
        "2887.TW": {"m": [8], "d": "2026-08-10", "v": 0.60} 
    }
    
    for item in etf_list:
        try:
            tk = yf.Ticker(item['symbol'])
            hist = tk.history(period="5d")
            if not hist.empty:
                curr_p = hist['Close'].iloc[-1]
                prev_p = hist['Close'].iloc[-2] if len(hist) >= 2 else curr_p
            else:
                curr_p = item['cost']
                prev_p = curr_p
            
            day_chg = (curr_p - prev_p) * item['shares']
            cfg = div_cfg.get(item['symbol'], {"m": [], "d": "無", "v": 0.0})
            
            status_light = "🔴" if day_chg > 0 else "🟢" if day_chg < 0 else "🔵"
            
            recovery_str = "—"
            if cfg['v'] > 0:
                if curr_p >= item['cost']: recovery_str = f"✅ 已填息"
                else:
                    gap = item['cost'] - curr_p
                    recovery_str = f"⏳ 填息 {max(0, (1-(gap/cfg['v']))*100):.0f}%" if gap < cfg['v'] else "貼息中"
            
            cash = cfg['v'] * item['shares']
            for m in cfg["m"]:
                m_stats[f"{m}月"]["total"] += cash
                m_stats[f"{m}月"]["detail"].append({"股票": item['symbol'].split('.')[0], "金額": int(cash)})
                annual_total += cash
                
            t_mkt += (item['shares'] * curr_p); t_pnl += item['manual_pnl']; t_cost += (item['shares'] * item['cost']); t_day_change += day_chg
            
            res.append({
                "狀態": status_light,
                "代號名稱": f"{item['symbol'].split('.')[0]} {item['name']}", 
                "均價": f"{item['cost']:.2f}",
                "現價": round(curr_p, 2), 
                "今日漲跌": day_chg, 
                "累積損益": item['manual_pnl'], 
                "配息": f"{cfg['v']:.2f}",
                "填息": recovery_str,
                "除息預計": cfg["d"]
            })
        except: continue
    return pd.DataFrame(res).sort_values(by="除息預計", ascending=True), t_mkt, t_pnl, t_cost, m_stats, annual_total, reminders, t_day_change

# --- 4. 介面渲染 ---
def render_custom_card(data):
    if data.get('error') or data['price'] == 0:
        b_color, p_str, c_str, t_str, l_dot = "#3b82f6", "讀取中...", "連線中", "", "🔵"
    else:
        b_color = "#ef4444" if data['diff'] > 0 else "#22c55e" if data['diff'] < 0 else "#3b82f6"
        l_dot = "🔴" if data['diff'] > 0 else "🟢" if data['diff'] < 0 else "🔵"
        p_str, c_str = f"{data['price']:,.2f}", f"{data['diff']:+,.2f} ({data['pct']:.2f}%)"
        t_str = f"🕒 {data['time']}"
    html = f"""
    <div style="background-color: white; border-radius: 10px; padding: 15px; margin-bottom: 15px; border: 1px solid #e5e7eb; border-left: 6px solid {b_color};">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
            <div style="font-size: 14px; color: #3b82f6; font-weight: bold;">{l_dot} {data['icon']} {data['name']}</div>
            <div style="font-size: 11px; color: #9ca3af;">{t_str}</div>
        </div>
        <div style="font-size: 28px; font-weight: 900; color: #111827;">{p_str}</div>
        <div style="font-size: 14px; font-weight: bold; color: {b_color};">{c_str}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

st.title("📱 淑英姐 ETF 隨身戰情室")

df, g_mkt, g_pnl, g_cost, g_months, g_annual, g_reminders, g_day_change = fetch_analysis(st.session_state.my_data['etfs'])

us_data, tw_data = fetch_market_data()
st.markdown("### 🌍 關鍵市場指標")
c1, c2, c3 = st.columns(3)
with c1: render_custom_card(us_data[0]); render_custom_card(us_data[3])
with c2: render_custom_card(us_data[1]); render_custom_card(us_data[4])
with c3: render_custom_card(us_data[2]); render_custom_card(tw_data[0])

st.divider()
mc1, mc2 = st.columns(2)
with mc1: st.metric("今日漲跌幅 (估)", f"{g_day_change:+,.0f} 元", delta_color="normal")
with mc2: st.metric("累積總損益 (手動)", f"{g_pnl:,.0f} 元")

if not df.empty:
    st.dataframe(df.style.format({"今日漲跌":"{:+,.0f}","累積損益":"{:,.0f}"}).map(lambda x: f'color:{"red" if (isinstance(x, (int,float)) and x>0) or str(x).startswith("+") else "green" if (isinstance(x, (int,float)) and x<0) or str(x).startswith("-") else "black"};font-weight:bold;', subset=['累積損益', '今日漲跌']), use_container_width=True, hide_index=True)

st.divider()
st.subheader("🗓️ 預估領息戰情牆")
month_order = [f"{m}月" for m in range(1, 13)]
monthly_totals = [g_months[m]["total"] for m in month_order]
chart_df = pd.DataFrame({"月份": month_order, "金額": monthly_totals})
st.altair_chart(alt.Chart(chart_df).mark_bar(color="#3b82f6").encode(x=alt.X("月份:N", sort=month_order), y="金額:Q").properties(height=300), use_container_width=True)

# --- 🛠 資產管理 ---
with st.expander("🛠 管理我的股票 (新增/刪除/修正)"):
    st.markdown("#### 1. ➕ 新增標的")
    nc1, nc2, nc3 = st.columns([2, 1, 1])
    with nc1: ns = st.text_input("輸入代號 (例: 2330.TW)", key="new_s").upper()
    with nc2: nsh = st.number_input("股數", value=1000, step=100, key="new_h")
    with nc3: 
        if st.button("✨ 點我新增"):
            if ns:
                tk = yf.Ticker(ns)
                nn = tk.info.get('longName', tk.info.get('shortName', ns))
                st.session_state.my_data['etfs'].append({"symbol": ns, "name": nn, "shares": nsh, "cost": 0.0, "manual_pnl": 0})
                st.success(f"已加入 {nn}！請在下方填寫成本後按儲存。")
    
    st.divider()
    st.markdown("#### 2. 📋 調整持股資料")
    updated_list = []
    for i, item in enumerate(st.session_state.my_data['etfs']):
        c1, c2, c3, c4, c5 = st.columns([1.5, 1, 1, 1, 0.5])
        with c1: st.write(f"**{item['name']}**")
        with c2: s = st.number_input(f"股數", value=int(item['shares']), key=f"s_{i}", step=100)
        with c3: c = st.number_input(f"成本", value=float(item['cost']), key=f"c_{i}")
        with c4: p = st.number_input(f"損益修正", value=int(item['manual_pnl']), key=f"p_{i}")
        with c5: 
            if st.button("🗑️", key=f"del_{i}"): continue
        updated_list.append({"symbol": item['symbol'], "name": item['name'], "shares": s, "cost": c, "manual_pnl": p})
    
    if st.button("💾 儲存所有變更", type="primary"):
        st.session_state.my_data['etfs'] = updated_list
        save_to_json(st.session_state.my_data)
        st.rerun()