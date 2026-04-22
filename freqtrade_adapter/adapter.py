"""Freqtrade Adapter - 與 Freqtrade API 溝通"""

import requests
import json
from typing import Dict, List, Optional
from datetime import datetime


class FreqtradeAdapter:
    """
    Freqtrade API 適配器
    用於：
    - 讀取目前倉位/訂單
    - 發送交易指令
    - 調整停損停利
    """
    
    def __init__(self, api_url: str = "http://127.0.0.1:18798", username: str = "freqtrade", password: str = "freqtrade123"):
        self.api_url = api_url
        self.username = username
        self.password = password
        self.session = requests.Session()
        self._authenticate()
    
    def _authenticate(self):
        """取得 JWT token"""
        resp = self.session.post(
            f"{self.api_url}/api/v1/token",
            json={"username": self.username, "password": self.password},
            timeout=10
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token")
        else:
            self.token = None
            print(f"Auth failed: {resp.status_code}")
    
    def _headers(self) -> Dict:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}
    
    def get_status(self) -> Dict:
        """取得 Bot 狀態"""
        resp = self.session.get(f"{self.api_url}/api/v1/show_config", headers=self._headers(), timeout=10)
        return resp.json() if resp.status_code == 200 else {"error": resp.text}
    
    def get_balance(self) -> Dict:
        """取得餘額"""
        resp = self.session.get(f"{self.api_url}/api/v1/balance", headers=self._headers(), timeout=10)
        return resp.json() if resp.status_code == 200 else {"error": resp.text}
    
    def get_trades(self, limit: int = 50) -> List[Dict]:
        """取得最近交易記錄"""
        resp = self.session.get(f"{self.api_url}/api/v1/trades?limit={limit}", headers=self._headers(), timeout=10)
        if resp.status_code == 200:
            return resp.json().get("trades", [])
        return []
    
    def get_open_trades(self) -> List[Dict]:
        """取得目前倉位"""
        resp = self.session.get(f"{self.api_url}/api/v1/status", headers=self._headers(), timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return []
    
    def get_profit(self) -> Dict:
        """取得獲利統計"""
        resp = self.session.get(f"{self.api_url}/api/v1/profit", headers=self._headers(), timeout=10)
        return resp.json() if resp.status_code == 200 else {"error": resp.text}
    
    def get_pairs(self) -> List[str]:
        """取得目前交易的幣對"""
        resp = self.session.get(f"{self.api_url}/api/v1/pairs", headers=self._headers(), timeout=10)
        if resp.status_code == 200:
            return resp.json().get("pairs", [])
        return []
    
    def reload_trade(self, trade_id: int) -> Dict:
        """重新載入特定交易"""
        resp = self.session.post(f"{self.api_url}/api/v1/reload_trade/{trade_id}", headers=self._headers(), timeout=10)
        return {"status": resp.status_code, "data": resp.json()} if resp.status_code == 200 else {"error": resp.text}
    
    def force_entry(self, pair: str, side: str = "long") -> Dict:
        """強制進場（需要 custom strategy 支持）"""
        resp = self.session.post(
            f"{self.api_url}/api/v1/force_entry",
            json={"pair": pair, "side": side},
            headers=self._headers(),
            timeout=10
        )
        return resp.json() if resp.status_code == 200 else {"error": resp.text}
    
    def force_exit(self, trade_id: int, order_type: str = "market") -> Dict:
        """強制出場"""
        resp = self.session.post(
            f"{self.api_url}/api/v1/force_exit/{trade_id}",
            json={"ordertype": order_type},
            headers=self._headers(),
            timeout=10
        )
        return resp.json() if resp.status_code == 200 else {"error": resp.text}
    
    def start(self) -> Dict:
        """啟動 Bot"""
        resp = self.session.post(f"{self.api_url}/api/v1/start", headers=self._headers(), timeout=10)
        return resp.json() if resp.status_code == 200 else {"error": resp.text}
    
    def stop(self) -> Dict:
        """停止 Bot"""
        resp = self.session.post(f"{self.api_url}/api/v1/stop", headers=self._headers(), timeout=10)
        return resp.json() if resp.status_code == 200 else {"error": resp.text}
    
    def get_whitelist(self) -> List[str]:
        """取得白名單（可用交易的對）"""
        resp = self.session.get(f"{self.api_url}/api/v1/whitelist", headers=self._headers(), timeout=10)
        if resp.status_code == 200:
            return resp.json().get("whitelist", [])
        return []
    
    def set_whitelist(self, pairs: List[str]) -> Dict:
        """
        設定白名單（Trade Core 產生的信號）
        這是核心整合點！
        """
        resp = self.session.post(
            f"{self.api_url}/api/v1/whitelist",
            json={"whitelist": pairs},
            headers=self._headers(),
            timeout=10
        )
        return resp.json() if resp.status_code == 200 else {"error": resp.text}
    
    def get_performance(self) -> List[Dict]:
        """取得各幣種表現"""
        resp = self.session.get(f"{self.api_url}/api/v1/performance", headers=self._headers(), timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return []


# Test function
def test_adapter():
    """測試 Freqtrade 連接"""
    adapter = FreqtradeAdapter()
    
    print("=== Bot Status ===")
    print(json.dumps(adapter.get_status(), indent=2, default=str)[:500])
    
    print("\n=== Balance ===")
    print(json.dumps(adapter.get_balance(), indent=2, default=str)[:300])
    
    print("\n=== Open Trades ===")
    print(adapter.get_open_trades())
    
    print("\n=== Whitelist ===")
    print(adapter.get_whitelist())
    
    return adapter


if __name__ == "__main__":
    test_adapter()