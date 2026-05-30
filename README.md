# bdrc-kangyur-audit

[![CI](https://github.com/ahxudhsh/bdrc-kangyur-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/ahxudhsh/bdrc-kangyur-audit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

审计 BDRC 甘珠尔（Kangyur）Unicode 电子文本的工具包：从 RDF 图发现子作品、下载电子文本、做多维度质量校验、并产出人类可读报告。

> 状态：**v0.1.0 开发中**。`walk` / `fetch` / `validate`（结构性）/ `report` 均已实现。`validate` 的词典 `lexical_score`（botok/Monlam）留到后续清洗。

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

# 1) 发现子作品（W → MW/IE → volume → UTM etext），写候选 CSV
bdrc-audit walk W22084 --limit 200 -o outputs/rdf_candidates.csv

# 2) 按候选 CSV 下载 Unicode 电子文本（限速 ≤2 req/s、3 次重试、断点续传）
bdrc-audit fetch outputs/rdf_candidates.csv -o outputs/raw

# 3) 结构性质量校验：目录 -> 200 行主索引（每行 pass/warn/fail）
bdrc-audit validate outputs/raw --candidates outputs/rdf_candidates.csv \
  -o outputs/kangyur_master_index_v0.csv

# 4) 由主索引渲染人类可读报告
bdrc-audit report --index outputs/kangyur_master_index_v0.csv -o outputs/report.md
```

`validate` 的结构性维度：UTF-8 合法性、藏文 Unicode 占比、shad（`།`）密度、`U+FFFD`、拉丁占比、`Image As Per Original Document` OCR 标记。`report` 输出含：摘要、失败分类、按 imagegroup 的 cohort 切片、≥3 个有证据的发现。

**网络/代理**：默认**直连**，开箱即用。如需走本地代理，设 `BDRC_PROXY`（或标准 `HTTPS_PROXY`），例如 `export BDRC_PROXY=http://127.0.0.1:7891`。

实测：`walk W22084 --limit 200` 得到 200 个子作品（全部 UTM 映射）；`fetch` 下载 200/200 成功，重跑自动跳过已存在文件。

## 开发

```bash
pytest -ra
```

CI 通过 GitHub Actions 在 Python 3.9–3.12 上运行 `pytest`。

## 路线图（五日工程 v0.1.0）

| Day | 内容 | 状态 |
| --- | --- | --- |
| 1 | 仓库骨架 + CLI 四子命令 stub + CI 跑通空 pytest | ✅ |
| 2 | 迁入 RDF walk + etext fetch（限速 ≤ 2 req/s、3 次重试、断点续传） | ✅ |
| 3 | Validator：结构性维度（`shad_density` 等）✅；`lexical_score`（botok/Monlam）留到清洗 | 🔶 |
| 4 | `report` → `outputs/report.md`（失败分类、cohort 切片、意外发现） | ✅ |
| 5 | 文档与 v0.1.0 发布（Release 挂 CSV + report） | ⏳ |

## License

[MIT](LICENSE)
