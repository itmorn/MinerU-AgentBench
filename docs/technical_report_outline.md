# 技术报告提纲

## 1. 项目概述

本项目构建面向财报、研报和招股说明书的 MinerU 增强型 Data Agent。系统利用 MinerU 完成复杂文档解析，并通过 Agent 流程完成结构化整理、质量校验和可追溯日志记录。

## 2. 业务痛点

- 财务 PDF 中表格密集，数字字段容易解析错位
- 招股说明书和年报页数长，章节层级复杂
- 下游 RAG 或语料生产需要统一 Markdown/JSON 格式
- 单次解析结果缺少质量检查和处理过程追踪

## 3. 系统架构

```text
输入 PDF/URL
→ Planner 生成任务计划
→ MinerU Parser 完成文档解析
→ PostProcessor 抽取章节、表格和数字线索
→ Validator 生成质量检查结果
→ Reporter 输出 Markdown、JSON 和日志
```

## 4. Agent 任务执行机制

- 根据输入来源选择 MinerU Agent API、精准 API 或本地 Markdown 后处理
- 自动轮询 MinerU 异步任务
- 统一保存解析结果和运行日志
- 失败时记录错误信息，便于复现与排查

## 5. 数据处理能力

- 标题层级提取
- Markdown/HTML 表格行列结构化
- 财务数字和单位识别
- 财务指标抽取
- 指标级一致性检查
- 文档结构完整性检查
- 结构化 JSON 输出

## 6. 典型任务示例

已完成 5 个真实 MinerU 精准 API 解析样例，输出均包含 `full.md`、`structured.json`、`quality_report.json` 和 `run.log.jsonl`。

| ID | 任务 | 页段 | 质量分 | 标题数 | 表格数 | 财务数字线索 | 财务指标 | 一致性检查 | 输出目录 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| example_01 | 董事会报告与经营数据解析 | 1-10 | 1.0 | 32 | 13 | 34 | 38 | 30 | `samples/output/board_report_postprocessed_p1_10` |
| example_02 | PDF 软件公司半年报财务章节解析 | 30-40 | 1.0 | 37 | 6 | 18 | 15 | 12 | `samples/output/example_02_pdf_software_h1_p30_40` |
| example_03 | 七匹狼年报首页与审计信息解析 | 1-20 | 1.0 | 60 | 26 | 61 | 73 | 63 | `samples/output/example_03_septwolves_annual_p1_20` |
| example_04 | 神州信息半年报公司信息与指标表解析 | 1-20 | 1.0 | 42 | 13 | 29 | 32 | 21 | `samples/output/example_04_dcits_h1_p1_20` |
| example_05 | 蓝思科技半年报主营业务与调研表解析 | 1-20 | 1.0 | 57 | 18 | 27 | 36 | 32 | `samples/output/example_05_lens_h1_p1_20` |

汇总文件：

- `samples/output/examples_summary.md`
- `samples/output/examples_summary.json`

## 7. 系统稳定性与复现

- 提供 `requirements.txt`
- 提供命令行入口 `run_agent.py`
- 输出 `run.log.jsonl`
- 保留样例输入和输出

## 8. 应用价值

- 财报和研报结构化入库
- 投研知识库构建
- RAG 语料清洗
- 审计和合规文档批处理
