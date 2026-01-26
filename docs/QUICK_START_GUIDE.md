# 快速啟動指南

AutoML Stat MCP 現在有多種啟動方式！

## 🚀 方式一：一鍵安裝（推薦新手）

```bash
./quick-install.sh
```

這個腳本會：
- ✅ 自動檢查系統需求
- ✅ 設定環境變數
- ✅ 下載 Docker 映像檔
- ✅ 啟動服務
- ✅ 執行健康檢查

## ⚡ 方式二：啟動腳本（推薦）

```bash
# 預設模式（僅統計分析，推薦新手）
./start.sh

# ML 模式（包含 AutoML 訓練）
./start.sh ml

# 完整模式（包含 MinIO 物件儲存）
./start.sh full

# 停止服務
./stop.sh
```

特色：
- 🎨 彩色界面
- 📊 自動健康檢查
- 📝 友善的錯誤訊息
- 📖 啟動後提示下一步

## 🎯 方式三：Makefile（最方便）

```bash
# 查看所有可用指令
make help

# 服務管理
make start          # 啟動預設服務
make start-ml       # 啟動 ML 服務
make start-full     # 啟動完整服務
make stop           # 停止所有服務
make restart        # 重啟服務
make restart-mcp    # 只重啟 MCP

# 監控
make logs           # 查看所有日誌
make logs-mcp       # 只看 MCP 日誌
make logs-stats     # 只看統計服務日誌
make status         # 服務狀態
make health         # 健康檢查

# 開發
make rebuild        # 重建並啟動
make rebuild-mcp    # 只重建 MCP
make shell-mcp      # 進入 MCP 容器
make test           # 執行測試

# 擴展
make scale-stats    # 擴展統計 worker
make scale-ml       # 擴展 ML worker

# 清理
make clean          # 停止並清理容器
make clean-all      # 完全清理（含資料）
```

## 🐳 方式四：Docker Compose（進階）

```bash
# 預設
docker compose up -d

# ML 訓練
docker compose --profile ml up -d

# 完整（含 MinIO）
docker compose --profile full up -d

# 停止
docker compose down

# 擴展 worker
docker compose up -d --scale stats-worker=4
```

## 📊 比較

| 方式 | 優點 | 適合對象 |
|------|------|----------|
| `quick-install.sh` | 一鍵完成，自動檢查 | 🆕 新手 |
| `start.sh` | 簡單直觀，有美化 | 👤 一般用戶 |
| `Makefile` | 功能完整，快速 | 👨‍💻 開發者 |
| `docker compose` | 最靈活，可自訂 | 🔧 進階用戶 |

## 🆘 常見問題

### Q: 啟動失敗？
```bash
# 檢查日誌
make logs

# 重新啟動
make restart
```

### Q: 修改程式碼後要重建？
```bash
# 重建 MCP 服務
make rebuild-mcp

# 或重建所有服務
make rebuild
```

### Q: 如何進入容器除錯？
```bash
# 進入 MCP 容器
make shell-mcp

# 或使用 docker
docker compose exec automl-mcp /bin/bash
```

### Q: 如何查看即時日誌？
```bash
# 所有服務
make logs

# 只看 MCP
make logs-mcp

# 最新 50 行
make tail
```

## 💡 推薦工作流程

1. **首次安裝**
   ```bash
   ./quick-install.sh
   ```

2. **日常啟動**
   ```bash
   make start
   ```

3. **查看日誌**
   ```bash
   make logs-mcp
   ```

4. **健康檢查**
   ```bash
   make health
   ```

5. **重啟服務**
   ```bash
   make restart-mcp
   ```

6. **停止服務**
   ```bash
   make stop
   ```

## 🎓 進階技巧

### 擴展 Worker 數量
```bash
# 擴展統計 worker
make scale-stats

# 擴展 ML worker
make scale-ml
```

### 只重建特定服務
```bash
make rebuild-mcp
```

### 查看資源使用
```bash
make top
```

### 完全清理重來
```bash
make clean-all
docker compose build --no-cache
make start
```

---

**提示**: 所有腳本都會自動進行健康檢查，確保服務正常運作！
