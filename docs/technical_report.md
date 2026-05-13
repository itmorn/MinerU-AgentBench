# 面向财报与研报的 MinerU 增强型 Data Agent 技术报告

## 1. 项目概述

本项目构建了一个面向财报、研报、招股说明书和上市公司公告的 MinerU 增强型 Data Agent。系统以 MinerU 作为底层复杂文档解析工具，将 PDF 等非结构化文档转换为 Markdown 与结构化中间结果；在此基础上，Agent 自动完成任务规划、工具调用、表格线索识别、财务数字抽取、质量检查和可追溯日志记录。

项目目标不是单纯完成 PDF 转文本，而是面向语料生产、投研知识库、审计材料整理和 RAG 数据清洗等真实场景，提供一条可复现、可检查、可扩展的数据处理链路。

## 2. 业务痛点

财报、研报和招股说明书具备明显的复杂文档特征：

- 页数较长，章节层级复杂，正文、目录、表格和注释混排
- 财务表格密集，数字字段多，容易出现错位、漏列或单位混淆
- 同一文档中同时包含经营描述、财务指标、风险提示、审计信息和调研记录
- 下游应用通常需要统一的 Markdown、JSON 和日志，而不仅是原始文本
- 单次解析结果如果缺少质量检查，难以判断是否适合直接进入语料库或知识库

因此，本系统采用“MinerU 解析 + Agent 后处理 + 质量校验”的方式，将复杂文档处理拆成可追踪的多阶段流程。

## 3. 系统架构

系统整体架构如下：

```text
输入 PDF/URL
→ Planner 生成任务计划
→ MinerU Parser 调用 MinerU 精准 API、轻量 API 或本地解析结果
→ PostProcessor 抽取标题、表格和财务数字线索
→ Validator 生成质量检查报告
→ Reporter 输出 Markdown、JSON 和 JSONL 日志
```

各模块职责如下：

- `Planner`：根据输入模式生成执行计划，明确解析、结构化、校验和报告输出步骤
- `MinerU Parser`：封装 MinerU 精准 API、Agent 轻量 API 和本地 Markdown 后处理模式
- `PostProcessor`：解析 MinerU 输出中的标题、HTML/Markdown 表格、财务数字与单位
- `Validator`：检查 Markdown 内容、标题结构、表格线索和财务数字线索是否完整
- `Reporter`：输出 `full.md`、`structured.json`、`quality_report.json` 和 `run.log.jsonl`

## 4. Agent 任务执行机制

系统提供统一命令行入口 `run_agent.py`，支持以下模式：

- `precision-url`：调用 MinerU 精准 API 解析远程 PDF URL
- `agent-url`：调用 MinerU Agent 轻量 API 解析远程 PDF URL
- `agent-file`：通过 MinerU Agent 轻量 API 上传本地文件解析
- `markdown`：复用已有 MinerU Markdown 结果进行 Agent 后处理

同时，系统提供 FastAPI 服务入口：

- `GET /health`：服务健康检查
- `POST /parse`：提交解析任务，返回输出目录、结构化结果路径、质量报告路径和日志路径

在精准 API 模式下，Agent 会自动完成：

1. 提交 MinerU 解析任务
2. 轮询异步任务状态
3. 下载 MinerU 返回的结果 ZIP
4. 从 ZIP 中提取 `full.md`
5. 对 Markdown 进行结构化处理
6. 生成质量报告和运行日志

运行日志使用 JSONL 格式，每一行记录一个关键事件，包括任务计划、工具调用、解析结果、质量检查和报告输出路径，便于复现与排查。

## 5. 数据处理能力

当前版本实现了以下数据处理能力：

- 标题层级提取：识别 Markdown 中的 `#` 标题，输出章节层级和所在行号
- 表格行列结构化：支持 Markdown 表格和 MinerU 输出的 HTML `<table>` 表格，输出 `headers` 与 `records`
- 财务数字识别：识别金额、百分比、带千分位的数字和常见单位
- 财务指标抽取：从表格和正文中抽取营业收入、营业成本、净利润、费用、现金流等指标
- 指标级一致性检查：针对可解析数值生成负值、零值和异常大数检查结果
- 文档统计：输出字符数、行数、标题数、表格数和数字线索数
- 质量检查：检查内容是否为空、标题结构是否足够、是否存在表格、结构化记录、财务指标和一致性检查
- 结构化输出：统一生成 `structured.json`，便于下游入库、检索和 RAG 流程使用

质量报告示例字段：

```json
{
  "score": 1.0,
  "checks": [
    {"name": "non_empty_markdown", "passed": true},
    {"name": "heading_structure", "passed": true},
    {"name": "table_signals", "passed": true},
    {"name": "financial_numeric_signals", "passed": true},
    {"name": "structured_table_records", "passed": true},
    {"name": "financial_metric_extraction", "passed": true},
    {"name": "metric_consistency_checks", "passed": true}
  ]
}
```

## 6. 典型任务执行示例

项目已完成 5 个真实 MinerU 精准 API 解析样例，输出均包含 `full.md`、`structured.json`、`quality_report.json` 和 `run.log.jsonl`。

| ID | 任务 | 页段 | 质量分 | 标题数 | 表格数 | 财务数字线索 | 财务指标 | 一致性检查 | 输出目录 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| example_01 | 董事会报告与经营数据解析 | 1-10 | 1.0 | 32 | 13 | 34 | 38 | 30 | `samples/output/board_report_postprocessed_p1_10` |
| example_02 | PDF 软件公司半年报财务章节解析 | 30-40 | 1.0 | 37 | 6 | 18 | 15 | 12 | `samples/output/example_02_pdf_software_h1_p30_40` |
| example_03 | 七匹狼年报首页与审计信息解析 | 1-20 | 1.0 | 60 | 26 | 61 | 73 | 63 | `samples/output/example_03_septwolves_annual_p1_20` |
| example_04 | 神州信息半年报公司信息与指标表解析 | 1-20 | 1.0 | 42 | 13 | 29 | 32 | 21 | `samples/output/example_04_dcits_h1_p1_20` |
| example_05 | 蓝思科技半年报主营业务与调研表解析 | 1-20 | 1.0 | 57 | 18 | 27 | 36 | 32 | `samples/output/example_05_lens_h1_p1_20` |

从结果看，Agent 能够在不同上市公司公告和财报材料中稳定识别章节、表格和财务数字线索。5 个样例均通过完整性检查，说明当前流程可以作为财务文档语料生产的初步自动化链路。

## 7. 系统稳定性与可复现性

项目提供完整的运行入口和说明文档：

- `README.md`：项目说明和快速开始
- `requirements.txt`：Python 依赖
- `run_agent.py`：统一命令行入口
- `app.py`：FastAPI 服务入口
- `docs/deployment.md`：部署与运行说明
- `scripts/run_precision_examples.sh`：典型样例批处理脚本
- `scripts/summarize_examples.py`：样例结果汇总脚本
- `tests/test_postprocess.py`：表格结构化和财务指标抽取测试

每次运行均生成独立输出目录，包含：

- `full.md`：MinerU 解析后的 Markdown
- `structured.json`：Agent 结构化结果
- `quality_report.json`：质量检查报告
- `run.log.jsonl`：可追溯运行日志

该设计保证了评审人员可以通过输入、输出和日志复查 Agent 的执行过程。

## 8. 应用价值

本系统可用于以下真实场景：

- 财报和研报结构化入库：将 PDF 中的章节、表格和关键数字转换成可检索结构
- 投研知识库构建：为 RAG 系统提供高质量 Markdown 和 JSON 语料
- 审计和合规文档批处理：对长文档进行自动解析、质检和日志留痕
- 上市公司公告监测：批量处理公告文件，提取经营指标和财务变化线索
- 数据生产流程质检：在解析后自动判断结果是否足够完整，减少人工抽检成本

## 9. 当前限制与后续优化

当前版本仍有可优化空间：

- 表格内容目前以线索识别和预览为主，后续可进一步拆分为行列级 JSON
- 跨页表格合并目前依赖表格相邻性和标题线索，后续可加入更明确的表头匹配
- 财务数字一致性校验目前偏基础，后续可加入合计校验、同比校验和单位归一化
- 对扫描件和低质量图片文档，可进一步加入 OCR 参数自动选择和重试策略

后续计划重点增强：

- 表格行列结构化
- 跨页表格合并
- 财务指标校验
- 批量任务调度
- Web API 服务化部署

## 10. 总结

本项目基于 MinerU 构建了一个面向财务文档的 Data Agent 原型。系统不只调用解析工具，而是形成了从任务规划、工具调用、结果处理、质量检查到日志追踪的完整闭环。通过 5 个公开上市公司文档样例验证，系统能够稳定输出 Markdown、结构化 JSON、质量报告和运行日志，具备进一步扩展到财报语料生产、投研知识库和审计材料处理场景的应用价值。
