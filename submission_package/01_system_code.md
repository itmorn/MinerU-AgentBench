# 01 系统实现代码或关键模块代码

## 提交内容

本项目提交 MinerU-DataAgent 的完整系统代码与关键模块代码，GitHub Repo 链接：

```text
https://github.com/itmorn/MinerU-AgentBench
```

## 关键代码模块

```text
agent/
  pipeline.py       # Agent 主流程：规划、解析、恢复、导出
  planner.py        # 输入分析、文档类型识别、策略选择、任务计划生成
  mineru_client.py  # MinerU Agent API / 精准 API 调用封装
  mineru_json.py    # MinerU JSON/content_list 后处理入口
  postprocess.py    # 章节树、表格、财务指标、单位归一化、质量报告
  schema.py         # 结构化结果 Schema 校验
  validator.py      # 质量诊断与自动恢复决策
  logger.py         # JSONL 可追踪运行日志

app.py              # FastAPI 服务入口
run_agent.py        # CLI / 配置文件 / 批处理入口
scripts/evaluate.py # Gold 标注对比评测脚本
schemas/structured.schema.json # 正式结构化输出 JSON Schema
```

## 已实现能力摘要

- 支持 MinerU Agent URL、文件上传、精准 API、本地 Markdown、MinerU JSON/content_list 多种输入。
- 支持 Agent 自动规划、解析策略选择、质量诊断、低质量自动重试。
- 支持章节树、表格结构化、跨页表格合并、字段类型识别、财务指标抽取。
- 支持金额单位归一化、同比/变动率重算、质量评分、warnings 和 Schema 校验。
- 支持 CLI、API、配置文件批处理、Docker Compose、Gold 评测。

## 复现入口

```bash
python run_agent.py --config samples/config_batch.json
python run_agent.py --mode mineru-json --mineru-json samples/mock/mineru_content_list.json --output-dir samples/output/json_mock
uvicorn app:app --host 0.0.0.0 --port 8000
```
