---
name: readme-updater
description: Intelligently update README.md to reflect code changes, new features, and API updates. Use when adding new features, changing APIs, or syncing documentation with code. Triggers: readme, 說明, 更新說明, update readme, 文檔同步, 更新文檔, documentation, docs.
---

# README 更新技能

## 描述
智能更新 README.md，保持與程式碼同步，支援多語言版本維護。

## 觸發條件
- 「更新 README」
- 被 git-precommit 編排器調用
- 新增重要功能後

## 法規依據
- 憲法：CONSTITUTION.md 第 6 條

## 更新策略

### 1. 偵測變更類型
- 新功能 → 更新功能列表
- 新依賴 → 更新安裝說明
- API 變更 → 更新使用範例
- 結構變更 → 更新專案結構

### 2. 更新區塊

| 區塊 | 條件 |
|------|------|
| 功能列表 | 新增/移除功能 |
| 安裝說明 | 依賴變更 |
| 使用範例 | API 變更 |
| 專案結構 | 目錄結構變更 |
| 配置說明 | 新增設定選項 |

### 3. 保持區塊
以下區塊不自動修改：
- 授權資訊
- 貢獻指南
- 致謝

---

## 🌐 多語言支援 (i18n)

### 檔案結構
```
README.md          # 主 README（預設語言）
README.zh-TW.md    # 繁體中文版本（可選）
README.en.md       # 英文版本（可選）
```

### 同步規則
```
如果使用者提供中文內容 → 同步到英文版（如存在）
如果使用者提供英文內容 → 同步到中文版（如存在）
如果主 README 變更 → 同步所有語言版本
```

### 翻譯原則
- 技術術語保持一致（使用術語表）
- 程式碼範例不翻譯，只翻譯註解
- 保持 Markdown 結構完全對應
- 連結指向對應語言版本

### 術語對照表

| 中文 | English |
|------|---------|
| 憲法 | Constitution |
| 子法 | Bylaws |
| 技能 | Skills |
| 記憶庫 | Memory Bank |
| 領域驅動設計 | Domain-Driven Design (DDD) |
| 資料存取層 | Data Access Layer (DAL) |
| 提交 | Commit |
| 工作流 | Workflow |
| 架構 | Architecture |
| 模組化 | Modular |

### 同步檢查清單
```markdown
- [ ] 章節數量一致
- [ ] 程式碼區塊一致
- [ ] 連結有效性
- [ ] 術語一致性
```

---

## 輸出格式

```
📝 README 更新分析

變更偵測：
  ✅ 新增功能：用戶認證模組
  ✅ 新增依賴：bcrypt

建議更新：
  [功能列表] 新增「🔐 用戶認證」
  [安裝說明] 新增 bcrypt 安裝指令

預覽：
  ## 功能
  - 🤖 Claude Skills
  - 📝 Memory Bank
+ - 🔐 用戶認證（新增）

多語言同步：
  ⏭️ README.zh-TW.md - 不存在，跳過
```
