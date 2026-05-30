# bdrc-kangyur-audit

[![CI](https://github.com/ahxudhsh/bdrc-kangyur-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/ahxudhsh/bdrc-kangyur-audit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%E2%80%933.12-blue.svg)](pyproject.toml)
[![Release](https://img.shields.io/github/v/release/ahxudhsh/bdrc-kangyur-audit?include_prereleases&sort=semver)](https://github.com/ahxudhsh/bdrc-kangyur-audit/releases)

> 一个端到端的命令行工具包，用来**审计 BDRC 甘珠尔（Kangyur）的藏文 Unicode 电子文本质量**：
> 从 RDF 图发现子作品 → 限速下载 → 多维度质量校验（pass/warn/fail）→ 人类可读报告。

---

## 目录

1. [项目简介](#1-项目简介)
2. [动机与背景](#2-动机与背景)
3. [流程与架构](#3-流程与架构)
4. [安装](#4-安装)
5. [快速上手（CLI）](#5-快速上手cli)
6. [校验方法学](#6-校验方法学)
7. [审计结果（W22084）](#7-审计结果w22084)
8. [项目结构](#8-项目结构)
9. [测试与持续集成](#9-测试与持续集成)
10. [路线图与已知限制](#10-路线图与已知限制)

[License](#license) · [Acknowledgements](#acknowledgements)

---

## 1. 项目简介

`bdrc-kangyur-audit` 把「从 BDRC 拿到甘珠尔藏文电子文本并判断它能不能用」这件事做成了一条
可复现、离线可测的命令行流水线。安装后提供单一入口 `bdrc-audit`，四个子命令对应四个阶段：

| 子命令 | 作用 |
| --- | --- |
| `walk` | 遍历 `purl.bdrc.io` 的 RDF 图，发现某个根 W 号下的子作品与其 UTM 电子文本 |
| `fetch` | 限速 / 重试 / 断点续传地下载这些电子文本 |
| `validate` | 结构性质量校验，给每个文件打 `pass` / `warn` / `fail` |
| `report` | 由主索引渲染含失败分类、cohort 切片与证据发现的 Markdown 报告 |

## 2. 动机与背景

前身 `branch_a` MVP 已能跑通 `RDF walk → etext → jsonl`，但其校验器**只查 UTF-8 strict +
藏文 Unicode 块占比 + `U+FFFD`**，无法识别 OCR / 去标点类脏数据。

典型反例：`MW22084_0008.txt` 藏文占比高达 **0.99**，旧校验器判 PASS，但它实际嵌入了
`Image As Per Original Document` 占位串、夹杂拉丁字母、音节粘连（缺 tsheg `་`）。
**「藏文占比高」并不等于「文本干净」** —— 这正是甘珠尔数据工程里最棘手的质量难点，
也是本工具包要解决的核心问题。

## 3. 流程与架构

```
root W (e.g. W22084)
      │  walk   purl.bdrc.io RDF: W → MW / IE → volumes → UTM etext
      ▼
outputs/rdf_candidates.csv         200 行候选（work_id, utm_id, etext_url, …）
      │  fetch  限速 ≤2 req/s · 3 次重试 · 断点续传
      ▼
outputs/raw/*.txt                  200 个藏文电子文本
      │  validate  结构性指标 → pass / warn / fail
      ▼
outputs/kangyur_master_index_v0.csv  200 行主索引（含 status 与指标）
      │  report  汇总 + 失败分类 + cohort 切片 + 发现
      ▼
outputs/report.md                  人类可读审计报告
```

共享网络层 `bdrc_audit.net` 统一管理代理、限速（`RateLimiter`）与重试（urllib3 `Retry`），
被 `walk` 与 `fetch` 复用；所有网络入口都可注入假 session，从而**离线可测**。

## 4. 安装

要求 Python ≥ 3.9。

```bash
git clone https://github.com/ahxudhsh/bdrc-kangyur-audit.git
cd bdrc-kangyur-audit
python -m pip install -e ".[dev]"     # 含 pytest / pytest-cov
bdrc-audit --version
```

**网络 / 代理**：默认**直连**，开箱即用。如需走本地代理，设 `BDRC_PROXY`（或标准 `HTTPS_PROXY`），
例如 `export BDRC_PROXY=http://127.0.0.1:7891`。

## 5. 快速上手（CLI）

```bash
# 1) 发现子作品（W → MW/IE → volume → UTM etext），写候选 CSV
bdrc-audit walk W22084 --limit 200 -o outputs/rdf_candidates.csv

# 2) 按候选 CSV 下载 Unicode 电子文本（限速 ≤2 req/s、3 次重试、断点续传）
bdrc-audit fetch outputs/rdf_candidates.csv -o outputs/raw

# 3) 结构性质量校验：目录 → 200 行主索引（每行 pass/warn/fail）
bdrc-audit validate outputs/raw --candidates outputs/rdf_candidates.csv \
  -o outputs/kangyur_master_index_v0.csv

# 4) 由主索引渲染人类可读报告
bdrc-audit report --index outputs/kangyur_master_index_v0.csv -o outputs/report.md
```

`fetch` 支持断点续传：已存在的非空文件自动跳过，加 `--force` 可强制重下。

## 6. 校验方法学

`validate` 当前为**结构性指标层（v0）**，对每个文件计算：

| 指标 | 含义 | 触发 |
| --- | --- | --- |
| UTF-8 合法性 | 字节能否 strict 解码 | 失败 → `fail` |
| `tibetan_ratio` | 藏文 Unicode 块（U+0F00–0FFF）占非空白字符比 | `<0.5` → `fail`；`<0.8` → `warn` |
| `has_image_marker` | 是否含 `Image As Per Original Document` | 命中 → `fail` |
| `fffd_count` | `U+FFFD` 替换字符数 | `>0` → `fail` |
| `shad_per_500_tib` | 每 500 藏文字符的 shad（`།`）数 | `<1` → `warn`（疑似去标点 OCR） |
| `latin_ratio` | 拉丁字母占比 | `>0.05` → `warn` |
| `n_chars` | 总字符数 | `<500` → `warn`（过短残片） |

状态优先级 `fail > warn > pass`，每行附可读原因（如 `image_marker`、`tibetan_ratio=0.17<0.5`）。

> **延后项**：词典级 `lexical_score`（按 tsheg 切音节，统计落在 botok / Monlam 词表的比例）
> 留到后续统一数据清洗阶段；它能进一步抓出「字都对、但音节粘连/拼写错」的脏数据。

## 7. 审计结果（W22084）

对德格甘珠尔根 `W22084` 实跑 200 个子作品（候选 → 下载 → 校验）：

- **walk**：200 个候选，全部成功映射到 UTM 电子文本
- **fetch**：200/200 下载成功，0 失败（约 7.5M 字符）
- **validate**：**183 `pass` · 7 `warn` · 10 `fail`**

报告中的证据性发现（节选）：

1. **高藏文占比 ≠ 干净**：`MW22084_0008`（占比 0.99）、`MW22084_0012`（0.97）含
   `Image As Per Original Document` 占位串，被判 `fail` —— 印证了第 2 节的核心问题。
2. **非藏文残桩**：8 个文件藏文占比 `<0.5`（最低 0.17、311 字符），多为题署 / 元数据残片。
3. **体量高度倾斜**：单文件字符数跨 250–963,025，最大 5 个文件占全部字符约 50%，抽样需分层。
4. **本批失败模式不是去标点**：shad 密度全部达标，污染主要来自 image-marker 与非藏文残桩。

> 完整 `kangyur_master_index_v0.csv`（200 行）与 `report.md` 作为
> [v0.1.0 Release](https://github.com/ahxudhsh/bdrc-kangyur-audit/releases) 附件提供
> （原始数据与产物不入 git 历史，见 `.gitignore`）。

## 8. 项目结构

```
bdrc-kangyur-audit/
├── src/bdrc_audit/
│   ├── cli.py        # argparse 入口：walk / fetch / validate / report
│   ├── net.py        # 共享 session：代理 + RateLimiter(≤2 req/s) + 重试
│   ├── walk.py       # RDF 图遍历（BdrcClient）→ 候选 CSV
│   ├── fetch.py      # 限速 / 重试 / 断点续传下载
│   ├── validate.py   # 结构性校验 → pass/warn/fail
│   └── report.py     # 主索引构建 + 报告渲染
├── tests/            # 离线单测（fake HTTP session）
├── .github/workflows/ci.yml
└── pyproject.toml    # src-layout, MIT, console_scripts: bdrc-audit
```

## 9. 测试与持续集成

```bash
pytest -ra                                   # 全部用例
pytest --cov=bdrc_audit --cov-report=term-missing   # 覆盖率
```

- 全套测试**离线可跑**：网络层注入假 session，不触达真实网络。
- 当前 **47 个用例通过，覆盖率 ~93%**（已超 ≥60% 目标）。
- GitHub Actions 在 **Python 3.9 / 3.10 / 3.11 / 3.12** 上运行 `pytest`，CI badge 见顶部。

## 10. 路线图与已知限制

| Day | 内容 | 状态 |
| --- | --- | --- |
| 1 | 仓库骨架 + CLI 四子命令 + CI | ✅ |
| 2 | RDF walk + etext fetch（限速 / 重试 / 断点续传） | ✅ |
| 3 | Validator 结构性维度（`shad_density` 等） | ✅ |
| 4 | `report` → 失败分类 / cohort 切片 / 证据发现 | ✅ |
| 5 | 文档 + v0.1.0 发布（Release 挂 CSV + report） | ✅ |

**已知限制**

- 词典级 `lexical_score`（botok / Monlam）尚未实现，去标点 / 音节级脏数据靠后续清洗补齐。
- `fetch` 当前为单线程顺序下载（受限速约束）；大规模丹珠尔场景可加并发队列。
- cohort 切片目前按 imagegroup；卷次（volume）维度待 walk 阶段补充字段。

## License

[MIT](LICENSE)

## Acknowledgements

数据来源 **Buddhist Digital Resource Center (BDRC)**，经 `purl.bdrc.io` 解析获取。
使用本工具请遵守 [BDRC 使用条款](https://www.bdrc.io/)与其速率限制（本工具默认 ≤ 2 req/s）。
