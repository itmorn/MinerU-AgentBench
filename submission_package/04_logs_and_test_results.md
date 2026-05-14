# 04 系统运行日志与测试结果

## 测试命令

单元测试：

```bash
python -m unittest discover -s tests
```

编译检查：

```bash
python -m compileall agent app.py run_agent.py scripts/evaluate.py
```

配置文件批处理：

```bash
python run_agent.py --config samples/config_batch.json
```

MinerU JSON 输入测试：

```bash
python run_agent.py \
  --mode mineru-json \
  --mineru-json samples/mock/mineru_content_list.json \
  --output-dir samples/output/json_mock \
  --max-retry 0
```

Gold 评测：

```bash
python scripts/evaluate.py \
  --gold samples/gold/mock_gold.json \
  --prediction samples/output/config_mock/structured.json \
  --output samples/output/config_mock/evaluation_report.json
```

## 当前测试覆盖

```text
tests/test_postprocess.py
  - HTML 表格 records 解析
  - 财务指标抽取
  - 单位归一化
  - 同比重算
  - 跨页表格合并

tests/test_mineru_json.py
  - MinerU JSON/content_list 转 Markdown
  - layout_blocks / figures / paragraphs 输出
  - source_blocks 追踪
  - 表格字段类型识别

tests/test_validator.py
  - 质量诊断
  - 自动恢复策略
  - 页码范围扩展
```

## 运行日志位置

每个样例输出目录中均包含 `run.log.jsonl`。日志记录任务输入、执行步骤、调用工具信息、质量评分和最终输出路径。

典型日志文件：

```text
samples/output/example_02_pdf_software_h1_p30_40/run.log.jsonl
samples/output/example_03_septwolves_annual_p1_20/run.log.jsonl
samples/output/example_04_dcits_h1_p1_20/run.log.jsonl
samples/output/example_05_lens_h1_p1_20/run.log.jsonl
samples/output/board_report_postprocessed_p1_10/run.log.jsonl
samples/output/config_mock/run.log.jsonl
samples/output/json_mock/run.log.jsonl
```

## 结果文件位置

典型结构化结果：

```text
samples/output/example_02_pdf_software_h1_p30_40/structured.json
samples/output/example_03_septwolves_annual_p1_20/structured.json
samples/output/example_04_dcits_h1_p1_20/structured.json
samples/output/example_05_lens_h1_p1_20/structured.json
samples/output/board_report_postprocessed_p1_10/structured.json
samples/output/config_mock/structured.json
samples/output/json_mock/structured.json
```

典型质量报告：

```text
samples/output/example_02_pdf_software_h1_p30_40/quality_report.json
samples/output/example_03_septwolves_annual_p1_20/quality_report.json
samples/output/example_04_dcits_h1_p1_20/quality_report.json
samples/output/example_05_lens_h1_p1_20/quality_report.json
samples/output/board_report_postprocessed_p1_10/quality_report.json
samples/output/config_mock/quality_report.json
samples/output/json_mock/quality_report.json
```

## Gold 评测结果

评测报告位置：

```text
samples/output/config_mock/evaluation_report.json
```

当前 mock gold 样例覆盖：

- `section_structure_accuracy`
- `table_detection_precision`
- `table_record_valid_rate`
- `financial_metric_hit_rate`
- `numeric_parse_success_rate`
- `unit_normalization_accuracy`
- `consistency_check_pass_rate`
- `retry_success_rate`
- `schema_valid_rate`

## 日志关键字段

`run.log.jsonl` 中包含以下关键字段：

```text
time
step
status
mode
selected_mode
page_range
profile
plan
tool
attempt
options
quality_score
checks
structured_json
tables_json
financial_metrics_json
quality_report
```

## 可追溯性说明

系统输出中的表格、章节和 MinerU JSON layout blocks 可通过以下字段追踪：

```text
table_id
logical_table_id
source_tables
source_blocks
block_id
page
bbox
confidence
start_line
end_line
```
