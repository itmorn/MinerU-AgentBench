# 03 完整技术报告文档

## 参考文档

完整技术报告正文见：

```text
docs/technical_report.md
docs/technical_report_outline.md
Miner U Data Agent 技术文档.docx
```

## 项目概述

MinerU-DataAgent 是一个面向财报、研报、上市公司公告和复杂 PDF 文档的智能数据处理 Agent。系统以 MinerU 的文档解析能力为底座，在其输出的 Markdown、JSON 或中间结构基础上，进一步完成任务规划、工具调用、结构化抽取、表格修复、财务指标标准化、质量校验、异常恢复和结果导出。

项目目标不是单纯 PDF 转 Markdown，而是将复杂文档加工为可验证、可追溯、可入库、可复用的结构化数据资产。

## 系统整体设计

系统采用分层架构：

```text
用户输入层
  PDF / URL / MinerU Markdown / MinerU JSON / 批任务配置

Agent 规划层
  输入分析 / 文档类型识别 / 风险判断 / 策略选择 / 任务计划

工具执行层
  MinerU Agent API / MinerU 精准 API / 本地后处理 / JSON 解析

结构化处理层
  章节树 / 表格对象 / 字段类型 / 财务指标 / 单位归一化

质量评估与恢复层
  Schema 校验 / 质量评分 / warnings / OCR 与页码扩展重试

结果导出层
  structured.json / tables.json / financial_metrics.json / quality_report.json / run.log.jsonl
```

## 任务执行机制

Agent 执行流程：

```text
AnalyzeInput
→ DetectDocumentType
→ SelectMinerUStrategy
→ RunParsingTool
→ BuildStructuredSchema
→ ValidateQuality
→ If low quality: DiagnoseFailure / RetryOrRepair
→ ExportResults
→ GenerateQualityReport
```

系统支持 `auto` 模式，根据输入自动选择 Markdown、MinerU JSON、Agent URL、Agent File 或 Precision URL 路径。

## 数据处理与工具调用能力

已实现能力：

- MinerU Agent URL 解析。
- MinerU Agent File 上传解析。
- MinerU Precision URL 解析。
- 本地 MinerU Markdown 后处理。
- MinerU JSON/content_list 后处理，保留 page、bbox、block_id、confidence。
- 标题层级识别与章节树构建。
- Markdown / HTML 表格解析。
- 跨页表格合并。
- 表格字段类型识别：metric、money、number、ratio、date、text。
- 财务指标抽取。
- 元、千元、万元、亿元、百分比归一化。
- 同比/变动率重算。
- Schema 校验、质量评分和 warnings。
- 自动恢复：低质量时切换 OCR、增强表格、扩大页码范围并重试。

## 系统性能与稳定性说明

稳定性设计：

- 所有任务生成 JSONL 运行日志，记录 planner、parser、recovery、validator、reporter 等步骤。
- 批处理任务支持单任务失败隔离，失败不会中断后续任务。
- 输出结果遵循 `schemas/structured.schema.json`。
- 单元测试覆盖后处理、单位归一化、跨页合并、MinerU JSON 输入、质量恢复决策。
- CLI、API、Docker 三种运行方式均可复现。

## 典型任务执行示例

以下样例均位于 `samples/output/`，每个目录包含 `structured.json`、`quality_report.json`、`run.log.jsonl` 等结果。

1. `samples/output/example_02_pdf_software_h1_p30_40`
   - 半年度报告局部页解析。
   - 覆盖标题、表格、财务数字和质量报告。

2. `samples/output/example_03_septwolves_annual_p1_20`
   - 年报前 20 页解析。
   - 覆盖章节结构、财务指标和日志追踪。

3. `samples/output/example_04_dcits_h1_p1_20`
   - 半年度报告前 20 页解析。
   - 覆盖 MinerU 精准 API 输出后处理。

4. `samples/output/example_05_lens_h1_p1_20`
   - 半年度报告前 20 页解析。
   - 覆盖表格密集文档结构化。

5. `samples/output/board_report_postprocessed_p1_10`
   - 董事会报告样例。
   - 覆盖本地后处理、质量评分和可追踪日志。

补充样例：

```text
samples/output/config_mock
samples/output/json_mock
```

## 适用场景与应用价值

适用场景：

- 金融财报、半年报、季报、招股说明书结构化。
- 研报、公告、审计报告数据抽取。
- 企业历史 PDF 档案治理。
- RAG 知识库构建。
- 行业大模型训练数据清洗。
- 文档问答和多模态文档理解评测。

应用价值：

- 将复杂 PDF 从可读文本提升为可计算、可校验、可追踪的数据资产。
- 降低人工阅读、清洗、核对财务数据的成本。
- 为大模型数据生态提供高质量行业语料生产工具链。
