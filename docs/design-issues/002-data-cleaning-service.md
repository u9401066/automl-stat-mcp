# Data Cleaning Service 設計規劃

> Created: 2025-12-09
> Status: 📋 Planning

## 1. 問題背景

### 為什麼需要獨立的 Data Cleaning Service？

目前的架構中，資料清理功能散落在：
- `automl-mcp-server/data_cleaner.py` - 內部模組，非 MCP tool
- `stats-worker/auto_analyze_task.py` - 只有偵測，無清理
- `upload_tools.py` - 欄位名稱清理（內建於上傳）

**問題：**
1. Agent 無法直接呼叫資料清理功能
2. 傾向分數分析要求 binary (0/1)，但真實資料常是 200/400 等
3. 研究資料常有複雜的清理需求（Excel 雜亂欄位、缺失值、異常值）
4. 缺乏標準化的資料前處理流程

## 2. 設計決策

### 選項 A: 嵌入現有 MCP Server（已嘗試）
```
automl-mcp-server
└── handlers/
    └── cleaning_tools.py  ← 新增
```
- ✅ 簡單，不需新服務
- ❌ MCP Server 變胖
- ❌ 邏輯混淆（MCP 應該是 thin wrapper）

### 選項 B: 獨立 Data Cleaning Service（建議）
```
┌─────────────────┐
│ automl-mcp      │
│ (MCP tools)     │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐     ┌─────────────────┐
│ automl-service  │     │ cleaning-service│  ← 新增
└─────────────────┘     └─────────────────┘
         │                      │
         ▼                      ▼
┌─────────────────┐     ┌─────────────────┐
│ automl-worker   │     │ stats-service   │
└─────────────────┘     └─────────────────┘
```
- ✅ 職責清晰
- ✅ 可獨立擴展
- ✅ 複用於 AutoML 和 Stats
- ❌ 多一個服務

### 選項 C: 整合到 Stats Service
```
stats-service
└── routes/
    ├── auto_analyze.py
    ├── eda.py
    ├── cleaning.py  ← 新增
    └── ...
```
- ✅ 不需新服務
- ✅ 資料清理常在分析前
- ❌ Stats Service 職責擴大

### 決定：採用選項 C（整合到 Stats Service）

**理由：**
1. 資料清理是統計分析的前置步驟，邏輯上相關
2. 避免服務過度拆分
3. Stats Service 已有 pandas 環境
4. 可共用 Redis + MinIO 基礎設施

## 3. 架構設計

### 3.1 服務架構

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AI Agent (Claude/Copilot)                    │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ MCP Protocol
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         AutoML MCP Server (8002)                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Tools:                                                          │ │
│  │ • Cleaning: convert_to_binary, handle_missing, encode_categorical│
│  │ • Analysis: auto_analyze, tableone, roc_analysis                │ │
│  │ • Training: submit_automl_job, quick_train                      │ │
│  └────────────────────────────────────────────────────────────────┘ │
└──────────────────┬───────────────────────────────────────┬──────────┘
                   │                                       │
                   ▼                                       ▼
┌──────────────────────────────────┐  ┌───────────────────────────────┐
│     AutoML Service (8001)        │  │    Stats Service (8003)       │
│  • Dataset management            │  │  • Statistical analysis       │
│  • Job submission                │  │  • Data cleaning (NEW)        │
│  • Model management              │  │  • TableOne generation        │
└──────────────────────────────────┘  └───────────────────────────────┘
                   │                                       │
                   ▼                                       ▼
┌──────────────────────────────────┐  ┌───────────────────────────────┐
│     AutoML Worker                │  │    Stats Worker               │
│  • AutoGluon training            │  │  • EDA reports                │
│  • Model evaluation              │  │  • Statistical tests          │
└──────────────────────────────────┘  └───────────────────────────────┘
```

### 3.2 新增 API Endpoints（Stats Service）

```
POST /cleaning/convert-binary
POST /cleaning/encode-categorical
POST /cleaning/handle-missing
POST /cleaning/remove-columns
POST /cleaning/filter-rows
POST /cleaning/rename-columns
GET  /cleaning/column-info
POST /cleaning/auto-clean
```

### 3.3 新增 MCP Tools

| Tool | 描述 | 同步/非同步 |
|------|------|------------|
| `convert_to_binary` | 轉換欄位為 0/1 | 同步 |
| `encode_categorical` | 類別編碼 | 同步 |
| `handle_missing_values` | 缺失值處理 | 同步 |
| `remove_columns` | 移除欄位 | 同步 |
| `filter_rows` | 篩選資料列 | 同步 |
| `rename_columns` | 重新命名欄位 | 同步 |
| `get_column_info` | 取得欄位資訊 | 同步 |
| `auto_clean_dataset` | 自動清理 | 同步 |

## 4. 實作計畫

### Phase 1: Stats Service 擴充（1 天）✅ 完成
- [x] 新增 `stats-service/src/routes/cleaning.py`
- [x] 實作同步清理 API endpoints
- [x] 新增 Pydantic schemas

### Phase 2: MCP Tools 更新（1 天）✅ 完成
- [x] `cleaning_tools.py` 直接呼叫 Stats Service API
- [x] 使用 StatsClient 進行 HTTP 呼叫
- [x] 測試 MCP tools 載入

### Phase 3: 整合與測試（進行中）
- [ ] 整合測試（upload → clean → analyze → train）
- [x] 更新 docker-compose.yml (stats-service 掛載 /data)
- [x] 部署到 Docker

## 5. 資料流程

### 標準工作流程
```
User: "分析 Ropica 200 vs 400 的治療效果"

Agent:
1. upload_dataset(file_path, name) → dataset_id + 處理過的 csv_path
2. get_column_info(csv_path) → 發現 Ropica_ML 是 200/400
3. convert_to_binary(csv_path, "Ropica_ML", {200: 0, 400: 1}) → cleaned_path
4. run_propensity_analysis(cleaned_path, treatment="Ropica_ML_binary", ...)
5. 返回結果給用戶
```

## 6. 檔案結構

```
stats-service/
└── src/
    └── routes/
        ├── __init__.py
        ├── auto_analyze.py
        ├── eda.py
        ├── tableone.py
        ├── propensity.py
        ├── survival.py
        ├── power.py
        ├── roc.py
        └── cleaning.py  ← 新增

automl-mcp-server/
└── src/
    └── infrastructure/
        └── mcp/
            └── handlers/
                ├── cleaning_tools.py  ← 修改：呼叫 stats-service API
                └── stats_client.py    ← 新增清理方法
```

## 7. 風險與緩解

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| Stats Service 負載增加 | 性能下降 | 清理操作輕量，影響有限 |
| 檔案傳輸開銷 | 延遲增加 | 使用共享 Volume，不傳輸資料 |
| API 相容性 | 升級困難 | 版本化 API |

## 8. 成功指標

- [ ] 傾向分數分析可處理非 0/1 資料
- [ ] 資料清理工具可透過 MCP 呼叫
- [ ] 完整工作流程：上傳 → 清理 → 分析 → 訓練
- [ ] 文件更新完成
