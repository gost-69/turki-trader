import requests
import time
from datetime import datetime
import pytz

TOKEN = "8943196164:AAE4n05GmR6lUz2EK3hunSqvtqJqeKwkSN8"
CHAT_ID = "8098064670"
TD_API_KEY = "c60218ea1d4248bf85d96e571a12491e"

SYMBOLS = ["EUR/USD", "GBP/USD", "USD/JPY", "BTC/USD", "CAD/JPY"]

# ========================================================
#  مفتاح الاستراتيجية الجديدة (One Candle Rule)
#  خلّه True عشان تشتغل جنب القديمة | False عشان تتوقف
# ========================================================
ENABLE_OCR = True
OCR_WEEKLY_LIMIT = 5   # حد إشارات الاستراتيجية الجديدة بالأسبوع (منفصل عن القديمة)

# ======= فلتر الأيام والأوقات (من كتاب Alex G) =======
def is_good_time():
    est = pytz.timezone("America/New_York")
    now = datetime.now(est)
    day = now.weekday()   # 0=Monday ... 6=Sunday
    hour = now.hour

    # تجنب الجمعة(4) والسبت(5) والأحد(6)
    if day in [4, 5, 6]:
        return False

    # فقط جلسة لندن/نيويورك: 11 مساءً - 11 صباحاً EST
    if not (hour >= 23 or hour < 11):
        return False

    return True

# ======= حد الإشارات الأسبوعية (الاستراتيجية القديمة) =======
weekly = {"count": 0, "week": None}

def can_send():
    est = pytz.timezone("America/New_York")
    week = datetime.now(est).isocalendar()[1]
    if weekly["week"] != week:
        weekly["count"] = 0
        weekly["week"] = week
    return weekly["count"] < 3

# ======= حد إشارات الاستراتيجية الجديدة (منفصل) =======
weekly_ocr = {"count": 0, "week": None}

def can_send_ocr():
    est = pytz.timezone("America/New_York")
    week = datetime.now(est).isocalendar()[1]
    if weekly_ocr["week"] != week:
        weekly_ocr["count"] = 0
        weekly_ocr["week"] = week
    return weekly_ocr["count"] < OCR_WEEKLY_LIMIT

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=data, timeout=10)
    except:
        pass

def get_candles(symbol, limit=100):
    url = "https://api.twelvedata.com/time_series"
    params = {"symbol": symbol, "interval": "15min", "outputsize": limit, "apikey": TD_API_KEY}
    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        if "values" in data:
            return [{"open": float(c["open"]), "high": float(c["high"]),
                     "low": float(c["low"]), "close": float(c["close"])}
                    for c in reversed(data["values"])]
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

# ======= تأكيد الشموع =======
def detect_pattern(candles):
    last = candles[-1]
    prev = candles[-2]
    body = abs(last["close"] - last["open"])
    wick_up = last["high"] - max(last["close"], last["open"])
    wick_down = min(last["close"], last["open"]) - last["low"]

    if last["close"] > last["open"] and prev["close"] < prev["open"]:
        if last["close"] > prev["open"] and last["open"] < prev["close"]:
            return "BUY", "Bullish Engulfing 🕯️"
    if last["close"] < last["open"] and prev["close"] > prev["open"]:
        if last["open"] > prev["close"] and last["close"] < prev["open"]:
            return "SELL", "Bearish Engulfing 🕯️"
    if body > 0 and wick_down > body * 2 and wick_up < body * 0.5:
        return "BUY", "Hammer 🔨"
    if body > 0 and wick_up > body * 2 and wick_down < body * 0.5:
        return "SELL", "Shooting Star ⭐"
    return None, None

def analyze(candles, symbol):
    highs, lows = find_highs_lows(candles)
    if len(highs) < 2 or len(lows) < 2:
        return None
    last = candles[-1]
    prev_high = highs[-1]
    prev_low = lows[-1]
    r = 3 if "JPY" in symbol else (1 if "BTC" in symbol else 5)

    pattern_dir, pattern_name = detect_pattern(candles)

    if last["low"] < prev_low and last["close"] > prev_high:
        # نتأكد إن الشمعة تؤكد الاتجاه
        if pattern_dir != "BUY":
            return None
        entry = last["close"]
        sl = prev_low - (prev_high - prev_low) * 0.1
        rr = entry - sl
        return {"signal":"BUY","entry":round(entry,r),"sl":round(sl,r),
                "tp1":round(entry+rr*1.5,r),"tp2":round(entry+rr*2.5,r),
                "tp3":round(entry+rr*3.5,r),"liq":round(prev_low,r),
                "pattern": pattern_name}

    if last["high"] > prev_high and last["close"] < prev_low:
        if pattern_dir != "SELL":
            return None
        entry = last["close"]
        sl = prev_high + (prev_high - prev_low) * 0.1
        rr = sl - entry
        return {"signal":"SELL","entry":round(entry,r),"sl":round(sl,r),
                "tp1":round(entry-rr*1.5,r),"tp2":round(entry-rr*2.5,r),
                "tp3":round(entry-rr*3.5,r),"liq":round(prev_high,r),
                "pattern": pattern_name}
    return None

# ========================================================
#  الاستراتيجية الجديدة: One Candle Rule (من كتاب Tony)
#  المنطق: حدد الاتجاه → أول شمعة عكسه (مرجع) →
#  السعر يكسر فوق/تحت المرجع → يرجع يختبره (retest) →
#  شمعة تأكيد → دخول. الوقف عند الهيكل، الهدف 2R.
# ========================================================
def get_trend(candles, lookback=10):
    seg = candles[-(lookback+1):-1]
    if len(seg) < 4:
        return None
    highs = [c["high"] for c in seg]
    lows = [c["low"] for c in seg]
    mid = len(seg) // 2
    up = (max(highs[mid:]) > max(highs[:mid])) and (min(lows[mid:]) > min(lows[:mid]))
    down = (max(highs[mid:]) < max(highs[:mid])) and (min(lows[mid:]) < min(lows[:mid]))
    if up:
        return "UP"
    if down:
        return "DOWN"
    return None

def analyze_one_candle_rule(candles, symbol):
    if len(candles) < 15:
        return None
    r = 3 if "JPY" in symbol else (1 if "BTC" in symbol else 5)
    trend = get_trend(candles)
    if trend is None:
        return None
    last = candles[-1]
    pattern_dir, pattern_name = detect_pattern(candles)
    window = candles[-12:-1]
    base_idx = len(candles) - 12

    if trend == "UP":
        # أول شمعة حمراء (عكس الاتجاه الصاعد) = المرجع
        ref = None
        ref_idx = None
        for k, c in enumerate(window):
            if c["close"] < c["open"]:
                ref = c
                ref_idx = base_idx + k
                break
        if ref is None:
            return None
        # لازم السعر يكسر فوق قمة المرجع
        broke = any(candles[j]["close"] > ref["high"] for j in range(ref_idx + 1, len(candles)))
        if not broke:
            return None
        # لازم الشمعة الأخيرة ترجع تختبر المستوى (retest)
        retest = last["low"] <= ref["high"] <= last["high"]
        if not retest:
            return None
        # لازم شمعة تأكيد شراء
        if pattern_dir != "BUY":
            return None
        entry = last["close"]
        level = ref["high"]
        sl = min(last["low"], ref["low"])
        risk = entry - sl
        if risk <= 0:
            return None
        return {"signal":"BUY","entry":round(entry,r),"sl":round(sl,r),
                "tp":round(entry+risk*2,r),"level":round(level,r),
                "pattern": pattern_name}

    if trend == "DOWN":
        # أول شمعة خضراء (عكس الاتجاه الهابط) = المرجع
        ref = None
        ref_idx = None
        for k, c in enumerate(window):
            if c["close"] > c["open"]:
                ref = c
                ref_idx = base_idx + k
                break
        if ref is None:
            return None
        broke = any(candles[j]["close"] < ref["low"] for j in range(ref_idx + 1, len(candles)))
        if not broke:
            return None
        retest = last["low"] <= ref["low"] <= last["high"]
        if not retest:
            return None
        if pattern_dir != "SELL":
            return None
        entry = last["close"]
        level = ref["low"]
        sl = max(last["high"], ref["high"])
        risk = sl - entry
        if risk <= 0:
            return None
        return {"signal":"SELL","entry":round(entry,r),"sl":round(sl,r),
                "tp":round(entry-risk*2,r),"level":round(level,r),
                "pattern": pattern_name}
    return None

def format_msg(s, symbol):
    e = "🟢" if s["signal"]=="BUY" else "🔴"
    d = "شراء ⬆️" if s["signal"]=="BUY" else "بيع ⬇️"
    left = 3 - weekly["count"] - 1
    return f"""{e} <b>إشارة عالية الجودة {d}</b> {e}
━━━━━━━━━━━━━━━
📊 <b>الزوج:</b> {symbol}
⏰ <b>الوقت:</b> {datetime.now().strftime('%H:%M')}
🕯️ <b>تأكيد:</b> {s['pattern']}
━━━━━━━━━━━━━━━
💧 <b>Liquidity Sweep:</b> {s['liq']}
🎯 <b>الدخول:</b> {s['entry']}
🛑 <b>Stop Loss:</b> {s['sl']}
━━━━━━━━━━━━━━━
✅ <b>TP1 (50%):</b> {s['tp1']}
✅ <b>TP2 (25%):</b> {s['tp2']}
✅ <b>TP3 (25%):</b> {s['tp3']}
━━━━━━━━━━━━━━━
📅 <b>إشارات باقية هذا الأسبوع:</b> {left}
⚠️ ريسك 1% فقط"""

def format_msg_ocr(s, symbol):
    e = "🟢" if s["signal"]=="BUY" else "🔴"
    d = "شراء ⬆️" if s["signal"]=="BUY" else "بيع ⬇️"
    left = OCR_WEEKLY_LIMIT - weekly_ocr["count"] - 1
    return f"""🆕 <b>One Candle Rule</b> 🆕
{e} <b>إشارة تجريبية {d}</b> {e}
━━━━━━━━━━━━━━━
📊 <b>الزوج:</b> {symbol}
⏰ <b>الوقت:</b> {datetime.now().strftime('%H:%M')}
🕯️ <b>تأكيد:</b> {s['pattern']}
━━━━━━━━━━━━━━━
📍 <b>مستوى الكسر/الرجعة:</b> {s['level']}
🎯 <b>الدخول:</b> {s['entry']}
🛑 <b>Stop Loss:</b> {s['sl']}
✅ <b>الهدف (2R):</b> {s['tp']}
━━━━━━━━━━━━━━━
🧪 <b>استراتيجية قيد الاختبار</b> — للمقارنة فقط
📅 <b>باقي هذا الأسبوع:</b> {left}
⚠️ ريسك 1% فقط"""

def main():
    startup = "🤖 <b>TurkiTrader Pro شغّال!</b>\n✅ فلاتر عالية الجودة مفعّلة\n📊 5 أزواج فوركس حقيقية\n📅 الاثنين-الخميس | جلسة لندن/نيويورك\n🕯️ تأكيد بالشموع | أقصى 3 إشارات أسبوعياً"
    if ENABLE_OCR:
        startup += f"\n🆕 استراتيجية One Candle Rule مفعّلة (تجريبية، حد {OCR_WEEKLY_LIMIT}/أسبوع)"
    send_telegram(startup)
    print("✅ البوت Pro شغّال")
    last_signals = {s: None for s in SYMBOLS}
    last_signals_ocr = {s: None for s in SYMBOLS}

    while True:
        if not is_good_time():
            print(f"⏸️ [{datetime.now().strftime('%H:%M')}] خارج وقت/يوم التداول — ينتظر")
            time.sleep(300)
            continue

        old_done = not can_send()
        ocr_done = (not ENABLE_OCR) or (not can_send_ocr())
        if old_done and ocr_done:
            print("📵 وصلنا الحد الأسبوعي للاستراتيجيتين")
            time.sleep(3600)
            continue

        now = datetime.now()
        for symbol in SYMBOLS:
            try:
                candles = get_candles(symbol)
                if not candles:
                    continue

                # ===== الاستراتيجية القديمة =====
                if can_send():
                    signal = analyze(candles, symbol)
                    if signal:
                        last = last_signals[symbol]
                        if last is None or (now - last).seconds > 3600:
                            weekly["count"] += 1
                            send_telegram(format_msg(signal, symbol))
                            last_signals[symbol] = now
                            print(f"✅ {symbol}: {signal['signal']} | إشارة {weekly['count']}/3")
                    else:
                        print(f"👀 [{now.strftime('%H:%M')}] {symbol}: لا إشارة مؤكدة (قديمة)")

                # ===== الاستراتيجية الجديدة (One Candle Rule) =====
                if ENABLE_OCR and can_send_ocr():
                    signal_ocr = analyze_one_candle_rule(candles, symbol)
                    if signal_ocr:
                        last_o = last_signals_ocr[symbol]
                        if last_o is None or (now - last_o).seconds > 3600:
                            weekly_ocr["count"] += 1
                            send_telegram(format_msg_ocr(signal_ocr, symbol))
                            last_signals_ocr[symbol] = now
                            print(f"🆕 {symbol}: {signal_ocr['signal']} | OCR {weekly_ocr['count']}/{OCR_WEEKLY_LIMIT}")
                    else:
                        print(f"👀 [{now.strftime('%H:%M')}] {symbol}: لا إشارة (OCR)")

                time.sleep(8)
            except Exception as ex:
                print(f"❌ {symbol}: {ex}")
        time.sleep(60)

if __name__ == "__main__":
    main()
