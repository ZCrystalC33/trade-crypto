"""
Layer 2 AI Decision Module - AI 裁決引擎

使用 MiniMax API 進行智能決策
"""

import re
import os
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


class APIKeyLoadError(Exception):
    """API Key 載入失敗"""
    pass


class MiniMaxAPIError(Exception):
    """MiniMax API 錯誤"""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"MiniMax API Error {status_code}: {message}")


class AIResponseParseError(Exception):
    """AI 回應解析錯誤"""
    pass


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
        """轉換為簡潔 Prompt"""
        tech_parts = []
        for name, ind in self.indicators.items():
            if isinstance(ind, dict):
                val = ind.get("value", ind.get("signal", "N/A"))
                sig = ind.get("signal", "")
            else:
                val = ind
                sig = ""
            tech_parts.append(f"{name}={val}({sig})")
        tech_text = ", ".join(tech_parts) if tech_parts else "無"
        
        sent_parts = []
        if self.sentiment.get("ticker"):
            t = self.sentiment["ticker"]
            sent_parts.append(f"24h{float(t.get('price_change_pct',0)):.1f}%")
            sent_parts.append(f"量${float(t.get('quote_volume',0))/1e9:.1f}B")
        if self.sentiment.get("funding_rate") is not None:
            fr = self.sentiment["funding_rate"]
            sent_parts.append(f"資金费{fr*100:.3f}%")
        if self.sentiment.get("orderbook_imbalance") is not None:
            imb = self.sentiment["orderbook_imbalance"]
            sent_parts.append(f"掛單{'多' if imb>0 else '空'}{abs(imb)*100:.0f}%")
        sent_text = ", ".join(sent_parts) if sent_parts else "無"
        
        return (f"幣種：{self.symbol} | 現價：${self.price:,.2f} | "
                f"Layer1：{self.layer1_decision} 信心{self.layer1_confidence*100:.0f}% "
                f"[{','.join(self.layer1_signals) if self.layer1_signals else '無'}] | "
                f"指標：{tech_text} | 情緒：{sent_text}\n\n"
                f"直接給出結論：決策(BUY/SELL/HOLD)、原因、信心(高/中/低)、"
                f"風險(高/中/低)、停損價、停利價。\n"
                f"格式：「決策：X | 原因：... | 信心：高 | 風險：中 | 停損：X | 停利：X」")


class MiniMaxClient:
    """MiniMax API 客戶端"""
    
    def __init__(self, api_key: str = None):
        if api_key is None:
            key_path = os.path.expanduser("~/.openclaw/credentials/minimax.key")
            try:
                with open(key_path) as f:
                    api_key = f.read().strip()
                
                # 檢查檔案權限
                stat = os.stat(key_path)
                mode = stat.st_mode & 0o777
                if mode & 0o077:  # 群組或其他人有讀寫權限
                    print(f"Warning: {key_path} has insecure permissions {oct(mode)}")
            except FileNotFoundError:
                raise APIKeyLoadError(f"Key file not found: {key_path}")
            except PermissionError:
                raise APIKeyLoadError(f"Permission denied: {key_path}")
            except OSError as e:
                raise APIKeyLoadError(f"Failed to read key: {e}")
        
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
            "max_tokens": 600
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
                raise MiniMaxAPIError(resp.status_code, resp.text)
        except requests.Timeout:
            raise MiniMaxAPIError(408, "Request timeout")
        except requests.ConnectionError as e:
            raise MiniMaxAPIError(0, f"Connection error: {e}")
        except MiniMaxAPIError:
            raise
        except Exception as e:
            raise MiniMaxAPIError(0, f"Unexpected error: {e}")


def parse_structured_response(response: str) -> Optional[Dict]:
    """嘗試解析結構化回應格式「決策：X | 原因：...」"""
    if not response:
        return None
    
    try:
        result = {
            "action": "HOLD",
            "confidence": 0.5,
            "reason": "",
            "risk_level": "MEDIUM",
            "stop_loss": None,
            "take_profit": None
        }
        
        # 解析結構化格式
        if "決策：" in response:
            match = re.search(r'決策[：:]\s*(BUY|SELL|HOLD)', response.upper())
            if match:
                result["action"] = match.group(1)
        
        if "原因：" in response or "原因:" in response:
            match = re.search(r'原因[：:]\s*(.+?)(?=\||\n|$)', response)
            if match:
                result["reason"] = match.group(1).strip()[:200]
        
        # 解析信心
        if "信心" in response:
            if any(c in response for c in ["信心：高", "信心：高", "信心高"]):
                result["confidence"] = 0.8
            elif any(c in response for c in ["信心：中", "信心：中", "信心中"]):
                result["confidence"] = 0.6
            elif any(c in response for c in ["信心：低", "信心：低", "信心低"]):
                result["confidence"] = 0.4
        
        # 解析風險
        if "風險" in response:
            if any(c in response for c in ["風險：低", "風險：低", "風險低", "risk=LOW"]):
                result["risk_level"] = "LOW"
            elif any(c in response for c in ["風險：高", "風險：高", "風險高", "risk=HIGH"]):
                result["risk_level"] = "HIGH"
        
        # 解析停損停利
        sl_match = re.search(r'停損[：:]\s*(\d+[\d,]*)', response)
        if sl_match:
            result["stop_loss"] = float(sl_match.group(1).replace(',', ''))
        
        tp_match = re.search(r'停利[：:]\s*(\d+[\d,]*)', response)
        if tp_match:
            result["take_profit"] = float(tp_match.group(1).replace(',', ''))
        
        return result
    except (re.error, ValueError, TypeError) as e:
        raise AIResponseParseError(f"Failed to parse response: {e}")


def parse_fallback_response(response: str) -> Dict:
    """備用解析：簡單搜索關鍵詞"""
    if not response:
        return {
            "action": "HOLD",
            "confidence": 0.5,
            "reason": "Empty response",
            "risk_level": "MEDIUM",
            "stop_loss": None,
            "take_profit": None
        }
    
    result = {
        "action": "HOLD",
        "confidence": 0.5,
        "reason": response[:200],
        "risk_level": "MEDIUM",
        "stop_loss": None,
        "take_profit": None
    }
    
    # 找 BUY/SELL/HOLD
    action_match = re.search(r'\b(BUY|SELL|HOLD)\b', response.upper())
    if action_match:
        result["action"] = action_match.group(1)
    
    # 簡單信心估計
    if any(c in response for c in ["很確定", "沒問題", "高信心"]):
        result["confidence"] = 0.8
    elif any(c in response for c in ["不太確定", "觀望", "低信心"]):
        result["confidence"] = 0.4
    
    # 簡單風險估計
    if "風險高" in response or "危險" in response:
        result["risk_level"] = "HIGH"
    elif "風險低" in response or "安全" in response:
        result["risk_level"] = "LOW"
    
    return result


class Layer2AIDecider:
    """Layer 2 AI 裁決引擎"""
    
    def __init__(self, api_key: str = None):
        self.minimax = MiniMaxClient(api_key)
        self.decision_history: List[Dict] = []
    
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
        """調用 AI"""
        prompt = request.to_prompt()
        
        messages = [
            {"role": "system", "content": "你是一個專業的加密貨幣交易分析師。直接給出結論，不要長篇分析。"},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.minimax.chat(messages)
        except MiniMaxAPIError as e:
            print(f"MiniMax API Error: {e}")
            return None
        
        if not response:
            return None
        
        # 解析回應
        try:
            result = parse_structured_response(response)
            if result:
                return result
        except AIResponseParseError:
            pass
        
        return parse_fallback_response(response)


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
            key_path = os.path.expanduser("~/.openclaw/credentials/binance.key")
            try:
                with open(key_path) as f:
                    lines = f.readlines()
                    for line in lines:
                        if "BINANCE_API_KEY=" in line:
                            binance_api_key = line.split("=")[1].strip()
                        elif "BINANCE_API_SECRET=" in line:
                            binance_secret = line.split("=")[1].strip()
            except FileNotFoundError:
                print(f"Warning: {key_path} not found, Binance API disabled")
            except PermissionError:
                print(f"Warning: Permission denied: {key_path}")
            except OSError as e:
                print(f"Warning: Failed to read {key_path}: {e}")
        
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
                lines.append(f"    AI 原因: {c.final_reason[:100]}")
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
