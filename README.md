# Trade Crypto

> 🤖 WSS (Wholesale Whale Sentiment & Strength) 加密貨幣交易系統
> 
> 雙層 AI 決策引擎 + Binance API + Freqtrade 整合

---

## 📊 系統定位

**本質：加密貨幣市場機會發掘引擎**

Trade Crypto 是一個**智能量化交易分析系統**，用於追蹤、分析加密貨幣市場，並生成交易信號。

**職責分工：**
- Trade Crypto 負責資料收集、技術指標計算、信號生成、進化學習
- 交易執行交給 Freqtrade 或其他交易系統

---

## 🏗️ 系統架構

```
┌─────────────────────────────────────────────────────────────┐
│                    Trade Crypto                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 1: 規則引擎          Layer 2: AI 裁決              │
│  ─────────────────          ─────────────────              │
│  • RSI 評估                • MiniMax API                  │
│  • KD 交叉檢測             • 自然語言解析                  │
│  • MACD 動量               • 矛盾仲裁                      │
│  • Bollinger 位置                                          │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  數據源                    分析引擎                        │
│  ─────────                ─────────                        │
│  • Binance API           • WSS 指標系統                   │
│  • CoinGecko             • 技術指標（OBV/ATR/             │
│  • LightRAG               •   VWAP/Ichimoku/Fib）           │
│                           • 雙層決策系統                    │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  輸出                    執行                              │
│  ─────                   ─────                              │
│  • WSS Score (0-100)     • Freqtrade 橋樑                  │
│  • BUY/SELL/HOLD         • 白名單管理                      │
│  • 信心度評估             • Dry Run / 實盤                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 核心功能

### 1. WSS 指標系統

WSS（批發鯨魚情緒與強度）指標從四大維度評估加密貨幣：

| 維度 | 權重 | 指標 |
|------|------|------|
| 基本面 | 20% | 用途、代幣經濟、團隊 |
| 鏈上指標 | 25% | 活躍地址、TVL、MVRV |
| 技術指標 | 30% | RSI、KD、MACD、EMA |
| 市場情緒 | 25% | 資金费率、未平倉量 |

**WSS Score 等級：**
- 🟢🟢 80-100：STRONG_BUY（強烈建議買入）
- 🟢 65-80：BUY（建議買入）
- 🟡 45-65：NEUTRAL（建議觀望）
- 🔴 30-45：SELL（建議賣出）
- 🔴🔴 0-30：STRONG_SELL（強烈建議賣出）

### 2. 雙層決策系統

```
Layer 1: 規則引擎
  └→ 指標觸發 → 候選名單
      ↓
Layer 2: AI 裁決（矛盾時）
  └→ 矛盾時 → AI 參考（情緒、新聞、鏈上）
```

**好處：**
1. 不會讓 AI 處理簡單決策
2. AI 只在複雜時介入
3. 可解釋性高
4. 回測容易

### 3. 市場龍頭掃描

- 從 Binance 獲取成交量前 30 名幣種
- 對每個幣種計算 WSS 分數
- 只對前 10 名進行完整分析
- 自動生成 Freqtrade 白名單建議

### 4. 技術指標

| 指標 | 說明 |
|------|------|
| RSI | 相對強度指數 |
| KD | 隨機指標 |
| MACD | 指數平滑異同移動平均線 |
| EMA | 指數移動平均線 |
| Bollinger | 布林帶 |
| OBV | 能量潮指標 |
| ATR | 平均真實波幅 |
| VWAP | 成交量加權平均價 |
| Ichimoku | 一目均衡表 |
| Fibonacci | 斐波那契回撤 |

---

## 📦 安裝

```bash
# Clone
git clone https://github.com/ZCrystalC33/trade-crypto.git
cd trade-crypto

# 安裝依賴
pip install requests pandas numpy

# 配置 API Key（可選）
mkdir -p ~/.openclaw/credentials
echo "BINANCE_API_KEY=your_key" > ~/.openclaw/credentials/binance.key
echo "BINANCE_API_SECRET=your_secret" >> ~/.openclaw/credentials/binance.key
```

---

## 🚀 快速開始

### 1. WSS 快速分析

```python
from signal_analyzer.wss_indicator import quick_analyze

result = quick_analyze("BTCUSDT")
print(f"WSS Score: {result['wss_score']}")
print(f"Verdict: {result['verdict']}")
```

### 2. 市場龍頭掃描

```python
from signal_analyzer.wss_top_scanner import create_scanner

scanner = create_scanner()
scanner.scan_top_symbols(limit=30)

print(scanner.summary())        # 打印報告
buys = scanner.get_buy_signals()  # 取得買入信號
```

### 3. 雙層決策

```python
from signal_analyzer.layer2_ai import DualLayerTradingSystem

system = DualLayerTradingSystem()
system.scan_and_decide(["BTCUSDT", "ETHUSDT"])

print(system.summary())
```

### 4. Freqtrade 白名單管理

```python
from signal_analyzer.wss_whitelist_manager import create_whitelist_manager

manager = create_whitelist_manager()
manager.scan_and_decide(top_n=10, min_score=50)

print(manager.summary())
```

---

## 📁 目錄結構

```
trade-crypto/
├── signal_analyzer/           # 核心分析模組
│   ├── wss_indicator.py       # WSS 指標系統
│   ├── wss_top_scanner.py     # 市場龍頭掃描
│   ├── wss_whitelist_manager.py # 白名單管理
│   ├── wss_freqtrade_connector.py # Freqtrade 橋樑
│   ├── dual_layer_decision.py # 雙層決策 Layer 1
│   ├── layer2_ai.py          # 雙層決策 Layer 2
│   ├── binance_provider.py   # Binance API
│   ├── crypto_indicators.py  # 技術指標
│   ├── crypto_data.py        # 數據獲取
│   ├── lightrag_analyzer.py  # LightRAG 分析
│   └── freqtrade_integration.py # Freqtrade API
├── config/                    # 配置文件
│   └── config.yaml
├── data/                     # 數據目錄
├── CHANGELOG.md              # 更新日誌
└── README.md                 # 本文件
```

---

## 🔧 配置

### Freqtrade Dry Run 模式確認

```bash
curl -u "freqtrade:freqtrade123" http://localhost:18798/api/v1/show_config
```

確認 `dry_run: true` 後再進行實盤操作。

### API Key 安全儲存

```bash
# 安全性：600（只有擁有者可讀）
chmod 600 ~/.openclaw/credentials/binance.key
```

---

## 📈 工作流程

```
1. 市場掃描
   Binance Top 30 → WSS 快速評估 → 排序

2. 精細分析
   前10名 → 完整 WSS 分析 → Layer 2 AI 裁決

3. 決策輸出
   BUY/SELL/HOLD → 信心度 → 風險等級

4. 執行交易
   Freqtrade API → forcebuy/forcesell → Dry Run

5. 白名單更新
   WSS 評估 → 白名單建議 → 配置更新
```

---

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

---

## 📄 授權

MIT License

---

## 🔗 相關連結

- [Freqtrade](https://www.freqtrade.io/)
- [Binance API](https://developers.binance.com/)
- [LightRAG](https://github.com/HKUPS/LightRAG)
- [MiniMax API](https://www.minimax.io/)
