from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class InputProfile:
    source_name: str
    source_type: str
    document_type: str
    risks: list[str]
    selected_mode: str


class AgentPlanner:
    def analyze(
        self,
        *,
        mode: str,
        input_url: str | None,
        input_file: Path | None,
        mineru_markdown: Path | None,
        mineru_json: Path | None = None,
        page_range: str,
        token_env: str,
        task_type: str,
    ) -> InputProfile:
        source_name = self._source_name(input_url, input_file, mineru_markdown, mineru_json)
        source_type = self._source_type(input_url, input_file, mineru_markdown, mineru_json)
        document_type = self._document_type(source_name, task_type)
        selected_mode = self._select_mode(mode, input_url, input_file, mineru_markdown, mineru_json, token_env)
        risks = self._risks(source_name, source_type, document_type, page_range)
        return InputProfile(
            source_name=source_name,
            source_type=source_type,
            document_type=document_type,
            risks=risks,
            selected_mode=selected_mode,
        )

    def build_plan(self, profile: InputProfile) -> list[dict[str, Any]]:
        plan: list[dict[str, Any]] = [
            {
                "step": "analyze_input",
                "goal": "detect document type and parsing risks",
                "document_type": profile.document_type,
                "risks": profile.risks,
            },
            {
                "step": "select_strategy",
                "goal": "choose MinerU parsing mode based on document complexity",
                "mode": profile.selected_mode,
            },
            {
                "step": "run_mineru",
                "goal": "extract text, layout and tables or reuse existing MinerU markdown",
            },
            {
                "step": "build_structured_schema",
                "goal": "build sections, tables, merged tables and financial metrics",
            },
            {
                "step": "validate_quality",
                "goal": "score output quality, validate schema and detect recoverable errors",
            },
            {
                "step": "export_results",
                "goal": "write JSON, Markdown and trace logs",
            },
        ]
        if profile.document_type == "financial_report":
            plan.insert(
                4,
                {
                    "step": "financial_checks",
                    "goal": "normalize units and recompute growth rates for financial tables",
                },
            )
        return plan

    def _select_mode(
        self,
        mode: str,
        input_url: str | None,
        input_file: Path | None,
        mineru_markdown: Path | None,
        mineru_json: Path | None,
        token_env: str,
    ) -> str:
        if mode != "auto":
            return mode
        if mineru_json:
            return "mineru-json"
        if mineru_markdown:
            return "markdown"
        if input_url and os.getenv(token_env):
            return "precision-url"
        if input_url:
            return "agent-url"
        if input_file:
            return "agent-file"
        return "markdown"

    def _source_name(
        self,
        input_url: str | None,
        input_file: Path | None,
        mineru_markdown: Path | None,
        mineru_json: Path | None,
    ) -> str:
        if input_file:
            return input_file.name
        if mineru_json:
            return mineru_json.name
        if mineru_markdown:
            return mineru_markdown.name
        if input_url:
            return input_url
        return "unknown"

    def _source_type(
        self,
        input_url: str | None,
        input_file: Path | None,
        mineru_markdown: Path | None,
        mineru_json: Path | None,
    ) -> str:
        if mineru_json:
            return "mineru_json"
        if mineru_markdown:
            return "mineru_markdown"
        if input_url:
            return "remote_document"
        if input_file:
            suffix = input_file.suffix.lower()
            return "pdf" if suffix == ".pdf" else suffix.lstrip(".") or "file"
        return "unknown"

    def _document_type(self, source_name: str, task_type: str) -> str:
        text = f"{source_name} {task_type}".lower()
        financial_keywords = (
            "financial",
            "annual",
            "report",
            "财报",
            "年报",
            "半年报",
            "季报",
            "招股",
            "审计",
        )
        return "financial_report" if any(keyword in text for keyword in financial_keywords) else "general_document"

    def _risks(self, source_name: str, source_type: str, document_type: str, page_range: str) -> list[str]:
        risks = []
        if document_type == "financial_report":
            risks.extend(["table_dense", "financial_units_mixed", "cross_page_table_possible"])
        if source_type == "pdf":
            risks.append("layout_complexity")
        if page_range and "-" in page_range:
            try:
                start, end = [int(part) for part in page_range.split("-", 1)]
            except ValueError:
                risks.append("page_range_unparsed")
            else:
                if end - start + 1 <= 3:
                    risks.append("narrow_page_range")
        if "scan" in source_name.lower() or "扫描" in source_name:
            risks.append("scanned_document_possible")
        return risks
