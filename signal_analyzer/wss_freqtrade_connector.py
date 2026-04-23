"""
WSS + Freqtrade 整合器

將 WSS 分析結果轉換為 Freqtrade 交易指令
"""

from typing import Dict, List, Optional
from signal_analyzer.wss_indicator import WSSIndicator, quick_analyze
from signal_analyzer.freqtrade_integration import FreqtradeIntegration, TradeDecision


class WSSFreqtradeConnector:
    """
    WSS 分析結果 → Freqtrade 執行的橋樑
    
    使用流程：
    1. scan_symbols() - 用 WSS 掃描標的
    2. get_trade_decisions() - 取得可交易信号
    3. execute_all() - 執行所有決策
    """
    
    def __init__(self, freqtrade: FreqtradeIntegration = None):
        self.freqtrade = freqtrade or FreqtradeIntegration()
        self.wss = WSSIndicator()
        self.last_decisions: List[TradeDecision] = []
    
    def scan_symbols(self, symbols: List[str], mode: str = "full") -> Dict:
        """
        掃描標的並生成交易信號
        
        Args:
            symbols: 幣種列表
            mode: "quick" (只用技術指標) 或 "full" (完整分析)
        
        Returns:
            {
                "buy_signals": [...],
                "sell_signals": [...],
                "hold_signals": [...],
                "summary": str
            }
        """
        buy_signals = []
        sell_signals = []
        hold_signals = []
        
        for symbol in symbols:
            if mode == "quick":
                result = quick_analyze(symbol)
            else:
                result = self.wss.analyze(symbol)
            
            if "error" in result:
                continue
            
            verdict = result.get("verdict", "NEUTRAL")
            price = result.get("price", 0)
            score = result.get("wss_score", 50)
            
            decision = TradeDecision(
                symbol=symbol,
                action=self._verdict_to_action(verdict),
                price=price,
                confidence=score / 100,
                reason=f"WSS {verdict} (score: {score:.0f})",
                risk_level=self._score_to_risk(score)
            )
            
            if verdict in ["STRONG_BUY", "BUY"]:
                buy_signals.append(decision)
            elif verdict in ["STRONG_SELL", "SELL"]:
                sell_signals.append(decision)
            else:
                hold_signals.append(decision)
        
        self.last_decisions = buy_signals + sell_signals + hold_signals
        
        return {
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "hold_signals": hold_signals,
            "summary": self._format_summary(buy_signals, sell_signals, hold_signals)
        }
    
    def get_trade_decisions(self, min_confidence: float = 0.7) -> List[TradeDecision]:
        """
        取得高信心度的交易決策
        
        Args:
            min_confidence: 最低信心度閾值
        """
        return [
            d for d in self.last_decisions
            if d.action != "HOLD" and d.confidence >= min_confidence
        ]
    
    def execute_all(self, dry_run: bool = None) -> List[Dict]:
        """
        執行所有待處理決策
        
        Args:
            dry_run: 是否只做模擬（None=跟隨freqtrade設定）
        """
        if dry_run is None:
            config = self.freqtrade.get_show_config()
            dry_run = config.get("dry_run", True)
        
        results = []
        for decision in self.last_decisions:
            if decision.action == "HOLD":
                continue
            
            result = self.freqtrade.execute_decision(decision, dry_run=dry_run)
            results.append(result)
        
        return results
    
    def execute_by_verdict(self, verdict: str, min_score: float = 65, dry_run: bool = None) -> List[Dict]:
        """
        只執行特定 verdict 的信號
        
        Args:
            verdict: "BUY", "SELL", "STRONG_BUY", "STRONG_SELL"
            min_score: 最低 WSS 分數
            dry_run: 是否只做模擬
        """
        # 掃描
        symbol_map = {}
        decisions = []
        
        for d in self.last_decisions:
            if d.action == verdict:
                score = d.confidence * 100
                if score >= min_score:
                    decisions.append(d)
        
        if not decisions:
            return [{"message": f"No {verdict} signals with score >= {min_score}"}]
        
        # 執行
        if dry_run is None:
            config = self.freqtrade.get_show_config()
            dry_run = config.get("dry_run", True)
        
        results = []
        for decision in decisions:
            result = self.freqtrade.execute_decision(decision, dry_run=dry_run)
            results.append(result)
        
        return results
    
    def _verdict_to_action(self, verdict: str) -> str:
        """WSS verdict 轉換為交易 action"""
        mapping = {
            "STRONG_BUY": "BUY",
            "BUY": "BUY",
            "NEUTRAL": "HOLD",
            "SELL": "SELL",
            "STRONG_SELL": "SELL"
        }
        return mapping.get(verdict, "HOLD")
    
    def _score_to_risk(self, score: float) -> str:
        """WSS 分數轉換為風險等級"""
        if score >= 80:
            return "LOW"
        elif score >= 60:
            return "MEDIUM"
        else:
            return "HIGH"
    
    def _format_summary(self, buys, sells, holds) -> str:
        """格式化摘要"""
        lines = []
        lines.append("=" * 50)
        lines.append("WSS + Freqtrade 掃描結果")
        lines.append("=" * 50)
        
        if buys:
            lines.append(f"\n📈 買入信號 ({len(buys)}):")
            for d in buys:
                lines.append(f"  ✓ {d.symbol} @ ${d.price:,.2f} (信心:{d.confidence:.0%})")
        else:
            lines.append("\n📈 買入信號: 無")
        
        if sells:
            lines.append(f"\n📉 賣出信號 ({len(sells)}):")
            for d in sells:
                lines.append(f"  ✓ {d.symbol} @ ${d.price:,.2f} (信心:{d.confidence:.0%})")
        else:
            lines.append("\n📉 賣出信號: 無")
        
        if holds:
            lines.append(f"\n⏸️ 觀望 ({len(holds)}):")
            for d in holds[:5]:
                lines.append(f"  - {d.symbol}")
            if len(holds) > 5:
                lines.append(f"  ... 還有 {len(holds)-5} 個")
        
        lines.append("\n" + "=" * 50)
        return "\n".join(lines)


def create_connector() -> WSSFreqtradeConnector:
    """工廠函數：創建連接器"""
    return WSSFreqtradeConnector()
