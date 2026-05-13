from __future__ import annotations

from html.parser import HTMLParser
import re
from dataclasses import dataclass
from typing import Any


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
NUMBER_RE = re.compile(r"(?<![A-Za-z])[-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?%?|[-+]?\d+(?:\.\d+)?%?")
MONEY_UNIT_RE = re.compile(r"(元|万元|亿元|人民币|%|百分点)")
CHAPTER_RE = re.compile(r"^([一二三四五六七八九十]+、|\(?[一二三四五六七八九十]+\)|\d+[.、])")
FINANCIAL_TERMS = ("营业收入", "营业成本", "净利润", "研发费用", "销售费用", "管理费用", "财务费用", "现金流量")


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
        financial_metrics = self._extract_financial_metrics(tables, numeric_mentions)
        consistency_checks = self._consistency_checks(financial_metrics)
        quality = self._quality_report(markdown, headings, tables, numeric_mentions, financial_metrics, consistency_checks)
        structured = {
            "source_name": source_name,
            "document_stats": {
                "line_count": len(lines),
                "char_count": len(markdown),
                "heading_count": len(headings),
                "table_count": len(tables),
                "numeric_mention_count": len(numeric_mentions),
                "financial_metric_count": len(financial_metrics),
            },
            "headings": headings,
            "tables": tables,
            "financial_metrics": financial_metrics[:200],
            "consistency_checks": consistency_checks,
            "numeric_mentions": numeric_mentions[:200],
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
                        "level": self._normalize_heading_level(match.group(2), len(match.group(1))),
                        "title": match.group(2).strip(),
                    }
                )
        return headings

    def _normalize_heading_level(self, title: str, markdown_level: int) -> int:
        title = title.strip()
        if re.match(r"^[一二三四五六七八九十]+、", title):
            return 1
        if re.match(r"^\([一二三四五六七八九十]+\)", title):
            return 2
        if re.match(r"^\d+[.、]", title):
            return 3
        if CHAPTER_RE.match(title):
            return min(markdown_level, 3)
        return markdown_level

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
        rows = self._parse_table_rows(text)
        headers = rows[0] if rows else []
        body_rows = rows[1:] if len(rows) > 1 else []
        tables.append(
            {
                "table_id": f"table_{len(tables) + 1:03d}",
                "start_line": block[0][0],
                "end_line": block[-1][0],
                "row_count": html_row_count if html_row_count else len(block),
                "column_count": max((len(row) for row in rows), default=0),
                "numeric_cell_count": len(NUMBER_RE.findall(text)),
                "headers": headers,
                "records": self._rows_to_records(headers, body_rows)[:50],
                "preview": [line for _, line in block[:5]],
            }
        )

    def _parse_table_rows(self, text: str) -> list[list[str]]:
        if "<table" in text.lower():
            parser = _HTMLTableParser()
            parser.feed(text)
            return parser.rows
        rows = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or set(stripped.replace("|", "").strip()) <= {"-", ":"}:
                continue
            if stripped.startswith("|") and stripped.endswith("|"):
                stripped = stripped[1:-1]
            cells = [cell.strip() for cell in stripped.split("|")]
            if len(cells) >= 2:
                rows.append(cells)
        return rows

    def _rows_to_records(self, headers: list[str], rows: list[list[str]]) -> list[dict[str, str]]:
        if not headers:
            return []
        records = []
        for row in rows:
            record: dict[str, str] = {}
            for index, value in enumerate(row):
                key = headers[index] if index < len(headers) and headers[index] else f"col_{index + 1}"
                record[key] = value
            records.append(record)
        return records

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

    def _extract_financial_metrics(
        self,
        tables: list[dict[str, Any]],
        numeric_mentions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        metrics: list[dict[str, Any]] = []
        for table in tables:
            headers = table.get("headers", [])
            records = table.get("records", [])
            for record in records:
                metric_name = self._metric_name(record)
                if not metric_name:
                    continue
                values = {
                    key: self._parse_number(value)
                    for key, value in record.items()
                    if key != metric_name and self._parse_number(value) is not None
                }
                if values:
                    metrics.append(
                        {
                            "source": table["table_id"],
                            "metric": record[metric_name],
                            "headers": headers,
                            "values": values,
                        }
                    )
        for mention in numeric_mentions:
            text = mention["text"]
            if any(term in text for term in FINANCIAL_TERMS):
                metrics.append(
                    {
                        "source": f"line_{mention['line']}",
                        "metric": self._matched_term(text),
                        "values": {"raw_numbers": mention["numbers"][:8]},
                        "text": text,
                    }
                )
        return metrics

    def _metric_name(self, record: dict[str, str]) -> str | None:
        for key, value in record.items():
            if key in ("科目", "项目", "指标", "分产品", "分行业") or any(term in value for term in FINANCIAL_TERMS):
                return key
        return None

    def _matched_term(self, text: str) -> str:
        for term in FINANCIAL_TERMS:
            if term in text:
                return term
        return "financial_metric"

    def _parse_number(self, value: str) -> float | None:
        match = NUMBER_RE.search(value.replace(",", ""))
        if not match:
            return None
        raw = match.group(0).replace(",", "").replace("%", "")
        try:
            return float(raw)
        except ValueError:
            return None

    def _consistency_checks(self, metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
        checks = []
        for metric in metrics:
            values = metric.get("values", {})
            if not isinstance(values, dict):
                continue
            numeric_values = [value for value in values.values() if isinstance(value, (int, float))]
            if not numeric_values:
                continue
            checks.append(
                {
                    "metric": metric["metric"],
                    "source": metric["source"],
                    "numeric_fields": len(numeric_values),
                    "has_negative": any(value < 0 for value in numeric_values),
                    "has_zero": any(value == 0 for value in numeric_values),
                    "status": "review" if any(abs(value) > 1_000_000_000_000 for value in numeric_values) else "ok",
                }
            )
        return checks[:200]

    def _quality_report(
        self,
        markdown: str,
        headings: list[dict[str, Any]],
        tables: list[dict[str, Any]],
        numeric_mentions: list[dict[str, Any]],
        financial_metrics: list[dict[str, Any]],
        consistency_checks: list[dict[str, Any]],
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
            {
                "name": "structured_table_records",
                "passed": any(table.get("records") for table in tables),
                "detail": f"Structured records extracted from {sum(1 for table in tables if table.get('records'))} tables.",
            },
            {
                "name": "financial_metric_extraction",
                "passed": len(financial_metrics) >= 3,
                "detail": f"Detected {len(financial_metrics)} financial metrics.",
            },
            {
                "name": "metric_consistency_checks",
                "passed": len(consistency_checks) >= 3,
                "detail": f"Generated {len(consistency_checks)} metric-level checks.",
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
        if "structured_table_records" in failed:
            suggestions.append("Inspect MinerU table output format and add a parser for that table style.")
        if "financial_metric_extraction" in failed:
            suggestions.append("Select pages containing financial statements or extend the financial term dictionary.")
        return suggestions


class _HTMLTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._current_row = []
        elif tag in {"td", "th"}:
            self._current_cell = []

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._current_row is not None and self._current_cell is not None:
            self._current_row.append("".join(self._current_cell).strip())
            self._current_cell = None
        elif tag == "tr" and self._current_row is not None:
            if any(cell for cell in self._current_row):
                self.rows.append(self._current_row)
            self._current_row = None
