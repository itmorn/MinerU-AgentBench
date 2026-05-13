# FinDoc MinerU Data Agent

面向财报、研报和招股说明书的 MinerU 增强型 Data Agent。系统以 MinerU 作为文档解析工具层，在其输出的 Markdown/JSON 基础上完成任务规划、结构化抽取、表格线索识别、质量校验和可追溯日志记录。

## 核心能力

- 支持 MinerU Agent 轻量 API、精准 API、本地 CLI 三种解析方式
- 自动生成任务计划和运行日志
- 将解析结果整理为统一的 `structured.json`
- 提取标题、表格 records、财务指标、财务数字和质量检查结果
- 生成指标级一致性检查
- 输出 Markdown、JSON、日志，便于复现和评审

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

使用 MinerU Agent 轻量 API 解析远程 URL：

```bash
python run_agent.py \
  --input-url "https://cdn-mineru.openxlab.org.cn/demo/example.pdf" \
  --mode agent-url \
  --output-dir samples/output/demo
```

使用 MinerU 精准 API 解析远程 URL：

```bash
export MINERU_TOKEN="你的 MinerU API Token"
python run_agent.py \
  --input-url "https://example.com/report.pdf" \
  --mode precision-url \
  --output-dir samples/output/report
```

使用本地 MinerU CLI：

```bash
mineru -p samples/input/board_report_2023.pdf -o samples/mineru_raw/board_report
python run_agent.py \
  --mineru-markdown samples/mineru_raw/board_report/full.md \
  --mode markdown \
  --output-dir samples/output/board_report
```

如果只是验证 Agent 后处理流程，可以先用已有 Markdown：

```bash
python run_agent.py \
  --mineru-markdown path/to/full.md \
  --mode markdown \
  --output-dir samples/output/demo
```

启动 API 服务：

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

本地 Markdown 后处理请求示例：

```bash
curl -X POST "http://127.0.0.1:8000/parse" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "markdown",
    "mineru_markdown": "samples/mock/mineru_full.md",
    "output_dir": "samples/output/api_mock"
  }'
```

## 输出文件

每次运行会在输出目录生成：

- `full.md`：MinerU 解析后的 Markdown
- `structured.json`：统一结构化结果
- `quality_report.json`：质量检查报告
- `run.log.jsonl`：任务计划、工具调用、检查步骤和最终结果日志

运行测试：

```bash
python -m unittest discover -s tests
```

## 典型样例

已完成 5 个真实 MinerU 精准 API 解析样例，结果汇总见：

- `samples/output/examples_summary.md`
- `docs/technical_report.md`
- `docs/release_notes.md`

## 推荐比赛包装

项目定位：

> 面向财报与研报的 MinerU 增强型 Data Agent，支持复杂 PDF 解析、跨页表格线索识别、财务数字一致性检查和结构化语料输出。

MinerU 负责底层文档解析，Agent 负责：

- 根据任务目标选择解析方式
- 调用 MinerU 并保存原始结果
- 对章节、表格、数字进行结构化整理
- 生成质量检查和异常提示
- 记录完整可追溯日志
