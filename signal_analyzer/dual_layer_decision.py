"""
雙層決策系統 (Dual-Layer Decision System)

Layer 1: 規則引擎 → 候選名單
Layer 2: AI 裁決 → 最終決策

使用方式：
    system = DualLayerDecisionSystem()
    
    # 掃描
    candidates = system.layer1_scan(["BTCUSDT", "ETHUSDT"])
    
    # AI 裁決（僅針對矛盾候選）
    if candidates.needs_ai_decision:
        final_decisions = system.layer2_ai_decide(candidates)
    else:
        final_decisions = candidates.confident_decisions
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


# ============================================================
# Layer 1: 規則引擎配置
# ============================================================

@dataclass
class RuleConfig:
    """規則配置"""
    # RSI 規則
    rsi_oversold: float = 35      # RSI 低於此值 = 超賣（考慮買入）
    rsi_overbought: float = 70     # RSI 高於此值 = 超買（考慮賣出）
    
    # 成交量規則
    volume_multiplier: float = 1.5  # 成交量超過此倍數 = 確認信號
    
    # 趨勢規則
    ema_trend_enabled: bool = True  # 是否啟用 EMA 趨勢過濾
    
    # 信心閾值
    confidence_threshold: float = 0.6  # 信心高於此值 = 自信決策


@dataclass
class IndicatorSignal:
    """單一指標信號"""
    name: str
    value: float
    signal: str  # "BUY", "SELL", "NEUTRAL"
    weight: float = 1.0
    confidence: float = 0.5


@dataclass
class SymbolAnalysis:
    """單一幣種分析結果"""
    symbol: str
    price: float
    indicators: Dict[str, IndicatorSignal] = field(default_factory=dict)
    
    # Layer 1 結果
    layer1_decision: str = "HOLD"  # "BUY", "SELL", "HOLD"
    layer1_confidence: float = 0.0
    layer1_score: float = 50.0      # 0-100
    layer1_signals: List[str] = field(default_factory=list)
    
    # Layer 2 需要？
    needs_ai: bool = False
    ai_reason: str = ""
    
    # 最終決策
    final_decision: str = "HOLD"
    final_confidence: float = 0.0
    final_reason: str = ""


@dataclass
class ScanResult:
    """掃描結果"""
    candidates: List[SymbolAnalysis] = field(default_factory=list)
    
    # 自信決策（Layer 1 就能確定）
    confident_buys: List[SymbolAnalysis] = field(default_factory=list)
    confident_sells: List[SymbolAnalysis] = field(default_factory=list)
    confident_holds: List[SymbolAnalysis] = field(default_factory=list)
    
    # 需要 AI 裁決
    needs_ai_decision: bool = False
    ai_candidates: List[SymbolAnalysis] = field(default_factory=list)
    
    # 時間戳
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class Layer1RuleEngine:
    """
    Layer 1: 規則引擎
    
    職責：
    1. 計算技術指標
    2. 應用規則
    3. 輸出初步決策 + 信心指數
    4. 判斷是否需要 AI 介入
    """
    
    def __init__(self, config: RuleConfig = None):
        self.config = config or RuleConfig()
        self._init_indicators()
    
    def _init_indicators(self):
        """初始化指標計算器"""
        from signal_analyzer.crypto_indicators import (
            calc_rsi, calc_macd, calc_kd, calc_bollinger, calc_ema
        )
        self.calc_rsi = calc_rsi
        self.calc_mac = calc_macd
        self.calc_kd = calc_kd
        self.calc_bollinger = calc_bollinger
        self.calc_ema = calc_ema
    
    def analyze(self, symbol: str, data_source) -> SymbolAnalysis:
        """
        分析單一幣種
        
        Args:
            symbol: 如 "BTCUSDT"
            data_source: BinanceDataSource 實例
        
        Returns:
            SymbolAnalysis 物件
        """
        # 取得 K 線數據
        klines = data_source.get_klines(symbol, "1h", 200)
        if not klines:
            return SymbolAnalysis(symbol=symbol, price=0)
        
        closes = [k["close"] for k in klines]
        highs = [k["high"] for k in klines]
        lows = [k["low"] for k in klines]
        volumes = [k["volume"] for k in klines]
        
        # 計算指標
        rsi = self.calc_rsi(closes, 14)
        dif, dea, macd_hist = self.calc_mac(closes, 12, 26, 9)
        k_vals, d_vals = self.calc_kd(highs, lows, closes, 9)
        bb_ma, bb_upper, bb_lower = self.calc_bollinger(closes, 20, 2)
        ema20 = self.calc_ema(closes, 20)
        ema60 = self.calc_ema(closes, 60)
        
        # 包裝指標信號
        indicators = {
            "RSI": IndicatorSignal("RSI", rsi[-1] if rsi[-1] else 50, self._rsi_signal(rsi[-1])),
            "KD_K": IndicatorSignal("KD_K", k_vals[-1] if k_vals[-1] else 50, self._kd_signal(k_vals[-1], d_vals[-1]), weight=1.5),
            "KD_D": IndicatorSignal("KD_D", d_vals[-1] if d_vals[-1] else 50, "NEUTRAL"),
            "MACD": IndicatorSignal("MACD", macd_hist[-1] if macd_hist[-1] else 0, self._macd_signal(macd_hist[-1]), weight=1.5),
            "EMA20": IndicatorSignal("EMA20", ema20[-1] if ema20[-1] else 0, "NEUTRAL"),
            "EMA60": IndicatorSignal("EMA60", ema60[-1] if ema60[-1] else 0, "NEUTRAL"),
            "BB_Position": IndicatorSignal("BB", self._bb_position(closes[-1], bb_upper[-1], bb_lower[-1]), "NEUTRAL"),
            "Volume": IndicatorSignal("Volume", volumes[-1] if volumes[-1] else 0, "NEUTRAL"),
        }
        
        # 計算 Layer 1 決策
        return self._calc_layer1_decision(symbol, closes[-1], indicators, volumes)
    
    def _rsi_signal(self, rsi: float) -> str:
        if rsi is None:
            return "NEUTRAL"
        if rsi < self.config.rsi_oversold:
            return "BUY"
        if rsi > self.config.rsi_overbought:
            return "SELL"
        return "NEUTRAL"
    
    def _kd_signal(self, k: float, d: float) -> str:
        if k is None or d is None:
            return "NEUTRAL"
        if k > d and k < 30:
            return "BUY"  # 金叉 + 超賣
        if k < d and k > 70:
            return "SELL"  # 死叉 + 超買
        if k > d:
            return "BUY"
        if k < d:
            return "SELL"
        return "NEUTRAL"
    
    def _macd_signal(self, hist: float) -> str:
        if hist is None:
            return "NEUTRAL"
        if hist > 0:
            return "BUY"
        return "SELL"
    
    def _bb_position(self, price: float, upper: float, lower: float) -> float:
        if not upper or not lower or upper == lower:
            return 0.5
        return (price - lower) / (upper - lower)
    
    def _calc_layer1_decision(self, symbol: str, price: float, 
                              indicators: Dict, volumes: List) -> SymbolAnalysis:
        """計算 Layer 1 決策"""
        
        # 加權投票
        buy_score = 0.0
        sell_score = 0.0
        total_weight = 0.0
        signals = []
        
        for name, ind in indicators.items():
            weight = ind.weight
            total_weight += weight
            
            if ind.signal == "BUY":
                buy_score += weight
                signals.append(f"{name}_BUY")
            elif ind.signal == "SELL":
                sell_score += weight
                signals.append(f"{name}_SELL")
        
        # 正規化到 0-100
        if total_weight > 0:
            buy_pct = (buy_score / total_weight) * 100
            sell_pct = (sell_score / total_weight) * 100
        else:
            buy_pct = 50
            sell_pct = 50
        
        # Layer 1 分數
        layer1_score = buy_pct
        
        # 信心計算
        confidence = abs(buy_score - sell_score) / total_weight if total_weight > 0 else 0
        confidence = min(1.0, confidence)  # 上限 1.0
        
        # 決策
        if confidence >= self.config.confidence_threshold:
            if buy_score > sell_score:
                decision = "BUY"
            elif sell_score > buy_score:
                decision = "SELL"
            else:
                decision = "HOLD"
        else:
            # 信心不足，需要 AI
            decision = "HOLD"
        
        # 評估是否需要 AI
        needs_ai = (
            confidence < self.config.confidence_threshold and
            (buy_score > 0 or sell_score > 0)
        )
        
        # AI 介入原因
        ai_reason = ""
        if needs_ai:
            if buy_score > sell_score * 0.8 and buy_score < sell_score:
                ai_reason = "買賣信號接近，需要 AI 判断方向"
            elif sell_score > buy_score * 0.8 and sell_score < buy_score:
                ai_reason = "買賣信號接近，需要 AI 判断方向"
            elif confidence < 0.3:
                ai_reason = "指標矛盾，信號混乱"
        
        result = SymbolAnalysis(
            symbol=symbol,
            price=price,
            indicators=indicators,
            layer1_decision=decision,
            layer1_confidence=confidence,
            layer1_score=layer1_score,
            layer1_signals=signals,
            needs_ai=needs_ai,
            ai_reason=ai_reason
        )
        
        return result
    
    def scan(self, symbols: List[str], data_source) -> ScanResult:
        """掃描多個幣種"""
        result = ScanResult()
        
        for symbol in symbols:
            try:
                analysis = self.analyze(symbol, data_source)
                result.candidates.append(analysis)
                
                # 分類
                if analysis.needs_ai:
                    result.needs_ai_decision = True
                    result.ai_candidates.append(analysis)
                else:
                    if analysis.layer1_decision == "BUY":
                        result.confident_buys.append(analysis)
                    elif analysis.layer1_decision == "SELL":
                        result.confident_sells.append(analysis)
                    else:
                        result.confident_holds.append(analysis)
            except Exception as e:
                print(f"Error scanning {symbol}: {e}")
        
        return result


# ============================================================
# Layer 2: AI 裁決引擎
# ============================================================

class Layer2AIDecider:
    """
    Layer 2: AI 裁決引擎
    
    職責：
    1. 接收 Layer 1 的矛盾候選
    2. 收集額外上下文（情緒、鏈上、新聞）
    3. 調用 AI 做最終裁決
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.decision_history = []
    
    def decide(self, candidates: List[SymbolAnalysis], 
               context: Dict = None) -> List[SymbolAnalysis]:
        """
        對矛盾候選做 AI 裁決
        
        Args:
            candidates: Layer 1 無法確定的候選
            context: 額外上下文（可選）
        
        Returns:
            附帶 AI 決策的 SymbolAnalysis 列表
        """
        results = []
        
        for candidate in candidates:
            # 構建 prompt
            prompt = self._build_prompt(candidate, context)
            
            # 調用 AI
            decision = self._call_ai(prompt)
            
            # 更新候選
            candidate.final_decision = decision["action"]
            candidate.final_confidence = decision["confidence"]
            candidate.final_reason = decision["reason"]
            
            results.append(candidate)
            self.decision_history.append({
                "timestamp": datetime.now().isoformat(),
                "symbol": candidate.symbol,
                "decision": decision
            })
        
        return results
    
    def _build_prompt(self, candidate: SymbolAnalysis, context: Dict = None) -> str:
        """構建 AI prompt"""
        
        # 格式化指標
        indicators_str = []
        for name, ind in candidate.indicators.items():
            indicators_str.append(f"- {name}: {ind.value:.2f} ({ind.signal})")
        
        indicators_text = "\n".join(indicators_str)
        
        prompt = f"""你是一個加密貨幣交易決策 AI。

【幣種】{candidate.symbol}
【價格】${candidate.price:,.2f}

【技術指標】
{indicators_text}

【Layer 1 分析】
- 初步決策：{candidate.layer1_decision}
- 信心：{candidate.layer1_confidence:.0%}
- 信號：{', '.join(candidate.layer1_signals) or '無'}
- 問題：{candidate.ai_reason}

【額外上下文】
{json.dumps(context or {}, ensure_ascii=False, indent=2)}

請輸出 JSON：
{{"action": "BUY/SELL/HOLD", "confidence": 0.0-1.0, "reason": "原因"}}
"""
        return prompt
    
    def _call_ai(self, prompt: str) -> Dict:
        """
        調用 AI API
        
        實際應該調用 MiniMax / Claude 等 API
        這裡用簡化版本
        """
        # 佔時：用規則模擬 AI
        # 實際專案應該調用真實 API
        
        # 簡單邏輯：如果 Layer 1 偏向買，且 AI 理由不充分，則 HOLD
        if "接近" in prompt:
            return {
                "action": "HOLD",
                "confidence": 0.5,
                "reason": "信號矛盾，觀望"
            }
        
        return {
            "action": "HOLD",
            "confidence": 0.5,
            "reason": "等待更明確信號"
        }


# ============================================================
# 雙層決策系統
# ============================================================

class DualLayerDecisionSystem:
    """
    雙層決策系統
    
    Layer 1: 規則引擎（快速、自信決策）
    Layer 2: AI 裁決（矛盾時介入）
    
    使用方式：
        system = DualLayerDecisionSystem()
        
        # 掃描
        scan_result = system.scan(["BTCUSDT", "ETHUSDT"])
        
        # 處理結果
        for decision in scan_result.confident_buys:
            print(f"買入: {decision.symbol}")
        
        if scan_result.needs_ai_decision:
            ai_results = system.ai_decide(scan_result.ai_candidates)
            for decision in ai_results:
                print(f"AI 裁決: {decision.final_decision} {decision.symbol}")
    """
    
    def __init__(self, config: RuleConfig = None, api_key: str = None):
        self.layer1 = Layer1RuleEngine(config)
        self.layer2 = Layer2AIDecider(api_key)
        self.last_scan_result: Optional[ScanResult] = None
    
    def scan(self, symbols: List[str], data_source) -> ScanResult:
        """
        掃描並做決策
        
        Args:
            symbols: 要掃描的幣種列表
            data_source: 數據源
        
        Returns:
            ScanResult
        """
        from signal_analyzer.crypto_data import BinanceDataSource
        
        if data_source is None:
            data_source = BinanceDataSource()
        
        # Layer 1: 規則引擎掃描
        self.last_scan_result = self.layer1.scan(symbols, data_source)
        
        return self.last_scan_result
    
    def ai_decide(self, candidates: List[SymbolAnalysis] = None,
                  context: Dict = None) -> List[SymbolAnalysis]:
        """
        對矛盾候選進行 AI 裁決
        
        Args:
            candidates: 如果為 None，使用上次掃描的矛盾候選
            context: 額外上下文
        
        Returns:
            AI 裁決後的 SymbolAnalysis 列表
        """
        if candidates is None:
            if self.last_scan_result is None:
                return []
            candidates = self.last_scan_result.ai_candidates
        
        return self.layer2.decide(candidates, context)
    
    def get_all_decisions(self) -> List[SymbolAnalysis]:
        """
        獲取所有最終決策
        
        Returns:
            所有幣種的最終決策列表
        """
        if self.last_scan_result is None:
            return []
        
        decisions = []
        
        # 自信決策（直接採用 Layer 1）
        for c in self.last_scan_result.confident_buys:
            c.final_decision = c.layer1_decision
            c.final_confidence = c.layer1_confidence
            c.final_reason = "Layer 1 自信決策"
            decisions.append(c)
        
        for c in self.last_scan_result.confident_sells:
            c.final_decision = c.layer1_decision
            c.final_confidence = c.layer1_confidence
            c.final_reason = "Layer 1 自信決策"
            decisions.append(c)
        
        for c in self.last_scan_result.confident_holds:
            c.final_decision = "HOLD"
            c.final_confidence = 0.5
            c.final_reason = "無明顯信號"
            decisions.append(c)
        
        # AI 裁決
        for c in self.last_scan_result.ai_candidates:
            decisions.append(c)
        
        return decisions
    
    def summary(self) -> str:
        """取得人類可讀的摘要"""
        if self.last_scan_result is None:
            return "尚無掃描結果"
        
        result = self.last_scan_result
        
        lines = []
        lines.append("=" * 60)
        lines.append("【雙層決策系統 - 掃描結果】")
        lines.append(f"時間：{result.timestamp}")
        lines.append("=" * 60)
        
        lines.append(f"\n📈 自信買入 ({len(result.confident_buys)}):")
        for c in result.confident_buys:
            lines.append(f"  ✓ {c.symbol} @ ${c.price:,.2f} (信心:{c.layer1_confidence:.0%})")
        
        lines.append(f"\n📉 自信賣出 ({len(result.confident_sells)}):")
        for c in result.confident_sells:
            lines.append(f"  ✓ {c.symbol} @ ${c.price:,.2f} (信心:{c.layer1_confidence:.0%})")
        
        lines.append(f"\n🤔 需要 AI 裁決 ({len(result.ai_candidates)}):")
        for c in result.ai_candidates:
            lines.append(f"  ? {c.symbol} - {c.ai_reason}")
        
        lines.append(f"\n⏸️ 觀望 ({len(result.confident_holds)}):")
        for c in result.confident_holds[:5]:
            lines.append(f"  - {c.symbol}")
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)


# ============================================================
# 快速使用函數
# ============================================================

def quick_decide(symbols: List[str] = None) -> Dict:
    """
    快速決策（懶人接口）
    
    使用方式：
        result = quick_decide(["BTCUSDT", "ETHUSDT"])
        print(result["buys"])
        print(result["summary"])
    """
    from signal_analyzer.crypto_data import BinanceDataSource
    
    if symbols is None:
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
    
    # 初始化
    system = DualLayerDecisionSystem()
    data_source = BinanceDataSource()
    
    # 掃描
    scan_result = system.scan(symbols, data_source)
    
    # 處理 AI 裁決
    if scan_result.needs_ai_decision:
        system.ai_decide()
    
    # 獲取所有決策
    decisions = system.get_all_decisions()
    
    # 分類
    buys = [d for d in decisions if d.final_decision == "BUY"]
    sells = [d for d in decisions if d.final_decision == "SELL"]
    holds = [d for d in decisions if d.final_decision == "HOLD"]
    
    return {
        "buys": buys,
        "sells": sells,
        "holds": holds,
        "needs_ai": scan_result.needs_ai_decision,
        "summary": system.summary()
    }
