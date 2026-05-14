from __future__ import annotations

from difflib import SequenceMatcher
from html.parser import HTMLParser
import re
from dataclasses import dataclass
from typing import Any

from agent.schema import validate_structured_schema


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
NUMBER_RE = re.compile(r"(?<![A-Za-z])[-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?%?|[-+]?\d+(?:\.\d+)?%?")
MONEY_UNIT_RE = re.compile(r"(人民币元|人民币|千元|万元|亿元|元|%|百分点)")
CHAPTER_RE = re.compile(r"^([一二三四五六七八九十]+、|\(?[一二三四五六七八九十]+\)|\d+[.、])")
PAGE_RE = re.compile(r"(?:第\s*)?(\d{1,5})\s*(?:页|/)")
FINANCIAL_TERMS = (
    "营业收入",
    "营业成本",
    "净利润",
    "归母净利润",
    "归属于上市公司股东的净利润",
    "经营活动现金流",
    "经营活动产生的现金流量净额",
    "资产总额",
    "负债总额",
    "研发费用",
    "销售费用",
    "管理费用",
    "财务费用",
    "毛利率",
    "净利率",
    "现金流量",
)
UNIT_MULTIPLIERS = {
    "元": 1.0,
    "人民币": 1.0,
    "人民币元": 1.0,
    "千元": 1_000.0,
    "万元": 10_000.0,
    "亿元": 100_000_000.0,
}
CURRENT_HEADER_RE = re.compile(r"(本期|本年|本报告期|本期金额|期末|本期数|202\d)")
PREVIOUS_HEADER_RE = re.compile(r"(上期|上年|上年同期|上期金额|期初|上期数|202\d)")
GROWTH_HEADER_RE = re.compile(r"(同比|变动|增长|增减|比例|率|%)")
TABLE_END_TERMS = ("合计", "总计", "小计")


@dataclass(frozen=True)
class PostProcessResult:
    structured: dict[str, Any]
    quality: dict[str, Any]


class MarkdownPostProcessor:
    def process(
        self,
        markdown: str,
        *,
        source_name: str,
        layout_blocks: list[dict[str, Any]] | None = None,
        figures: list[dict[str, Any]] | None = None,
        paragraphs: list[dict[str, Any]] | None = None,
    ) -> PostProcessResult:
        layout_blocks = layout_blocks or []
        figures = figures or []
        paragraphs = paragraphs or []
        lines = markdown.splitlines()
        headings = self._extract_headings(lines)
        self._attach_source_blocks(headings, layout_blocks)
        sections = self._build_sections(headings, line_count=len(lines))
        tables = self._extract_table_blocks(lines, headings)
        self._attach_source_blocks(tables, layout_blocks)
        self._enrich_table_fields(tables)
        self._attach_tables_to_sections(sections, tables)
        merged_tables = self._merge_cross_page_tables(tables)
        numeric_mentions = self._extract_numeric_mentions(lines)
        financial_metrics = self._extract_financial_metrics(merged_tables or tables, numeric_mentions)
        consistency_checks = self._consistency_checks(financial_metrics)
        warnings = self._warnings(markdown, headings, tables, financial_metrics, consistency_checks)
        document_meta = {
            "source_name": source_name,
            "document_type": self._infer_document_type(source_name, markdown),
            "language": "zh" if re.search(r"[\u4e00-\u9fff]", markdown) else "unknown",
        }
        structured = {
            "document_id": self._document_id(source_name),
            "document_meta": document_meta,
            "schema_version": "1.1.0",
            "source_name": source_name,
            "document_stats": {
                "line_count": len(lines),
                "char_count": len(markdown),
                "heading_count": len(headings),
                "section_count": len(sections),
                "table_count": len(tables),
                "merged_table_count": len(merged_tables),
                "numeric_mention_count": len(numeric_mentions),
                "financial_metric_count": len(financial_metrics),
                "layout_block_count": len(layout_blocks),
                "figure_count": len(figures),
                "paragraph_count": len(paragraphs),
            },
            "layout_blocks": layout_blocks[:1000],
            "paragraphs": paragraphs[:1000],
            "figures": figures[:500],
            "headings": headings,
            "sections": sections,
            "tables": tables,
            "merged_tables": merged_tables,
            "financial_metrics": financial_metrics[:500],
            "consistency_checks": consistency_checks,
            "numeric_mentions": numeric_mentions[:200],
            "warnings": warnings,
            "quality_report": {},
        }
        schema_issues = validate_structured_schema(structured)
        quality = self._quality_report(
            markdown,
            headings,
            tables,
            numeric_mentions,
            financial_metrics,
            consistency_checks,
            schema_issues,
            warnings,
        )
        structured["quality_report"] = quality
        schema_issues = validate_structured_schema(structured)
        if schema_issues:
            quality["schema_issues"] = schema_issues
        return PostProcessResult(structured=structured, quality=quality)

    def _attach_source_blocks(self, items: list[dict[str, Any]], layout_blocks: list[dict[str, Any]]) -> None:
        for item in items:
            start = item.get("start_line") or item.get("line")
            end = item.get("end_line") or item.get("line")
            matches = [
                block
                for block in layout_blocks
                if self._line_ranges_overlap(start, end, block.get("line_start"), block.get("line_end"))
            ]
            if matches:
                item["source_blocks"] = [
                    {
                        "block_id": block.get("block_id"),
                        "type": block.get("type"),
                        "page": block.get("page"),
                        "bbox": block.get("bbox"),
                        "confidence": block.get("confidence"),
                    }
                    for block in matches[:5]
                ]

    def _line_ranges_overlap(self, left_start: int | None, left_end: int | None, right_start: int | None, right_end: int | None) -> bool:
        if left_start is None or left_end is None or right_start is None or right_end is None:
            return False
        return max(left_start, right_start) <= min(left_end, right_end)

    def _extract_headings(self, lines: list[str]) -> list[dict[str, Any]]:
        headings: list[dict[str, Any]] = []
        for index, line in enumerate(lines, start=1):
            match = HEADING_RE.match(line)
            if match:
                headings.append(
                    {
                        "line": index,
                        "level": self._normalize_heading_level(match.group(2), len(match.group(1))),
                        "title": self._clean_cell(match.group(2)),
                        "page": self._nearest_page(lines, index),
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

    def _build_sections(self, headings: list[dict[str, Any]], *, line_count: int) -> list[dict[str, Any]]:
        roots: list[dict[str, Any]] = []
        stack: list[dict[str, Any]] = []
        for index, heading in enumerate(headings):
            next_line = headings[index + 1]["line"] - 1 if index + 1 < len(headings) else line_count
            node = {
                "title": heading["title"],
                "level": heading["level"],
                "line_start": heading["line"],
                "line_end": next_line,
                "page_start": heading.get("page"),
                "page_end": None,
                "children": [],
                "tables": [],
            }
            while stack and stack[-1]["level"] >= node["level"]:
                finished = stack.pop()
                finished["page_end"] = heading.get("page") or finished.get("page_start")
            if stack:
                stack[-1]["children"].append(node)
            else:
                roots.append(node)
            stack.append(node)
        for node in stack:
            node["page_end"] = node.get("page_start")
        return roots

    def _attach_tables_to_sections(self, sections: list[dict[str, Any]], tables: list[dict[str, Any]]) -> None:
        for table in tables:
            node = self._deepest_section_for_line(sections, table["start_line"])
            if node is not None:
                node["tables"].append(table["table_id"])

    def _deepest_section_for_line(self, sections: list[dict[str, Any]], line: int) -> dict[str, Any] | None:
        match = None
        for section in sections:
            if section["line_start"] <= line <= section["line_end"]:
                child_match = self._deepest_section_for_line(section["children"], line)
                match = child_match or section
        return match

    def _extract_table_blocks(self, lines: list[str], headings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        tables: list[dict[str, Any]] = []
        current: list[tuple[int, str]] = []
        for index, line in enumerate(lines, start=1):
            if self._looks_like_table_line(line):
                current.append((index, line))
                continue
            if current:
                self._append_table(tables, current, lines, headings)
                current = []
        if current:
            self._append_table(tables, current, lines, headings)
        return tables

    def _append_table(
        self,
        tables: list[dict[str, Any]],
        block: list[tuple[int, str]],
        lines: list[str],
        headings: list[dict[str, Any]],
    ) -> None:
        text = "\n".join(line for _, line in block)
        html_row_count = text.lower().count("<tr")
        rows = self._parse_table_rows(text)
        rows = self._repair_rows(rows)
        headers = rows[0] if rows else []
        body_rows = rows[1:] if len(rows) > 1 else []
        section = self._section_for_line(headings, block[0][0])
        context_unit = self._context_unit(lines, block[0][0])
        table_id = f"table_{len(tables) + 1:03d}"
        tables.append(
            {
                "table_id": table_id,
                "logical_table_id": table_id,
                "section": section["title"] if section else None,
                "section_level": section["level"] if section else None,
                "start_line": block[0][0],
                "end_line": block[-1][0],
                "page_start": self._nearest_page(lines, block[0][0]),
                "page_end": self._nearest_page(lines, block[-1][0]),
                "row_count": html_row_count if html_row_count else len(rows),
                "column_count": max((len(row) for row in rows), default=0),
                "numeric_cell_count": len(NUMBER_RE.findall(text)),
                "context_unit": context_unit,
                "headers": headers,
                "fields": [self._field_schema(header, context_unit) for header in headers],
                "records": self._rows_to_records(headers, body_rows)[:500],
                "preview": [line for _, line in block[:5]],
            }
        )

    def _enrich_table_fields(self, tables: list[dict[str, Any]]) -> None:
        for table in tables:
            context_unit = table.get("context_unit")
            table["fields"] = [self._field_schema(header, context_unit) for header in table.get("headers", [])]

    def _field_schema(self, header: str, context_unit: str | None = None) -> dict[str, Any]:
        field_type = self._field_type(header, context_unit)
        return {
            "name": header,
            "normalized_name": self._normalize_header(header),
            "field_type": field_type,
            "unit": self._field_unit(header, context_unit, field_type),
            "confidence": 0.8,
        }

    def _field_type(self, header: str, context_unit: str | None = None) -> str:
        text = f"{header}{context_unit or ''}"
        if any(term in header for term in ("项目", "科目", "指标", "名称", "分行业", "分产品")):
            return "metric"
        if any(term in text for term in ("日期", "年度", "期间", "时间")):
            return "date"
        if "%" in text or any(term in text for term in ("比例", "率", "同比", "变动", "增减")):
            return "ratio"
        if any(unit in text for unit in UNIT_MULTIPLIERS):
            return "money"
        if any(term in text for term in ("金额", "本期", "上期", "本年", "上年", "期末", "期初")):
            return "number"
        return "text"

    def _field_unit(self, header: str, context_unit: str | None, field_type: str) -> str | None:
        if field_type == "ratio":
            return "ratio"
        unit = self._unit_from_text(header) or context_unit
        if field_type in {"money", "number"} and unit:
            return "元" if unit in UNIT_MULTIPLIERS else unit
        return None

    def _normalize_header(self, header: str) -> str:
        normalized = self._clean_cell(header)
        mapping = {
            "科目": "metric",
            "项目": "metric",
            "指标": "metric",
            "本期数": "current",
            "本期金额": "current",
            "上期数": "previous",
            "上年同期数": "previous",
            "上年同期金额": "previous",
            "同比变动": "growth_rate",
            "变动比例": "growth_rate",
        }
        return mapping.get(normalized, normalized)

    def _parse_table_rows(self, text: str) -> list[list[str]]:
        if "<table" in text.lower():
            parser = _HTMLTableParser()
            parser.feed(text)
            return parser.rows
        rows = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or set(stripped.replace("|", "").strip()) <= {"-", ":", " "}:
                continue
            if stripped.startswith("|") and stripped.endswith("|"):
                stripped = stripped[1:-1]
            cells = [self._clean_cell(cell) for cell in stripped.split("|")]
            if len(cells) >= 2:
                rows.append(cells)
        return rows

    def _repair_rows(self, rows: list[list[str]]) -> list[list[str]]:
        if not rows:
            return rows
        width = max(len(row) for row in rows)
        repaired = []
        for row in rows:
            if len(row) < width:
                row = row + [""] * (width - len(row))
            repaired.append([self._clean_cell(cell) for cell in row[:width]])
        return repaired

    def _rows_to_records(self, headers: list[str], rows: list[list[str]]) -> list[dict[str, str]]:
        if not headers:
            return []
        normalized_headers = self._dedupe_headers(headers)
        records = []
        for row in rows:
            record: dict[str, str] = {}
            for index, value in enumerate(row):
                key = normalized_headers[index] if index < len(normalized_headers) and normalized_headers[index] else f"col_{index + 1}"
                record[key] = self._clean_cell(value)
            if any(record.values()):
                records.append(record)
        return records

    def _dedupe_headers(self, headers: list[str]) -> list[str]:
        seen: dict[str, int] = {}
        result = []
        for index, header in enumerate(headers, start=1):
            key = self._clean_cell(header) or f"col_{index}"
            seen[key] = seen.get(key, 0) + 1
            result.append(key if seen[key] == 1 else f"{key}_{seen[key]}")
        return result

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

    def _merge_cross_page_tables(self, tables: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        for table in tables:
            if not merged or not self._should_merge(merged[-1], table):
                logical = dict(table)
                logical["merged_table_id"] = f"merged_table_{len(merged) + 1:03d}"
                logical["source_tables"] = [table["table_id"]]
                logical["merge_reason"] = "single_table"
                logical["records"] = list(table.get("records", []))
                merged.append(logical)
                continue
            target = merged[-1]
            target["source_tables"].append(table["table_id"])
            target["end_line"] = table["end_line"]
            target["page_end"] = table.get("page_end")
            target["row_count"] += table.get("row_count", 0)
            target["numeric_cell_count"] += table.get("numeric_cell_count", 0)
            target["records"].extend(table.get("records", []))
            target["merge_reason"] = "same_headers_and_adjacent_content"
            table["logical_table_id"] = target["merged_table_id"]
        return merged

    def _should_merge(self, previous: dict[str, Any], current: dict[str, Any]) -> bool:
        if previous.get("section") != current.get("section"):
            return False
        if current["start_line"] - previous["end_line"] > 12:
            return False
        previous_headers = previous.get("headers", [])
        current_headers = current.get("headers", [])
        if not previous_headers or not current_headers:
            return False
        if previous.get("records"):
            last_metric = next(iter(previous["records"][-1].values()), "")
            if any(term in last_metric for term in TABLE_END_TERMS):
                return False
        similarity = SequenceMatcher(None, "|".join(previous_headers), "|".join(current_headers)).ratio()
        return similarity >= 0.82 or (len(previous_headers) == len(current_headers) and similarity >= 0.65)

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
                metric_key = self._metric_name(record)
                if not metric_key:
                    continue
                values: dict[str, float] = {}
                normalized_values: dict[str, dict[str, Any]] = {}
                for key, value in record.items():
                    if key == metric_key:
                        continue
                    parsed = self._parse_number(value)
                    if parsed is None:
                        continue
                    values[key] = parsed
                    normalized = self._normalize_financial_value(value, table.get("context_unit"))
                    if normalized:
                        normalized_values[key] = normalized
                if values:
                    metrics.append(
                        {
                            "source": table.get("merged_table_id") or table["table_id"],
                            "source_tables": table.get("source_tables", [table["table_id"]]),
                            "section": table.get("section"),
                            "metric": record[metric_key],
                            "headers": headers,
                            "values": values,
                            "normalized_values": normalized_values,
                            "unit_context": table.get("context_unit"),
                        }
                    )
        for mention in numeric_mentions:
            text = mention["text"]
            if any(term in text for term in FINANCIAL_TERMS):
                normalized = [self._normalize_financial_value(number, self._unit_from_text(text)) for number in mention["numbers"][:8]]
                metrics.append(
                    {
                        "source": f"line_{mention['line']}",
                        "metric": self._matched_term(text),
                        "values": {"raw_numbers": mention["numbers"][:8]},
                        "normalized_values": [item for item in normalized if item],
                        "text": text,
                    }
                )
        return metrics

    def _metric_name(self, record: dict[str, str]) -> str | None:
        preferred = ("科目", "项目", "指标", "分产品", "分行业", "名称")
        for key in preferred:
            if key in record:
                return key
        for key, value in record.items():
            if any(term in value for term in FINANCIAL_TERMS):
                return key
        return None

    def _matched_term(self, text: str) -> str:
        for term in FINANCIAL_TERMS:
            if term in text:
                return term
        return "financial_metric"

    def _parse_number(self, value: str) -> float | None:
        match = re.search(r"[-+]?\d+(?:\.\d+)?%?", value.replace(",", ""))
        if not match:
            return None
        raw = match.group(0).replace(",", "").replace("%", "")
        try:
            return float(raw)
        except ValueError:
            return None

    def _normalize_financial_value(self, value: str, context_unit: str | None = None) -> dict[str, Any] | None:
        parsed = self._parse_number(value)
        if parsed is None:
            return None
        raw_unit = self._unit_from_text(value) or context_unit
        if "%" in value or raw_unit == "%":
            return {
                "raw_value": value,
                "raw_number": parsed,
                "raw_unit": "%",
                "normalized_value": parsed / 100,
                "unit": "ratio",
            }
        multiplier = UNIT_MULTIPLIERS.get(raw_unit or "元", 1.0)
        return {
            "raw_value": value,
            "raw_number": parsed,
            "raw_unit": raw_unit or "元",
            "normalized_value": parsed * multiplier,
            "unit": "元",
        }

    def _unit_from_text(self, text: str) -> str | None:
        matches = MONEY_UNIT_RE.findall(text)
        for unit in ("亿元", "万元", "千元", "人民币元", "人民币", "元", "%"):
            if unit in matches:
                return unit
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
            growth_check = self._growth_check(metric)
            checks.append(
                {
                    "metric": metric["metric"],
                    "source": metric["source"],
                    "numeric_fields": len(numeric_values),
                    "has_negative": any(value < 0 for value in numeric_values),
                    "has_zero": any(value == 0 for value in numeric_values),
                    "growth_check": growth_check,
                    "status": self._metric_status(numeric_values, growth_check),
                }
            )
        return checks[:500]

    def _growth_check(self, metric: dict[str, Any]) -> dict[str, Any] | None:
        normalized = metric.get("normalized_values")
        if not isinstance(normalized, dict):
            return None
        current = previous = reported = None
        for key, payload in normalized.items():
            value = payload.get("normalized_value") if isinstance(payload, dict) else None
            if value is None:
                continue
            if GROWTH_HEADER_RE.search(key):
                reported = payload.get("raw_number")
            elif CURRENT_HEADER_RE.search(key):
                current = value
            elif PREVIOUS_HEADER_RE.search(key):
                previous = value
        if current is None or previous in (None, 0) or reported is None:
            return None
        calculated = (current - previous) / previous * 100
        delta = abs(calculated - reported)
        return {
            "current": current,
            "previous": previous,
            "reported_growth_rate": reported,
            "calculated_growth_rate": round(calculated, 4),
            "delta": round(delta, 4),
            "status": "pass" if delta <= 0.2 else "warning",
        }

    def _metric_status(self, numeric_values: list[float], growth_check: dict[str, Any] | None) -> str:
        if any(abs(value) > 1_000_000_000_000_000 for value in numeric_values):
            return "review"
        if growth_check and growth_check["status"] != "pass":
            return "warning"
        return "ok"

    def _quality_report(
        self,
        markdown: str,
        headings: list[dict[str, Any]],
        tables: list[dict[str, Any]],
        numeric_mentions: list[dict[str, Any]],
        financial_metrics: list[dict[str, Any]],
        consistency_checks: list[dict[str, Any]],
        schema_issues: list[dict[str, Any]],
        warnings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        checks = [
            {
                "name": "non_empty_markdown",
                "passed": len(markdown.strip()) > 100,
                "detail": "Markdown content should be available for downstream processing.",
            },
            {
                "name": "heading_structure",
                "passed": len(headings) >= 1,
                "detail": f"Detected {len(headings)} headings.",
            },
            {
                "name": "table_signals",
                "passed": len(tables) >= 1,
                "detail": f"Detected {len(tables)} table-like blocks.",
            },
            {
                "name": "financial_numeric_signals",
                "passed": len(numeric_mentions) >= 1,
                "detail": f"Detected {len(numeric_mentions)} lines with financial numeric signals.",
            },
            {
                "name": "structured_table_records",
                "passed": any(table.get("records") for table in tables),
                "detail": f"Structured records extracted from {sum(1 for table in tables if table.get('records'))} tables.",
            },
            {
                "name": "financial_metric_extraction",
                "passed": len(financial_metrics) >= 1,
                "detail": f"Detected {len(financial_metrics)} financial metrics.",
            },
            {
                "name": "metric_consistency_checks",
                "passed": len(consistency_checks) >= 1,
                "detail": f"Generated {len(consistency_checks)} metric-level checks.",
            },
            {
                "name": "schema_valid",
                "passed": not schema_issues,
                "detail": f"Schema issues: {len(schema_issues)}.",
            },
        ]
        score = round(sum(1 for item in checks if item["passed"]) / len(checks), 3)
        return {
            "score": score,
            "checks": checks,
            "schema_issues": schema_issues,
            "warnings": warnings,
            "review_suggestions": self._suggestions(checks, warnings),
        }

    def _suggestions(self, checks: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> list[str]:
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
        if "schema_valid" in failed:
            suggestions.append("Repair structured output before downstream ingestion.")
        if any(warning.get("warning_type") == "growth_rate_mismatch" for warning in warnings):
            suggestions.append("Review tables with growth-rate mismatches; source rows may be shifted or units may be inconsistent.")
        return suggestions

    def _warnings(
        self,
        markdown: str,
        headings: list[dict[str, Any]],
        tables: list[dict[str, Any]],
        financial_metrics: list[dict[str, Any]],
        consistency_checks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        warnings: list[dict[str, Any]] = []
        if len(markdown.strip()) <= 100:
            warnings.append(
                {
                    "warning_type": "low_text_volume",
                    "message": "parsed text is too short",
                    "suggestion": "retry with OCR or a wider page range",
                }
            )
        if not headings:
            warnings.append(
                {
                    "warning_type": "missing_sections",
                    "message": "no markdown headings were detected",
                    "suggestion": "inspect MinerU output or enable layout-aware parsing",
                }
            )
        for table in tables:
            if table.get("records") and any(len(record) != table.get("column_count") for record in table["records"]):
                warnings.append(
                    {
                        "warning_type": "table_column_mismatch",
                        "message": f"{table['table_id']} may contain merged or missing cells",
                        "suggestion": "manual review recommended",
                    }
                )
        for check in consistency_checks:
            growth = check.get("growth_check")
            if growth and growth.get("status") == "warning":
                warnings.append(
                    {
                        "warning_type": "growth_rate_mismatch",
                        "message": f"{check['metric']} reported growth does not match recalculated value",
                        "suggestion": "review source table row and unit context",
                    }
                )
        if not financial_metrics and any(term in markdown for term in FINANCIAL_TERMS):
            warnings.append(
                {
                    "warning_type": "financial_metric_missing",
                    "message": "financial keywords exist but no structured financial metric was extracted",
                    "suggestion": "extend table parsing or field extraction rules",
                }
            )
        return warnings

    def _section_for_line(self, headings: list[dict[str, Any]], line: int) -> dict[str, Any] | None:
        previous = None
        for heading in headings:
            if heading["line"] <= line:
                previous = heading
            else:
                break
        return previous

    def _context_unit(self, lines: list[str], line: int) -> str | None:
        start = max(0, line - 6)
        context = "\n".join(lines[start:line])
        return self._unit_from_text(context)

    def _nearest_page(self, lines: list[str], line: int) -> int | None:
        start = max(0, line - 4)
        end = min(len(lines), line + 3)
        for text in reversed(lines[start:end]):
            match = PAGE_RE.search(text)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    return None
        return None

    def _infer_document_type(self, source_name: str, markdown: str) -> str:
        text = f"{source_name}\n{markdown[:3000]}"
        if any(term in text for term in ("年度报告", "半年度报告", "季度报告", "招股说明书", "财务报表", "审计报告", *FINANCIAL_TERMS)):
            return "financial_report"
        return "general_document"

    def _document_id(self, source_name: str) -> str:
        cleaned = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", source_name).strip("_")
        return cleaned or "unknown_document"

    def _clean_cell(self, value: str) -> str:
        return re.sub(r"\s+", " ", value.replace("\u3000", " ")).strip()


class _HTMLTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "tr":
            self._current_row = []
        if tag.lower() in {"td", "th"} and self._current_row is not None:
            self._current_cell = []

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"td", "th"} and self._current_row is not None and self._current_cell is not None:
            self._current_row.append(re.sub(r"\s+", " ", "".join(self._current_cell)).strip())
            self._current_cell = None
        if lowered == "tr" and self._current_row is not None:
            if any(cell for cell in self._current_row):
                self.rows.append(self._current_row)
            self._current_row = None
