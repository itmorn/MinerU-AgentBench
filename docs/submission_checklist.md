# 提交材料清单

## 必交材料

- GitHub 仓库链接
- 系统部署与运行说明：`docs/deployment.md`
- 技术报告：`docs/technical_report.md`
- 典型任务样例输出：`samples/output/`
- 系统运行日志：各样例目录下的 `run.log.jsonl`
- 测试结果汇总：`samples/output/examples_summary.md`

## 推荐提交结构

```text
.
├── README.md
├── requirements.txt
├── run_agent.py
├── app.py
├── agent/
├── scripts/
├── tests/
├── docs/
│   ├── deployment.md
│   ├── technical_report.md
│   └── submission_checklist.md
└── samples/
    ├── input/
    └── output/
```

## 提交前检查

- 确认仓库中没有 MinerU Token、手机号、账号 Cookie 或 `.env`
- 确认 `python -m unittest discover -s tests` 通过
- 确认 `python -m compileall app.py agent run_agent.py scripts tests` 通过
- 确认 5 个样例输出目录均包含：
  - `full.md`
  - `structured.json`
  - `quality_report.json`
  - `run.log.jsonl`
- 确认 `README.md` 能指导评审人员复现
- 确认技术报告中不少于 5 个典型任务示例

## 可选加分材料

- 2-3 分钟演示视频
- PPT 项目介绍
- API 服务部署地址
- 更多 PDF 样例输出
