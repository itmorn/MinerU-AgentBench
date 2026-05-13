# 发布说明

## 当前版本

版本：`v0.1.0`

定位：面向财报、研报和上市公司公告的 MinerU 增强型 Data Agent 原型。

## 已完成能力

- MinerU 精准 API 调用
- MinerU Agent 轻量 API 调用
- 本地 Markdown 后处理
- FastAPI 服务入口
- 标题、表格、财务数字线索抽取
- 表格行列级结构化输出
- 财务指标抽取和指标级一致性检查
- 质量检查报告
- JSONL 运行日志
- 单元测试
- 5 个真实公开 PDF 解析样例

## 建议 GitHub 内容

建议提交：

- `README.md`
- `requirements.txt`
- `run_agent.py`
- `app.py`
- `agent/`
- `scripts/`
- `tests/`
- `docs/`
- `samples/mock/`
- `samples/output/examples_summary.md`
- `samples/output/examples_summary.json`
- 5 个典型样例输出目录

谨慎提交：

- `samples/input/` 中的 PDF 文件体积较大，但均为公开披露文档。若 GitHub 仓库希望轻量化，可以只保留来源链接和输出结果。

不要提交：

- `.env`
- MinerU Token
- 账号 Cookie
- Python `__pycache__`
- 个人手机号、身份证、银行卡等隐私材料

## 比赛附件建议

若平台允许上传附件，建议打包：

- 完整代码
- `docs/technical_report.md`
- `docs/deployment.md`
- `samples/output/`
- `samples/mock/`
- `samples/input/` 中用于复现的公开 PDF

## 复现命令

命令行模式：

```bash
python run_agent.py \
  --mode markdown \
  --mineru-markdown samples/mock/mineru_full.md \
  --output-dir samples/output/release_check
```

API 模式：

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```
