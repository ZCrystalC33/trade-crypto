"""
Layer 2 AI Decision Module - AI 裁決引擎

使用 MiniMax API 進行智能決策
"""

import json
import re
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AIDecisionRequest:
    """AI 決策請求"""
    symbol: str
    price: float
    
    # Layer 1 結果
    layer1_decision: str
    layer1_confidence: float
    layer1_score: float
    layer1_signals: List[str]
    
    # 技術指標
    indicators: Dict
    
    # 市場情緒
    sentiment: Dict
    
    # 額外上下文
    context: Dict
    
    def to_prompt(self) -> str:
        """轉換為自然語言 Prompt"""
        
        # 格式化技術指標
        tech_lines = []
        for name, ind in self.indicators.items():
            if isinstance(ind, dict):
                val = ind.get("value", ind.get("signal", "N/A"))
                sig = ind.get("signal", "")
            else:
                val = ind
                sig = ""
            tech_lines.append(f"- {name}: {val} ({sig})")
        tech_text = "\n".join(tech_lines) if tech_lines else "無數據"
        
        # 格式化情緒
        sent_lines = []
        if self.sentiment.get("ticker"):
            t = self.sentiment["ticker"]
            sent_lines.append(f"- 24h 價格變化: {t.get('price_change_pct', 0):.2f}%")
            sent_lines.append(f"- 24h 成交量: ${t.get('quote_volume', 0):,.0f}")
        if self.sentiment.get("funding_rate") is not None:
            fr = self.sentiment["funding_rate"]
            sent_lines.append(f"- 資金费率: {fr*100:.4f}%")
        if self.sentiment.get("orderbook_imbalance") is not None:
            imb = self.sentiment["orderbook_imbalance"]
            bias = "偏多" if imb > 0 else "偏空"
            sent_lines.append(f"- 掛單失衡: {abs(imb)*100:.1f}% {bias}")
        sent_text = "\n".join(sent_lines) if sent_lines else "無數據"
        
        prompt = f"""分析這個加密貨幣交易情境並給出決策：

幣種: {self.symbol}
現價: ${self.price:,.2f}

Layer 1 分析結果：
- 初步決策: {self.layer1_decision}
- 信心程度: {self.layer1_confidence*100:.0f}%
- 分數: {self.layer1_score:.1f}/100
- 觸發信號: {', '.join(self.layer1_signals) if self.layer1_signals else '無'}

技術指標：
{tech_text}

市場情緒：
{sent_text}

請用繁體中文回答：
1. 你的交易決策是什麼？（BUY、SELL 或 HOLD）
2. 為什麼？
3. 信心程度（高、中、低）
4. 風險等級（高、中、低）
5. 建議停損價位（可選）
6. 建議停利價位（可選）
"""
        return prompt


class MiniMaxClient:
    """MiniMax API 客戶端"""
    
    def __init__(self, api_key: str = None):
        if api_key is None:
            try:
                with open("/home/snow/.openclaw/credentials/minimax.key") as f:
                    api_key = f.read().strip()
            except:
                pass
        
        self.api_key = api_key
        self.base_url = "https://api.minimax.io/v1"
    
    def chat(self, messages: List[Dict], model: str = "MiniMax-M2.7") -> Optional[str]:
        """發送聊天請求"""
        if not self.api_key:
            return None
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 1000
        }
        
        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if resp.status_code == 200:
                data = resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content")
            else:
                print(f"MiniMax API Error: {resp.status_code} - {resp.text}")
                return None
        except Exception as e:
            print(f"MiniMax API Error: {e}")
            return None


class Layer2AIDecider:
    """Layer 2 AI 裁決引擎"""
    
    def __init__(self, api_key: str = None):
        self.minimax = MiniMaxClient(api_key)
        self.decision_history = []
    
    def decide(self, candidates: List, binance_provider = None) -> List:
        """對矛盾候選做 AI 裁決"""
        results = []
        
        for candidate in candidates:
            sentiment = {}
            if binance_provider:
                sentiment = binance_provider.get_market_sentiment(candidate.symbol)
            
            request = AIDecisionRequest(
                symbol=candidate.symbol,
                price=candidate.price,
                layer1_decision=candidate.layer1_decision,
                layer1_confidence=candidate.layer1_confidence,
                layer1_score=candidate.layer1_score,
                layer1_signals=candidate.layer1_signals,
                indicators={
                    name: {"value": ind.value, "signal": ind.signal}
                    for name, ind in candidate.indicators.items()
                },
                sentiment=sentiment,
                context={}
            )
            
            decision = self._call_ai(request)
            
            if decision:
                candidate.final_decision = decision.get("action", "HOLD")
                candidate.final_confidence = decision.get("confidence", 0.5)
                candidate.final_reason = decision.get("reason", "AI 分析")
                candidate.risk_level = decision.get("risk_level", "MEDIUM")
                candidate.entry_price = decision.get("entry_price")
                candidate.stop_loss = decision.get("stop_loss")
                candidate.take_profit = decision.get("take_profit")
            else:
                candidate.final_decision = "HOLD"
                candidate.final_confidence = 0.3
                candidate.final_reason = "AI 不可用，默認觀望"
                candidate.risk_level = "MEDIUM"
            
            results.append(candidate)
            
            self.decision_history.append({
                "timestamp": datetime.now().isoformat(),
                "symbol": candidate.symbol,
                "decision": decision
            })
        
        return results
    
    def _call_ai(self, request: AIDecisionRequest) -> Optional[Dict]:
        """調用 AI - 從自然語言回應中提取決策"""
        prompt = request.to_prompt()
        
        messages = [
            {"role": "system", "content": "你是一個專業的加密貨幣交易分析師。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.minimax.chat(messages)
        
        if not response:
            return None
        
        # 從回應中提取決策
        try:
            # 找 BUY/SELL/HOLD
            action_match = re.search(r'(BUY|SELL|HOLD)', response.upper())
            action = action_match.group(1) if action_match else "HOLD"
            
            # 估計信心程度
            confidence = 0.5
            if "信心" in response:
                if any(c in response for c in ["信心程度 高", "信心: 高", "信心高"]):
                    confidence = 0.8
                elif any(c in response for c in ["信心程度 中", "信心: 中", "信心中"]):
                    confidence = 0.6
                elif any(c in response for c in ["信心程度 低", "信心: 低", "信心低"]):
                    confidence = 0.4
            
            # 估計風險等級
            risk_level = "MEDIUM"
            if "風險" in response:
                if any(c in response for c in ["風險 低", "風險: 低", "風險低", "LOW"]):
                    risk_level = "LOW"
                elif any(c in response for c in ["風險 高", "風險: 高", "風險高", "HIGH"]):
                    risk_level = "HIGH"
            
            # 嘗試找停損/停利
            stop_loss = None
            take_profit = None
            
            sl_match = re.search(r'停損.*?(\d+[\d,]*)', response)
            if sl_match:
                stop_loss = float(sl_match.group(1).replace(',', ''))
            
            tp_match = re.search(r'停利.*?(\d+[\d,]*)', response)
            if tp_match:
                take_profit = float(tp_match.group(1).replace(',', ''))
            
            return {
                "action": action,
                "confidence": confidence,
                "reason": response[:500],
                "risk_level": risk_level,
                "stop_loss": stop_loss,
                "take_profit": take_profit
            }
            
        except Exception as e:
            print(f"Parse Error: {e}")
            print(f"Response: {response[:300]}")
            return None


# ============================================================
# 整合版雙層系統
# ============================================================

class DualLayerTradingSystem:
    """
    整合版雙層交易系統
    
    使用方式：
        system = DualLayerTradingSystem()
        system.scan_and_decide(["BTCUSDT", "ETHUSDT"])
    """
    
    def __init__(self, binance_api_key: str = None, binance_secret: str = None):
        if binance_api_key is None:
            try:
                with open("/home/snow/.openclaw/credentials/binance.key") as f:
                    lines = f.readlines()
                    for line in lines:
                        if "BINANCE_API_KEY=" in line:
                            binance_api_key = line.split("=")[1].strip()
                        elif "BINANCE_API_SECRET=" in line:
                            binance_secret = line.split("=")[1].strip()
            except:
                pass
        
        self.binance = None
        if binance_api_key:
            from signal_analyzer.binance_provider import BinanceProvider
            self.binance = BinanceProvider(binance_api_key, binance_secret)
        
        from signal_analyzer.dual_layer_decision import DualLayerDecisionSystem, RuleConfig
        self.dual_layer = DualLayerDecisionSystem(RuleConfig())
        
        from signal_analyzer.layer2_ai import Layer2AIDecider
        self.layer2 = Layer2AIDecider()
        
        self.last_results: List = []
    
    def scan_and_decide(self, symbols: List[str]) -> Dict:
        """掃描並做決策"""
        scan_result = self.dual_layer.scan(symbols, self.binance)
        
        results = {
            "buys": scan_result.confident_buys,
            "sells": scan_result.confident_sells,
            "holds": scan_result.confident_holds,
            "ai_candidates": scan_result.ai_candidates,
            "needs_ai": scan_result.needs_ai_decision,
            "timestamp": scan_result.timestamp
        }
        
        if scan_result.needs_ai_decision and self.binance:
            ai_results = self.layer2.decide(scan_result.ai_candidates, self.binance)
            results["ai_decisions"] = ai_results
            results["ai_candidates"] = ai_results
        else:
            results["ai_decisions"] = []
        
        self.last_results = results
        return results
    
    def get_buy_decisions(self) -> List:
        """取得所有買入決策"""
        if not self.last_results:
            return []
        
        buys = list(self.last_results.get("buys", []))
        for c in self.last_results.get("ai_decisions", []):
            if c.final_decision == "BUY":
                buys.append(c)
        return buys
    
    def get_sell_decisions(self) -> List:
        """取得所有賣出決策"""
        if not self.last_results:
            return []
        
        sells = list(self.last_results.get("sells", []))
        for c in self.last_results.get("ai_decisions", []):
            if c.final_decision == "SELL":
                sells.append(c)
        return sells
    
    def summary(self) -> str:
        """人類可讀摘要"""
        if not self.last_results:
            return "尚無掃描結果"
        
        lines = []
        lines.append("=" * 60)
        lines.append("【雙層交易系統 - 掃描結果】")
        lines.append(f"時間：{self.last_results['timestamp']}")
        lines.append("=" * 60)
        
        buys = self.last_results.get("buys", [])
        lines.append(f"\n📈 自信買入 ({len(buys)}):")
        if buys:
            for c in buys:
                lines.append(f"  ✓ {c.symbol} @ ${c.price:,.2f} (信心:{c.layer1_confidence:.0%})")
        else:
            lines.append("  無")
        
        sells = self.last_results.get("sells", [])
        lines.append(f"\n📉 自信賣出 ({len(sells)}):")
        if sells:
            for c in sells:
                lines.append(f"  ✓ {c.symbol} @ ${c.price:,.2f} (信心:{c.layer1_confidence:.0%})")
        else:
            lines.append("  無")
        
        ai_decs = self.last_results.get("ai_decisions", [])
        lines.append(f"\n🤖 AI 裁決 ({len(ai_decs)}):")
        if ai_decs:
            for c in ai_decs:
                lines.append(f"  【{c.final_decision}】{c.symbol} @ ${c.price:,.2f}")
                lines.append(f"    AI 原因: {c.final_reason[:150]}...")
                lines.append(f"    信心: {c.final_confidence:.0%} | 風險: {getattr(c, 'risk_level', 'MEDIUM')}")
                if hasattr(c, 'stop_loss') and c.stop_loss and c.take_profit:
                    lines.append(f"    停損: ${c.stop_loss:,.2f} | 停利: ${c.take_profit:,.2f}")
        else:
            lines.append("  無需 AI 裁決")
        
        holds = self.last_results.get("holds", [])
        lines.append(f"\n⏸️ 觀望 ({len(holds)}):")
        if holds:
            for c in holds[:5]:
                lines.append(f"  - {c.symbol}")
            if len(holds) > 5:
                lines.append(f"  ... 還有 {len(holds)-5} 個")
        
        lines.append("\n" + "=" * 60)
        return "\n".join(lines)


def run_trading_system(symbols: List[str] = None) -> DualLayerTradingSystem:
    """快速運行交易系統"""
    if symbols is None:
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
    
    system = DualLayerTradingSystem()
    system.scan_and_decide(symbols)
    
    return system
