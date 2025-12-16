# 子法：檔案路徑規範

> 依據憲法第 7.1 條「測試即文檔」、第 7.2 條「環境即程式碼」訂定

---

## 第 1 條：路徑類型定義

本專案存在 **兩種環境**，路徑必須區分：

| 環境 | 說明 | 範例 |
|------|------|------|
| **Host（本機）** | 開發者電腦或伺服器 | `/home/eric/workspace251204/sample_data/iris.csv` |
| **Container（容器）** | Docker 容器內部 | `/data/sample_data/iris.csv` |

### 1.1 路徑映射關係

```yaml
# docker-compose.yml 掛載
Host 路徑                           →  Container 路徑
./sample_data                       →  /data/sample_data (read-only)
./projects                          →  /data/projects (read-write)
```

---

## 第 2 條：何時使用哪種路徑

### 2.1 使用 Container 路徑的場景

| 場景 | 使用路徑 | 範例 |
|------|----------|------|
| MCP 工具參數 | `/data/...` | `csv_path="/data/sample_data/iris.csv"` |
| 容器內程式碼 | `/data/...` | `pd.read_csv("/data/sample_data/iris.csv")` |
| API 請求 | `/data/...` | `{"source_path": "/data/projects/my_study/data.csv"}` |

### 2.2 使用 Host 路徑的場景

| 場景 | 使用路徑 | 範例 |
|------|----------|------|
| 本機測試（無 Docker） | 絕對路徑 | `/home/eric/workspace251204/sample_data/iris.csv` |
| E2E 測試（檢查檔案存在） | 絕對路徑 | `os.path.exists("/home/eric/.../iris.csv")` |
| IDE 開發 | 相對或絕對 | `sample_data/iris.csv` |

---

## 第 3 條：測試檔案放置規範

### 3.1 測試檔案位置

```
workspace/
├── tests/                          # 整合測試、E2E 測試
│   ├── test_e2e.py
│   ├── test_e2e_full.py
│   └── requirements.txt
├── automl-mcp-server/
│   └── tests/                      # MCP Server 單元測試
│       ├── unit/
│       │   ├── test_error_scenarios_isolated.py
│       │   └── test_service_mock_isolated.py
│       └── integration/
├── automl-service/
│   └── tests/                      # AutoML Service 單元測試
├── stats-service/
│   └── tests/                      # Stats Service 單元測試
└── stats-worker/
    └── tests/                      # Stats Worker 單元測試
```

### 3.2 禁止放置位置

```
❌ workspace/test.py               # 根目錄禁止放測試
❌ workspace/temp_test.py          # 禁止臨時測試
❌ workspace/sample_data/test.py   # sample_data 是資料夾
❌ 任何服務的 src/ 內放測試        # 程式碼與測試分離
```

### 3.3 測試資料位置

```
✅ workspace/sample_data/           # 共用範例資料
✅ workspace/tests/fixtures/        # E2E 測試專用 fixtures
✅ {service}/tests/fixtures/        # 服務單元測試 fixtures
❌ workspace/datasets/              # 使用者資料，非測試資料
```

---

## 第 4 條：常見錯誤與修正

### 4.1 路徑混淆錯誤

```python
# ❌ 錯誤：在 MCP 工具中使用 Host 路徑
csv_path="/home/eric/workspace251204/sample_data/iris.csv"

# ✅ 正確：使用 Container 路徑
csv_path="/data/sample_data/iris.csv"
```

### 4.2 測試檔案位置錯誤

```python
# ❌ 錯誤：測試放在根目錄
/workspace251204/my_test.py

# ✅ 正確：放入對應的 tests/ 資料夾
/workspace251204/tests/test_my_feature.py
```

### 4.3 相對路徑錯誤

```python
# ❌ 錯誤：假設工作目錄
open("sample_data/iris.csv")  # 依賴 cwd

# ✅ 正確：使用絕對路徑或明確基準
from pathlib import Path
BASE_DIR = Path(__file__).parent.parent
data_path = BASE_DIR / "sample_data" / "iris.csv"
```

---

## 第 5 條：MCP 工具路徑驗證

### 5.1 有效路徑前綴

MCP Server 只接受以下前綴的路徑：

```python
VALID_PATH_PREFIXES = [
    "/data/sample_data",   # 範例資料
    "/data/projects",      # 使用者專案
]
```

### 5.2 路徑驗證規則

1. 必須以 `/data/` 開頭
2. 必須是 `.csv` 檔案（分析工具）
3. 禁止 `..` 路徑遍歷
4. 禁止符號連結到容器外

---

## 第 6 條：範例資料集

### 6.1 可用資料集清單

| 檔案 | Container 路徑 | 說明 |
|------|----------------|------|
| iris.csv | `/data/sample_data/iris.csv` | 鳶尾花分類 |
| breast_cancer.csv | `/data/sample_data/breast_cancer.csv` | 乳癌診斷 |
| heart_disease.csv | `/data/sample_data/heart_disease.csv` | 心臟病 |
| titanic.csv | `/data/sample_data/titanic.csv` | 鐵達尼號 |
| diabetes.csv | `/data/sample_data/diabetes.csv` | 糖尿病 |
| medical_study_200.csv | `/data/sample_data/medical_study_200.csv` | 醫學研究 |

### 6.2 使用範例

```python
# E2E 測試中使用
response = await client.post(
    "/analysis/quick",
    json={"csv_path": "/data/sample_data/iris.csv"}
)
```

---

## 附則

### 第 7 條：路徑問題排查

遇到 `FileNotFoundError` 時：

1. **確認環境**：在容器內還是 Host？
2. **確認掛載**：docker-compose.yml 是否正確掛載？
3. **確認路徑前綴**：使用正確的前綴
4. **確認檔案存在**：先用 `list_available_files` MCP 工具檢查
