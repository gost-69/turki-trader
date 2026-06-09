import requests
import time
from datetime import datetime

TOKEN = "8943196164:AAE4n05GmR6lUz2EK3hunSqvtqJqeKwkSN8"
CHAT_ID = "8098064670"
SYMBOL = "EURUSD"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    requests.post(url, data=data)

def get_candles(limit=100):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": "EURUSDT", "interval": "15m", "limit": limit}
    response = requests.get(url, params=params)
    candles = response.json()
    result = []
    for c in candles:
        result.append({
            "open": float(c[1]),
            "high": float(c[2]),
            "low": float(c[3]),
            "close": float(c[4])
        })
    return result

def find_highs_lows(candles):
    highs = []
    lows = []
    for i in range(2, len(candles)-1):
        if candles[i-1]["high"] > candles[i-2]["high"] and candles[i-1]["high"] > candles[i]["high"]:
            highs.append(candles[i-1]["high"])
        if candles[i-1]["low"] < candles[i-2]["low"] and candles[i-1]["low"] < candles[i]["low"]:
            lows.append(candles[i-1]["low"])
    return highs, lows

def analyze(candles):
    highs, lows = find_highs_lows(candles)
    if len(highs) < 2 or len(lows) < 2:
        return None
    last = candles[-1]
    prev_high = highs[-1]
    prev_low = lows[-1]
    if last["low"] < prev_low and last["close"] > prev_high:
        entry = last["close"]
        sl = prev_low - (prev_high - prev_low) * 0.1
        rr = entry - sl
        return {"signal":"BUY","entry":round(entry,5),"sl":round(sl,5),
                "tp1":round(entry+rr*1.5,5),"tp2":round(entry+rr*2.5,5),
                "tp3":round(entry+rr*3.5,5),"liq":round(prev_low,5)}
    if last["high"] > prev_high and last["close"] < prev_low:
        entry = last["close"]
        sl = prev_high + (prev_high - prev_low) * 0.1
        rr = sl - entry
        return {"signal":"SELL","entry":round(entry,5),"sl":round(sl,5),
                "tp1":round(entry-rr*1.5,5),"tp2":round(entry-rr*2.5,5),
                "tp3":round(entry-rr*3.5,5),"liq":round(prev_high,5)}
    return None

def format_msg(s):
    e = "🟢" if s["signal"]=="BUY" else "🔴"
    d = "شراء ⬆️" if s["signal"]=="BUY" else "بيع ⬇️"
    return f"""{e} <b>إشارة {d}</b> {e}
━━━━━━━━━━━━━━━
📊 <b>الزوج:</b> {SYMBOL}
⏰ <b>الوقت:</b> {datetime.now().strftime('%H:%M')}
━━━━━━━━━━━━━━━
💧 <b>Liquidity Sweep:</b> {s['liq']}
🎯 <b>الدخول:</b> {s['entry']}
🛑 <b>Stop Loss:</b> {s['sl']}
━━━━━━━━━━━━━━━
✅ <b>TP1 (50%):</b> {s['tp1']}
✅ <b>TP2 (25%):</b> {s['tp2']}
✅ <b>TP3 (25%):</b> {s['tp3']}
━━━━━━━━━━━━━━━
⚠️ ريسك 1% فقط"""

def main():
    send_telegram("🤖 <b>TurkiTrader شغّال!</b>\nيراقب السوق الآن 👀")
    print("✅ البوت شغّال")
    last_signal = None
    while True:
        try:
            candles = get_candles()
            signal = analyze(candles)
            now = datetime.now()
            if signal:
                if last_signal is None or (now - last_signal).seconds > 3600:
                    send_telegram(format_msg(signal))
                    last_signal = now
                    print(f"✅ إشارة: {signal['signal']} - {now.strftime('%H:%M')}")
            else:
                print(f"👀 [{now.strftime('%H:%M')}] يراقب... لا إشارة")
            time.sleep(60)
        except Exception as e:
            print(f"❌ خطأ: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
