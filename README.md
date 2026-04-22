# TRADE-Crypto

LLM-driven crypto trading system with Freqtrade execution.

## Architecture

```
Signal Analyzer → Decision Agent (LLM) → Freqtrade Adapter → Freqtrade
```

- **Signal Analyzer**: 讀取 Binance 數據，計算技術指標
- **Decision Agent**: LLM 決策引擎，評估買/賣/持有
- **Freqtrade Adapter**: 與 Freqtrade API 溝通，發送交易指令
- **Freqtrade**: 純執行者，負責實際交易

## 目錄結構

```
trade-crypto/
├── signal_analyzer/      # 市場數據分析
│   ├── crypto_data.py    # Binance API
│   └── crypto_indicators.py # 技術指標計算
├── decision_agent/       # LLM 決策引擎
│   ├── agent.py          # 決策邏輯
│   └── prompts/          # Prompt 模板
├── freqtrade_adapter/    # Freqtrade API
│   └── adapter.py        # API 適配器
└── config/
    └── config.yaml        # 設定檔
```

## 使用方式

```bash
cd ~/trade-crypto

# 掃描市場
python3 -c "
import sys; sys.path.insert(0, '.')
from signal_analyzer.crypto_indicators import CryptoIndicators
ci = CryptoIndicators()
print(ci.analyze('BTCUSDT'))
"

# 執行 Decision Agent
python3 -m decision_agent.agent
```

## 與 Freqtrade 的整合

Freqtrade 運行在 dry-run 模式：
- API: http://127.0.0.1:18798
- Username: freqtrade
- Password: freqtrade123

Decision Agent 會：
1. 掃描市場信號
2. 評估買/賣/持有
3. 將 BUY 決策的幣種寫入 Freqtrade whitelist

## 重要提醒

⚠️ 這是一個系統藍圖，需要進一步開發：
- LLM API 整合（目前使用規則引擎）
- 完整的決策進化系統
- 風險管理增強

**注意**：目前所有交易都是 dry-run 模擬，沒有真實資金風險。
