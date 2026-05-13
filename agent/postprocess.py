from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
NUMBER_RE = re.compile(r"(?<![A-Za-z])[-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?%?|[-+]?\d+(?:\.\d+)?%?")
MONEY_UNIT_RE = re.compile(r"(元|万元|亿元|人民币|%|百分点)")


@dataclass(frozen=True)
class PostProcessResult:
    structured: dict[str, Any]
    quality: dict[str, Any]


class MarkdownPostProcessor:
    def process(self, markdown: str, *, source_name: str) -> PostProcessResult:
        lines = markdown.splitlines()
        headings = self._extract_headings(lines)
        tables = self._extract_table_blocks(lines)
        numeric_mentions = self._extract_numeric_mentions(lines)
        quality = self._quality_report(markdown, headings, tables, numeric_mentions)
        structured = {
            "source_name": source_name,
            "document_stats": {
                "line_count": len(lines),
                "char_count": len(markdown),
                "heading_count": len(headings),
                "table_count": len(tables),
                "numeric_mention_count": len(numeric_mentions),
            },
            "headings": headings,
            "tables": tables,
            "numeric_mentions": numeric_mentions[:200],
            "agent_notes": [
                "MinerU parses the source document into Markdown/JSON-like assets.",
                "The Agent normalizes document signals for downstream financial QA and corpus production.",
                "Quality checks flag weak structure, sparse tables, and missing financial units for review.",
            ],
        }
        return PostProcessResult(structured=structured, quality=quality)

    def _extract_headings(self, lines: list[str]) -> list[dict[str, Any]]:
        headings: list[dict[str, Any]] = []
        for index, line in enumerate(lines, start=1):
            match = HEADING_RE.match(line)
            if match:
                headings.append(
                    {
                        "line": index,
                        "level": len(match.group(1)),
                        "title": match.group(2).strip(),
                    }
                )
        return headings

    def _extract_table_blocks(self, lines: list[str]) -> list[dict[str, Any]]:
        tables: list[dict[str, Any]] = []
        current: list[tuple[int, str]] = []
        for index, line in enumerate(lines, start=1):
            if self._looks_like_table_line(line):
                current.append((index, line))
                continue
            if current:
                self._append_table(tables, current)
                current = []
        if current:
            self._append_table(tables, current)
        return tables

    def _append_table(self, tables: list[dict[str, Any]], block: list[tuple[int, str]]) -> None:
        text = "\n".join(line for _, line in block)
        html_row_count = text.lower().count("<tr")
        tables.append(
            {
                "table_id": f"table_{len(tables) + 1:03d}",
                "start_line": block[0][0],
                "end_line": block[-1][0],
                "row_count": html_row_count if html_row_count else len(block),
                "numeric_cell_count": len(NUMBER_RE.findall(text)),
                "preview": [line for _, line in block[:5]],
            }
        )

    def _looks_like_table_line(self, line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        pipe_count = stripped.count("|")
        if pipe_count >= 2:
            return True
        lowered = stripped.lower()
        if "<table" in lowered or "<tr" in lowered or ("<td" in lowered and "</td>" in lowered):
            return True
        if "\t" in stripped and len(NUMBER_RE.findall(stripped)) >= 2:
            return True
        return False

    def _extract_numeric_mentions(self, lines: list[str]) -> list[dict[str, Any]]:
        mentions: list[dict[str, Any]] = []
        for index, line in enumerate(lines, start=1):
            numbers = NUMBER_RE.findall(line)
            if not numbers:
                continue
            units = MONEY_UNIT_RE.findall(line)
            if numbers and (units or len(numbers) >= 3):
                mentions.append(
                    {
                        "line": index,
                        "numbers": numbers[:20],
                        "units": sorted(set(units)),
                        "text": line.strip()[:300],
                    }
                )
        return mentions

    def _quality_report(
        self,
        markdown: str,
        headings: list[dict[str, Any]],
        tables: list[dict[str, Any]],
        numeric_mentions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        checks = [
            {
                "name": "non_empty_markdown",
                "passed": len(markdown.strip()) > 100,
                "detail": "Markdown content should be available for downstream processing.",
            },
            {
                "name": "heading_structure",
                "passed": len(headings) >= 3,
                "detail": f"Detected {len(headings)} headings.",
            },
            {
                "name": "table_signals",
                "passed": len(tables) >= 1,
                "detail": f"Detected {len(tables)} table-like blocks.",
            },
            {
                "name": "financial_numeric_signals",
                "passed": len(numeric_mentions) >= 3,
                "detail": f"Detected {len(numeric_mentions)} lines with financial numeric signals.",
            },
        ]
        score = round(sum(1 for item in checks if item["passed"]) / len(checks), 3)
        return {
            "score": score,
            "checks": checks,
            "review_suggestions": self._suggestions(checks),
        }

    def _suggestions(self, checks: list[dict[str, Any]]) -> list[str]:
        suggestions = []
        failed = {item["name"] for item in checks if not item["passed"]}
        if "heading_structure" in failed:
            suggestions.append("Run MinerU with a wider page range or inspect whether headings were flattened.")
        if "table_signals" in failed:
            suggestions.append("Enable table recognition or choose pages containing financial statements.")
        if "financial_numeric_signals" in failed:
            suggestions.append("Choose report pages with financial data or enable OCR for scanned pages.")
        return suggestions
