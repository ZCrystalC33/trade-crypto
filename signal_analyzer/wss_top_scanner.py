"""
WSS Top Crypto Scanner - 市場前30幣種掃描器

功能：
1. 從 Binance 獲取成交量前30名的幣種
2. 對每個幣種計算 WSS 分數
3. 只對前10名進行完整分析
"""

import time
from typing import Dict, List
from signal_analyzer.binance_provider import BinanceProvider
from signal_analyzer.wss_indicator import WSSIndicator
from signal_analyzer.crypto_indicators import CryptoIndicators


class WSSTopCryptoScanner:
    """
    WSS 市場龍頭幣種掃描器
    
    使用流程：
    1. scan_top_symbols() - 掃描市場前30名
    2. get_top10() - 取得前10名分析
    3. execute_trades() - 執行交易
    """
    
    def __init__(self):
        self.binance = BinanceProvider()
        self.wss = WSSIndicator()
        self.indicators = CryptoIndicators()
        self.results: Dict[str, Dict] = {}
    
    def scan_top_symbols(self, limit: int = 30, interval: str = "1h") -> Dict:
        """
        掃描市場成交量前 N 名的幣種
        
        Args:
            limit: 掃描多少名（預設30）
            interval: K線週期
        
        Returns:
            {
                "all_symbols": [...],  # 所有掃描的幣種
                "ranked": [...],        # 按WSS分數排序
                "top10": [...],         # 前10名詳細分析
                "summary": str
            }
        """
        print(f"📊 獲取市場前 {limit} 名幣種...")
        
        # 1. 獲取 Binance 成交量排行
        try:
            top_symbols = self.binance.get_top_symbols(limit=limit)
        except:
            # Fallback 列表
            top_symbols = [
                "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
                "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
                "MATICUSDT", "LTCUSDT", "SHIBUSDT", "TRXUSDT", "ATOMUSDT",
                "UNIUSDT", "ETCUSDT", "XLMUSDT", "BCHUSDT", "APTUSDT",
                "NEARUSDT", "FILUSDT", "ARBUSDT", "LDOUSDT", "CROUSDT",
                "VETUSDT", "ALGOUSDT", "FTMUSDT", "SANDUSDT", "MANAUSDT"
            ][:limit]
        
        print(f"✅ 獲取到 {len(top_symbols)} 個幣種")
        
        # 2. 對每個幣種計算 WSS 分數（快速評估）
        print(f"🔍 快速評估 {len(top_symbols)} 個幣種...")
        quick_scores = []
        
        for i, symbol in enumerate(top_symbols):
            if (i + 1) % 10 == 0:
                print(f"  進度: {i+1}/{len(top_symbols)}")
            
            try:
                # 使用 WSS 快速分析
                wss_result = self.wss.analyze(symbol)
                
                if "error" not in wss_result:
                    quick_scores.append({
                        "symbol": symbol,
                        "wss_score": wss_result.get("wss_score", 50),
                        "verdict": wss_result.get("verdict", "NEUTRAL"),
                        "price": wss_result.get("price", 0),
                        "change_24h": wss_result.get("change_24h", 0)
                    })
                else:
                    # 降級到簡單技術指標
                    ind_result = self.indicators.analyze(symbol, interval=interval, limit=100)
                    if "error" not in ind_result:
                        quick_scores.append({
                            "symbol": symbol,
                            "wss_score": ind_result.get("score", 50),
                            "verdict": self._score_to_verdict(ind_result.get("score", 50)),
                            "price": ind_result.get("price", 0),
                            "change_24h": ind_result.get("change_24h", 0)
                        })
            except Exception as e:
                print(f"  ⚠️ {symbol}: {e}")
        
        # 3. 按 WSS 分數排序
        ranked = sorted(quick_scores, key=lambda x: x["wss_score"], reverse=True)
        
        # 4. 對前10名進行完整分析
        print(f"📝 對前10名進行完整分析...")
        top10_detailed = []
        
        for i, item in enumerate(ranked[:10]):
            symbol = item["symbol"]
            print(f"  [{i+1}] {symbol}...")
            
            try:
                # 完整 WSS 分析
                detailed = self.wss.analyze(symbol)
                
                if "error" not in detailed:
                    top10_detailed.append({
                        "rank": i + 1,
                        "symbol": symbol,
                        "wss_score": detailed.get("wss_score", 50),
                        "verdict": detailed.get("verdict", "NEUTRAL"),
                        "price": detailed.get("price", 0),
                        "change_24h": detailed.get("change_24h", 0),
                        "signals": detailed.get("signals", []),
                        "indicators": detailed.get("indicators", {}),
                        "dimensions": detailed.get("dimensions", {})
                    })
                else:
                    # 降級
                    top10_detailed.append({
                        "rank": i + 1,
                        "symbol": symbol,
                        **item
                    })
                
                time.sleep(0.5)  # 避免API限制
                
            except Exception as e:
                print(f"  ⚠️ {symbol} 詳細分析失敗: {e}")
                top10_detailed.append({"rank": i + 1, "symbol": symbol, **item})
        
        # 存儲結果
        self.results = {
            "all": quick_scores,
            "ranked": ranked,
            "top10": top10_detailed
        }
        
        return self.results
    
    def get_top10(self) -> List[Dict]:
        """取得前10名分析結果"""
        return self.results.get("top10", [])
    
    def get_buy_signals(self) -> List[Dict]:
        """取得買入信號（前10名中）"""
        top10 = self.get_top10()
        return [d for d in top10 if d.get("verdict") in ["STRONG_BUY", "BUY"]]
    
    def get_sell_signals(self) -> List[Dict]:
        """取得賣出信號（前10名中）"""
        top10 = self.get_top10()
        return [d for d in top10 if d.get("verdict") in ["STRONG_SELL", "SELL"]]
    
    def summary(self) -> str:
        """生成摘要報告"""
        if not self.results:
            return "尚無掃描結果"
        
        ranked = self.results.get("ranked", [])
        top10 = self.results.get("top10", [])
        
        lines = []
        lines.append("=" * 60)
        lines.append("【WSS 市場龍頭掃描報告】")
        lines.append("=" * 60)
        
        # 買入信號
        buys = self.get_buy_signals()
        lines.append(f"\n📈 買入信號 ({len(buys)}):")
        if buys:
            for d in buys:
                lines.append(f"  ✓ #{d['rank']} {d['symbol']} "
                           f"@{d.get('price', 0):,.2f} "
                           f"(WSS: {d.get('wss_score', 0):.0f})")
        else:
            lines.append("  無")
        
        # 賣出信號
        sells = self.get_sell_signals()
        lines.append(f"\n📉 賣出信號 ({len(sells)}):")
        if sells:
            for d in sells:
                lines.append(f"  ✓ #{d['rank']} {d['symbol']} "
                           f"@{d.get('price', 0):,.2f} "
                           f"(WSS: {d.get('wss_score', 0):.0f})")
        else:
            lines.append("  無")
        
        # 前10名總覽
        lines.append(f"\n🏆 前10名 WSS 分數:")
        for d in top10:
            verdict_icon = {
                "STRONG_BUY": "🟢🟢",
                "BUY": "🟢",
                "NEUTRAL": "🟡",
                "SELL": "🔴",
                "STRONG_SELL": "🔴🔴"
            }.get(d.get("verdict", ""), "⚪")
            
            lines.append(f"  {verdict_icon} #{d['rank']:2d} {d['symbol']:10s} "
                        f"WSS:{d.get('wss_score', 0):3.0f} "
                        f"24h:{d.get('change_24h', 0):+.1f}%")
        
        lines.append("\n" + "=" * 60)
        return "\n".join(lines)
    
    def _score_to_verdict(self, score: float) -> str:
        """分數轉 verdict"""
        if score >= 80:
            return "STRONG_BUY"
        elif score >= 65:
            return "BUY"
        elif score >= 45:
            return "NEUTRAL"
        elif score >= 30:
            return "SELL"
        else:
            return "STRONG_SELL"


def create_scanner() -> WSSTopCryptoScanner:
    """工廠函數"""
    return WSSTopCryptoScanner()
