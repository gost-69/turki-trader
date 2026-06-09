import requests
import time
from datetime import datetime

TOKEN = "8943196164:AAE4n05GmR6lUz2EK3hunSqvtqJqeKwkSN8"
CHAT_ID = "8098064670"

SYMBOLS = {
    "EURUSD":  "EURUSDT",
    "GBPUSD":  "GBPUSDT",
    "USDJPY":  "USDUSDT",
    "BTCUSDT": "BTCUSDT",
    "CADJPY":  "CADJPY"
}

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=data, timeout=10)
    except:
        pass

def get_candles(binance_symbol, limit=100):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": binance_symbol, "interval": "15m", "limit": limit}
    try:
        response = requests.get(url, params=params, timeout=10)
        candles = response.json()
        if isinstance(candles, list):
            return [{"open": float(c[1]), "high": float(c[2]),
                     "low": float(c[3]), "close": float(c[4])} for c in candles]
    except:
        pass
    return []

def find_highs_lows(candles):
    highs, lows = [], []
    for i in range(2, len(candles)-1):
        if candles[i-1]["high"] > candles[i-2]["high"] and candles[i-1]["high"] > candles[i]["high"]:
            highs.append(candles[i-1]["high"])
        if candles[i-1]["low"] < candles[i-2]["low"] and candles[i-1]["low"] < candles[i]["low"]:
            lows.append(candles[i-1]["low"])
    return highs, lows

def analyze(candles, symbol):
    highs, lows = find_highs_lows(candles)
    if len(highs) < 2 or len(lows) < 2:
        return None
    last = candles[-1]
    prev_high = highs[-1]
    prev_low = lows[-1]
    r = 5 if "JPY" in symbol else 5

    if last["low"] < prev_low and last["close"] > prev_high:
        entry = last["close"]
        sl = prev_low - (prev_high - prev_low) * 0.1
        rr = entry - sl
        return {"signal":"BUY","entry":round(entry,r),"sl":round(sl,r),
                "tp1":round(entry+rr*1.5,r),"tp2":round(entry+rr*2.5,r),
                "tp3":round(entry+rr*3.5,r),"liq":round(prev_low,r)}

    if last["high"] > prev_high and last["close"] < prev_low:
        entry = last["close"]
        sl = prev_high + (prev_high - prev_low) * 0.1
        rr = sl - entry
        return {"signal":"SELL","entry":round(entry,r),"sl":round(sl,r),
                "tp1":round(entry-rr*1.5,r),"tp2":round(entry-rr*2.5,r),
                "tp3":round(entry-rr*3.5,r),"liq":round(prev_high,r)}
    return None

def format_msg(s, symbol):
    e = "🟢" if s["signal"]=="BUY" else "🔴"
    d = "شراء ⬆️" if s["signal"]=="BUY" else "بيع ⬇️"
    return f"""{e} <b>إشارة {d}</b> {e}
━━━━━━━━━━━━━━━
📊 <b>الزوج:</b> {symbol}
⏰ <b>الوقت:</b> {datetime.now().strftime('%H:%M')}
━━━━━━━━━━━━━━━
💧 <b>Liquidity Sweep:</b> {s['liq']}
🎯 <b>الدخول:</b> {s['entry']}
�� <b>Stop Loss:</b> {s['sl']}
━━━━━━━━━━━━━━━
✅ <b>TP1 (50%):</b> {s['tp1']}
✅ <b>TP2 (25%):</b> {s['tp2']}
✅ <b>TP3 (25%):</b> {s['tp3']}
━━━━━━━━━━━━━━━
⚠️ ريسك 1% فقط"""

def main():
    send_telegram("🤖 <b>TurkiTrader يراقب 5 أزواج!</b>\n📊 EURUSD | GBPUSD | USDJPY | BTCUSDT | CADJPY\n👀 كل دقيقة...")
    print("✅ البوت شغّال — يراقب 5 أزواج")
    last_signals = {s: None for s in SYMBOLS}

    while True:
        now = datetime.now()
        for display_name, binance_name in SYMBOLS.items():
            try:
                candles = get_candles(binance_name)
                if not candles:
                    print(f"⚠️ [{now.strftime('%H:%M')}] {display_name}: ما في بيانات")
                    continue
                signal = analyze(candles, display_name)
                if signal:
                    last = last_signals[display_name]
                    if last is None or (now - last).seconds > 3600:
                        send_telegram(format_msg(signal, display_name))
                        last_signals[display_name] = now
                        print(f"✅ {display_name}: {signal['signal']} - {now.strftime('%H:%M')}")
                else:
                    print(f"👀 [{now.strftime('%H:%M')}] {display_name}: لا إشارة")
            except Exception as ex:
                print(f"❌ {display_name}: {ex}")
        time.sleep(60)

if __name__ == "__main__":
    main()
