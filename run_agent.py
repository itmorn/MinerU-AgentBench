from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from agent.pipeline import AgentConfig, DocumentAgent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the MinerU enhanced Data Agent.")
    parser.add_argument("--config", help="JSON/YAML task config. Supports a single task or {'tasks': [...]} batch.")
    parser.add_argument(
        "--mode",
        choices=["auto", "agent-url", "agent-file", "precision-url", "markdown", "mineru-json"],
        default="auto",
        help="MinerU invocation mode or local markdown post-processing mode.",
    )
    parser.add_argument("--input-url", help="Remote document URL for MinerU URL APIs.")
    parser.add_argument("--input-file", help="Local document path for Agent file upload API.")
    parser.add_argument("--mineru-markdown", help="Existing MinerU full.md path.")
    parser.add_argument("--mineru-json", help="Existing MinerU JSON/content_list path.")
    parser.add_argument("--output-dir", help="Directory for agent outputs.")
    parser.add_argument("--task-type", default="financial_report_structuring", help="Task goal for planner decisions.")
    parser.add_argument("--language", default="ch", help="Document language for OCR.")
    parser.add_argument("--page-range", default="1-10", help="Page range for MinerU API.")
    parser.add_argument("--token-env", default="MINERU_TOKEN", help="Env var name for precision API token.")
    parser.add_argument("--poll-seconds", type=float, default=3.0, help="Polling interval.")
    parser.add_argument("--timeout-seconds", type=float, default=600.0, help="Polling timeout.")
    parser.add_argument("--quality-threshold", type=float, default=0.85, help="Minimum quality score before recovery advice.")
    parser.add_argument("--max-retry", type=int, default=1, help="Maximum automatic recovery attempts.")
    parser.add_argument("--enable-ocr", action="store_true", help="Force OCR mode for MinerU calls.")
    parser.add_argument("--disable-table", action="store_true", help="Disable table recognition for MinerU calls.")
    parser.add_argument("--disable-formula", action="store_true", help="Disable formula recognition for MinerU calls.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.config:
        results = run_config(Path(args.config))
        for index, item in enumerate(results, start=1):
            if item["status"] == "completed":
                result = item["result"]
                print(f"task_{index}.structured_json={result.structured_json}")
                print(f"task_{index}.quality_report={result.quality_report}")
                print(f"task_{index}.run_log={result.run_log}")
            else:
                print(f"task_{index}.status=failed")
                print(f"task_{index}.error={item['error']}")
        return
    if not args.output_dir:
        raise SystemExit("--output-dir is required unless --config is used.")
    result = DocumentAgent(config_from_mapping(vars(args))).run()
    print(f"structured_json={result.structured_json}")
    print(f"quality_report={result.quality_report}")
    print(f"run_log={result.run_log}")


def run_config(path: Path):
    payload = load_config(path)
    raw_tasks = payload.get("tasks") if isinstance(payload, dict) and "tasks" in payload else [payload]
    results = []
    for index, raw in enumerate(raw_tasks, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"Task {index} must be an object.")
        try:
            result = DocumentAgent(config_from_mapping(raw)).run()
        except Exception as exc:
            results.append({"status": "failed", "task_index": index, "error": str(exc), "task": raw})
            continue
        results.append({"status": "completed", "task_index": index, "result": result, "task": raw})
    report_path = path.with_name(f"{path.stem}_batch_report.json")
    report_path.write_text(json.dumps(_batch_report(results), ensure_ascii=False, indent=2), encoding="utf-8")
    return results


def _batch_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    tasks = []
    for item in results:
        if item["status"] == "completed":
            result = item["result"]
            tasks.append(
                {
                    "task_index": item["task_index"],
                    "status": "completed",
                    "structured_json": str(result.structured_json),
                    "quality_report": str(result.quality_report),
                    "run_log": str(result.run_log),
                }
            )
        else:
            tasks.append(
                {
                    "task_index": item["task_index"],
                    "status": "failed",
                    "error": item["error"],
                }
            )
    return {
        "total": len(results),
        "completed": sum(1 for item in results if item["status"] == "completed"),
        "failed": sum(1 for item in results if item["status"] == "failed"),
        "tasks": tasks,
    }


def load_config(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise RuntimeError("YAML config requires PyYAML. Use .json config or install pyyaml.") from exc
    loaded = yaml.safe_load(text)
    if not isinstance(loaded, dict):
        raise ValueError("Config root must be an object.")
    return loaded


def config_from_mapping(data: dict[str, Any]) -> AgentConfig:
    output_dir = data.get("output_dir")
    if not output_dir:
        raise ValueError("output_dir is required.")
    config = AgentConfig(
        mode=data.get("mode", "auto"),
        output_dir=Path(output_dir),
        input_url=data.get("input_url"),
        input_file=Path(data["input_file"]) if data.get("input_file") else None,
        mineru_markdown=Path(data["mineru_markdown"]) if data.get("mineru_markdown") else None,
        mineru_json=Path(data["mineru_json"]) if data.get("mineru_json") else None,
        task_type=data.get("task_type", "financial_report_structuring"),
        language=data.get("language", "ch"),
        page_range=data.get("page_range", "1-10"),
        token_env=data.get("token_env", "MINERU_TOKEN"),
        poll_seconds=float(data.get("poll_seconds", 3.0)),
        timeout_seconds=float(data.get("timeout_seconds", 600.0)),
        quality_threshold=float(data.get("quality_threshold", 0.85)),
        max_retry=int(data.get("max_retry", 1)),
        enable_table=not bool(data.get("disable_table", False)),
        enable_formula=not bool(data.get("disable_formula", False)),
        enable_ocr=bool(data.get("enable_ocr", False)),
    )
    return config


if __name__ == "__main__":
    main()
