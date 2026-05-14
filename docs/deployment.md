# 部署与运行说明

## 环境要求

- Python 3.10+
- 可访问 MinerU API 的网络环境
- 可选：本地安装 MinerU CLI

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行方式

### 方式一：MinerU Agent 轻量 API

适合快速演示，无需 Token，但文件大小和页数有限制。

```bash
python run_agent.py \
  --mode agent-url \
  --input-url "https://cdn-mineru.openxlab.org.cn/demo/example.pdf" \
  --page-range "1-10" \
  --output-dir samples/output/demo_agent
```

### 方式二：MinerU 精准 API

适合比赛正式材料，需申请 Token。

```bash
export MINERU_TOKEN="你的 Token"
python run_agent.py \
  --mode precision-url \
  --input-url "https://example.com/report.pdf" \
  --page-range "1-20" \
  --output-dir samples/output/demo_precision
```

### 方式三：本地 MinerU CLI + Agent 后处理

```bash
mineru -p samples/input/board_report_2023.pdf -o samples/mineru_raw/board_report
python run_agent.py \
  --mode markdown \
  --mineru-markdown samples/mineru_raw/board_report/full.md \
  --output-dir samples/output/board_report
```

### 方式四：配置文件批处理

```bash
python run_agent.py --config samples/config_batch.json
```

配置文件支持单任务对象，也支持 `{"tasks": [...]}` 批任务数组。常用字段包括 `mode`、`input_url`、`input_file`、`mineru_markdown`、`output_dir`、`page_range`、`quality_threshold`、`max_retry`、`enable_ocr`。

### 方式五：MinerU JSON 后处理

```bash
python run_agent.py \
  --mode mineru-json \
  --mineru-json samples/mock/mineru_content_list.json \
  --output-dir samples/output/json_mock
```

该模式会将 MinerU JSON/content_list 转换为 Markdown 后处理，并保留 `layout_blocks`、`figures`、`paragraphs`、表格 `source_blocks`、字段类型和 bbox/page 追踪信息。

### 方式六：Docker Compose

```bash
docker compose up --build
curl http://127.0.0.1:8000/health
```

## 日志查看

```bash
cat samples/output/demo_agent/run.log.jsonl
```

日志包含任务计划、工具调用、解析结果、质量检查和报告输出路径。

## API 服务

启动服务：

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

解析已有 MinerU Markdown：

```bash
curl -X POST "http://127.0.0.1:8000/parse" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "markdown",
    "mineru_markdown": "samples/mock/mineru_full.md",
    "output_dir": "samples/output/api_mock"
  }'
```

解析远程 PDF URL：

```bash
export MINERU_TOKEN="你的 Token"
curl -X POST "http://127.0.0.1:8000/parse" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "precision-url",
    "input_url": "https://static.cninfo.com.cn/finalpage/2024-03-28/1219426184.PDF",
    "page_range": "1-10",
    "output_dir": "samples/output/api_precision_demo"
  }'
```

批量解析：

```bash
curl -X POST "http://127.0.0.1:8000/batch_parse" \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": [
      {
        "mode": "markdown",
        "mineru_markdown": "samples/mock/mineru_full.md",
        "output_dir": "samples/output/api_batch_mock"
      }
    ]
  }'
```

## Gold 评测

```bash
python scripts/evaluate.py \
  --gold samples/gold/mock_gold.json \
  --prediction samples/output/config_mock/structured.json \
  --output samples/output/config_mock/evaluation_report.json
```
