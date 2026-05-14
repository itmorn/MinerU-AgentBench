from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RecoveryDecision:
    diagnosis: list[str]
    action: str
    parse_options: dict[str, Any]


class QualityValidator:
    def diagnose(self, quality: dict[str, Any]) -> list[str]:
        failed = [item["name"] for item in quality.get("checks", []) if not item.get("passed")]
        diagnosis = []
        if "non_empty_markdown" in failed:
            diagnosis.append("text_too_short")
        if "table_signals" in failed or "structured_table_records" in failed:
            diagnosis.append("table_count_too_low")
        if "financial_metric_extraction" in failed:
            diagnosis.append("financial_metrics_missing")
        if "schema_valid" in failed:
            diagnosis.append("schema_invalid")
        return diagnosis or ["quality_score_below_threshold"]

    def decide_recovery(self, diagnosis: list[str], *, page_range: str) -> RecoveryDecision:
        action = self.retry_action(diagnosis)
        parse_options: dict[str, Any] = {"enable_table": True, "enable_formula": True}
        if action == "retry_with_ocr":
            parse_options["is_ocr"] = True
        if action == "retry_with_table_enhancement":
            parse_options["enable_table"] = True
        if action == "expand_page_range_or_retry_field_extraction":
            parse_options["page_range"] = self.expand_page_range(page_range)
        return RecoveryDecision(diagnosis=diagnosis, action=action, parse_options=parse_options)

    def retry_action(self, diagnosis: list[str]) -> str:
        if "text_too_short" in diagnosis:
            return "retry_with_ocr"
        if "table_count_too_low" in diagnosis:
            return "retry_with_table_enhancement"
        if "financial_metrics_missing" in diagnosis:
            return "expand_page_range_or_retry_field_extraction"
        if "schema_invalid" in diagnosis:
            return "repair_json_schema"
        return "diagnose_and_replan"

    def expand_page_range(self, page_range: str) -> str:
        if not page_range or "-" not in page_range:
            return page_range
        try:
            start, end = [int(part.strip()) for part in page_range.split("-", 1)]
        except ValueError:
            return page_range
        width = max(end - start + 1, 1)
        return f"{start}-{end + width}"
