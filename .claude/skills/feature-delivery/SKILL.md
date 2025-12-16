---
name: feature-delivery
description: Complete feature delivery workflow including testing, documentation, and handoff to ensure features are production-ready. Use when a feature is complete and needs final checks before release. Triggers: DELIVER, 交付, 完成功能, feature done, ship it, 交給用戶, ready to ship, 可以上線, 發布, release, 準備好了.
---

# Feature Delivery 技能 (功能交付)

## 描述
確保功能完整交付，包含所有必要文件、測試、和使用說明。

## 觸發條件
- 「交付 {功能}」
- 「完成功能」「feature done」
- 「ship it」「準備上線」

---

## 🎯 交付檢查清單

```
┌─────────────────────────────────────────────────────────────────────┐
│                   Feature Delivery Checklist                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  [1] 程式碼完整性                                                    │
│      □ 所有功能實現完成                                              │
│      □ 無 TODO/FIXME 遺留                                           │
│      □ 程式碼已格式化                                                │
│                                                                      │
│  [2] 測試覆蓋                                                        │
│      □ 單元測試                                                      │
│      □ 整合測試（如需要）                                            │
│      □ E2E 測試（如需要）                                            │
│                                                                      │
│  [3] 文件更新                                                        │
│      □ README 更新（如需要）                                         │
│      □ CHANGELOG 更新                                                │
│      □ API 文件（如需要）                                            │
│      □ 使用說明                                                      │
│                                                                      │
│  [4] 品質檢查                                                        │
│      □ 靜態分析通過                                                  │
│      □ 無安全漏洞                                                    │
│      □ 效能可接受                                                    │
│                                                                      │
│  [5] 交付物                                                          │
│      □ 交付物清單                                                    │
│      □ 使用範例                                                      │
│      □ 已知限制                                                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Phase 1: 程式碼完整性檢查

### 1.1 檢查 TODO/FIXME

```bash
# 搜尋未完成的標記
grep_search(query="TODO|FIXME|XXX|HACK", isRegexp=true)
```

處理方式：
- **必須修復**：立即修復
- **可以延後**：建立 Issue 並記錄
- **已過時**：刪除

### 1.2 程式碼格式化

```bash
# Python 格式化
run_in_terminal(command="ruff format {path}")

# 檢查
run_in_terminal(command="ruff check {path}")
```

### 1.3 確認功能完整

```
功能：{功能名稱}

需求檢查：
□ {需求 1} - ✅ 已實現
□ {需求 2} - ✅ 已實現
□ {需求 3} - ✅ 已實現
```

---

## 📋 Phase 2: 測試覆蓋

### 2.1 執行所有相關測試

```bash
# 單元測試
runTests(files=["{service}/tests/unit/"])

# 整合測試
runTests(files=["{service}/tests/integration/"])

# E2E 測試
runTests(files=["tests/"])
```

### 2.2 檢查覆蓋率（可選）

```bash
runTests(mode="coverage", coverageFiles=["{target_files}"])
```

### 2.3 測試報告

```
測試結果：{功能名稱}

單元測試：15/15 passed ✅
整合測試：5/5 passed ✅
E2E 測試：3/3 passed ✅

覆蓋率：85% ✅
```

---

## 📋 Phase 3: 文件更新

### 3.1 CHANGELOG 更新

```markdown
## [Unreleased]

### Added
- {新功能描述} (#issue)
  - {子功能 1}
  - {子功能 2}
```

### 3.2 README 更新（如需要）

如果是使用者可見的功能：
- 更新功能列表
- 新增使用範例
- 更新安裝說明（如有新依賴）

### 3.3 API 文件（如適用）

```markdown
## {API 名稱}

### 描述
{功能描述}

### 端點
`POST /api/v1/{endpoint}`

### 請求
```json
{
  "param1": "value1",
  "param2": "value2"
}
```

### 回應
```json
{
  "result": "...",
  "status": "success"
}
```

### 範例
{curl 或 Python 範例}
```

---

## 📋 Phase 4: 品質檢查

### 4.1 靜態分析

```bash
# Python
ruff check {path}
mypy {path}  # 如有使用

# 檢查結果
get_errors(filePaths=["{paths}"])
```

### 4.2 安全檢查

```bash
# 檢查敏感資訊
grep_search(query="password|secret|api_key|token", isRegexp=true, includePattern="{feature_path}")

# 確認無硬編碼密碼
# 確認使用環境變數
```

### 4.3 效能考量

- 是否有明顯的效能瓶頸？
- 資料量大時是否可行？
- 需要快取嗎？

---

## 📋 Phase 5: 產出交付物

### 5.1 交付物清單

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 功能交付：{功能名稱}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📅 完成日期：YYYY-MM-DD
👤 負責人：{name}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 交付檔案清單
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

新增：
- `{path/to/new/file1}` - {說明}
- `{path/to/new/file2}` - {說明}

修改：
- `{path/to/modified/file}` - {變更說明}

文件：
- `README.md` - 更新功能列表
- `CHANGELOG.md` - 新增 v{x.x.x} 條目

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 測試狀態
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| 類型 | 數量 | 狀態 |
|------|------|------|
| 單元測試 | {N} | ✅ |
| 整合測試 | {N} | ✅ |
| E2E 測試 | {N} | ✅ |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📖 使用說明
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 基本用法

```{language}
{基本使用範例}
```

### 進階用法

```{language}
{進階使用範例}
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 已知限制
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- {限制 1}
- {限制 2}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔮 後續改進建議
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- {改進建議 1}
- {改進建議 2}
```

### 5.2 Git 提交

```bash
# 使用 git-precommit skill
# 「準備 commit」

git commit -m "feat({scope}): {功能描述}

- {子功能 1}
- {子功能 2}

Closes #{issue_number}"
```

---

## ⚠️ 交付前最終確認

```
📋 最終確認清單

程式碼：
□ 所有功能實現 ✅
□ 無 TODO/FIXME ✅
□ 程式碼格式化 ✅

測試：
□ 單元測試通過 ✅
□ 整合測試通過 ✅
□ E2E 測試通過 ✅

文件：
□ CHANGELOG 更新 ✅
□ README 更新（如需要） ✅
□ 使用說明完整 ✅

品質：
□ 靜態分析通過 ✅
□ 無安全問題 ✅

交付：
□ 交付物清單完整 ✅
□ 使用範例可執行 ✅
□ 已知限制已說明 ✅

✅ 準備交付！
```

---

## 💡 快速交付模式

如果是小功能，可以簡化為：

```
1. 測試通過確認
2. CHANGELOG 更新
3. 簡短交付清單
4. Git 提交
```
