"""
Freqtrade API Integration Module

對接 Freqtrade 乾運行/實盤交易
"""

import requests
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TradeDecision:
    """交易決策"""
    symbol: str
    action: str  # BUY, SELL, HOLD
    price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    confidence: float = 0.5
    reason: str = ""
    risk_level: str = "MEDIUM"


class FreqtradeIntegration:
    """Freqtrade API 整合器"""
    
    def __init__(self, api_url: str = "http://127.0.0.1:18798", 
                 username: str = "freqtrade", password: str = "freqtrade123"):
        self.api_url = api_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self._token = None
        
        # 測試連接
        self._ping()
    
    def _ping(self) -> bool:
        """測試連接"""
        try:
            resp = self.session.get(f"{self.api_url}/api/v1/ping", timeout=5)
            return resp.status_code == 200
        except:
            return False
    
    def _get_token(self) -> str:
        """獲取認證 Token"""
        if self._token:
            return self._token
        
        try:
            resp = self.session.post(
                f"{self.api_url}/api/v1/token/login",
                json={"username": self.username, "password": self.password},
                timeout=5
            )
            if resp.status_code == 200:
                self._token = resp.json().get("token")
                return self._token
        except:
            pass
        
        return None
    
    def _headers(self) -> Dict:
        """請求頭"""
        token = self._get_token()
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}
    
    def get_status(self) -> Dict:
        """獲取機器人狀態"""
        try:
            resp = self.session.get(
                f"{self.api_url}/api/v1/status",
                headers=self._headers(),
                timeout=5
            )
            if resp.status_code == 200:
                return resp.json()
            return {"status": "error", "reason": resp.text}
        except Exception as e:
            return {"status": "error", "reason": str(e)}
    
    def get_show_config(self) -> Dict:
        """獲取配置"""
        try:
            resp = self.session.get(
                f"{self.api_url}/api/v1/show_config",
                headers=self._headers(),
                timeout=5
            )
            if resp.status_code == 200:
                return resp.json()
            return {}
        except:
            return {}
    
    def get_balance(self) -> Dict:
        """獲取餘額"""
        try:
            resp = self.session.get(
                f"{self.api_url}/api/v1/balance",
                headers=self._headers(),
                timeout=5
            )
            if resp.status_code == 200:
                return resp.json()
            return {}
        except:
            return {}
    
    def get_open_trades(self) -> List[Dict]:
        """獲取開放倉位"""
        status = self.get_status()
        if isinstance(status, dict) and status.get("result"):
            return status["result"]
        return []
    
    def get_trades(self, limit: int = 50) -> List[Dict]:
        """獲取交易歷史"""
        try:
            resp = self.session.get(
                f"{self.api_url}/api/v1/trades",
                headers=self._headers(),
                params={"limit": limit},
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("result", [])
            return []
        except:
            return []
    
    def get_profit(self) -> Dict:
        """獲取利潤統計"""
        try:
            resp = self.session.get(
                f"{self.api_url}/api/v1/profit",
                headers=self._headers(),
                timeout=5
            )
            if resp.status_code == 200:
                return resp.json()
            return {}
        except:
            return {}
    
    def get_whitelist(self) -> List[str]:
        """獲取白名單（可交易對）"""
        try:
            resp = self.session.get(
                f"{self.api_url}/api/v1/whitelist",
                headers=self._headers(),
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("whitelist", [])
            return []
        except:
            return []
    
    def start_bot(self) -> bool:
        """啟動機器人"""
        try:
            resp = self.session.post(
                f"{self.api_url}/api/v1/start",
                headers=self._headers(),
                timeout=5
            )
            return resp.status_code == 200
        except:
            return False
    
    def stop_bot(self) -> bool:
        """停止機器人"""
        try:
            resp = self.session.post(
                f"{self.api_url}/api/v1/stop",
                headers=self._headers(),
                timeout=5
            )
            return resp.status_code == 200
        except:
            return False
    
    def force_buy(self, symbol: str, price: float = None, dry_run: bool = True) -> Dict:
        """
        強制買入（由策略信號觸發）
        
        Args:
            symbol: 交易對，如 BTCUSDT
            price: 買入價格（可選）
            dry_run: 是否只做模擬
        """
        try:
            payload = {"pair": symbol}
            if price:
                payload["price"] = price
            
            resp = self.session.post(
                f"{self.api_url}/api/v1/forcebuy",
                headers=self._headers(),
                json=payload,
                timeout=10
            )
            
            if resp.status_code == 200:
                result = resp.json()
                if dry_run:
                    result["dry_run"] = True
                return result
            else:
                return {"error": resp.text}
        except Exception as e:
            return {"error": str(e)}
    
    def force_sell(self, symbol: str, reason: str = "exit_signal") -> Dict:
        """
        強制賣出（由策略信號觸發）
        """
        try:
            resp = self.session.post(
                f"{self.api_url}/api/v1/forcesell",
                headers=self._headers(),
                json={"pair": symbol, "reason": reason},
                timeout=10
            )
            
            if resp.status_code == 200:
                return resp.json()
            else:
                return {"error": resp.text}
        except Exception as e:
            return {"error": str(e)}
    
    def execute_decision(self, decision: TradeDecision, dry_run: bool = True) -> Dict:
        """
        執行交易決策
        
        流程：
        1. 檢查決策
        2. 如果是 BUY，檢查餘額
        3. 執行交易
        4. 返回結果
        """
        result = {
            "symbol": decision.symbol,
            "action": decision.action,
            "price": decision.price,
            "success": False,
            "message": ""
        }
        
        # 檢查 dry_run 模式
        config = self.get_show_config()
        is_dry_run = config.get("dry_run", True)
        
        if is_dry_run:
            result["dry_run"] = True
        
        if decision.action == "HOLD":
            result["success"] = True
            result["message"] = "觀望，不執行交易"
            return result
        
        # 檢查倉位
        open_trades = self.get_open_trades()
        current_position = next((t for t in open_trades if t.get("pair") == decision.symbol), None)
        
        if decision.action == "BUY":
            if current_position:
                result["message"] = f"已有倉位：{decision.symbol}，跳過買入"
                return result
            
            # 執行買入
            trade_result = self.force_buy(decision.symbol, decision.price, is_dry_run)
            if "error" in trade_result:
                result["message"] = trade_result["error"]
            else:
                result["success"] = True
                result["message"] = f"{'模擬' if is_dry_run else '實盤'}買入 {decision.symbol} @ {decision.price}"
                result["trade_id"] = trade_result.get("trade_id")
        
        elif decision.action == "SELL":
            if not current_position:
                result["message"] = f"無倉位可賣：{decision.symbol}"
                return result
            
            # 執行賣出
            trade_result = self.force_sell(decision.symbol)
            if "error" in trade_result:
                result["message"] = trade_result["error"]
            else:
                result["success"] = True
                result["message"] = f"{'模擬' if is_dry_run else '實盤'}賣出 {decision.symbol}"
                result["trade_id"] = current_position.get("trade_id")
        
        return result
    
    def get_trading_summary(self) -> str:
        """獲取交易摘要"""
        lines = []
        lines.append("=" * 50)
        lines.append("Freqtrade 交易摘要")
        lines.append("=" * 50)
        
        # 狀態
        status = self.get_status()
        lines.append(f"\n機器人狀態: {status.get('state', 'unknown')}")
        
        # 配置
        config = self.get_show_config()
        lines.append(f"Dry Run: {config.get('dry_run', 'unknown')}")
        lines.append(f"Trading Mode: {config.get('trading_mode', 'unknown')}")
        
        # 利潤
        profit = self.get_profit()
        if profit.get("profit_all_percent"):
            lines.append(f"\n總利潤: {float(profit['profit_all_percent']):.2f}%")
        
        # 開放倉位
        open_trades = self.get_open_trades()
        lines.append(f"\n開放倉位: {len(open_trades)}")
        for t in open_trades[:5]:
            lines.append(f"  - {t.get('pair')}: {t.get('amount')} @ {t.get('open_rate')}")
        
        lines.append("=" * 50)
        return "\n".join(lines)


def create_freqtrade() -> FreqtradeIntegration:
    """工廠函數：創建 Freqtrade 整合器"""
    return FreqtradeIntegration()
