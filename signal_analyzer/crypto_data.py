"""
Crypto Data Source - 從 Binance 讀取數據
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json


class BinanceDataSource:
    """Binance API 資料源"""
    
    BASE_URL = "https://api.binance.com/api/v3"
    
    def __init__(self):
        self.session = requests.Session()
    
    def get_klines(self, symbol: str, interval: str = "15m", limit: int = 100) -> List[Dict]:
        """取得 K 線數據"""
        endpoint = f"{self.BASE_URL}/klines"
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit
        }
        
        try:
            resp = self.session.get(endpoint, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            result = []
            for k in data:
                result.append({
                    "open_time": datetime.fromtimestamp(k[0] / 1000),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "close_time": datetime.fromtimestamp(k[6] / 1000)
                })
            return result
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return []
    
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """取得 24hr 統計"""
        endpoint = f"{self.BASE_URL}/ticker/24hr"
        params = {"symbol": symbol.upper()}
        
        try:
            resp = self.session.get(endpoint, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            return {
                "symbol": data["symbol"],
                "price_change": float(data["priceChange"]),
                "price_change_pct": float(data["priceChangePercent"]),
                "last_price": float(data["lastPrice"]),
                "volume": float(data["volume"]),
                "quote_volume": float(data["quoteVolume"]),
                "high_24h": float(data["highPrice"]),
                "low_24h": float(data["lowPrice"])
            }
        except Exception as e:
            print(f"Error fetching ticker {symbol}: {e}")
            return None
    
    def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[Dict]:
        """取得 Order Book"""
        endpoint = f"{self.BASE_URL}/depth"
        params = {"symbol": symbol.upper(), "limit": limit}
        
        try:
            resp = self.session.get(endpoint, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            return {
                "bids": [[float(p), float(q)] for p, q in data.get("bids", [])],
                "asks": [[float(p), float(q)] for p, q in data.get("asks", [])]
            }
        except Exception as e:
            print(f"Error fetching orderbook {symbol}: {e}")
            return None
    
    def get_available_symbols(self) -> List[str]:
        """取得可交易的 Symbol 列表"""
        endpoint = f"{self.BASE_URL}/exchangeInfo"
        
        try:
            resp = self.session.get(endpoint, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            symbols = [
                s["symbol"] for s in data["symbols"]
                if s["quoteAsset"] == "USDT" and s["status"] == "TRADING"
            ]
            return symbols[:50]
        except Exception as e:
            print(f"Error fetching symbols: {e}")
            return []