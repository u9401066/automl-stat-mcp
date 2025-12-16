---
name: debug-workflow
description: Systematic debugging workflow for finding and fixing issues. Triggers: DEBUG, 除錯, bug, 找問題, 為什麼不work, 出錯了, error, fix bug.
---

# Debug Workflow 技能 (除錯流程)

## 描述
系統化的除錯流程，從問題重現到修復驗證。

## 觸發條件
- 「除錯」「debug」「找問題」
- 「為什麼不 work」「出錯了」
- 「error」「fix bug」
- 使用者報告錯誤

---

## 🎯 除錯流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Debug Workflow                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐     │
│   │ REPRODUCE│───▶│ LOCATE   │───▶│   FIX    │───▶│  VERIFY  │     │
│   │  重現    │    │  定位    │    │  修復    │    │  驗證    │     │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘     │
│        │               │               │               │            │
│        ▼               ▼               ▼               ▼            │
│   - 理解錯誤       - 讀取日誌      - 修改程式碼    - 重新測試       │
│   - 收集資訊       - 搜尋程式碼    - 可能多處修改  - 確認修復       │
│   - 重現步驟       - 找到根因      - 不引入新bug   - 更新測試       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Phase 1: REPRODUCE (重現)

### 1.1 收集錯誤資訊

**必須收集：**

| 資訊 | 取得方式 |
|------|----------|
| 錯誤訊息 | 使用者提供 / 日誌 |
| 完整 Traceback | 終端機輸出 / 日誌 |
| 發生情境 | 使用者描述 |
| 重現步驟 | 使用者提供 |

### 1.2 理解錯誤

```
🔴 錯誤報告

錯誤類型：{TypeError / ValueError / etc.}
錯誤訊息：{message}

發生位置：
- 檔案：{filename}
- 行號：{line}
- 函數：{function}

發生情境：
- 操作：{使用者做了什麼}
- 輸入：{輸入了什麼}
```

### 1.3 重現問題

```bash
# 執行測試重現
runTests(files=["{test_file}"], testNames=["{test_name}"])

# 或手動執行
run_in_terminal(command="{重現命令}")
```

**重現成功的判斷：**
- ✅ 看到完全相同的錯誤訊息
- ✅ 錯誤穩定發生（不是偶發）

---

## 📋 Phase 2: LOCATE (定位)

### 2.1 閱讀 Traceback

從下往上讀，找到：
1. **最底層**：錯誤發生的確切位置
2. **往上追溯**：呼叫鏈
3. **自己的程式碼**：從哪裡進入錯誤

### 2.2 搜尋相關程式碼

```bash
# 搜尋錯誤相關的程式碼
grep_search(query="{error_keyword}", isRegexp=false)

# 搜尋函數定義
grep_search(query="def {function_name}", isRegexp=false)

# 搜尋相關類別
grep_search(query="class {class_name}", isRegexp=false)
```

### 2.3 讀取問題檔案

```bash
read_file(filePath="{file}", startLine={error_line - 20}, endLine={error_line + 20})
```

### 2.4 分析根因

```
🔍 根因分析

表面錯誤：{表面上的錯誤訊息}
實際原因：{為什麼會發生這個錯誤}

錯誤類型分類：
□ 邏輯錯誤（程式邏輯不正確）
□ 類型錯誤（資料類型不符）
□ 邊界條件（特殊情況未處理）
□ 外部依賴（API 變更、服務不可用）
□ 設定錯誤（環境變數、設定檔）
□ 路徑錯誤（檔案找不到）
```

---

## 📋 Phase 3: FIX (修復)

### 3.1 設計修復方案

```
🔧 修復方案

問題：{問題描述}
方案：{修復方法}

需要修改：
- `{file1}` - {修改內容}
- `{file2}` - {修改內容}

風險評估：
- 影響範圍：{低/中/高}
- 可能副作用：{說明}
```

### 3.2 實施修復

```bash
# 修改檔案
replace_string_in_file(filePath="{path}", oldString="...", newString="...")

# 如果多處修改
multi_replace_string_in_file(...)
```

### 3.3 修復原則

| 原則 | 說明 |
|------|------|
| 最小改動 | 只修改必要的部分 |
| 不引入新bug | 修復不應破壞其他功能 |
| 理解再改 | 完全理解問題後再修改 |
| 一次改一處 | 不要同時修復多個問題 |

---

## 📋 Phase 4: VERIFY (驗證)

### 4.1 驗證修復

```bash
# 重新執行失敗的測試
runTests(files=["{test_file}"], testNames=["{test_name}"])

# 檢查語法錯誤
get_errors(filePaths=["{modified_files}"])
```

### 4.2 回歸測試

```bash
# 執行所有相關測試
runTests(files=["{related_test_files}"])

# 執行完整測試（如果修改影響大）
runTests()
```

### 4.3 驗證清單

```
✅ 驗證清單

□ 原問題已修復
□ 原測試通過
□ 相關測試通過
□ 無新錯誤產生
□ 靜態分析通過
```

---

## 📋 Phase 5: 記錄與收尾

### 5.1 更新測試

如果原本沒有測試覆蓋這個案例：

```python
def test_{bug_scenario}():
    """
    Regression test for {bug_description}
    
    Bug: {bug_id or description}
    Fixed: {date}
    """
    # 重現原本會失敗的情況
    result = {function_call}
    assert result == expected
```

### 5.2 更新文件

```markdown
# CHANGELOG.md

### Fixed
- {Bug 描述} - {簡短說明}
```

### 5.3 提交修復

```bash
git commit -m "fix({scope}): {bug 描述}

Root cause: {根因}
Solution: {修復方式}

Closes #{issue_number}"
```

---

## 🔧 常見錯誤類型速查

### FileNotFoundError

```bash
# 檢查路徑
ls -la {path}

# 容器內路徑問題？
# Host: /home/eric/workspace251204/sample_data/
# Container: /data/sample_data/
```

### ImportError / ModuleNotFoundError

```bash
# 檢查套件安裝
pip list | grep {package}

# 檢查 Python 環境
which python
```

### TypeError

```python
# 常見原因：
# 1. None 傳入不接受 None 的函數
# 2. 參數順序錯誤
# 3. 字串傳入需要數字的地方
```

### KeyError / IndexError

```python
# 常見原因：
# 1. 字典/列表存取不存在的鍵/索引
# 2. API 回應格式變更
# 3. 資料格式不符預期
```

### ConnectionError

```bash
# 檢查服務狀態
docker compose ps

# 檢查網路
curl http://localhost:{port}/health
```

---

## 💡 除錯技巧

### 1. 二分法定位

```python
# 在懷疑的程式碼中加入 print
print(f"DEBUG: variable = {variable}")
print(f"DEBUG: reached checkpoint 1")
```

### 2. 檢查邊界條件

- 空值 (None, "", [], {})
- 單一元素
- 非常大的值
- 負數
- 特殊字元

### 3. 檢查日誌

```bash
# Docker 日誌
docker compose logs -f {service}

# 過濾錯誤
docker compose logs {service} | grep -i error
```

### 4. 逐步執行

```python
# 使用 breakpoint() 進入互動模式
def problematic_function():
    breakpoint()  # 這裡會暫停
    ...
```

---

## 📌 除錯報告範例

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 Bug 修復報告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 問題描述
FileNotFoundError: /home/eric/sample_data/iris.csv

🔍 根因分析
在 MCP 工具中使用了 Host 路徑，應該使用 Container 路徑

🔧 修復方式
將路徑從 `/home/eric/sample_data/` 改為 `/data/sample_data/`

📁 修改檔案
- `automl-mcp-server/src/infrastructure/.../tools.py`

✅ 驗證結果
- 單元測試：通過
- E2E 測試：通過

📝 預防措施
- 新增路徑驗證，拒絕非 /data/ 開頭的路徑
- 新增測試案例覆蓋此情境
```
