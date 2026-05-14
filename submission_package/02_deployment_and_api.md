# 02 系统部署与运行说明文档

## 参考文档

完整部署说明见：

```text
docs/deployment.md
README.md
```

## 运行环境要求

- 操作系统：Linux / macOS / Windows WSL，推荐 Linux。
- Python：3.10+，推荐 Python 3.11。
- 依赖库：见 `requirements.txt`。
- 网络：调用 MinerU API 时需要外网访问；本地 Markdown / MinerU JSON 后处理不需要网络。
- Token：使用 MinerU 精准 API 时需要设置 `MINERU_TOKEN`。
- 硬件：本项目主要做 API 调用与后处理，普通 CPU 环境即可；处理大批量长文档时建议 4C8G 以上。

## 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## CLI 运行方式

本地 Markdown 后处理：

```bash
python run_agent.py \
  --mode markdown \
  --mineru-markdown samples/mock/mineru_full.md \
  --output-dir samples/output/mock
```

MinerU JSON/content_list 后处理：

```bash
python run_agent.py \
  --mode mineru-json \
  --mineru-json samples/mock/mineru_content_list.json \
  --output-dir samples/output/json_mock
```

配置文件批处理：

```bash
python run_agent.py --config samples/config_batch.json
```

MinerU 精准 API：

```bash
export MINERU_TOKEN="你的 MinerU Token"
python run_agent.py \
  --mode precision-url \
  --input-url "https://example.com/report.pdf" \
  --page-range "1-20" \
  --output-dir samples/output/demo_precision
```

## API 服务

启动服务：

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

解析接口：

```http
POST /parse
Content-Type: application/json
```

请求示例：

```json
{
  "mode": "markdown",
  "mineru_markdown": "samples/mock/mineru_full.md",
  "output_dir": "samples/output/api_mock",
  "task_type": "financial_report_structuring",
  "quality_threshold": 0.85,
  "max_retry": 0
}
```

返回字段：

```json
{
  "task_id": "api_mock",
  "status": "completed",
  "output_dir": "samples/output/api_mock",
  "full_md": "samples/output/api_mock/full.md",
  "structured_json": "samples/output/api_mock/structured.json",
  "tables_json": "samples/output/api_mock/tables.json",
  "financial_metrics_json": "samples/output/api_mock/financial_metrics.json",
  "quality_report": "samples/output/api_mock/quality_report.json",
  "run_log": "samples/output/api_mock/run.log.jsonl",
  "quality_score": 1.0
}
```

批处理接口：

```http
POST /batch_parse
Content-Type: application/json
```

## Docker 运行

```bash
docker compose up --build
curl http://127.0.0.1:8000/health
```

## 测试方法

```bash
python -m unittest discover -s tests
python -m compileall agent app.py run_agent.py scripts/evaluate.py
```

Gold 标注评测：

```bash
python scripts/evaluate.py \
  --gold samples/gold/mock_gold.json \
  --prediction samples/output/config_mock/structured.json \
  --output samples/output/config_mock/evaluation_report.json
```

## 日志查看

每个任务输出目录都会生成：

```text
run.log.jsonl
quality_report.json
structured.json
tables.json
financial_metrics.json
full.md
```

日志查看示例：

```bash
tail -n 20 samples/output/config_mock/run.log.jsonl
```
