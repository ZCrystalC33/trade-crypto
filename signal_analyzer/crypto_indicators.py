"""
Technical Indicators for Crypto
"""

import math
from typing import List, Dict, Optional


def calc_ema(values: List[float], period: int) -> List[float]:
    """計算 EMA（忽略 None 值）"""
    if len(values) < period:
        return [None] * len(values)
    
    k = 2 / (period + 1)
    result = [None] * len(values)
    
    first_valid_idx = next((i for i, v in enumerate(values) if v is not None), -1)
    if first_valid_idx == -1:
        return [None] * len(values)
    
    start_idx = first_valid_idx + period - 1
    if start_idx >= len(values):
        return [None] * len(values)
    
    result[start_idx] = values[start_idx]
    prev_ema = values[start_idx]
    
    for i in range(start_idx + 1, len(values)):
        if values[i] is not None:
            ema_val = values[i] * k + prev_ema * (1 - k)
            result[i] = ema_val
            prev_ema = ema_val
    
    return result


def calc_rsi(closes: List[float], period: int = 14) -> List[float]:
    """計算 RSI (Wilder平滑版)"""
    if len(closes) < period + 1:
        return [None] * len(closes)
    
    result = [None] * period
    
    gains = []
    losses = []
    for i in range(1, period + 1):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        result.append(100)
    else:
        rs = avg_gain / avg_loss
        result.append(100 - 100 / (1 + rs))
    
    for i in range(period + 1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gain = max(diff, 0)
        loss = max(-diff, 0)
        
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        
        if avg_loss == 0:
            result.append(100)
        else:
            rs = avg_gain / avg_loss
            result.append(100 - 100 / (1 + rs))
    
    return result


def calc_macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
    """計算 MACD (DIF, DEA, MACD_BAR)"""
    if len(closes) < slow:
        return [None] * len(closes), [None] * len(closes), [None] * len(closes)
    
    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)
    
    dif = []
    for i in range(len(closes)):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            dif.append(ema_fast[i] - ema_slow[i])
        else:
            dif.append(None)
    
    dea = calc_ema(dif, signal)
    
    macd_bar = []
    for i in range(len(closes)):
        if dif[i] is not None and dea[i] is not None:
            macd_bar.append(2 * (dif[i] - dea[i]))
        else:
            macd_bar.append(None)
    
    return dif, dea, macd_bar


def calc_kd(highs: List[float], lows: List[float], closes: List[float], period: int = 9) -> tuple:
    """計算 KD 指標"""
    if len(closes) < period:
        return [None] * len(closes), [None] * len(closes)
    
    k_values = [None] * period
    d_values = [None] * period
    
    for i in range(period, len(closes)):
        high_max = max(highs[i - period + 1:i + 1])
        low_min = min(lows[i - period + 1:i + 1])
        
        rsv = (closes[i] - low_min) / (high_max - low_min) * 100 if high_max != low_min else 50
        
        prev_k = k_values[i - 1] if k_values[i - 1] is not None else 50
        k = 2 / 3 * prev_k + 1 / 3 * rsv
        k_values.append(k)
        
        prev_d = d_values[i - 1] if d_values[i - 1] is not None else 50
        d = 2 / 3 * prev_d + 1 / 3 * k
        d_values.append(d)
    
    return k_values, d_values


def calc_bollinger(closes: List[float], period: int = 20, std_mult: float = 2) -> tuple:
    """計算布林帶 (MA, Upper, Lower)"""
    if len(closes) < period:
        return [None] * len(closes), [None] * len(closes), [None] * len(closes)
    
    ma = []
    upper = []
    lower = []
    
    for i in range(len(closes)):
        if i < period - 1:
            ma.append(None)
            upper.append(None)
            lower.append(None)
        else:
            window = closes[i - period + 1:i + 1]
            m = sum(window) / period
            variance = sum((x - m) ** 2 for x in window) / (period - 1)
            std = variance ** 0.5
            
            ma.append(m)
            upper.append(m + std_mult * std)
            lower.append(m - std_mult * std)
    
    return ma, upper, lower


def calc_obv(closes: List[float], volumes: List[float]) -> List[float]:
    """計算 OBV（能量潮指標）"""
    if len(closes) < 2 or len(volumes) < 2:
        return [None] * len(closes)
    
    result = [None]
    obv = 0
    
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv += volumes[i]
        elif closes[i] < closes[i - 1]:
            obv -= volumes[i]
        result.append(obv)
    
    return result


def calc_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[float]:
    """計算 ATR（平均真實波幅）"""
    if len(closes) < period + 1:
        return [None] * len(closes)
    
    tr_list = [None]
    
    for i in range(1, len(closes)):
        tr1 = highs[i] - lows[i]
        tr2 = abs(highs[i] - closes[i - 1])
        tr3 = abs(lows[i] - closes[i - 1])
        tr_list.append(max(tr1, tr2, tr3))
    
    atr = calc_ema(tr_list, period)
    return atr


def calc_vwap(highs: List[float], lows: List[float], closes: List[float], volumes: List[float]) -> Optional[float]:
    """計算 VWAP（成交量加權平均價）"""
    if len(closes) < 2 or len(volumes) < 2:
        return None
    
    typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
    total_pv = sum(tp * v for tp, v in zip(typical_prices, volumes))
    total_vol = sum(volumes)
    
    if total_vol == 0:
        return None
    
    return total_pv / total_vol


def calc_ichimoku(highs: List[float], lows: List[float], closes: List[float]) -> Dict:
    """計算 Ichimoku 雲圖指標"""
    n = len(closes)
    if n < 26:
        return {
            "tenkan": [None] * n,
            "kijun": [None] * n,
            "senkou_a": [None] * n,
            "senkou_b": [None] * n,
            "chikou": [None] * n,
            "signal": "NEUTRAL"
        }
    
    tenkan = []
    kijun = []
    senkou_a = []
    senkou_b = []
    chikou = []
    
    for i in range(n):
        # Tenkan-sen (9 period)
        if i < 9:
            tenkan.append(None)
        else:
            window_h = highs[i - 9:i + 1]
            window_l = lows[i - 9:i + 1]
            if not window_h:
                tenkan.append(None)
            else:
                tenkan.append((max(window_h) + min(window_l)) / 2)
        
        # Kijun-sen (26 period)
        if i < 26:
            kijun.append(None)
        else:
            window_h = highs[i - 26:i + 1]
            window_l = lows[i - 26:i + 1]
            if not window_h:
                kijun.append(None)
            else:
                kijun.append((max(window_h) + min(window_l)) / 2)
        
        # Senkou Span A
        if i < 26:
            senkou_a.append(None)
        else:
            if tenkan[i] is not None and kijun[i] is not None:
                senkou_a.append((tenkan[i] + kijun[i]) / 2)
            else:
                senkou_a.append(None)
        
        # Senkou Span B (52 period)
        if i < 52:
            senkou_b.append(None)
        else:
            window_h = highs[i - 52:i + 1]
            window_l = lows[i - 52:i + 1]
            if not window_h:
                senkou_b.append(None)
            else:
                senkou_b.append((max(window_h) + min(window_l)) / 2)
        
        # Chikou Span
        chikou.append(closes[i] if i >= 26 else None)
    
    # 計算信號
    signal = "NEUTRAL"
    if n >= 26:
        price = closes[-1]
        idx = n - 26
        
        sa = senkou_a[idx] if senkou_a[idx] is not None else 0
        sb = senkou_b[idx] if senkou_b[idx] is not None else 0
        
        if price > sa and price > sb:
            signal = "BULLISH"
        elif price < sa and price < sb:
            signal = "BEARISH"
        
        cloud_thick = abs(sa - sb)
        if cloud_thick < price * 0.005:
            signal = "NEUTRAL"
    
    return {
        "tenkan": tenkan,
        "kijun": kijun,
        "senkou_a": senkou_a,
        "senkou_b": senkou_b,
        "chikou": chikou,
        "signal": signal
    }


def calc_fibonacci(highs: List[float], lows: List[float], period: int = 100) -> Dict:
    """計算斐波那契回撤水平"""
    n = len(highs)
    if n < period:
        return {}
    
    high = max(highs[-period:])
    low = min(lows[-period:])
    diff = high - low
    
    levels = {
        "level_0": low,
        "level_236": low + diff * 0.236,
        "level_382": low + diff * 0.382,
        "level_500": low + diff * 0.500,
        "level_618": low + diff * 0.618,
        "level_786": low + diff * 0.786,
        "level_100": high
    }
    
    current = highs[-1]
    if diff > 0:
        levels["current_retrace"] = (high - current) / diff * 100
    else:
        levels["current_retrace"] = 0
    
    return levels


def detect_golden_cross(k_values: List[float], d_values: List[float]) -> str:
    """檢測 KD 黃金交叉/死亡交叉"""
    if len(k_values) < 2 or k_values[-1] is None or d_values[-1] is None:
        return "NONE"
    
    k_prev = k_values[-2]
    d_prev = d_values[-2]
    
    if k_prev is None or d_prev is None:
        return "NONE"
    
    if k_prev < d_prev and k_values[-1] > d_values[-1] and k_values[-1] < 30:
        return "GOLDEN"
    
    if k_prev > d_prev and k_values[-1] < d_values[-1] and k_values[-1] > 70:
        return "DEAD"
    
    return "NONE"


def detect_macd_cross(dif: List[float], dea: List[float]) -> str:
    """檢測 MACD 交叉"""
    if len(dif) < 2 or dif[-1] is None or dea[-1] is None:
        return "NONE"
    
    if dif[-2] is None or dea[-2] is None:
        return "NONE"
    
    if dif[-2] < dea[-2] and dif[-1] > dea[-1] and dif[-1] < 0:
        return "GOLDEN"
    
    if dif[-2] > dea[-2] and dif[-1] < dea[-1] and dif[-1] > 0:
        return "DEAD"
    
    return "NONE"


class CryptoIndicators:
    """加密貨幣技術指標計算器"""
    
    def __init__(self):
        self.data_source = None
    
    def analyze(self, symbol: str, interval: str = "15m", limit: int = 200) -> Dict:
        """分析單一幣種（增強版）"""
        from signal_analyzer.crypto_data import BinanceDataSource
        
        if not self.data_source:
            self.data_source = BinanceDataSource()
        
        klines = self.data_source.get_klines(symbol, interval, limit)
        if not klines:
            return {"error": f"No data for {symbol}"}
        
        closes = [k["close"] for k in klines]
        highs = [k["high"] for k in klines]
        lows = [k["low"] for k in klines]
        volumes = [k["volume"] for k in klines]
        
        ticker = self.data_source.get_ticker(symbol)
        
        # 基本指標
        k_values, d_values = calc_kd(highs, lows, closes, 9)
        dif, dea, macd_bar = calc_macd(closes, 12, 26, 9)
        rsi = calc_rsi(closes, 14)
        ema20 = calc_ema(closes, 20)
        ema60 = calc_ema(closes, 60)
        bb_ma, bb_upper, bb_lower = calc_bollinger(closes, 20, 2)
        
        # 新增指標
        obv = calc_obv(closes, volumes)
        atr = calc_atr(highs, lows, closes, 14)
        vwap = calc_vwap(highs, lows, closes, volumes)
        ichimoku = calc_ichimoku(highs, lows, closes)
        fib = calc_fibonacci(highs, lows, 100)
        
        # 交叉檢測
        kd_cross = detect_golden_cross(k_values, d_values)
        macd_cross = detect_macd_cross(dif, dea)
        
        # 分數
        score = self._calc_score(
            k_values[-1] if k_values else None,
            d_values[-1] if d_values else None,
            rsi[-1] if rsi else None,
            dif[-1] if dif else None,
            macd_bar[-1] if macd_bar else None,
            closes[-1] if closes else None,
            bb_upper[-1] if bb_upper else None,
            bb_lower[-1] if bb_lower else None,
            ticker["price_change_pct"] if ticker else 0,
            atr[-1] if atr and atr[-1] else None,
            vwap if vwap else None,
            closes[-1] if closes else None
        )
        
        # 信號
        signals = []
        if kd_cross == "GOLDEN":
            signals.append("KD_GOLDEN")
        if kd_cross == "DEAD":
            signals.append("KD_DEAD")
        if macd_cross == "GOLDEN":
            signals.append("MACD_GOLDEN")
        if macd_cross == "DEAD":
            signals.append("MACD_DEAD")
        if rsi[-1] and rsi[-1] < 30:
            signals.append("RSI_OVERSOLD")
        if rsi[-1] and rsi[-1] > 70:
            signals.append("RSI_OVERBOUGHT")
        if obv and len(obv) > 1 and obv[-1] and obv[-2]:
            signals.append("OBV_BULLISH" if obv[-1] > obv[-2] else "OBV_BEARISH")
        if atr and len(atr) > 1 and atr[-1] and atr[-2]:
            if atr[-1] > atr[-2]:
                signals.append("ATR_INCREASING")
        if vwap and closes[-1]:
            signals.append("PRICE_ABOVE_VWAP" if closes[-1] > vwap else "PRICE_BELOW_VWAP")
        if ichimoku["signal"] != "NEUTRAL":
            signals.append(f"ICHIMOKU_{ichimoku['signal']}")
        if fib and 38 < fib.get("current_retrace", 0) < 50:
            signals.append("FIB_382_50")
        elif fib and 50 < fib.get("current_retrace", 0) < 62:
            signals.append("FIB_50_618")
        
        return {
            "symbol": symbol,
            "price": closes[-1] if closes else None,
            "change_24h": ticker["price_change_pct"] if ticker else None,
            "volume_24h": ticker["quote_volume"] if ticker else None,
            "indicators": {
                "KD": {
                    "K": round(k_values[-1], 2) if k_values and k_values[-1] else None,
                    "D": round(d_values[-1], 2) if d_values and d_values[-1] else None,
                    "cross": kd_cross
                },
                "MACD": {
                    "dif": round(dif[-1], 4) if dif and dif[-1] else None,
                    "dea": round(dea[-1], 4) if dea and dea[-1] else None,
                    "hist": round(macd_bar[-1], 4) if macd_bar and macd_bar[-1] else None,
                    "cross": macd_cross
                },
                "RSI": round(rsi[-1], 2) if rsi and rsi[-1] else None,
                "BB": {
                    "MA": round(bb_ma[-1], 2) if bb_ma and bb_ma[-1] else None,
                    "Upper": round(bb_upper[-1], 2) if bb_upper and bb_upper[-1] else None,
                    "Lower": round(bb_lower[-1], 2) if bb_lower and bb_lower[-1] else None
                },
                "EMA": {
                    "EMA20": round(ema20[-1], 2) if ema20 and ema20[-1] else None,
                    "EMA60": round(ema60[-1], 2) if ema60 and ema60[-1] else None
                },
                "OBV": round(obv[-1], 2) if obv and obv[-1] else None,
                "ATR": round(atr[-1], 4) if atr and atr[-1] else None,
                "VWAP": round(vwap, 4) if vwap else None,
                "Ichimoku": {
                    "tenkan": round(ichimoku["tenkan"][-1], 2) if ichimoku["tenkan"] and ichimoku["tenkan"][-1] else None,
                    "kijun": round(ichimoku["kijun"][-1], 2) if ichimoku["kijun"] and ichimoku["kijun"][-1] else None,
                    "signal": ichimoku["signal"]
                },
                "Fibonacci": {
                    "retrace_pct": round(fib.get("current_retrace", 0), 1),
                    "level_382": round(fib.get("level_382", 0), 2),
                    "level_618": round(fib.get("level_618", 0), 2)
                }
            },
            "signals": signals,
            "score": score
        }
    
    def _calc_score(self, k, d, rsi, dif, macd_hist, price, bb_upper, bb_lower, change_24h, atr, vwap, current_price) -> int:
        """計算综合分數"""
        score = 50
        
        if rsi:
            if rsi < 30:
                score += 15
            elif rsi > 70:
                score -= 15
            else:
                score += (50 - abs(rsi - 50)) / 5
        
        if macd_hist is not None:
            if macd_hist > 0:
                score += 10
            else:
                score -= 10
        
        if change_24h:
            if change_24h > 5:
                score += 10
            elif change_24h < -5:
                score -= 10
            else:
                score += change_24h
        
        if price and bb_upper and bb_lower:
            if price < bb_lower:
                score += 10
            elif price > bb_upper:
                score -= 10
        
        if vwap and current_price:
            if current_price > vwap:
                score += 5
            else:
                score -= 5
        
        return max(0, min(100, round(score)))
