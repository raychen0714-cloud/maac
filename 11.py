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
    # 預設載入 2026/05 最新持股數據
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
            if len(hist) >= 2:
                curr_p, prev_p = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
            else:
                curr_p = tk.fast_info.get('lastPrice', item['cost'])
                prev_p = tk.fast_info.get('regularMarketPreviousClose', curr_p)
            
            day_chg = (curr_p - prev_p) * item['shares']
            cfg = div_cfg.get(item['symbol'], {"m": [], "d": "無", "v": 0.0})
            
            status_light = "🔴" if day_chg > 0 else "🟢" if day_chg < 0 else "🔵"
            
            recovery_str = "—"
            if cfg['v'] > 0:
                if curr_p >= item['cost']: recovery_str = f"✅ 已填息"
                else:
                    gap = item['cost'] - curr_p
                    recovery_str = f"⏳ 填息 {max(0, (1-(gap/cfg['v']))*100):.0f}%" if gap < cfg['v'] else "貼息中"
            
            if cfg["d"] != "無":
                try:
                    if 0 <= (datetime.strptime(cfg["d"], "%Y-%m-%d") - today).days <= 25:
                        reminders.append({"code": item['symbol'].split('.')[0], "date": datetime.strptime(cfg["d"], "%Y-%m-%d").strftime("%m/%d")})
                except: pass
            
            cash = cfg['v'] * item['shares']
            for m in cfg["m"]:
                m_stats[f"{m}月"]["total"] += cash
                m_stats[f"{m}月"]["detail"].append({"股票": item['symbol'].split('.')[0], "金額": int(cash)})
                annual_total += cash
                
            t_mkt += (item['shares'] * curr_p); t_pnl += item['manual_pnl']; t_cost += (item['shares'] * item['cost']); t_day_change += day_chg
            
            res.append({
                "狀態": status_light,
                "代號名稱": f"{item['symbol'].split('.')[0]} {item['name']}", 
                "買入均價": f"台幣 {item['cost']:.2f} 元",
                "現價": round(curr_p, 2), 
                "今日漲跌": day_chg, 
                "累積損益": item['manual_pnl'], 
                "配息金額": f"台幣 {cfg['v']:.2f} 元",
                "填息進度": recovery_str,
                "除息預計": cfg["d"]
            })
        except: continue
    return pd.DataFrame(res).sort_values(by="除息預計", ascending=True), t_mkt, t_pnl, t_cost, m_stats, annual_total, reminders, t_day_change

# --- 4. 介面渲染器 ---
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

# --- 5. 主介面 ---
st.title("📱 淑英姐 ETF 隨身戰情室")

df, g_mkt, g_pnl, g_cost, g_months, g_annual, g_reminders, g_day_change = fetch_analysis(st.session_state.my_data['etfs'])

if g_reminders:
    st.markdown("""<style>@keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } } .blink-box { animation: blink 1.2s linear infinite; background-color: #fee2e2; padding: 15px; border-radius: 10px; margin-bottom: 20px; border: 2px solid #ef4444; }</style>""", unsafe_allow_html=True)
    for r in g_reminders:
        st.markdown(f'<div class="blink-box"><span style="font-size: 20px;">💰 🚨</span> <b style="color: #b91c1c; font-size: 18px;"> 除息預告：</b> <span style="color: #b91c1c; font-size: 18px;">{r["code"]} 將於 {r["date"]} 除息！</span></div>', unsafe_allow_html=True)

us_data, tw_data = fetch_market_data()
st.markdown("### 🌍 關鍵美股指標")
c1, c2, c3 = st.columns(3)
with c1: render_custom_card(us_data[0]); render_custom_card(us_data[3])
with c2: render_custom_card(us_data[1]); render_custom_card(us_data[4])
with c3: render_custom_card(us_data[2])

st.markdown("### 🇹🇼 關鍵台股點數")
tc1, tc2 = st.columns(2)
with tc1: render_custom_card(tw_data[0]); render_custom_card(tw_data[2])
with tc2: render_custom_card(tw_data[1]); render_custom_card(tw_data[3])

st.divider()
p_col = "#ef4444" if g_pnl >= 0 else "#22c55e"
d_col = "#ef4444" if g_day_change >= 0 else "#22c55e"
mc1, mc2 = st.columns(2)
with mc1: st.markdown(f"<div style='text-align:center; background-color:#f8fafc; padding:10px; border-radius:10px;'>今日損益<h2 style='color:{d_col}; margin:0;'>台幣 {g_day_change:+,.0f} 元</h2></div>", unsafe_allow_html=True)
with mc2: st.markdown(f"<div style='text-align:center; background-color:#f8fafc; padding:10px; border-radius:10px;'>累積總損益<h2 style='color:{p_col}; margin:0;'>台幣 {g_pnl:,.0f} 元</h2></div>", unsafe_allow_html=True)

if not df.empty:
    st.dataframe(df.style.format({"現價":"{:.2f}","今日漲跌":"{:+,.0f}","累積損益":"{:,.0f}"}).map(lambda x: f'color:{"red" if (isinstance(x, (int,float)) and x>0) or str(x).startswith("+") else "green" if (isinstance(x, (int,float)) and x<0) or str(x).startswith("-") else "black"};font-weight:bold;', subset=['累積損益', '今日漲跌']), use_container_width=True, hide_index=True)

st.divider()
st.subheader("🗓️ 領息視覺化戰情牆")
month_order = [f"{m}月" for m in range(1, 13)]
monthly_totals = [g_months[m]["total"] for m in month_order]
chart_df = pd.DataFrame({"月份": month_order, "領息金額": monthly_totals})

chart = alt.Chart(chart_df).mark_bar(color="#3b82f6", cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
    x=alt.X("月份:N", sort=month_order, axis=alt.Axis(labelAngle=0)),
    y=alt.Y("領息金額:Q", title="金額 (台幣)"),
    tooltip=[] 
).properties(height=350)
st.altair_chart(chart, use_container_width=True)

st.markdown("#### 🔍 每月領息明細 (台幣)")
detail_rows = []
for m in month_order:
    if g_months[m]["detail"]:
        for d in g_months[m]["detail"]:
            detail_rows.append({"月份": m, "股票來源": d["股票"], "預估領息金額": f"台幣 {d['金額']:,} 元"})

if detail_rows: st.table(pd.DataFrame(detail_rows))
else: st.write("目前尚無領息數據。")

st.metric("預估年領總息", f"台幣 {g_annual:,.0f} 元")

# --- 🛠 改良版：新增股票移至頂端 ---
with st.expander("🛠 資產管理 (可新增/刪除股票)"):
    # 1. 新增股票功能移至頂端
    st.write("➕ **新增股票標的**")
    nc1, nc2, nc3 = st.columns([2, 1, 1])
    with nc1: new_symbol = st.text_input("股票代號 (例: 2330.TW)", key="new_sym", placeholder="輸入代號.TW").upper()
    with nc2: new_shares = st.number_input("股數", value=1000, step=100, key="new_sh")
    with nc3: 
        add_btn = st.button("✨ 點我新增")
    
    st.divider()
    
    # 持股列表與刪除功能
    st.write("📋 **當前持股編輯**")
    updated_list = []
    
    # 處理新增邏輯
    if add_btn and new_symbol:
        try:
            tk = yf.Ticker(new_symbol)
            new_name = tk.info.get('longName', tk.info.get('shortName', new_symbol))
            # 暫時加入當前 session 列表中，待存檔按鈕點擊後寫入 JSON
            st.session_state.my_data['etfs'].append({"symbol": new_symbol, "name": new_name, "shares": new_shares, "cost": 0.0, "manual_pnl": 0})
            st.success(f"已新增 {new_name}！請調整下方成本後點擊儲存。")
        except: st.error("代號錯誤，請檢查是否包含 .TW")

    for i, item in enumerate(st.session_state.my_data.get('etfs', [])):
        c1, c2, c3, c4, c5 = st.columns([1.5, 1, 1, 1, 0.5])
        with c1: st.write(f"**{item['name']}**")
        with c2: s = st.number_input(f"股數", value=int(item['shares']), key=f"s_{i}", step=100)
        with c3: c = st.number_input(f"成本", value=float(item['cost']), key=f"c_{i}")
        with c4: p = st.number_input(f"損益修正", value=int(item['manual_pnl']), key=f"p_{i}")
        with c5: 
            if st.button("🗑️", key=f"del_{i}"): continue
        updated_list.append({"symbol": item['symbol'], "name": item['name'], "shares": s, "cost": c, "manual_pnl": p})
    
    st.divider()
    if st.button("💾 儲存所有變更並更新畫面", type="primary"):
        st.session_state.my_data['etfs'] = updated_list
        save_to_json(st.session_state.my_data)
        st.cache_data.clear()
        st.rerun()