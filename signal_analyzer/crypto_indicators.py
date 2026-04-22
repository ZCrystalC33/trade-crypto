"""
Technical Indicators for Crypto
"""

import math
from typing import List, Dict, Optional


def calc_ema(values: List[float], period: int) -> List[float]:
    """計算 EMA（忽略 None 值）"""
    # 先過濾 None
    clean = [v for v in values if v is not None]
    if len(clean) < period:
        return [None] * len(values)
    
    k = 2 / (period + 1)
    result = [None] * len(values)
    
    # 找到第一個有效位置
    first_valid_idx = next((i for i, v in enumerate(values) if v is not None), -1)
    if first_valid_idx >= period - 1:
        result[period - 1] = values[period - 1]
        prev_ema = values[period - 1]
        
        for i in range(period, len(values)):
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
    
    # 計算第一筆 RSI
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
    
    # 後續用 Wilder 平滑
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
    
    # DIF = EMA(fast) - EMA(slow)
    dif = []
    for i in range(len(closes)):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            dif.append(ema_fast[i] - ema_slow[i])
        else:
            dif.append(None)
    
    # DEA = EMA(DIF, signal)
    dea = calc_ema(dif, signal)
    
    # MACD_Bar = 2 * (DIF - DEA)
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
        # 找出最高/最低
        high_max = max(highs[i - period + 1:i + 1])
        low_min = min(lows[i - period + 1:i + 1])
        
        rsv = (closes[i] - low_min) / (high_max - low_min) * 100 if high_max != low_min else 50
        
        # K = 2/3 * 前K + 1/3 * RSV
        prev_k = k_values[i - 1] if k_values[i - 1] is not None else 50
        k = 2 / 3 * prev_k + 1 / 3 * rsv
        k_values.append(k)
        
        # D = 2/3 * 前D + 1/3 * K
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


def detect_golden_cross(k_values: List[float], d_values: List[float]) -> str:
    """檢測 KD 黃金交叉/死亡交叉"""
    if len(k_values) < 2 or k_values[-1] is None or d_values[-1] is None:
        return "NONE"
    
    k_prev = k_values[-2]
    d_prev = d_values[-2]
    
    if k_prev is None or d_prev is None:
        return "NONE"
    
    # 黃金交叉：K 從下往上穿越 D，且 K < 30
    if k_prev < d_prev and k_values[-1] > d_values[-1] and k_values[-1] < 30:
        return "GOLDEN"
    
    # 死亡交叉：K 從上往下穿越 D，且 K > 70
    if k_prev > d_prev and k_values[-1] < d_values[-1] and k_values[-1] > 70:
        return "DEAD"
    
    return "NONE"


def detect_macd_cross(dif: List[float], dea: List[float]) -> str:
    """檢測 MACD 交叉"""
    if len(dif) < 2 or dif[-1] is None or dea[-1] is None:
        return "NONE"
    
    if dif[-2] is None or dea[-2] is None:
        return "NONE"
    
    # 黃金交叉：DIF 從下往上穿越 DEA，且 DIF < 0
    if dif[-2] < dea[-2] and dif[-1] > dea[-1] and dif[-1] < 0:
        return "GOLDEN"
    
    # 死亡交叉：DIF 從上往下穿越 DEA，且 DIF > 0
    if dif[-2] > dea[-2] and dif[-1] < dea[-1] and dif[-1] > 0:
        return "DEAD"
    
    return "NONE"


class CryptoIndicators:
    """加密貨幣技術指標計算器"""
    
    def __init__(self):
        self.data_source = None
    
    def analyze(self, symbol: str, interval: str = "15m", limit: int = 100) -> Dict:
        """
        分析單一幣種
        
        Returns:
            {
                "symbol": str,
                "price": float,
                "change_24h": float,
                "indicators": {
                    "KD": {"K": float, "D": float, "cross": str},
                    "MACD": {"dif": float, "dea": float, "hist": float, "cross": str},
                    "RSI": float,
                    "BB": {"MA": float, "Upper": float, "Lower": float},
                    "EMA": {"EMA20": float, "EMA60": float}
                },
                "signals": ["KD_GOLDEN", "RSI_OVERSOLD", ...],
                "score": 0-100
            }
        """
        from signal_analyzer.crypto_data import BinanceDataSource
        
        if not self.data_source:
            self.data_source = BinanceDataSource()
        
        # 取得 K 線數據
        klines = self.data_source.get_klines(symbol, interval, limit)
        if not klines:
            return {"error": f"No data for {symbol}"}
        
        closes = [k["close"] for k in klines]
        highs = [k["high"] for k in klines]
        lows = [k["low"] for k in klines]
        
        # 取得 24hr ticker
        ticker = self.data_source.get_ticker(symbol)
        
        # 計算指標
        k_values, d_values = calc_kd(highs, lows, closes, 9)
        dif, dea, macd_bar = calc_macd(closes, 12, 26, 9)
        rsi = calc_rsi(closes, 14)
        ema20 = calc_ema(closes, 20)
        ema60 = calc_ema(closes, 60)
        bb_ma, bb_upper, bb_lower = calc_bollinger(closes, 20, 2)
        
        # 檢測交叉
        kd_cross = detect_golden_cross(k_values, d_values)
        macd_cross = detect_macd_cross(dif, dea)
        
        # 計算分數
        score = self._calc_score(
            k_values[-1] if k_values else None,
            d_values[-1] if d_values else None,
            rsi[-1] if rsi else None,
            dif[-1] if dif else None,
            macd_bar[-1] if macd_bar else None,
            closes[-1] if closes else None,
            bb_upper[-1] if bb_upper else None,
            bb_lower[-1] if bb_lower else None,
            ticker["price_change_pct"] if ticker else 0
        )
        
        # 收集信號
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
                }
            },
            "signals": signals,
            "score": score
        }
    
    def _calc_score(self, k, d, rsi, dif, macd_hist, price, bb_upper, bb_lower, change_24h) -> int:
        """計算综合分數 0-100"""
        score = 50  # 基礎分
        
        # RSI 評估
        if rsi:
            if rsi < 30:
                score += 15  # 超賣
            elif rsi > 70:
                score -= 15  # 超買
            else:
                score += (50 - abs(rsi - 50)) / 5  # 接近 50 加分
        
        # MACD 評估
        if macd_hist is not None:
            if macd_hist > 0:
                score += 10
            else:
                score -= 10
        
        # 24hr 變化
        if change_24h:
            if change_24h > 5:
                score += 10
            elif change_24h < -5:
                score -= 10
            else:
                score += change_24h
        
        # 布林帶位置
        if price and bb_upper and bb_lower:
            if price < bb_lower:
                score += 10  # 突破下限
            elif price > bb_upper:
                score -= 10  # 突破上限
        
        return max(0, min(100, round(score)))