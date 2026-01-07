# Active Context

## Current Status (2026-01-06)

### 🎯 剛完成: 全專案代碼品質審計與發布前清理 (Code Quality Audit)

**核心工作：**
1. **Ruff 規範達成**：透過「外科手術式」手動修復，清除了 `stats-service` 與 `automl-service` 所有的 `B904` (Exception chaining) 與 `W293` (Trailing whitespace) 報錯。
2. **MyPy 類型修正**：
   - `cleaning.py`: 為 `changes` 字典添加 `Dict[str, Any]` 註解，解決屬性訪問錯誤。
   - `power.py`: 為統計結果添加 `float()` 強制轉型，解決 `statsmodels` 回傳 Any 導致的類型不匹配。
   - `direct.py`: 修復了預測結果與推薦字典的類型分配報錯。
3. **uv 環境標準化**：全面切換到 `uv` 作業，確保環境一致性。

**目前品質指標：**
- **automl-service**: 路由層 Ruff 0 報錯。
- **stats-service**: 路由層 Ruff 0 報錯，MyPy 剩餘錯誤已降至基礎設施層。
- **automl-mcp-server**: 待處理 (剩餘 200+ 簽名不一致報錯)。

**已修正文件列表：**
- `stats-service/src/routes/*.py` (全體)
- `automl-service/src/interface/api/routes/*.py` (全體)
- `stats-service/src/routes/__init__.py` (導入修復)

---

## Previous Status (2025-12-17)

### 🎯 平台狀態: v0.5.0 - Visualization + Local Results ✅

**核心設計原則 (重要!):**

> **Agent 只負責四件事：**
> 1. 傳入檔案路徑
> 2. 建立工單（含參數設定）
> 3. 查詢工單狀態
> 4. 取得輸出連結
>
> **所有資料處理、計算、視覺化都是 AutoML 系統內部的事！**

### ✅ 剛完成: Phase 8 Visualization + Local Results

**Phase 8A-8D: Visualization Module**
- `visualization/survival.py` - 生存分析圖（KM 曲線、風險表）
- `visualization/roc.py` - ROC/PR 曲線（信賴區間、校正曲線）
- `visualization/group_comparison.py` - 組間比較（箱形圖、直方圖）
- `visualization/automl.py` - AutoML 結果（特徵重要性、SHAP、學習曲線）

**Results Storage (全部存 MinIO)**
- 分析結果: Redis (7天 TTL) + MinIO (永久)
- 視覺化圖片: MinIO `stats-reports/{user_id}/`
- 查詢工具: `list_analysis_results`, `list_user_visualizations`

**使用者可直接存取:**
- 瀏覽 `./results/eric/` 看自己的分析結果
- 開啟 HTML 報告檢視視覺化圖表
- 複製 PNG 圖表到簡報

### ✅ 已整合

1. **Worker 整合範例**
   - `process_roc_full_eval_job()` 使用 MinIO 上傳
   - 自動儲存圖表到 MinIO stats-reports bucket
   - 生成分析結果並存到 Redis + MinIO

3. **文檔更新**
   - README.md, CHANGELOG.md, ARCHITECTURE_AUDIT.md
   - systemPatterns.md (3 個新 patterns)

### 📋 下一步

1. **整合其餘 worker tasks** - 將 JobResultsManager 應用到所有分析任務
2. **圖表自動化** - 各分析類型自動產生對應圖表
3. **Phase 9: Meta-Analysis** - 固定效應、隨機效應、森林圖

## Current Goals

- ## 當前工作焦點
- ✅ 發現並修復關鍵安全漏洞
- ## 重大發現 - 安全漏洞
- 透過「真正能抓 Bug 的測試」發現：
- 1. 🔴 **Path Traversal 攻擊** - `/etc/passwd` 可被讀取！已修復
- 2. 🟡 **Power 分析輸入驗證不足** - effect_size=0, alpha>1 等被接受，已修復
- ## 今日完成
- 1. ✅ CI/CD 自動化測試 (.github/workflows/test.yml)
- 2. ✅ Performance Benchmarks (11 tests, ~30ms avg)
- 3. ✅ E2E 測試覆蓋改善 (91→114 passed)
- 4. ✅ 安全漏洞修復 (路徑遍歷 + 輸入驗證)
- 5. ✅ 安全測試 (24 tests)
- ## 測試結果
- - 149 passed, 12 skipped, 0 failed
- - 安全測試 24/24 通過
- ## 下一步
- - 更新 ROADMAP 標記安全掃描完成
- - 檢查其他端點是否有類似漏洞

## Current Blockers

- None

## References

- [ROADMAP](../docs/ROADMAP.md) - 完整開發藍圖
- [CHANGELOG](../CHANGELOG.md) - 版本更新記錄
- [Design Issue #001](../docs/design-issues/001-data-cleaning-workflow.md) - 資料清理設計