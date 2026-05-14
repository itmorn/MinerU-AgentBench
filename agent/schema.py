from __future__ import annotations

from typing import Any


REQUIRED_STRUCTURED_KEYS = {
    "schema_version",
    "document_meta",
    "document_stats",
    "layout_blocks",
    "paragraphs",
    "figures",
    "sections",
    "tables",
    "merged_tables",
    "financial_metrics",
    "quality_report",
    "warnings",
}


def validate_structured_schema(structured: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    missing = sorted(REQUIRED_STRUCTURED_KEYS - set(structured))
    if missing:
        issues.append({"path": "$", "message": f"missing required keys: {', '.join(missing)}"})

    type_expectations = {
        "document_meta": dict,
        "document_stats": dict,
        "layout_blocks": list,
        "paragraphs": list,
        "figures": list,
        "sections": list,
        "tables": list,
        "merged_tables": list,
        "financial_metrics": list,
        "quality_report": dict,
        "warnings": list,
    }
    for key, expected in type_expectations.items():
        if key in structured and not isinstance(structured[key], expected):
            issues.append({"path": key, "message": f"expected {expected.__name__}"})

    for index, table in enumerate(structured.get("tables", [])):
        if not isinstance(table, dict):
            issues.append({"path": f"tables[{index}]", "message": "expected object"})
            continue
        for key in ("table_id", "headers", "records", "row_count", "column_count", "fields"):
            if key not in table:
                issues.append({"path": f"tables[{index}]", "message": f"missing {key}"})
        if "records" in table and not isinstance(table["records"], list):
            issues.append({"path": f"tables[{index}].records", "message": "expected array"})
        if "fields" in table and not isinstance(table["fields"], list):
            issues.append({"path": f"tables[{index}].fields", "message": "expected array"})

    for index, metric in enumerate(structured.get("financial_metrics", [])):
        if not isinstance(metric, dict):
            issues.append({"path": f"financial_metrics[{index}]", "message": "expected object"})
            continue
        for key in ("metric", "source"):
            if key not in metric:
                issues.append({"path": f"financial_metrics[{index}]", "message": f"missing {key}"})

    return issues
