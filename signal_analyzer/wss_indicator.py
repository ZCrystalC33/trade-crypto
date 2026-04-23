"""
WSS Indicator System - Wholesale Whale Sentiment & Strength
加密貨幣多維度評估指標

基於四大維度：
1. 基本面 (Fundamentals) - 用途、團隊、Tokenomics
2. 鏈上指標 (On-chain) - 活躍地址、TVL、機構活動、MVRV
3. 技術指標 (Technical) - 價格趨勢、動量、成交量
4. 市場情緒 (Market Sentiment) - 社群、槓桿、資金费率

WSS Score: 0-100
- 80-100: 極強 → 考慮做多
- 60-80: 強 → 觀察
- 40-60: 中性 → 觀望
- 20-40: 弱 → 謹慎
- 0-20: 極弱 → 避免
"""

import math
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta


# ============================================================
# 維度 1: 基本面 (Fundamentals) - 0-25 分
# ============================================================

class FundamentalsAnalyzer:
    """
    基本面分析
    注意：大部分需要手動更新或第三方 API
    這裡使用假設值，實際使用需要對接真實數據源
    """
    
    def __init__(self):
        # 從 CoinGecko 等 API 獲取的項目數據
        self.project_cache = {}
    
    def analyze(self, symbol: str) -> Dict:
        """
        分析基本面的各個維度
        返回 0-25 的分數
        """
        project = self._get_project_data(symbol)
        
        # 各維度分數 (0-5)
        utility_score = self._calc_utility_score(project)  # 用途
        team_score = self._calc_team_score(project)  # 團隊
        tokenomics_score = self._calc_tokenomics_score(project)  # 代幣經濟
        tech_score = self._calc_tech_score(project)  # 技術
        
        total = utility_score + team_score + tokenomics_score + tech_score
        
        return {
            "total": round(total, 2),
            "breakdown": {
                "utility": round(utility_score, 2),
                "team": round(team_score, 2),
                "tokenomics": round(tokenomics_score, 2),
                "tech": round(tech_score, 2)
            },
            "signals": self._generate_signals(utility_score, team_score, tokenomics_score, tech_score)
        }
    
    def _get_project_data(self, symbol: str) -> Dict:
        """
        獲取項目數據
        實際應該對接 CoinGecko / DeFiLlama / 第三方 API
        """
        # 這裡用示例數據
        # 實際項目應該有真實的項目調研
        default_projects = {
            "BTC": {
                "name": "Bitcoin",
                "category": "store_of_value",
                "utility_score": 5,
                "team_public": True,
                "team_score": 4,
                "tokenomics": {
                    "total_supply": 21000000,
                    "circulating_supply": 19500000,
                    "inflation": 0.018,
                    "teamAllocation": 0.05
                },
                "tech_score": 5,
                "hack_history": False
            },
            "ETH": {
                "name": "Ethereum",
                "category": "smart_contract",
                "utility_score": 5,
                "team_public": True,
                "team_score": 4,
                "tokenomics": {
                    "total_supply": None,  # 動態
                    "circulating_supply": 120000000,
                    "inflation": 0.05,
                    "teamAllocation": 0.15
                },
                "tech_score": 5,
                "hack_history": True  # DAO Hack (2016)
            },
            "BNB": {
                "name": "BNB",
                "category": "exchange_token",
                "utility_score": 4,
                "team_public": True,
                "team_score": 5,
                "tokenomics": {
                    "total_supply": 200000000,
                    "circulating_supply": 150000000,
                    "inflation": -0.20,  # 回購銷毀
                    "teamAllocation": 0.30
                },
                "tech_score": 4,
                "hack_history": False
            }
        }
        
        # 嘗試從快取讀取，否則返回預設值
        if symbol in self.project_cache:
            return self.project_cache[symbol]
        
        return default_projects.get(symbol.upper().replace("USDT", ""), {
            "name": symbol,
            "category": "unknown",
            "utility_score": 2,
            "team_public": False,
            "team_score": 2,
            "tokenomics": {
                "total_supply": None,
                "circulating_supply": None,
                "inflation": 0.1,
                "teamAllocation": 0.40
            },
            "tech_score": 2,
            "hack_history": True
        })
    
    def _calc_utility_score(self, project: Dict) -> float:
        """計算用途分數 (0-5)"""
        category_scores = {
            "store_of_value": 4,
            "smart_contract": 5,
            "defi": 4,
            "exchange_token": 3,
            "gaming": 3,
            "ai": 4,
            "meme": 1,
            "unknown": 2
        }
        return category_scores.get(project.get("category", "unknown"), 2)
    
    def _calc_team_score(self, project: Dict) -> float:
        """計算團隊分數 (0-5)"""
        score = 2  # 預設
        
        if project.get("team_public"):
            score += 2
        
        if project.get("vc_backed"):
            score += 1
        
        return min(5, score)
    
    def _calc_tokenomics_score(self, project: Dict) -> float:
        """計算代幣經濟分數 (0-5)"""
        tokenomics = project.get("tokenomics", {})
        
        score = 3  # 預設
        
        # 供應量合理性
        total = tokenomics.get("total_supply")
        if total and total < 1000000000:  # < 10億
            score += 1
        
        # 團隊份額
        team_alloc = tokenomics.get("teamAllocation", 0)
        if team_alloc < 0.15:
            score += 1
        elif team_alloc > 0.30:
            score -= 1
        
        # 發行率（負發行 = 回購銷毀 = 加分）
        inflation = tokenomics.get("inflation", 0)
        if inflation < 0:
            score += 1
        elif inflation > 0.10:
            score -= 1
        
        return max(0, min(5, score))
    
    def _calc_tech_score(self, project: Dict) -> float:
        """計算技術分數 (0-5)"""
        score = 3  # 預設
        
        if project.get("hack_history"):
            score -= 2
        
        return max(0, min(5, score))
    
    def _generate_signals(self, utility, team, tokenomics, tech) -> List[str]:
        """生成基本面信號"""
        signals = []
        
        if utility >= 4:
            signals.append("HIGH_UTILITY")
        elif utility <= 2:
            signals.append("LOW_UTILITY")
        
        if team >= 4:
            signals.append("STRONG_TEAM")
        
        if tokenomics >= 4:
            signals.append("GOOD_TOKENOMICS")
        elif tokenomics <= 2:
            signals.append("RISKY_TOKENOMICS")
        
        if tech >= 4:
            signals.append("STRONG_TECH")
        
        return signals


# ============================================================
# 維度 2: 鏈上指標 (On-chain) - 0-25 分
# ============================================================

class OnChainAnalyzer:
    """
    鏈上指標分析
    數據來源: CoinGecko API (免費)
    """
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self):
        self.session = requests.Session()
    
    def analyze(self, symbol: str) -> Dict:
        """
        分析鏈上指標
        返回 0-25 的分數
        """
        data = self._fetch_onchain_data(symbol)
        
        if not data:
            return {
                "total": 0,
                "breakdown": {},
                "signals": ["NO_DATA"]
            }
        
        # 各維度分數 (0-5)
        active_addr_score = self._calc_active_addresses_score(data)  # 活躍地址
        volume_score = self._calc_volume_score(data)  # 交易量
        tvl_score = self._calc_tvl_score(data)  # TVL
        mvrv_score = self._calc_mvrv_score(data)  # MVRV
        whale_score = self._calc_whale_score(data)  # 大戶活動
        
        total = active_addr_score + volume_score + tvl_score + mvrv_score + whale_score
        
        return {
            "total": round(total, 2),
            "breakdown": {
                "active_addresses": round(active_addr_score, 2),
                "volume": round(volume_score, 2),
                "tvl": round(tvl_score, 2),
                "mvrv": round(mvrv_score, 2),
                "whale": round(whale_score, 2)
            },
            "raw_data": data,
            "signals": self._generate_signals(active_addr_score, volume_score, tvl_score, mvrv_score, whale_score)
        }
    
    def _fetch_onchain_data(self, symbol: str) -> Optional[Dict]:
        """從 CoinGecko 獲取鏈上數據"""
        # 轉換 symbol 格式
        coin_id = self._symbol_to_coingecko_id(symbol)
        
        endpoint = f"{self.BASE_URL}/coins/{coin_id}"
        params = {
            "localization": False,
            "tickers": False,
            "community_data": False,
            "developer_data": False
        }
        
        try:
            resp = self.session.get(endpoint, params=params, timeout=10)
            if resp.status_code == 404:
                return None
            
            data = resp.json()
            
            return {
                "active_addresses": data.get("on_analytics", {}).get("active_addresses"),
                "volume_24h": data.get("trading_volumes", [None])[0],
                "tvl": data.get("market_data", {}).get("total_value_locked", {}).get("usd"),
                "mvrv": self._estimate_mvrv(data),
                "market_cap": data.get("market_data", {}).get("market_cap", {}).get("usd"),
                "price_change_24h": data.get("market_data", {}).get("price_change_percentage_24h")
            }
        except Exception as e:
            print(f"Error fetching onchain data for {symbol}: {e}")
            return None
    
    def _symbol_to_coingecko_id(self, symbol: str) -> str:
        """Symbol → CoinGecko ID 映射"""
        mapping = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "BNB": "binancecoin",
            "SOL": "solana",
            "XRP": "ripple",
            "ADA": "cardano",
            "DOGE": "dogecoin",
            "DOT": "polkadot",
            "MATIC": "matic-network",
            "AVAX": "avalanche-2",
            "LINK": "chainlink",
            "UNI": "uniswap",
            "ATOM": "cosmos",
            "LTC": "litecoin",
            "FIL": "filecoin"
        }
        
        clean = symbol.upper().replace("USDT", "").replace("BUSD", "")
        return mapping.get(clean, clean.lower())
    
    def _estimate_mvrv(self, data: Dict) -> float:
        """
        估算 MVRV
        MVRV = 市值 / 已實現市值
        這裡用簡化估算
        """
        market_cap = data.get("market_cap")
        if not market_cap:
            return None
        
        # 簡化估算：假設已實現市值 = 市值 * 0.6
        # 實際需要從鏈上數據計算
        realized_cap = market_cap * 0.6
        
        return market_cap / realized_cap if realized_cap else None
    
    def _calc_active_addresses_score(self, data: Dict) -> float:
        """活躍地址分數 (0-5)"""
        active = data.get("active_addresses")
        if not active:
            return 2.5  # 無數據
        
        # 簡化評估：相對排名
        # 實際需要歷史對比
        if active > 1000000:  # > 100 萬
            return 5
        elif active > 100000:  # > 10 萬
            return 4
        elif active > 10000:  # > 1 萬
            return 3
        elif active > 1000:
            return 2
        else:
            return 1
    
    def _calc_volume_score(self, data: Dict) -> float:
        """交易量分數 (0-5)"""
        volume = data.get("volume_24h")
        market_cap = data.get("market_cap")
        
        if not volume or not market_cap:
            return 2.5
        
        # Volume / MarketCap 比率
        ratio = volume / market_cap
        
        if ratio > 0.3:  # 高換手
            return 4
        elif ratio > 0.1:
            return 3
        elif ratio > 0.05:
            return 2
        else:
            return 1
    
    def _calc_tvl_score(self, data: Dict) -> float:
        """TVL 分數 (0-5)"""
        tvl = data.get("tvl")
        
        if not tvl:
            return 2.5  # 無 DeFi
        
        if tvl > 10000000000:  # > 100 億
            return 5
        elif tvl > 1000000000:  # > 10 億
            return 4
        elif tvl > 100000000:  # > 1 億
            return 3
        elif tvl > 10000000:  # > 1000 萬
            return 2
        else:
            return 1
    
    def _calc_mvrv_score(self, data: Dict) -> float:
        """
        MVRV 分數 (0-5)
        MVRV < 1: 低估
        MVRV = 1-3: 合理
        MVRV > 3: 高估
        """
        mvrv = data.get("mvrv")
        
        if not mvrv:
            return 2.5
        
        if mvrv < 1:
            return 5  # 嚴重低估
        elif mvrv < 2:
            return 4  # 低估
        elif mvrv < 3:
            return 3  # 合理
        elif mvrv < 4:
            return 2  # 偏高
        else:
            return 1  # 嚴重高估
    
    def _calc_whale_score(self, data: Dict) -> float:
        """
        大戶活動分數 (0-5)
        這裡用交易量作為代理指標
        實際需要追蹤大額轉帳
        """
        volume = data.get("volume_24h")
        market_cap = data.get("market_cap")
        
        if not volume or not market_cap:
            return 2.5
        
        # 大戶活動指標：高交易量 + 高市值比率
        ratio = volume / market_cap
        
        if ratio > 0.5:
            return 5
        elif ratio > 0.3:
            return 4
        elif ratio > 0.1:
            return 3
        elif ratio > 0.05:
            return 2
        else:
            return 1
    
    def _generate_signals(self, addr, vol, tvl, mvrv, whale) -> List[str]:
        """生成鏈上信號"""
        signals = []
        
        if addr >= 4:
            signals.append("HIGH_ACTIVITY")
        elif addr <= 2:
            signals.append("LOW_ACTIVITY")
        
        if mvrv <= 2:
            signals.append("MVRV_UNDERVALUED")
        elif mvrv >= 4:
            signals.append("MVRV_OVERVALUED")
        
        if tvl >= 4:
            signals.append("HIGH_TVL")
        
        if whale >= 4:
            signals.append("HIGH_WHALE_ACTIVITY")
        
        return signals


# ============================================================
# 維度 3: 技術指標 (Technical) - 0-25 分
# ============================================================

class TechnicalAnalyzer:
    """
    技術指標分析
    複用現有的技術指標系統
    """
    
    def __init__(self):
        from signal_analyzer.crypto_indicators import (
            calc_rsi, calc_macd, calc_kd, calc_bollinger, calc_ema
        )
        self.calc_rsi = calc_rsi
        self.calc_macd = calc_macd
        self.calc_kd = calc_kd
        self.calc_bollinger = calc_bollinger
        self.calc_ema = calc_ema
    
    def analyze(self, symbol: str, data_source) -> Dict:
        """
        分析技術指標
        返回 0-25 的分數
        """
        # 取得 K 線數據
        klines = data_source.get_klines(symbol, "1h", 200)
        if not klines:
            return {"total": 0, "breakdown": {}, "signals": ["NO_DATA"]}
        
        closes = [k["close"] for k in klines]
        highs = [k["high"] for k in klines]
        lows = [k["low"] for k in klines]
        volumes = [k["volume"] for k in klines]
        
        # 計算指標
        rsi = self.calc_rsi(closes, 14)
        dif, dea, macd_hist = self.calc_macd(closes, 12, 26, 9)
        k_values, d_values = self.calc_kd(highs, lows, closes, 9)
        bb_ma, bb_upper, bb_lower = self.calc_bollinger(closes, 20, 2)
        ema20 = self.calc_ema(closes, 20)
        ema60 = self.calc_ema(closes, 60)
        
        # 各維度分數
        trend_score = self._calc_trend_score(closes, ema20, ema60)  # 趨勢
        momentum_score = self._calc_momentum_score(rsi, k_values, d_values)  # 動量
        volume_score = self._calc_volume_score(volumes, closes)  # 成交量
        volatility_score = self._calc_volatility_score(bb_upper, bb_lower, closes)  # 波動性
        
        total = trend_score + momentum_score + volume_score + volatility_score
        
        return {
            "total": round(total, 2),
            "breakdown": {
                "trend": round(trend_score, 2),
                "momentum": round(momentum_score, 2),
                "volume": round(volume_score, 2),
                "volatility": round(volatility_score, 2)
            },
            "raw": {
                "rsi": round(rsi[-1], 2) if rsi and rsi[-1] else None,
                "kd_k": round(k_values[-1], 2) if k_values and k_values[-1] else None,
                "kd_d": round(d_values[-1], 2) if d_values and d_values[-1] else None,
                "macd_hist": round(macd_hist[-1], 4) if macd_hist and macd_hist[-1] else None,
                "price": round(closes[-1], 2),
                "ema20": round(ema20[-1], 2) if ema20 and ema20[-1] else None,
                "ema60": round(ema60[-1], 2) if ema60 and ema60[-1] else None
            },
            "signals": self._generate_signals(rsi, k_values, d_values, macd_hist, closes, bb_upper, bb_lower, volumes)
        }
    
    def _calc_trend_score(self, closes: List[float], ema20, ema60) -> float:
        """趨勢分數 (0-5)"""
        if not closes or not ema20 or not ema60:
            return 2.5
        
        price = closes[-1]
        e20 = ema20[-1]
        e60 = ema60[-1]
        
        if price > e20 > e60:
            return 5  # 強上升趨勢
        elif price > e20:
            return 4  # 偏上升
        elif price < e20 < e60:
            return 1  # 強下降趨勢
        elif price < e20:
            return 2  # 偏下降
        else:
            return 3  # 盤整
    
    def _calc_momentum_score(self, rsi: List[float], k_values: List[float], d_values: List[float]) -> float:
        """動量分數 (0-5)"""
        if not rsi or rsi[-1] is None:
            return 2.5
        
        rsi_val = rsi[-1]
        k = k_values[-1] if k_values else 50
        d = d_values[-1] if d_values else 50
        
        # RSI 評估
        rsi_score = 2.5
        if 40 <= rsi_val <= 60:
            rsi_score = 3  # 合理區間
        elif rsi_val < 30:
            rsi_score = 4.5  # 超賣，可能反彈
        elif rsi_val > 70:
            rsi_score = 1.5  # 超買
        
        # KD 評估
        kd_score = 2.5
        if k > d and k < 30:
            kd_score = 4.5  # 金叉超賣
        elif k < d and k > 70:
            kd_score = 1.5  # 死叉超買
        elif k > d:
            kd_score = 3.5  # 多頭
        else:
            kd_score = 2  # 空頭
        
        return (rsi_score + kd_score) / 2
    
    def _calc_volume_score(self, volumes: List[float], closes: List[float]) -> float:
        """成交量分數 (0-5)"""
        if len(volumes) < 20:
            return 2.5
        
        # 最近 5 日平均成交量 vs 20 日平均
        recent_avg = sum(volumes[-5:]) / 5
        hist_avg = sum(volumes[-20:]) / 20
        
        ratio = recent_avg / hist_avg if hist_avg > 0 else 1
        
        if ratio > 2:
            return 5  # 成交量暴增
        elif ratio > 1.5:
            return 4
        elif ratio > 0.8:
            return 3
        elif ratio > 0.5:
            return 2
        else:
            return 1
    
    def _calc_volatility_score(self, bb_upper: List[float], bb_lower: List[float], closes: List[float]) -> float:
        """波動性分數 (0-5) - 布林帶位置"""
        if not bb_upper or not closes or bb_upper[-1] is None:
            return 2.5
        
        price = closes[-1]
        upper = bb_upper[-1]
        lower = bb_lower[-1]
        
        # 計算價格在布林帶的位置 (0-1)
        position = (price - lower) / (upper - lower) if upper != lower else 0.5
        
        # 低波動性（布林帶窄）通常預示大波動
        bandwidth = (upper - lower) / closes[-20] if closes[-20] > 0 else 0.1
        
        vol_score = 2.5
        
        # 位置評估
        if position < 0.2:
            vol_score = 4.5  # 接近下軌，可能反彈
        elif position > 0.8:
            vol_score = 2  # 接近上軌
        
        # 波動性調整
        if bandwidth < 0.03:
            vol_score += 0.5  # 低波動預示突破
        elif bandwidth > 0.1:
            vol_score -= 0.5  # 高波動
        
        return max(0, min(5, vol_score))
    
    def _generate_signals(self, rsi, k_values, d_values, macd_hist, closes, bb_upper, bb_lower, volumes) -> List[str]:
        """生成技術信號"""
        signals = []
        
        if rsi and rsi[-1]:
            if rsi[-1] < 30:
                signals.append("RSI_OVERSOLD")
            elif rsi[-1] > 70:
                signals.append("RSI_OVERBOUGHT")
        
        if k_values and d_values and len(k_values) >= 2:
            k_prev, k_curr = k_values[-2], k_values[-1]
            d_prev, d_curr = d_values[-2], d_values[-1]
            
            if k_prev < d_prev and k_curr > d_curr and k_curr < 30:
                signals.append("KD_GOLDEN")
            elif k_prev > d_prev and k_curr < d_curr and k_curr > 70:
                signals.append("KD_DEAD")
        
        if macd_hist and macd_hist[-1]:
            if macd_hist[-1] > 0:
                signals.append("MACD_BULLISH")
            else:
                signals.append("MACD_BEARISH")
        
        if bb_upper and closes and bb_upper[-1]:
            if closes[-1] < bb_lower[-1]:
                signals.append("BB_BREAK_LOW")
            elif closes[-1] > bb_upper[-1]:
                signals.append("BB_BREAK_HIGH")
        
        return signals


# ============================================================
# 維度 4: 市場情緒 (Market Sentiment) - 0-25 分
# ============================================================

class SentimentAnalyzer:
    """
    市場情緒分析
    數據來源: Binance API + 估算
    """
    
    def __init__(self):
        from signal_analyzer.crypto_data import BinanceDataSource
        self.data_source = BinanceDataSource()
    
    def analyze(self, symbol: str) -> Dict:
        """
        分析市場情緒
        返回 0-25 的分數
        """
        # 取得期貨數據（如果有的話）
        ticker = self.data_source.get_ticker(symbol)
        
        # 各維度分數
        funding_score = self._calc_funding_score(ticker)  # 資金费率
        price_change_score = self._calc_price_change_score(ticker)  # 價格變化
        volume_score = self._calc_volume_score(ticker)  # 成交量變化
        fear_greed_score = self._calc_fear_greed_score()  # 恐懼/貪婪
        social_score = self._calc_social_score(symbol)  # 社群活躍度
        
        total = funding_score + price_change_score + volume_score + fear_greed_score + social_score
        
        return {
            "total": round(total, 2),
            "breakdown": {
                "funding": round(funding_score, 2),
                "price_change": round(price_change_score, 2),
                "volume": round(volume_score, 2),
                "fear_greed": round(fear_greed_score, 2),
                "social": round(social_score, 2)
            },
            "signals": self._generate_signals(funding_score, price_change_score, volume_score, fear_greed_score)
        }
    
    def _calc_funding_score(self, ticker: Dict) -> float:
        """
        資金费率分數 (0-5)
        注意：Binance USDT 期貨的 funding rate
        正數 = 多頭付費，負數 = 空頭付費
        """
        if not ticker:
            return 2.5
        
        # 估算 funding rate (需要實際期貨 API)
        # 這裡用 24h 價格變化作為代理
        change_pct = abs(ticker.get("price_change_pct", 0))
        
        if change_pct > 20:
            return 1  # 極度貪婪
        elif change_pct > 10:
            return 2
        elif change_pct > 5:
            return 3
        elif change_pct > 2:
            return 4
        else:
            return 5  # 低波動 = 資金费率溫和
    
    def _calc_price_change_score(self, ticker: Dict) -> float:
        """價格變化分數 (0-5)"""
        if not ticker:
            return 2.5
        
        change_pct = ticker.get("price_change_pct", 0)
        
        # 温和的上漲最好
        if 2 <= change_pct <= 8:
            return 5  # 温和上漲
        elif change_pct > 15:
            return 2  # 過熱
        elif change_pct < -15:
            return 1  # 暴跌
        elif -5 <= change_pct < 2:
            return 3  # 輕微下跌或持平
        else:
            return 2  # 中等下跌
    
    def _calc_volume_score(self, ticker: Dict) -> float:
        """成交量分數 (0-5)"""
        if not ticker:
            return 2.5
        
        volume = ticker.get("quote_volume", 0)
        
        # 這裡需要與歷史平均對比
        # 簡化：高成交量通常是趨勢確認
        if volume > 1000000000:  # > 10 億 USDT
            return 4
        elif volume > 100000000:  # > 1 億
            return 3
        elif volume > 10000000:  # > 1000 萬
            return 2
        else:
            return 1
    
    def _calc_fear_greed_score(self) -> float:
        """
        恐懼/貪婪指數分數 (0-5)
        實際應該對接 Alternative.me API
        """
        # 估算值（需要真實 API）
        # 這裡返回中性值
        fear_greed = 50  # 預設中性
        
        if fear_greed < 20:
            return 5  # 極度恐�ф = 買入機會
        elif fear_greed < 40:
            return 4
        elif fear_greed < 60:
            return 3
        elif fear_greed < 80:
            return 2
        else:
            return 1  # 極度貪婪
    
    def _calc_social_score(self, symbol: str) -> float:
        """
        社群活躍度分數 (0-5)
        實際應該對接 Twitter/Discord/Telegram API
        """
        # 估算值
        # 高社群活躍度可能是雙面刃
        return 3  # 預設中性
    
    def _generate_signals(self, funding, price_change, volume, fear_greed) -> List[str]:
        """生成情緒信號"""
        signals = []
        
        if funding <= 2:
            signals.append("HIGH_FUNDING_RATE")
        
        if price_change >= 4:
            signals.append("STRONG_PRICE_UP")
        elif price_change <= 2:
            signals.append("PRICE_WEAK")
        
        if fear_greed <= 2:
            signals.append("EXTREME_GREED")
        elif fear_greed >= 4:
            signals.append("EXTREME_FEAR")
        
        return signals


# ============================================================
# WSS 綜合指標
# ============================================================

class WSSIndicator:
    """
    WSS - Wholesale Whale Sentiment & Strength
    加密貨幣綜合評估指標
    """
    
    def __init__(self):
        self.fundamentals = FundamentalsAnalyzer()
        self.onchain = OnChainAnalyzer()
        self.technical = TechnicalAnalyzer()
        self.sentiment = SentimentAnalyzer()
    
    def analyze(self, symbol: str, data_source=None) -> Dict:
        """
        完整分析
        
        Args:
            symbol: 交易對，如 "BTCUSDT"
            data_source: 數據源，如果為 None 則創建新的
        
        Returns:
            {
                "symbol": str,
                "wss_score": 0-100,
                "verdict": "STRONG_BUY" | "BUY" | "NEUTRAL" | "SELL" | "STRONG_SELL",
                "dimensions": {
                    "fundamentals": {...},
                    "onchain": {...},
                    "technical": {...},
                    "sentiment": {...}
                },
                "all_signals": [...],
                "summary": str
            }
        """
        if not data_source:
            from signal_analyzer.crypto_data import BinanceDataSource
            data_source = BinanceDataSource()
        
        # 維度分析
        fund_result = self.fundamentals.analyze(symbol)
        onchain_result = self.onchain.analyze(symbol)
        tech_result = self.technical.analyze(symbol, data_source)
        sentiment_result = self.sentiment.analyze(symbol)
        
        # 總分 (0-100)
        total = (
            fund_result["total"] +
            onchain_result["total"] +
            tech_result["total"] +
            sentiment_result["total"]
        )
        
        # 維度權重
        weights = {
            "fundamentals": 0.20,  # 基本面 20%
            "onchain": 0.25,       # 鏈上 25%
            "technical": 0.30,     # 技術 30%
            "sentiment": 0.25      # 情緒 25%
        }
        
        weighted_total = (
            fund_result["total"] * weights["fundamentals"] +
            onchain_result["total"] * weights["onchain"] +
            tech_result["total"] * weights["technical"] +
            sentiment_result["total"] * weights["sentiment"]
        ) * 4  # 放大到 100
        
        # 判斷
        verdict = self._get_verdict(weighted_total, tech_result, sentiment_result)
        
        # 收集所有信號
        all_signals = []
        all_signals.extend(fund_result.get("signals", []))
        all_signals.extend(onchain_result.get("signals", []))
        all_signals.extend(tech_result.get("signals", []))
        all_signals.extend(sentiment_result.get("signals", []))
        
        return {
            "symbol": symbol,
            "wss_score": round(weighted_total, 1),
            "verdict": verdict,
            "dimensions": {
                "fundamentals": fund_result,
                "onchain": onchain_result,
                "technical": tech_result,
                "sentiment": sentiment_result
            },
            "all_signals": all_signals,
            "weights": weights,
            "summary": self._generate_summary(weighted_total, verdict, all_signals)
        }
    
    def _get_verdict(self, score: float, tech: Dict, sentiment: Dict) -> str:
        """根據分數和信號生成判斷"""
        signals = tech.get("signals", []) + sentiment.get("signals", [])
        
        # 基本判斷
        if score >= 80:
            if "RSI_OVERBOUGHT" in signals or "HIGH_FUNDING_RATE" in signals:
                return "NEUTRAL"  # 過熱警告
            return "STRONG_BUY"
        elif score >= 65:
            return "BUY"
        elif score >= 45:
            return "NEUTRAL"
        elif score >= 30:
            return "SELL"
        else:
            return "STRONG_SELL"
    
    def _generate_summary(self, score: float, verdict: str, signals: List[str]) -> str:
        """生成摘要文字"""
        verdicts_ch = {
            "STRONG_BUY": "強烈建議買入",
            "BUY": "建議買入",
            "NEUTRAL": "建議觀望",
            "SELL": "建議賣出",
            "STRONG_SELL": "強烈建議賣出"
        }
        
        summary = f"WSS分數: {score:.1f}/100，{verdicts_ch.get(verdict, verdict)}"
        
        # 添加關鍵信號
        key_signals = [s for s in signals if any(k in s for k in ["GOLDEN", "OVERSOLD", "UNDERVALUED", "STRONG"])]
        if key_signals:
            summary += f"\n關鍵信號: {', '.join(key_signals[:3])}"
        
        return summary


# ============================================================
# 快速分析函數
# ============================================================

def quick_analyze(symbol: str) -> Dict:
    """
    快速分析（只用技術指標）
    用於即時決策
    """
    from signal_analyzer.crypto_data import BinanceDataSource
    from signal_analyzer.crypto_indicators import (
        calc_rsi, calc_macd, calc_kd, calc_bollinger, calc_ema
    )
    
    data_source = BinanceDataSource()
    
    # 取得數據
    klines = data_source.get_klines(symbol, "1h", 200)
    ticker = data_source.get_ticker(symbol)
    
    if not klines:
        return {"error": f"No data for {symbol}"}
    
    closes = [k["close"] for k in klines]
    highs = [k["high"] for k in klines]
    lows = [k["low"] for k in klines]
    
    # 計算指標
    rsi = calc_rsi(closes, 14)
    dif, dea, macd_hist = calc_macd(closes, 12, 26, 9)
    k_values, d_values = calc_kd(highs, lows, closes, 9)
    bb_ma, bb_upper, bb_lower = calc_bollinger(closes, 20, 2)
    ema20 = calc_ema(closes, 20)
    
    # 簡單評分
    score = 50
    
    if rsi[-1] and rsi[-1] < 30:
        score += 15
    elif rsi[-1] and rsi[-1] > 70:
        score -= 15
    
    if macd_hist[-1] and macd_hist[-1] > 0:
        score += 10
    else:
        score -= 10
    
    if closes[-1] > ema20[-1]:
        score += 10
    else:
        score -= 10
    
    if k_values[-1] > d_values[-1]:
        score += 5
    else:
        score -= 5
    
    # 決定
    if score >= 80:
        verdict = "STRONG_BUY"
    elif score >= 65:
        verdict = "BUY"
    elif score >= 45:
        verdict = "NEUTRAL"
    elif score >= 30:
        verdict = "SELL"
    else:
        verdict = "STRONG_SELL"
    
    return {
        "symbol": symbol,
        "price": closes[-1],
        "wss_score": score,
        "verdict": verdict,
        "indicators": {
            "RSI": round(rsi[-1], 2) if rsi[-1] else None,
            "KD_K": round(k_values[-1], 2) if k_values[-1] else None,
            "KD_D": round(d_values[-1], 2) if d_values[-1] else None,
            "MACD_Hist": round(macd_hist[-1], 4) if macd_hist[-1] else None,
            "EMA20": round(ema20[-1], 2) if ema20[-1] else None,
            "BB_Position": "OVERSOLD" if closes[-1] < bb_lower[-1] else ("OVERBOUGHT" if closes[-1] > bb_upper[-1] else "NEUTRAL")
        }
    }
