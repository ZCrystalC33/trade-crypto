"""
LLM Decision Agent - TRADE-Crypto 的大脑

職責：
1. 讀取市場數據（Signal Analyzer）
2. 評估交易機會（使用 LLM）
3. 發送指令給 Freqtrade（Freqtrade Adapter）
4. 持續學習進化
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

from trade_crypto.signal_analyzer.crypto_indicators import CryptoIndicators
from trade_crypto.freqtrade_adapter.adapter import FreqtradeAdapter
from trade_crypto.decision_agent.prompts.decision_prompts import DECISION_PROMPT, SCORING_PROMPT


class DecisionAgent:
    """
    LLM Decision Agent
    
    使用方式：
        agent = DecisionAgent()
        signals = agent.scan_top_symbols(["BTCUSDT", "ETHUSDT"])
        decisions = agent.decide(signals)
        agent.execute(decisions)
    """
    
    def __init__(self):
        self.indicator = CryptoIndicators()
        self.freqtrade = FreqtradeAdapter()
        self.decision_history = []
    
    def scan_symbol(self, symbol: str, interval: str = "15m") -> Dict:
        """分析單一幣種"""
        return self.indicator.analyze(symbol, interval)
    
    def scan_top_symbols(self, symbols: List[str] = None, interval: str = "15m") -> List[Dict]:
        """掃描多個幣種"""
        if symbols is None:
            # 預設 Top 10 by volume
            from trade_crypto.signal_analyzer.crypto_data import BinanceDataSource
            ds = BinanceDataSource()
            tickers = ds.get_ticker("BTCUSDT")  # dummy call to check connection
            symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", 
                      "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT"]
        
        results = []
        for sym in symbols:
            try:
                result = self.scan_symbol(sym, interval)
                results.append(result)
            except Exception as e:
                print(f"Error scanning {sym}: {e}")
        
        # 按分數排序
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results
    
    def decide(self, signals: List[Dict]) -> List[Dict]:
        """
        根據信號做出決策
        
        這個方法使用規則引擎模擬 LLM 決策
        完整版應該呼叫實際的 LLM API
        """
        decisions = []
        
        for signal in signals:
            if "error" in signal:
                continue
            
            # 根據信號評估
            decision = self._evaluate_signal(signal)
            decisions.append(decision)
        
        return decisions
    
    def _evaluate_signal(self, signal: Dict) -> Dict:
        """評估單一信號"""
        score = signal.get("score", 50)
        indicators = signal.get("indicators", {})
        signals = signal.get("signals", [])
        
        # 基本決策邏輯
        decision = "HOLD"
        confidence = 0.5
        reason = []
        
        # 買入條件
        buy_score = 0
        if "KD_GOLDEN" in signals:
            buy_score += 3
            reason.append("KD 黃金交叉")
        if "RSI_OVERSOLD" in signals:
            buy_score += 2
            reason.append("RSI 超賣")
        if "MACD_GOLDEN" in signals:
            buy_score += 2
            reason.append("MACD 黃金交叉")
        
        # 賣出條件
        sell_score = 0
        if "KD_DEAD" in signals:
            sell_score += 3
            reason.append("KD 死亡交叉")
        if "RSI_OVERBOUGHT" in signals:
            sell_score += 2
            reason.append("RSI 超買")
        if "MACD_DEAD" in signals:
            sell_score += 2
            reason.append("MACD 死亡交叉")
        
        # 決定
        if buy_score >= 4:
            decision = "BUY"
            confidence = min(0.9, 0.5 + buy_score * 0.1)
        elif sell_score >= 4:
            decision = "SELL"
            confidence = min(0.9, 0.5 + sell_score * 0.1)
        elif score >= 70:
            decision = "BUY"
            confidence = 0.6
            reason.append("高分評價")
        elif score <= 30:
            decision = "SELL"
            confidence = 0.6
            reason.append("低分警示")
        
        # 停損停利
        price = signal.get("price", 0)
        if decision == "BUY":
            stop_loss = round(price * 0.95, 2)   # 5% 停損
            take_profit = round(price * 1.10, 2)  # 10% 停利
        elif decision == "SELL":
            stop_loss = round(price * 1.05, 2)
            take_profit = round(price * 0.90, 2)
        else:
            stop_loss = None
            take_profit = None
        
        return {
            "symbol": signal["symbol"],
            "price": price,
            "score": score,
            "decision": decision,
            "confidence": confidence,
            "reason": "; ".join(reason) if reason else "無明顯信號",
            "signals": signals,
            "parameters": {
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "position_size": "5%",
                "timeframe": "15m"
            },
            "risk_assessment": "中等風險" if confidence < 0.8 else "信心較高"
        }
    
    def execute(self, decisions: List[Dict]) -> Dict:
        """
        執行決策
        將 Buy 決策的幣種發送到 Freqtrade whitelist
        """
        buy_pairs = [d["symbol"] for d in decisions if d["decision"] == "BUY"]
        
        # 記錄決策歷史
        for d in decisions:
            self.decision_history.append({
                "timestamp": datetime.now().isoformat(),
                "decision": d
            })
        
        if not buy_pairs:
            return {"status": "no_action", "reason": "無買入信號"}
        
        # 更新 Freqtrade whitelist
        result = self.freqtrade.set_whitelist(buy_pairs)
        
        return {
            "status": "executed",
            "pairs": buy_pairs,
            "freqtrade_response": result
        }
    
    def get_status(self) -> Dict:
        """取得當前系統狀態"""
        freqtrade_status = self.freqtrade.get_status()
        open_trades = self.freqtrade.get_open_trades()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "freqtrade": freqtrade_status.get("bot_name", "unknown") if isinstance(freqtrade_status, dict) else "unknown",
            "open_trades_count": len(open_trades) if isinstance(open_trades, list) else 0,
            "open_trades": open_trades[:3] if isinstance(open_trades, list) else [],
            "total_decisions": len(self.decision_history)
        }
    
    def summary(self) -> str:
        """取得人類可讀的狀態摘要"""
        status = self.get_status()
        
        lines = []
        lines.append("=" * 50)
        lines.append("【TRADE-Crypto 系統狀態】")
        lines.append(f"時間：{status['timestamp']}")
        lines.append(f"Freqtrade：{status['freqtrade']}")
        lines.append(f"開倉部位：{status['open_trades_count']}")
        lines.append(f"總決策次數：{status['total_decisions']}")
        lines.append("=" * 50)
        
        if status['open_trades']:
            lines.append("\n目前倉位：")
            for trade in status['open_trades']:
                lines.append(f"  {trade.get('pair', 'unknown')}: {trade.get('profit_abs', 'N/A')}")
        
        return "\n".join(lines)


def run_demo():
    """演示 Decision Agent 的完整流程"""
    print("=== TRADE-Crypto Decision Agent Demo ===\n")
    
    # 1. 初始化
    agent = DecisionAgent()
    
    # 2. 掃描市場
    print("1. 掃描市場...")
    signals = agent.scan_top_symbols(["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"])
    
    print(f"\n發現 {len(signals)} 個信號：")
    for s in signals[:5]:
        if "error" not in s:
            print(f"  {s['symbol']}: score={s['score']}, signals={s['signals']}")
    
    # 3. 做決策
    print("\n2. 評估決策...")
    decisions = agent.decide(signals)
    
    for d in decisions:
        if d["decision"] != "HOLD":
            print(f"  {d['decision']} {d['symbol']} @ {d['price']} (信心:{d['confidence']:.0%})")
            print(f"    原因：{d['reason']}")
    
    # 4. 執行
    print("\n3. 發送指令到 Freqtrade...")
    result = agent.execute(decisions)
    print(f"  結果：{result}")
    
    # 5. 顯示狀態
    print("\n4. 系統狀態：")
    print(agent.summary())
    
    return agent, signals, decisions, result


if __name__ == "__main__":
    run_demo()