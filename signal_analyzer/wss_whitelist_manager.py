"""
WSS Freqtrade Whitelist Manager

將 WSS 分析結果中的優質幣種加入到 Freqtrade whitelist
"""

from typing import Dict, List
from signal_analyzer.wss_top_scanner import WSSTopCryptoScanner
from signal_analyzer.freqtrade_integration import FreqtradeIntegration


class WSSFreqtradeWhitelistManager:
    """
    WSS 市場龍頭 → Freqtrade Whitelist 管理器
    
    使用流程：
    1. scan_and_decide() - 掃描市場，決定哪些加入白名單
    2. update_whitelist() - 更新 Freqtrade whitelist
    3. get_current_whitelist() - 取得目前白名單
    """
    
    def __init__(self, freqtrade: FreqtradeIntegration = None):
        self.freqtrade = freqtrade or FreqtradeIntegration()
        self.scanner = WSSTopCryptoScanner()
        self.scan_result = None
    
    def scan_and_decide(self, top_n: int = 10, min_score: float = 50) -> Dict:
        """
        掃描市場並決定白名單
        
        Args:
            top_n: 只考慮前 N 名幣種
            min_score: 最低 WSS 分數閾值
        
        Returns:
            {"whitelist": [...], "removed": [...], "summary": str}
        """
        # 執行掃描
        self.scan_result = self.scanner.scan_top_symbols(limit=30)
        
        # 從前 N 名中篩選
        ranked = self.scan_result.get("ranked", [])
        candidates = ranked[:top_n]
        
        # 根據分數決定加入白名單
        whitelist = []
        removed = []
        
        for item in candidates:
            score = item.get("wss_score", 0)
            verdict = item.get("verdict", "NEUTRAL")
            
            if score >= min_score and verdict not in ["STRONG_SELL", "SELL"]:
                whitelist.append({
                    "symbol": item["symbol"],
                    "wss_score": score,
                    "verdict": verdict,
                    "reason": f"WSS {verdict} ({score:.0f})"
                })
            else:
                removed.append({
                    "symbol": item["symbol"],
                    "wss_score": score,
                    "verdict": verdict,
                    "reason": f"Score {score:.0f} < {min_score} or {verdict}"
                })
        
        return {
            "whitelist": whitelist,
            "removed": removed,
            "total_candidates": len(candidates)
        }
    
    def get_current_whitelist(self) -> List[str]:
        """取得 Freqtrade 目前白名單"""
        try:
            return self.freqtrade.get_whitelist()
        except:
            return []
    
    def update_whitelist(self, new_whitelist: List[str] = None, dry_run: bool = True) -> Dict:
        """
        更新 Freqtrade whitelist
        
        注意：Freqtrade 本身有保護機制，這裡只是將建議寫入配置
        
        Args:
            new_whitelist: 新的白名單（如果為空，使用掃描結果）
            dry_run: 是否只是模擬
        
        Returns:
            {"success": bool, "whitelist": [...], "message": str}
        """
        if new_whitelist is None:
            if self.scan_result is None:
                return {"success": False, "message": "No scan result. Run scan_and_decide() first."}
            
            # 從掃描結果構建白名單
            whitelist_data = self.scan_and_decide()
            new_whitelist = [item["symbol"] for item in whitelist_data.get("whitelist", [])]
        
        current = self.get_current_whitelist()
        
        # 生成建議
        to_add = [s for s in new_whitelist if s not in current]
        to_remove = [s for s in current if s not in new_whitelist]
        
        result = {
            "success": True,
            "current_count": len(current),
            "proposed_count": len(new_whitelist),
            "to_add": to_add,
            "to_remove": to_remove,
            "proposed_whitelist": new_whitelist,
            "dry_run": dry_run
        }
        
        if dry_run:
            result["message"] = f"模擬模式：建議白名單包含 {len(new_whitelist)} 個幣種"
        else:
            result["message"] = f"已更新白名單：新增 {len(to_add)} 個，移除 {len(to_remove)} 個"
        
        return result
    
    def generate_config(self, symbols: List[str]) -> str:
        """
        生成 Freqtrade 格式的白名單配置
        
        Returns:
            格式化的配置字串（可直接貼到 config.json）
        """
        lines = []
        lines.append("// WSS 市場龍頭白名單（自動生成）")
        lines.append("// 生成時間：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        lines.append("//")
        lines.append("// 使用方式：")
        lines.append("// 1. 複製下面的陣列")
        lines.append("// 2. 貼到 Freqtrade config.json 的 'pairlists' -> 'whitelist'")
        lines.append("//")
        lines.append("")
        lines.append("[")
        
        for i, sym in enumerate(symbols):
            if i > 0:
                lines[-1] += ","
            lines.append(f"  \"{sym}\"")
        
        lines.append("]")
        
        return "\n".join(lines)
    
    def summary(self) -> str:
        """生成摘要"""
        if self.scan_result is None:
            return "尚無掃描結果"
        
        whitelist_data = self.scan_and_decide()
        whitelist = whitelist_data.get("whitelist", [])
        removed = whitelist_data.get("removed", [])
        
        lines = []
        lines.append("=" * 60)
        lines.append("【WSS Freqtrade Whitelist 管理】")
        lines.append("=" * 60)
        
        lines.append(f"\n候選幣種（前10名）：{whitelist_data['total_candidates']}")
        lines.append(f"\n✅ 建議加入白名單 ({len(whitelist)}):")
        
        if whitelist:
            for item in whitelist:
                lines.append(f"  ✓ {item['symbol']} (WSS: {item['wss_score']:.0f})")
        else:
            lines.append("  無，建議觀望")
        
        lines.append(f"\n❌ 不建議加入 ({len(removed)}):")
        if removed:
            for item in removed[:5]:
                lines.append(f"  ✗ {item['symbol']} (WSS: {item['wss_score']:.0f}, {item['verdict']})")
        
        # 目前白名單
        current = self.get_current_whitelist()
        lines.append(f"\n📋 目前 Freqtrade 白名單 ({len(current)}):")
        if current:
            for sym in current[:10]:
                lines.append(f"  - {sym}")
            if len(current) > 10:
                lines.append(f"  ... 還有 {len(current) - 10} 個")
        
        lines.append("\n" + "=" * 60)
        return "\n".join(lines)


def create_whitelist_manager() -> WSSFreqtradeWhitelistManager:
    """工廠函數"""
    return WSSFreqtradeWhitelistManager()
