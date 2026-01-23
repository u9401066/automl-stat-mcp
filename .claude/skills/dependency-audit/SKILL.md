```skill
---
name: dependency-audit
description: Audit project dependencies including missing imports, security vulnerabilities, license compliance, and version updates. Use when checking for missing packages, security issues, or license conflicts. Triggers: DEP, deps, 依賴檢查, dependency audit, pip-audit, 缺少套件, missing import, 安全漏洞, vulnerability, 授權檢查, license check, 套件更新, outdated.
---

# Dependency Audit 技能 (依賴審計)

## 描述
檢查專案依賴：缺少的 imports、安全漏洞、授權合規、版本更新。

## 觸發條件
- 「依賴檢查」「檢查依賴」
- 「缺少套件」「missing import」
- 「pip-audit」「安全漏洞」
- 「授權檢查」「license check」

---

## 🎯 審計流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Dependency Audit Workflow                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   [1] 缺失 Import 掃描  ──▶ 找出程式碼引用但未安裝的套件            │
│   [2] 安全漏洞掃描      ──▶ pip-audit / safety 檢查已知 CVE         │
│   [3] 授權合規檢查      ──▶ 檢查第三方套件的 License                │
│   [4] 版本更新檢查      ──▶ 找出過期需更新的套件                    │
│   [5] 依賴衝突檢查      ──▶ 檢查版本衝突                            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📋 [1] 缺失 Import 掃描

### 方法 A：使用 Pylance MCP

```
# 優先使用 Pylance MCP 工具
mcp_pylance_mcp_s_pylanceImports(workspaceRoot)
```

Pylance 會回傳：
- `resolved_imports`: 已解析的模組
- `unresolved_imports`: 找不到的模組（需要安裝）

### 方法 B：手動掃描

```bash
# 收集所有 import 語句
grep -rh "^import \|^from " --include="*.py" */src/ | \
    sed 's/^import //' | sed 's/^from //' | \
    cut -d' ' -f1 | cut -d'.' -f1 | \
    sort -u > /tmp/imports.txt

# 對照 requirements.txt
comm -23 /tmp/imports.txt <(cat */requirements*.txt | \
    grep -v "^#" | cut -d'=' -f1 | cut -d'>' -f1 | cut -d'<' -f1 | \
    tr '[:upper:]' '[:lower:]' | sort -u)
```

### 常見 Import ↔ 套件名稱對應

| Import 名稱 | PyPI 套件名稱 |
|-------------|---------------|
| `cv2` | `opencv-python` |
| `PIL` | `Pillow` |
| `sklearn` | `scikit-learn` |
| `yaml` | `PyYAML` |
| `bs4` | `beautifulsoup4` |
| `dateutil` | `python-dateutil` |

### 修復方式

```bash
# 使用 uv 安裝缺失套件
uv add <package-name>

# 或更新 requirements.txt
pip freeze > requirements.txt
```

---

## 📋 [2] 安全漏洞掃描

### 工具選項

| 工具 | 安裝 | 用途 |
|------|------|------|
| pip-audit | `pip install pip-audit` | PyPI 官方，檢查 requirements |
| safety | `pip install safety` | Safety DB，更多來源 |
| bandit | `pip install bandit` | 程式碼安全分析 |
| trivy | Docker image | 容器 + 依賴掃描 |

### pip-audit 使用

```bash
# 安裝
pip install pip-audit

# 掃描當前環境
pip-audit

# 掃描 requirements.txt
pip-audit -r requirements.txt

# JSON 輸出（適合 CI）
pip-audit --format json -o audit-report.json

# 嚴格模式（有漏洞就失敗）
pip-audit --strict
```

### safety 使用

```bash
# 安裝
pip install safety

# 掃描
safety check

# 掃描 requirements
safety check -r requirements.txt

# 完整報告
safety check --full-report
```

### Trivy 容器掃描

```bash
# 掃描 Docker Image
trivy image automl-mcp-server:latest

# 掃描專案目錄
trivy fs .

# 只報告 HIGH/CRITICAL
trivy fs . --severity HIGH,CRITICAL
```

### 輸出範例

```
Found 2 known vulnerabilities:

Name           Version    ID                  Severity  Fixed Versions
-----------    -------    ------------------  --------  --------------
cryptography   3.4.6      PYSEC-2021-62       HIGH      3.4.7
requests       2.25.1     CVE-2023-32681      MEDIUM    2.31.0
```

### 修復方式

```bash
# 更新有漏洞的套件
uv add cryptography@latest requests@latest

# 或指定修復版本
pip install cryptography>=3.4.7 requests>=2.31.0
```

---

## 📋 [3] 授權合規檢查

### 工具

```bash
# 安裝 pip-licenses
pip install pip-licenses

# 列出所有套件授權
pip-licenses

# 輸出 CSV（方便分析）
pip-licenses --format=csv > licenses.csv

# 只顯示特定授權（例如找 GPL）
pip-licenses --from=mixed | grep -i "gpl"
```

### 授權風險等級

| 授權類型 | 風險 | 說明 |
|----------|------|------|
| MIT, BSD, Apache 2.0 | ✅ 低 | 商業友好 |
| LGPL | ⚠️ 中 | 動態連結 OK |
| GPL | 🔴 高 | 衍生作品需開源 |
| AGPL | 🔴 高 | 網路服務也算分發 |
| SSPL | 🔴 高 | MongoDB 授權 |
| Unknown | ⚠️ 未知 | 需人工確認 |

### 產生授權報告

```bash
# 產生 Markdown 格式報告
pip-licenses --format=markdown > docs/THIRD_PARTY_LICENSES.md

# 包含套件描述
pip-licenses --with-description --format=markdown > docs/THIRD_PARTY_LICENSES.md
```

### 本專案授權合規

由於本專案使用 **Apache 2.0**，以下授權相容：
- ✅ MIT, BSD, ISC
- ✅ Apache 2.0
- ⚠️ LGPL（需注意連結方式）
- ❌ GPL, AGPL（不相容）

---

## 📋 [4] 版本更新檢查

### 使用 pip-outdated

```bash
# 列出過期套件
pip list --outdated

# 使用 pip-review（互動式更新）
pip install pip-review
pip-review --local --interactive
```

### 使用 uv

```bash
# 查看可更新套件
uv pip list --outdated

# 更新所有套件
uv sync --upgrade
```

### 版本更新策略

| 類型 | 範例 | 建議 |
|------|------|------|
| Patch | 1.0.0 → 1.0.1 | ✅ 自動更新 |
| Minor | 1.0.0 → 1.1.0 | ⚠️ 測試後更新 |
| Major | 1.0.0 → 2.0.0 | 🔴 謹慎，可能有破壞性變更 |

---

## 📋 [5] 依賴衝突檢查

### 使用 pip check

```bash
# 檢查衝突
pip check

# 輸出範例
# requests 2.25.1 requires urllib3<1.27, but you have urllib3 2.0.0
```

### 使用 pipdeptree

```bash
# 安裝
pip install pipdeptree

# 顯示依賴樹
pipdeptree

# 只顯示衝突
pipdeptree --warn fail

# 反向顯示（誰依賴這個套件）
pipdeptree --reverse --packages requests
```

### 解決衝突

```bash
# 方法 1：降級衝突套件
pip install urllib3<1.27

# 方法 2：升級有要求的套件
pip install requests --upgrade

# 方法 3：使用相容版本（讓 pip 自動解決）
pip install requests urllib3 --upgrade
```

---

## 🔧 自動化腳本

### 完整審計腳本

```bash
#!/bin/bash
# scripts/dependency-audit.sh

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 Dependency Audit Report"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Date: $(date)"
echo ""

echo "=== 1. Missing Imports ==="
# 使用 Pylance MCP 或 grep 方法

echo ""
echo "=== 2. Security Vulnerabilities ==="
pip-audit 2>/dev/null || echo "pip-audit not installed"

echo ""
echo "=== 3. License Check ==="
pip-licenses --format=plain 2>/dev/null | head -20 || echo "pip-licenses not installed"
echo "(truncated, run 'pip-licenses' for full list)"

echo ""
echo "=== 4. Outdated Packages ==="
pip list --outdated 2>/dev/null | head -20 || echo "Error"

echo ""
echo "=== 5. Dependency Conflicts ==="
pip check 2>/dev/null || echo "No conflicts"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

### GitHub Actions 整合

```yaml
# .github/workflows/dependency-audit.yml
name: Dependency Audit

on:
  schedule:
    - cron: '0 0 * * 1'  # 每週一
  push:
    paths:
      - 'requirements*.txt'
      - 'pyproject.toml'

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          pip install pip-audit safety pip-licenses
          pip install -r requirements.txt
          
      - name: Security audit
        run: pip-audit --strict
        
      - name: License check
        run: |
          pip-licenses --format=markdown > license-report.md
          # 檢查有無 GPL
          if pip-licenses | grep -qi "GPL"; then
            echo "⚠️ GPL license detected!"
          fi
```

---

## 📊 審計報告範本

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 依賴審計報告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

日期：YYYY-MM-DD
專案：clinical-automl-mcp

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 摘要
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| 項目 | 狀態 | 數量 |
|------|------|------|
| 缺失 Import | ✅ | 0 |
| 安全漏洞 | ⚠️ | 2 |
| 授權問題 | ✅ | 0 |
| 過期套件 | ⚠️ | 5 |
| 衝突 | ✅ | 0 |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 安全漏洞
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| 套件 | 版本 | CVE | 嚴重度 | 修復版本 |
|------|------|-----|--------|----------|
| cryptography | 3.4.6 | CVE-2021-XXX | HIGH | 3.4.7 |
| requests | 2.25.1 | CVE-2023-XXX | MEDIUM | 2.31.0 |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 過期套件
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| 套件 | 當前 | 最新 | 類型 |
|------|------|------|------|
| pandas | 2.0.0 | 2.2.0 | minor |
| numpy | 1.25.0 | 1.26.0 | minor |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 行動項目
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. [x] 更新 cryptography >= 3.4.7
2. [x] 更新 requests >= 2.31.0
3. [ ] 考慮更新 pandas, numpy

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 💡 最佳實踐

### CI/CD 整合
- 每次 PR 執行 `pip-audit --strict`
- 每週排程完整審計
- 安全漏洞 block merge

### requirements.txt 版本釘選
```
# 推薦：指定最低版本 + 相容版本
requests>=2.31.0,<3.0.0

# 或完全釘選（需定期更新）
requests==2.31.0
```

### 第三方授權文件
- 維護 `docs/THIRD_PARTY_LICENSES.md`
- 每次新增依賴時更新
- 發布前確認授權相容
```
