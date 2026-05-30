# Release self-check — v0.1.0

发布前逐项核对（对应五日工程交付物）。

## 代码与安装

- [x] 公开仓库，MIT License
- [x] `pip install -e .` 可用，`bdrc-audit --version` 输出 `0.1.0`
- [x] CLI 四子命令 `walk` / `fetch` / `validate` / `report` 均可运行

## 质量门禁

- [x] `pytest` 全绿（47 passed）
- [x] 覆盖率 ≥ 60%（实测 ~93%）
- [x] 测试离线可跑（fake HTTP session，不触达网络）
- [x] 无 lint 错误
- [x] GitHub Actions CI 在 3.9–3.12 通过，badge 绿色

## 交付物

- [x] `outputs/kangyur_master_index_v0.csv`（200 行，每行 `status: pass/warn/fail`）
- [x] `outputs/report.md`（含摘要 / 失败分类 / cohort 切片 / ≥3 证据发现）
- [x] 回归用例：`MW22084_0008` 判为 `fail`（不再 pass）

## 文档

- [x] README 含 10 个 section（简介 / 动机 / 架构 / 安装 / 用法 / 方法学 / 结果 / 结构 / 测试 / 路线图）
- [x] 代理 / 限速行为有说明
- [x] 已知限制（`lexical_score` 延后）写明

## 发布

- [x] 打 `v0.1.0` tag 并推送
- [x] 创建 GitHub Release v0.1.0
- [x] Release 附件：`kangyur_master_index_v0.csv` + `report.md` + 交付物 zip
