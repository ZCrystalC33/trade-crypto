"""
Binance API Provider - 增強版數據源
支持現貨和期貨 API
"""

import hmac
import hashlib
import time
import requests
from typing import Dict, List, Optional
from datetime import datetime


class BinanceProvider:
    """
    Binance API 提供者
    
    支持:
    - 現貨市場數據
    - 期貨市場數據
    - 帳戶信息
    - 資金费率
    """
    
    SPOT_BASE_URL = "https://api.binance.com"
    FUTURES_BASE_URL = "https://fapi.binance.com"
    
    def __init__(self, api_key: str = None, api_secret: str = None, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"X-MBX-APIKEY": api_key})
    
    def _sign(self, params: Dict) -> str:
        """簽名請求"""
        query = "&".join([f"{k}={v}" for k, v in params.items()])
        signature = hmac.new(
            self.api_secret.encode(),
            query.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _get(self, base_url: str, endpoint: str, params: Dict = None, signed: bool = False) -> Dict:
        """GET 請求"""
        url = f"{base_url}{endpoint}"
        params = params or {}
        
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["signature"] = self._sign(params)
        
        try:
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Error: {e}")
            return {}
    
    def _post(self, base_url: str, endpoint: str, params: Dict = None, signed: bool = False) -> Dict:
        """POST 請求"""
        url = f"{base_url}{endpoint}"
        params = params or {}
        
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["signature"] = self._sign(params)
        
        try:
            resp = self.session.post(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Error: {e}")
            return {}
    
    # ============================================================
    # 現貨市場數據
    # ============================================================
    
    def get_klines(self, symbol: str, interval: str = "1h", limit: int = 200) -> List[Dict]:
        """取得 K 線數據"""
        data = self._get(self.SPOT_BASE_URL, "/api/v3/klines", {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit
        })
        
        result = []
        for k in data:
            result.append({
                "open_time": datetime.fromtimestamp(k[0] / 1000),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "close_time": datetime.fromtimestamp(k[6] / 1000),
                "quote_volume": float(k[7])
            })
        return result
    
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """取得 24hr Ticker"""
        data = self._get(self.SPOT_BASE_URL, "/api/v3/ticker/24hr", {
            "symbol": symbol.upper()
        })
        
        if not data:
            return None
        
        return {
            "symbol": data["symbol"],
            "price": float(data["lastPrice"]),
            "price_change": float(data["priceChange"]),
            "price_change_pct": float(data["priceChangePercent"]),
            "high_24h": float(data["highPrice"]),
            "low_24h": float(data["lowPrice"]),
            "volume": float(data["volume"]),
            "quote_volume": float(data["quoteVolume"]),
        }
    
    def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[Dict]:
        """取得掛單簿"""
        data = self._get(self.SPOT_BASE_URL, "/api/v3/depth", {
            "symbol": symbol.upper(),
            "limit": limit
        })
        
        if not data:
            return None
        
        return {
            "bids": [[float(p), float(q)] for p, q in data.get("bids", [])],
            "asks": [[float(p), float(q)] for p, q in data.get("asks", [])]
        }
    
    def get_recent_trades(self, symbol: str, limit: int = 50) -> List[Dict]:
        """取得近期成交"""
        data = self._get(self.SPOT_BASE_URL, "/api/v3/trades", {
            "symbol": symbol.upper(),
            "limit": limit
        })
        
        return [{
            "id": t["id"],
            "price": float(t["price"]),
            "qty": float(t["qty"]),
            "time": datetime.fromtimestamp(t["time"] / 1000),
            "is_buyer_maker": t["isBuyerMaker"]
        } for t in data]
    
    # ============================================================
    # 期貨市場數據
    # ============================================================
    
    def get_funding_rate(self, symbol: str) -> Optional[float]:
        """取得資金费率"""
        data = self._get(self.FUTURES_BASE_URL, "/fapi/v1/premiumIndex", {
            "symbol": symbol.upper()
        })
        
        if not data:
            return None
        
        return float(data.get("lastFundingRate", 0))
    
    def get_open_interest(self, symbol: str) -> Optional[Dict]:
        """取得未平倉量"""
        data = self._get(self.FUTURES_BASE_URL, "/fapi/v1/openInterest", {
            "symbol": symbol.upper()
        })
        
        if not data:
            return None
        
        return {
            "symbol": data.get("symbol", symbol),
            "open_interest": float(data.get("openInterest", 0)),
            "pair": data.get("pair", symbol)
        }
    
    def get_top_long_short_ratio(self, symbol: str, period: str = "1h") -> Optional[Dict]:
        """取得多空比率"""
        # 這個需要期貨情緒 API
        data = self._get(self.FUTURES_BASE_URL, "/fapi/fundustrade/LongShortRatio", {
            "symbol": symbol.upper(),
            "period": period
        })
        
        if not data or len(data) == 0:
            return None
        
        latest = data[-1]
        return {
            "symbol": symbol,
            "long_short_ratio": float(latest.get("longShortRatio", 1)),
            "long_account_ratio": float(latest.get("longAccountOpenInterestVo")),
            "short_account_ratio": float(latest.get("shortAccountOpenInterestVo")),
        }
    
    # ============================================================
    # 帳戶數據（需要 API Key）
    # ============================================================
    
    def get_account(self) -> Optional[Dict]:
        """取得帳戶信息"""
        if not self.api_key:
            return None
        
        data = self._get(self.SPOT_BASE_URL, "/api/v3/account", signed=True)
        
        if not data:
            return None
        
        balances = []
        for b in data.get("balances", []):
            free = float(b["free"])
            locked = float(b["locked"])
            if free > 0 or locked > 0:
                balances.append({
                    "asset": b["asset"],
                    "free": free,
                    "locked": locked,
                    "total": free + locked
                })
        
        return {
            "account_type": data.get("accountType", "SPOT"),
            "balances": balances
        }
    
    def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """取得開放訂單"""
        if not self.api_key:
            return []
        
        params = {"timestamp": int(time.time() * 1000)}
        if symbol:
            params["symbol"] = symbol.upper()
        
        data = self._get(self.SPOT_BASE_URL, "/api/v3/openOrders", params, signed=True)
        
        return [{
            "symbol": o["symbol"],
            "side": o["side"],
            "type": o["type"],
            "price": float(o.get("price", 0)),
            "orig_qty": float(o["origQty"]),
            "executed_qty": float(o["executedQty"]),
            "time": datetime.fromtimestamp(o["time"] / 1000)
        } for o in data]
    
    # ============================================================
    # 市場掃描
    # ============================================================
    
    def get_top_symbols(self, limit: int = 20) -> List[str]:
        """取得成交量最高的幣種"""
        data = self._get(self.SPOT_BASE_URL, "/api/v3/ticker/24hr")
        
        if not data:
            return ["BTCUSDT", "ETHUSDT"]
        
        # 過濾 USDT 交易對，按成交量排序
        symbols = [
            s["symbol"] for s in data
            if s["symbol"].endswith("USDT")
            and float(s["quoteVolume"]) > 1000000  # > 100萬 USDT
        ]
        
        # 按成交量排序
        symbols.sort(
            key=lambda x: next((float(s["quoteVolume"]) for s in data if s["symbol"] == x), 0),
            reverse=True
        )
        
        return symbols[:limit]
    
    def get_market_sentiment(self, symbol: str) -> Dict:
        """
        取得市場情緒數據
        
        整合多個維度：
        - 資金费率（期貨）
        - 未平倉量
        - 多空比率
        - 現貨/期貨溢價
        """
        sentiment = {
            "symbol": symbol,
            "funding_rate": None,
            "open_interest": None,
            "long_short_ratio": None,
            "ticker": None,
            "orderbook_imbalance": None
        }
        
        # 現貨 Ticker
        sentiment["ticker"] = self.get_ticker(symbol)
        
        # 期貨資金费率
        sentiment["funding_rate"] = self.get_funding_rate(symbol)
        
        # 未平倉量
        oi = self.get_open_interest(symbol)
        if oi:
            sentiment["open_interest"] = oi["open_interest"]
        
        # 掛單簿失衡
        ob = self.get_orderbook(symbol, 50)
        if ob:
            bid_total = sum(q for _, q in ob["bids"])
            ask_total = sum(q for _, q in ob["asks"])
            if bid_total + ask_total > 0:
                imbalance = (bid_total - ask_total) / (bid_total + ask_total)
                sentiment["orderbook_imbalance"] = imbalance
        
        return sentiment


# ============================================================
# 快速初始化
# ============================================================

def create_binance_provider() -> BinanceProvider:
    """使用儲存的 API Key 建立 Provider"""
    try:
        with open("/home/snow/.openclaw/credentials/binance.key") as f:
            lines = f.readlines()
        
        api_key = None
        api_secret = None
        
        for line in lines:
            if "BINANCE_API_KEY=" in line:
                api_key = line.split("=")[1].strip()
            elif "BINANCE_API_SECRET=" in line:
                api_secret = line.split("=")[1].strip()
        
        if api_key and api_secret:
            return BinanceProvider(api_key, api_secret)
    except Exception as e:
        print(f"Error loading API key: {e}")
    
    return BinanceProvider()
