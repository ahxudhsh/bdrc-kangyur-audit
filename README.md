# bdrc-kangyur-audit

[![CI](https://github.com/ahxudhsh/bdrc-kangyur-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/ahxudhsh/bdrc-kangyur-audit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

审计 BDRC 甘珠尔（Kangyur）Unicode 电子文本的工具包：从 RDF 图发现子作品、下载电子文本、做多维度质量校验、并产出人类可读报告。

> 状态：**v0.1.0 — Day 1 骨架**。CLI 四子命令已接好参数解析，处理逻辑为 stub，将在 Day 2–4 逐步迁入。

## 安装

```bash
git clone https://github.com/ahxudhsh/bdrc-kangyur-audit.git
cd bdrc-kangyur-audit
python -m pip install -e ".[dev]"
```

要求 Python ≥ 3.9。

## CLI

安装后提供 `bdrc-audit` 命令，包含四个子命令：

```bash
bdrc-audit --version
bdrc-audit --help

bdrc-audit walk W22084 --limit 5        # 发现子作品（W → IE → UTM）
bdrc-audit fetch candidates.csv -o outputs/raw   # 下载 Unicode 电子文本
bdrc-audit validate outputs/raw          # 多维度质量校验
bdrc-audit report --index outputs/kangyur_master_index_v0.csv -o outputs/report.md
```

Day 1 阶段，各子命令仅打印「未实现」提示并正常退出（exit 0），用于验证命令骨架接线。

## 开发

```bash
pytest -ra
```

CI 通过 GitHub Actions 在 Python 3.9–3.12 上运行 `pytest`。

## 路线图（五日工程 v0.1.0）

| Day | 内容 |
| --- | --- |
| 1 | 仓库骨架 + CLI 四子命令 stub + CI 跑通空 pytest（本提交） |
| 2 | 迁入 RDF walk + etext fetch（限速 ≤ 2 req/s、3 次重试、断点续传） |
| 3 | Validator 升级：`lexical_score` + `shad_density` |
| 4 | `report` → `outputs/report.md`（失败分类、cohort 切片、意外发现） |
| 5 | 文档与 v0.1.0 发布（Release 挂 CSV + report） |

## License

[MIT](LICENSE)
