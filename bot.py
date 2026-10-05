import os, threading, requests, time
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "SUPER V7 - 11 IN 1 - LIVE"
def run_web(): flask_app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
threading.Thread(target=run_web, daemon=True).start()

TOKEN = os.environ.get("TOKEN") or os.environ.get("TELEGRAM_TOKEN")
BINANCE = "https://data-api.binance.vision"
CHAT_FILE = "/tmp/chats.txt"

# 70 COIN DUNG CHUNG CHO CA 11 BOT CU
COINS = ["BTC","ETH","SOL","BNB","XRP","ADA","AVAX","DOT","TRX","LINK","NEAR","POL","LTC","BCH","ETC","XLM","UNI","OP","ARB","SUI","APT","FIL","HBAR","TAO","FET","RENDER","WLD","INJ","STX","IMX","SEI","ENA","ONDO","ZEC","HYPE","AAVE","MKR","LDO","ATOM","TIA","EGLD","ALGO","VET","ICP","QNT","FTM","THETA","FLOW","KAVA","ROSE","MNT","STRK","METIS","PENDLE","ENS","CRV","COMP","SNX","DYDX","GMX","1INCH","JUP","PYTH","W","S","AR","GRT","OCEAN","AGIX"]
COINS = list(dict.fromkeys(COINS))

def load_chats():
    try:
        with open(CHAT_FILE,'r') as f: return set(int(x) for x in f.read().split() if x)
    except: return set()
def save_chats(s):
    try:
        with open(CHAT_FILE,'w') as f: f.write(' '.join(map(str,s)))
    except: pass
CHAT_IDS = load_chats()

def fmt(p):
    p=float(p)
    if p<0.001: return f"${p:.6f}"
    return f"${p:.4f}"

# --- CAC CHI BAO ---
def calc_rsi(c, p=14):
    if len(c) < p+1: return 50
    gains=[]; losses=[]
    for i in range(1,len(c)):
        d=c[i]-c[i-1]; gains.append(d if d>0 else 0); losses.append(abs(d) if d<0 else 0)
    ag=sum(gains[:p])/p; al=sum(losses[:p])/p
    for i in range(p,len(gains)):
        ag=(ag*(p-1)+gains[i])/p; al=(al*(p-1)+losses[i])/p
    if al==0: return 100
    return 100-(100/(1+ag/al))

def calc_mfi(h,l,c,v,p=14):
    if len(c)<p+1: return 50
    tp=[(hh+ll+cc)/3 for hh,ll,cc in zip(h,l,c)]
    rmf=[t*vv for t,vv in zip(tp,v)]
    pos=0; neg=0
    for i in range(1,p+1):
        if tp[-i]>tp[-i-1]: pos+=rmf[-i]
        elif tp[-i]<tp[-i-1]: neg+=rmf[-i]
    if neg==0: return 100
    return 100-(100/(1+pos/neg))

def calc_stoch(c,h,l,k=14,d=3):
    if len(c)<k: return 50,50
    ll=min(l[-k:]); hh=max(h[-k:])
    if hh==ll: return 50,50
    k_val=(c[-1]-ll)/(hh-ll)*100
    return k_val, k_val # don gian hoa, dung K thoi

# --- SCAN CHUNG ---
def get_klines(sym, interval="4h", limit=100):
    try:
        r=requests.get(f"{BINANCE}/api/v3/klines?symbol={sym}USDT&interval={interval}&limit={limit}",timeout=8).json()
        if isinstance(r, dict): return None
        return r
    except: return None

def scan_all_strategies():
    result={"RSI<30":[],"MFI_WALE":[],"MA20":[],"STOCH":[],"WICK":[],"BREAKOUT":[],"AAVE_LDO_ONDO":[]}
    for sym in COINS:
        kl=get_klines(sym,"4h",100)
        if not kl: continue
        closes=[float(x[4]) for x in kl]; highs=[float(x[2]) for x in kl]; lows=[float(x[3]) for x in kl]; vols=[float(x[5]) for x in kl]
        if len(closes)<60: continue

        rsi=calc_rsi(closes); mfi=calc_mfi(highs,lows,closes,vols)
        ema20=sum(closes[-20:])/20; ema50=sum(closes[-50:])/50
        k,_=calc_stoch(closes,highs,lows)

        # 1. RSI <30 (con top30-rsi-breakout cu)
        if rsi<30 and ema20>ema50: result["RSI<30"].append((sym,rsi,closes[-1]))
        # 2. MFI WHALE (con mfiwhalepr cu) - MFI <20 + vol dot bien
        if mfi<20 and vols[-1] > sum(vols[-20:-1])/19 * 1.8: result["MFI_WALE"].append((sym,mfi,closes[-1]))
        # 3. MA20 (bot-ma20-personal)
        if closes[-1]>ema20 and closes[-2]<sum(closes[-21:-1])/20: result["MA20"].append((sym,rsi,closes[-1]))
        # 4. STOCHASTIC (bot-stochastic-personal)
        if k<20: result["STOCH"].append((sym,k,closes[-1]))
        # 5. WICK SNIPER (wicksniper) - rut rau duoi dai
        body=abs(closes[-1]-float(kl[-1][1])); lower_wick=min(float(kl[-1][1]),closes[-1])-lows[-1]
        if lower_wick > body*2 and rsi<40: result["WICK"].append((sym,rsi,closes[-1]))
        # 6. BREAKOUT
        if closes[-1]==max(highs[-20:]): result["BREAKOUT"].append((sym,rsi,closes[-1]))
        # 7. AAVE LDO ONDO rieng
        if sym in ["AAVE","LDO","ONDO"] and rsi<35: result["AAVE_LDO_ONDO"].append((sym,rsi,closes[-1]))

    for k in result: result[k]=sorted(result[k], key=lambda x:x[1])[:5]
    return result

def auto_loop():
    while True:
        time.sleep(3600)
        res=scan_all_strategies()
        total=sum(len(v) for v in res.values())
        if total==0 or not CHAT_IDS: continue
        msg=f"⏰ AUTO SUPER V7 - {total} KEO:\n\n"
        for strat, lst in res.items():
            if lst:
                msg+=f"--- {strat} ---\n"
                for s,r,p in lst: msg+=f"{s} {r:.1f} {fmt(p)}\n"
                msg+="\n"
        for cid in list(CHAT_IDS):
            try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":cid,"text":msg},timeout=10)
            except: pass
threading.Thread(target=auto_loop, daemon=True).start()

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("SUPER V7 - 11 BOT GOP 1\n\n/scan_all - quet tat ca\n/scan_rsi - RSI<30\n/scan_mfi - MFI Whale\n/scan_ma - MA20\n/scan_stoch - Stochastic\n/scan_wick - Wick Sniper\n/scan_aave - AAVE/LDO/ONDO\n/auto_scan - bat auto 1h\n/stop_auto - tat")

async def scan_cmd(update,ctx, key):
    await update.message.reply_text(f"Dang quet {key} 70 coin...")
    res=scan_all_strategies()
    lst=res.get(key, [])
    if key=="ALL":
        msg="💎 SUPER V7 - TONG HOP:\n\n"
        for k,v in res.items():
            if v:
                msg+=f"{k}: {', '.join([f'{s}({r:.0f})' for s,r,_ in v])}\n"
        await update.message.reply_text(msg or "Khong co keo nao luc nay")
        return
    if not lst:
        await update.message.reply_text(f"0 keo {key}")
        return
    msg=f"💎 {key} ({len(lst)}):\n\n"
    for s,r,p in lst: msg+=f"{s} RSI:{r:.1f} {fmt(p)} SL:{fmt(p*0.97)} TP:{fmt(p*1.15)}\n\n"
    await update.message.reply_text(msg)

async def scan_all(update,ctx): await scan_cmd(update,ctx,"ALL")
async def scan_rsi(update,ctx): await scan_cmd(update,ctx,"RSI<30")
async def scan_mfi(update,ctx): await scan_cmd(update,ctx,"MFI_WALE")
async def scan_ma(update,ctx): await scan_cmd(update,ctx,"MA20")
async def scan_stoch(update,ctx): await scan_cmd(update,ctx,"STOCH")
async def scan_wick(update,ctx): await scan_cmd(update,ctx,"WICK")
async def scan_aave(update,ctx): await scan_cmd(update,ctx,"AAVE_LDO_ONDO")

async def auto_on(update,ctx):
    CHAT_IDS.add(update.effective_chat.id); save_chats(CHAT_IDS)
    await update.message.reply_text("Da BAT auto 1h cho SUPER V7")
async def auto_off(update,ctx):
    CHAT_IDS.discard(update.effective_chat.id); save_chats(CHAT_IDS)
    await update.message.reply_text("Da TAT auto")

if __name__=="__main__":
    app=ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start)); app.add_handler(CommandHandler("menu",start))
    app.add_handler(CommandHandler("scan_all",scan_all)); app.add_handler(CommandHandler("scan",scan_all))
    app.add_handler(CommandHandler("scan_rsi",scan_rsi)); app.add_handler(CommandHandler("scan_mfi",scan_mfi))
    app.add_handler(CommandHandler("scan_ma",scan_ma)); app.add_handler(CommandHandler("scan_stoch",scan_stoch))
    app.add_handler(CommandHandler("scan_wick",scan_wick)); app.add_handler(CommandHandler("scan_aave",scan_aave))
    app.add_handler(CommandHandler("auto_scan",auto_on)); app.add_handler(CommandHandler("stop_auto",auto_off))
    print("SUPER V7 RUNNING"); app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES, close_loop=False, stop_signals=None)import os, threading, requests, time
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "SUPER V7 - 11 IN 1 - LIVE"
def run_web(): flask_app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
threading.Thread(target=run_web, daemon=True).start()

TOKEN = os.environ.get("TOKEN") or os.environ.get("TELEGRAM_TOKEN")
BINANCE = "https://data-api.binance.vision"
CHAT_FILE = "/tmp/chats.txt"

# 70 COIN DUNG CHUNG CHO CA 11 BOT CU
COINS = ["BTC","ETH","SOL","BNB","XRP","ADA","AVAX","DOT","TRX","LINK","NEAR","POL","LTC","BCH","ETC","XLM","UNI","OP","ARB","SUI","APT","FIL","HBAR","TAO","FET","RENDER","WLD","INJ","STX","IMX","SEI","ENA","ONDO","ZEC","HYPE","AAVE","MKR","LDO","ATOM","TIA","EGLD","ALGO","VET","ICP","QNT","FTM","THETA","FLOW","KAVA","ROSE","MNT","STRK","METIS","PENDLE","ENS","CRV","COMP","SNX","DYDX","GMX","1INCH","JUP","PYTH","W","S","AR","GRT","OCEAN","AGIX"]
COINS = list(dict.fromkeys(COINS))

def load_chats():
    try:
        with open(CHAT_FILE,'r') as f: return set(int(x) for x in f.read().split() if x)
    except: return set()
def save_chats(s):
    try:
        with open(CHAT_FILE,'w') as f: f.write(' '.join(map(str,s)))
    except: pass
CHAT_IDS = load_chats()

def fmt(p):
    p=float(p)
    if p<0.001: return f"${p:.6f}"
    return f"${p:.4f}"

# --- CAC CHI BAO ---
def calc_rsi(c, p=14):
    if len(c) < p+1: return 50
    gains=[]; losses=[]
    for i in range(1,len(c)):
        d=c[i]-c[i-1]; gains.append(d if d>0 else 0); losses.append(abs(d) if d<0 else 0)
    ag=sum(gains[:p])/p; al=sum(losses[:p])/p
    for i in range(p,len(gains)):
        ag=(ag*(p-1)+gains[i])/p; al=(al*(p-1)+losses[i])/p
    if al==0: return 100
    return 100-(100/(1+ag/al))

def calc_mfi(h,l,c,v,p=14):
    if len(c)<p+1: return 50
    tp=[(hh+ll+cc)/3 for hh,ll,cc in zip(h,l,c)]
    rmf=[t*vv for t,vv in zip(tp,v)]
    pos=0; neg=0
    for i in range(1,p+1):
        if tp[-i]>tp[-i-1]: pos+=rmf[-i]
        elif tp[-i]<tp[-i-1]: neg+=rmf[-i]
    if neg==0: return 100
    return 100-(100/(1+pos/neg))

def calc_stoch(c,h,l,k=14,d=3):
    if len(c)<k: return 50,50
    ll=min(l[-k:]); hh=max(h[-k:])
    if hh==ll: return 50,50
    k_val=(c[-1]-ll)/(hh-ll)*100
    return k_val, k_val # don gian hoa, dung K thoi

# --- SCAN CHUNG ---
def get_klines(sym, interval="4h", limit=100):
    try:
        r=requests.get(f"{BINANCE}/api/v3/klines?symbol={sym}USDT&interval={interval}&limit={limit}",timeout=8).json()
        if isinstance(r, dict): return None
        return r
    except: return None

def scan_all_strategies():
    result={"RSI<30":[],"MFI_WALE":[],"MA20":[],"STOCH":[],"WICK":[],"BREAKOUT":[],"AAVE_LDO_ONDO":[]}
    for sym in COINS:
        kl=get_klines(sym,"4h",100)
        if not kl: continue
        closes=[float(x[4]) for x in kl]; highs=[float(x[2]) for x in kl]; lows=[float(x[3]) for x in kl]; vols=[float(x[5]) for x in kl]
        if len(closes)<60: continue

        rsi=calc_rsi(closes); mfi=calc_mfi(highs,lows,closes,vols)
        ema20=sum(closes[-20:])/20; ema50=sum(closes[-50:])/50
        k,_=calc_stoch(closes,highs,lows)

        # 1. RSI <30 (con top30-rsi-breakout cu)
        if rsi<30 and ema20>ema50: result["RSI<30"].append((sym,rsi,closes[-1]))
        # 2. MFI WHALE (con mfiwhalepr cu) - MFI <20 + vol dot bien
        if mfi<20 and vols[-1] > sum(vols[-20:-1])/19 * 1.8: result["MFI_WALE"].append((sym,mfi,closes[-1]))
        # 3. MA20 (bot-ma20-personal)
        if closes[-1]>ema20 and closes[-2]<sum(closes[-21:-1])/20: result["MA20"].append((sym,rsi,closes[-1]))
        # 4. STOCHASTIC (bot-stochastic-personal)
        if k<20: result["STOCH"].append((sym,k,closes[-1]))
        # 5. WICK SNIPER (wicksniper) - rut rau duoi dai
        body=abs(closes[-1]-float(kl[-1][1])); lower_wick=min(float(kl[-1][1]),closes[-1])-lows[-1]
        if lower_wick > body*2 and rsi<40: result["WICK"].append((sym,rsi,closes[-1]))
        # 6. BREAKOUT
        if closes[-1]==max(highs[-20:]): result["BREAKOUT"].append((sym,rsi,closes[-1]))
        # 7. AAVE LDO ONDO rieng
        if sym in ["AAVE","LDO","ONDO"] and rsi<35: result["AAVE_LDO_ONDO"].append((sym,rsi,closes[-1]))

    for k in result: result[k]=sorted(result[k], key=lambda x:x[1])[:5]
    return result

def auto_loop():
    while True:
        time.sleep(3600)
        res=scan_all_strategies()
        total=sum(len(v) for v in res.values())
        if total==0 or not CHAT_IDS: continue
        msg=f"⏰ AUTO SUPER V7 - {total} KEO:\n\n"
        for strat, lst in res.items():
            if lst:
                msg+=f"--- {strat} ---\n"
                for s,r,p in lst: msg+=f"{s} {r:.1f} {fmt(p)}\n"
                msg+="\n"
        for cid in list(CHAT_IDS):
            try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":cid,"text":msg},timeout=10)
            except: pass
threading.Thread(target=auto_loop, daemon=True).start()

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("SUPER V7 - 11 BOT GOP 1\n\n/scan_all - quet tat ca\n/scan_rsi - RSI<30\n/scan_mfi - MFI Whale\n/scan_ma - MA20\n/scan_stoch - Stochastic\n/scan_wick - Wick Sniper\n/scan_aave - AAVE/LDO/ONDO\n/auto_scan - bat auto 1h\n/stop_auto - tat")

async def scan_cmd(update,ctx, key):
    await update.message.reply_text(f"Dang quet {key} 70 coin...")
    res=scan_all_strategies()
    lst=res.get(key, [])
    if key=="ALL":
        msg="💎 SUPER V7 - TONG HOP:\n\n"
        for k,v in res.items():
            if v:
                msg+=f"{k}: {', '.join([f'{s}({r:.0f})' for s,r,_ in v])}\n"
        await update.message.reply_text(msg or "Khong co keo nao luc nay")
        return
    if not lst:
        await update.message.reply_text(f"0 keo {key}")
        return
    msg=f"💎 {key} ({len(lst)}):\n\n"
    for s,r,p in lst: msg+=f"{s} RSI:{r:.1f} {fmt(p)} SL:{fmt(p*0.97)} TP:{fmt(p*1.15)}\n\n"
    await update.message.reply_text(msg)

async def scan_all(update,ctx): await scan_cmd(update,ctx,"ALL")
async def scan_rsi(update,ctx): await scan_cmd(update,ctx,"RSI<30")
async def scan_mfi(update,ctx): await scan_cmd(update,ctx,"MFI_WALE")
async def scan_ma(update,ctx): await scan_cmd(update,ctx,"MA20")
async def scan_stoch(update,ctx): await scan_cmd(update,ctx,"STOCH")
async def scan_wick(update,ctx): await scan_cmd(update,ctx,"WICK")
async def scan_aave(update,ctx): await scan_cmd(update,ctx,"AAVE_LDO_ONDO")

async def auto_on(update,ctx):
    CHAT_IDS.add(update.effective_chat.id); save_chats(CHAT_IDS)
    await update.message.reply_text("Da BAT auto 1h cho SUPER V7")
async def auto_off(update,ctx):
    CHAT_IDS.discard(update.effective_chat.id); save_chats(CHAT_IDS)
    await update.message.reply_text("Da TAT auto")

if __name__=="__main__":
    app=ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start)); app.add_handler(CommandHandler("menu",start))
    app.add_handler(CommandHandler("scan_all",scan_all)); app.add_handler(CommandHandler("scan",scan_all))
    app.add_handler(CommandHandler("scan_rsi",scan_rsi)); app.add_handler(CommandHandler("scan_mfi",scan_mfi))
    app.add_handler(CommandHandler("scan_ma",scan_ma)); app.add_handler(CommandHandler("scan_stoch",scan_stoch))
    app.add_handler(CommandHandler("scan_wick",scan_wick)); app.add_handler(CommandHandler("scan_aave",scan_aave))
    app.add_handler(CommandHandler("auto_scan",auto_on)); app.add_handler(CommandHandler("stop_auto",auto_off))
    print("SUPER V7 RUNNING"); app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES, close_loop=False, stop_signals=None)
