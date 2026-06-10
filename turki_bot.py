import requests
import time
from datetime import datetime

TOKEN = "8943196164:AAE4n05GmR6lUz2EK3hunSqvtqJqeKwkSN8"
CHAT_ID = "8098064670"
TD_API_KEY = "c60218ea1d4248bf85d96e571a12491e"

SYMBOLS = ["EUR/USD", "GBP/USD", "USD/JPY", "BTC/USD", "CAD/JPY"]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=data, timeout=10)
    except:
        pass

def get_candles(symbol, limit=100):
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": "15min",
        "outputsize": limit,
        "apikey": TD_API_KEY
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        if "values" in data:
            candles = []
            # Twelve Data يرجع الأحدث أولاً، نعكسها
            for c in reversed(data["values"]):
                candles.append({
                    "open": float(c["open"]),
                    "high": float(c["high"]),
                    "low": float(c["low"]),
                    "close": float(c["close"])
                })
            return candles
        else:
            print(f"⚠️ {symbol}: {data.get('message', 'لا بيانات')}")
    except Exception as e:
        print(f"❌ {symbol}: {e}")
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
    r = 3 if "JPY" in symbol else (1 if "BTC" in symbol else 5)

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
🛑 <b>Stop Loss:</b> {s['sl']}
━━━━━━━━━━━━━━━
✅ <b>TP1 (50%):</b> {s['tp1']}
✅ <b>TP2 (25%):</b> {s['tp2']}
✅ <b>TP3 (25%):</b> {s['tp3']}
━━━━━━━━━━━━━━━
⚠️ ريسك 1% فقط"""

def main():
    send_telegram("🤖 <b>TurkiTrader - بيانات فوركس حقيقية!</b>\n📊 EUR/USD | GBP/USD | USD/JPY | BTC/USD | CAD/JPY\n👀 كل دقيقة...")
    print("✅ البوت شغّال — بيانات فوركس حقيقية")
    last_signals = {s: None for s in SYMBOLS}

    while True:
        now = datetime.now()
        for symbol in SYMBOLS:
            try:
                candles = get_candles(symbol)
                if not candles:
                    continue
                signal = analyze(candles, symbol)
                if signal:
                    last = last_signals[symbol]
                    if last is None or (now - last).seconds > 3600:
                        send_telegram(format_msg(signal, symbol))
                        last_signals[symbol] = now
                        print(f"✅ {symbol}: {signal['signal']} - {now.strftime('%H:%M')}")
                else:
                    print(f"👀 [{now.strftime('%H:%M')}] {symbol}: لا إشارة")
                time.sleep(8)  # احترام حد الـ API المجاني
            except Exception as ex:
                print(f"❌ {symbol}: {ex}")
        time.sleep(60)

if __name__ == "__main__":
    main()
