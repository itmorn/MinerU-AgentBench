from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from agent.logger import JsonlLogger
from agent.mineru_client import MinerUClient
from agent.postprocess import MarkdownPostProcessor


@dataclass(frozen=True)
class AgentConfig:
    mode: str
    output_dir: Path
    input_url: str | None = None
    input_file: Path | None = None
    mineru_markdown: Path | None = None
    language: str = "ch"
    page_range: str = "1-10"
    token_env: str = "MINERU_TOKEN"
    poll_seconds: float = 3.0
    timeout_seconds: float = 600.0


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

    def run(self) -> AgentRunResult:
        self.logger.event("planner", "started", mode=self.config.mode, page_range=self.config.page_range)
        plan = self._build_plan()
        self.logger.event("planner", "completed", plan=plan)

        markdown = self._obtain_markdown()
        full_md = self.output_dir / "full.md"
        full_md.write_text(markdown, encoding="utf-8")
        self.logger.event("parser", "completed", markdown_path=str(full_md), char_count=len(markdown))

        processor = MarkdownPostProcessor()
        source_name = self._source_name()
        result = processor.process(markdown, source_name=source_name)
        structured_path = self.output_dir / "structured.json"
        quality_path = self.output_dir / "quality_report.json"
        structured_path.write_text(json.dumps(result.structured, ensure_ascii=False, indent=2), encoding="utf-8")
        quality_path.write_text(json.dumps(result.quality, ensure_ascii=False, indent=2), encoding="utf-8")
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
            quality_report=str(quality_path),
        )
        return AgentRunResult(
            structured_json=structured_path,
            quality_report=quality_path,
            run_log=self.log_path,
        )

    def _build_plan(self) -> list[dict[str, str]]:
        return [
            {"step": "parse", "tool": "MinerU", "goal": "Convert source document into Markdown."},
            {"step": "structure", "tool": "MarkdownPostProcessor", "goal": "Extract headings, tables, and numeric signals."},
            {"step": "validate", "tool": "QualityChecker", "goal": "Check structure completeness and financial data signals."},
            {"step": "report", "tool": "JsonlLogger", "goal": "Write reproducible outputs and trace logs."},
        ]

    def _obtain_markdown(self) -> str:
        mode = self.config.mode
        if mode == "markdown":
            if not self.config.mineru_markdown:
                raise ValueError("--mineru-markdown is required for markdown mode.")
            self.logger.event("parser", "started", tool="local-markdown", path=str(self.config.mineru_markdown))
            target = self.output_dir / "mineru_source.md"
            shutil.copyfile(self.config.mineru_markdown, target)
            return self.config.mineru_markdown.read_text(encoding="utf-8")

        client = MinerUClient(
            token_env=self.config.token_env,
            poll_seconds=self.config.poll_seconds,
            timeout_seconds=self.config.timeout_seconds,
        )
        if mode == "agent-url":
            if not self.config.input_url:
                raise ValueError("--input-url is required for agent-url mode.")
            self.logger.event("parser", "started", tool="mineru-agent-url", url=self.config.input_url)
            result = client.parse_agent_url(
                self.config.input_url,
                language=self.config.language,
                page_range=self.config.page_range,
            )
            self.logger.event("parser", "mineru_result", source=result.source, raw=result.raw)
            return result.markdown

        if mode == "agent-file":
            if not self.config.input_file:
                raise ValueError("--input-file is required for agent-file mode.")
            self.logger.event("parser", "started", tool="mineru-agent-file", path=str(self.config.input_file))
            result = client.parse_agent_file(
                self.config.input_file,
                language=self.config.language,
                page_range=self.config.page_range,
            )
            self.logger.event("parser", "mineru_result", source=result.source, raw=result.raw)
            return result.markdown

        if mode == "precision-url":
            if not self.config.input_url:
                raise ValueError("--input-url is required for precision-url mode.")
            self.logger.event("parser", "started", tool="mineru-precision-url", url=self.config.input_url)
            result = client.parse_precision_url(
                self.config.input_url,
                language=self.config.language,
                page_range=self.config.page_range,
            )
            self.logger.event("parser", "mineru_result", source=result.source, raw=result.raw)
            return result.markdown

        raise ValueError(f"Unsupported mode: {mode}")

    def _source_name(self) -> str:
        if self.config.input_file:
            return self.config.input_file.name
        if self.config.input_url:
            return self.config.input_url
        if self.config.mineru_markdown:
            return self.config.mineru_markdown.name
        return "unknown"

