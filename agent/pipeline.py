from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from agent.logger import JsonlLogger
from agent.mineru_client import MinerUClient
from agent.mineru_json import MinerUJsonParser
from agent.planner import AgentPlanner
from agent.postprocess import MarkdownPostProcessor
from agent.validator import QualityValidator


@dataclass(frozen=True)
class AgentConfig:
    mode: str
    output_dir: Path
    input_url: str | None = None
    input_file: Path | None = None
    mineru_markdown: Path | None = None
    mineru_json: Path | None = None
    task_type: str = "financial_report_structuring"
    language: str = "ch"
    page_range: str = "1-10"
    token_env: str = "MINERU_TOKEN"
    poll_seconds: float = 3.0
    timeout_seconds: float = 600.0
    quality_threshold: float = 0.85
    max_retry: int = 1
    enable_table: bool = True
    enable_formula: bool = True
    enable_ocr: bool = False


@dataclass(frozen=True)
class AgentRunResult:
    structured_json: Path
    quality_report: Path
    run_log: Path


class DocumentAgent:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.output_dir = config.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.output_dir / "run.log.jsonl"
        self.logger = JsonlLogger(self.log_path)
        self.planner = AgentPlanner()
        self.validator = QualityValidator()
        self.profile = self.planner.analyze(
            mode=config.mode,
            input_url=config.input_url,
            input_file=config.input_file,
            mineru_markdown=config.mineru_markdown,
            mineru_json=config.mineru_json,
            page_range=config.page_range,
            token_env=config.token_env,
            task_type=config.task_type,
        )

    def run(self) -> AgentRunResult:
        self.logger.event(
            "planner",
            "started",
            mode=self.config.mode,
            selected_mode=self.profile.selected_mode,
            page_range=self.config.page_range,
        )
        plan = self._build_plan()
        self.logger.event("planner", "completed", profile=self.profile.__dict__, plan=plan)

        processor = MarkdownPostProcessor()
        source_name = self._source_name()
        markdown, metadata = self._obtain_markdown(attempt=0)
        self.logger.event("parser", "completed", attempt=0, char_count=len(markdown))
        result = processor.process(markdown, source_name=source_name, **metadata)
        result, markdown, metadata = self._recover_if_needed(processor, markdown, source_name, result, metadata)
        full_md = self.output_dir / "full.md"
        structured_path = self.output_dir / "structured.json"
        quality_path = self.output_dir / "quality_report.json"
        tables_path = self.output_dir / "tables.json"
        financial_metrics_path = self.output_dir / "financial_metrics.json"
        full_md.write_text(markdown, encoding="utf-8")
        structured_path.write_text(json.dumps(result.structured, ensure_ascii=False, indent=2), encoding="utf-8")
        quality_path.write_text(json.dumps(result.quality, ensure_ascii=False, indent=2), encoding="utf-8")
        tables_path.write_text(json.dumps(result.structured["tables"], ensure_ascii=False, indent=2), encoding="utf-8")
        financial_metrics_path.write_text(
            json.dumps(result.structured["financial_metrics"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.logger.event(
            "validator",
            "completed",
            quality_score=result.quality["score"],
            checks=result.quality["checks"],
        )
        self.logger.event(
            "reporter",
            "completed",
            structured_json=str(structured_path),
            tables_json=str(tables_path),
            financial_metrics_json=str(financial_metrics_path),
            quality_report=str(quality_path),
        )
        return AgentRunResult(
            structured_json=structured_path,
            quality_report=quality_path,
            run_log=self.log_path,
        )

    def _build_plan(self) -> list[dict[str, str]]:
        return self.planner.build_plan(self.profile)

    def _obtain_markdown(self, *, attempt: int, parse_options: dict | None = None) -> tuple[str, dict]:
        parse_options = parse_options or {}
        mode = self.profile.selected_mode
        if mode == "markdown":
            if not self.config.mineru_markdown:
                raise ValueError("--mineru-markdown is required for markdown mode.")
            self.logger.event("parser", "started", attempt=attempt, tool="local-markdown", path=str(self.config.mineru_markdown))
            target = self.output_dir / "mineru_source.md"
            shutil.copyfile(self.config.mineru_markdown, target)
            return self.config.mineru_markdown.read_text(encoding="utf-8"), {}

        if mode == "mineru-json":
            if not self.config.mineru_json:
                raise ValueError("--mineru-json is required for mineru-json mode.")
            self.logger.event("parser", "started", attempt=attempt, tool="local-mineru-json", path=str(self.config.mineru_json))
            parsed = MinerUJsonParser().parse_path(self.config.mineru_json)
            target = self.output_dir / "mineru_source.json"
            shutil.copyfile(self.config.mineru_json, target)
            return parsed.markdown, {
                "layout_blocks": parsed.layout_blocks,
                "figures": parsed.figures,
                "paragraphs": parsed.paragraphs,
            }

        options = self._parse_options(parse_options)
        client = MinerUClient(
            token_env=self.config.token_env,
            poll_seconds=self.config.poll_seconds,
            timeout_seconds=self.config.timeout_seconds,
        )
        if mode == "agent-url":
            if not self.config.input_url:
                raise ValueError("--input-url is required for agent-url mode.")
            self.logger.event("parser", "started", attempt=attempt, tool="mineru-agent-url", url=self.config.input_url, options=options)
            result = client.parse_agent_url(
                self.config.input_url,
                language=self.config.language,
                page_range=options["page_range"],
                enable_table=options["enable_table"],
                enable_formula=options["enable_formula"],
                is_ocr=options["is_ocr"],
            )
            self.logger.event("parser", "mineru_result", source=result.source, raw=result.raw)
            return result.markdown, {}

        if mode == "agent-file":
            if not self.config.input_file:
                raise ValueError("--input-file is required for agent-file mode.")
            self.logger.event("parser", "started", attempt=attempt, tool="mineru-agent-file", path=str(self.config.input_file), options=options)
            result = client.parse_agent_file(
                self.config.input_file,
                language=self.config.language,
                page_range=options["page_range"],
                enable_table=options["enable_table"],
                enable_formula=options["enable_formula"],
                is_ocr=options["is_ocr"],
            )
            self.logger.event("parser", "mineru_result", source=result.source, raw=result.raw)
            return result.markdown, {}

        if mode == "precision-url":
            if not self.config.input_url:
                raise ValueError("--input-url is required for precision-url mode.")
            self.logger.event("parser", "started", attempt=attempt, tool="mineru-precision-url", url=self.config.input_url, options=options)
            result = client.parse_precision_url(
                self.config.input_url,
                language=self.config.language,
                page_range=options["page_range"],
                enable_table=options["enable_table"],
                enable_formula=options["enable_formula"],
                is_ocr=options["is_ocr"],
            )
            self.logger.event("parser", "mineru_result", source=result.source, raw=result.raw)
            return result.markdown, {}

        raise ValueError(f"Unsupported mode: {mode}")

    def _parse_options(self, overrides: dict) -> dict:
        options = {
            "page_range": self.config.page_range,
            "enable_table": self.config.enable_table,
            "enable_formula": self.config.enable_formula,
            "is_ocr": self.config.enable_ocr,
        }
        options.update({key: value for key, value in overrides.items() if value is not None})
        return options

    def _recover_if_needed(
        self,
        processor: MarkdownPostProcessor,
        markdown: str,
        source_name: str,
        result,
        metadata: dict,
    ) -> tuple[object, str, dict]:
        score = float(result.quality.get("score", 0))
        if score >= self.config.quality_threshold:
            self.logger.event(
                "recovery",
                "skipped",
                reason="quality_threshold_met",
                quality_score=score,
                threshold=self.config.quality_threshold,
            )
            return result, markdown, metadata
        diagnosis = self.validator.diagnose(result.quality)
        self.logger.event(
            "recovery",
            "diagnosed",
            quality_score=score,
            threshold=self.config.quality_threshold,
            issues=diagnosis,
        )
        if self.profile.selected_mode == "markdown" or self.config.max_retry <= 0:
            repaired = processor.process(markdown, source_name=source_name, **metadata)
            repaired.quality["recovery"] = {
                "status": "local_repair_only",
                "reason": "source markdown is fixed or retries disabled",
                "diagnosis": diagnosis,
            }
            self.logger.event("recovery", "local_repair_completed", quality_score=repaired.quality["score"])
            return repaired, markdown, metadata
        best_result = result
        best_markdown = markdown
        for attempt in range(1, self.config.max_retry + 1):
            decision = self.validator.decide_recovery(diagnosis, page_range=self.config.page_range)
            self.logger.event("recovery", "retry_started", attempt=attempt, action=decision.action, options=decision.parse_options)
            try:
                retried_markdown, retried_metadata = self._obtain_markdown(attempt=attempt, parse_options=decision.parse_options)
            except Exception as exc:
                self.logger.event("recovery", "retry_failed", attempt=attempt, error=str(exc))
                break
            retried_result = processor.process(retried_markdown, source_name=source_name, **retried_metadata)
            retried_score = float(retried_result.quality.get("score", 0))
            self.logger.event("recovery", "retry_completed", attempt=attempt, quality_score=retried_score)
            if retried_score >= float(best_result.quality.get("score", 0)):
                best_result = retried_result
                best_markdown = retried_markdown
                metadata = retried_metadata
            if retried_score >= self.config.quality_threshold:
                best_result.quality["recovery"] = {
                    "status": "recovered",
                    "attempt": attempt,
                    "action": decision.action,
                    "diagnosis": decision.diagnosis,
                }
                return best_result, best_markdown, metadata
            diagnosis = self.validator.diagnose(retried_result.quality)
        best_result.quality["recovery"] = {
            "status": "retry_exhausted",
            "action": self.validator.retry_action(diagnosis),
            "diagnosis": diagnosis,
        }
        return best_result, best_markdown, metadata

    def _source_name(self) -> str:
        if self.config.input_file:
            return self.config.input_file.name
        if self.config.input_url:
            return self.config.input_url
        if self.config.mineru_json:
            return self.config.mineru_json.name
        if self.config.mineru_markdown:
            return self.config.mineru_markdown.name
        return "unknown"
