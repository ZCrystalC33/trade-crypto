# CHANGELOG.md - Trade Crypto

## [Unreleased] - 2026-04-23

### Added

#### WSS 交易系統
- **wss_indicator.py** - WSS (Wholesale Whale Sentiment & Strength) 指標系統
  - 四大維度：基本面、鏈上指標、技術指標、市場情緒
  - WSS Score 0-100 分評估
  - 支持 BUY/SELL/HOLD 決策

- **wss_top_scanner.py** - 市場龍頭幣種掃描器
  - 從 Binance 獲取成交量前30名
  - 對前10名進行完整 WSS 分析
  - 買入/賣出信號識別

- **wss_whitelist_manager.py** - Freqtrade 白名單管理器
  - 根據 WSS 分數過濾候選幣種
  - 生成 Freqtrade 格式配置
  - 白名單新增/移除建議

- **wss_freqtrade_connector.py** - WSS + Freqtrade 橋樑
  - scan_symbols() - 掃描標的
  - execute_all() - 執行交易
  - 支持 dry-run 模式

#### 雙層決策系統
- **dual_layer_decision.py** - Layer 1 規則引擎
  - RSI、KD、MACD、EMA、Bollinger 指標
  - 信心度評估
  - 矛盾檢測（進 Layer 2）

- **layer2_ai.py** - Layer 2 AI 裁決引擎
  - MiniMax API 整合
  - 自然語言回應解析
  - 自然語言理由生成

#### 數據源整合
- **binance_provider.py** - Binance API 提供者
  - 現貨/期貨市場數據
  - 資金费率、未平倉量
  - 帳戶信息（需要 API Key）

- **crypto_indicators.py** - 技術指標計算器
  - RSI、MACD、KD、Bollinger
  - OBV（能量潮）
  - ATR（平均真實波幅）
  - VWAP（成交量加權平均價）
  - Ichimoku 雲圖
  - Fibonacci 回撤水平

#### 分析系統
- **lightrag_analyzer.py** - LightRAG 文檔分析流程
  - 文本攝入與處理
  - 混合查詢（hybrid/keyword/vector）
  - 實體關係圖譜

- **freqtrade_integration.py** - Freqtrade API 整合
  - forcebuy/forcesell
  - 倉位查詢
  - 交易歷史
  - Dry Run 模式支持

### Changed

#### AI 分析優化
- 改用簡潔 Prompt 格式（減少 tokens）
- 結構化回應解析
- 備用解析器（fallback parser）
- 60秒超時設定

#### WSS 增強
- 新增 OBV、ATR、VWAP、Ichimoku、Fibonacci 指標
- 修正 Ichimoku 窗口索引計算
- ATR 波動性信號

### Fixed

- **crypto_indicators.py**
  - Ichimoku 邊界計算錯誤
  - 窗口索引從 8 改為 9

---

## [v0.1.0] - 2026-04-23

### Added

- Initial implementation
- WSS indicator system
- Dual-layer decision system (Layer 1 Rules + Layer 2 AI)
- Binance API provider
- Basic crypto indicators (RSI, MACD, KD, Bollinger, EMA)

---

## Files Structure

```
signal_analyzer/
├── wss_indicator.py              # WSS 核心指標
├── wss_top_scanner.py            # 市場龍頭掃描
├── wss_whitelist_manager.py      # 白名單管理
├── wss_freqtrade_connector.py    # Freqtrade 橋樑
├── dual_layer_decision.py        # 雙層決策 Layer 1
├── layer2_ai.py                  # 雙層決策 Layer 2 (AI)
├── binance_provider.py           # Binance API
├── crypto_indicators.py         # 技術指標計算
├── crypto_data.py               # 數據獲取
├── lightrag_analyzer.py         # LightRAG 分析流程
└── freqtrade_integration.py    # Freqtrade API
```
