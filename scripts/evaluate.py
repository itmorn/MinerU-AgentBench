from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.schema import validate_structured_schema


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate structured output against a gold JSON file.")
    parser.add_argument("--gold", required=True, help="Gold structured JSON path.")
    parser.add_argument("--prediction", required=True, help="Predicted structured JSON path.")
    parser.add_argument("--output", help="Optional evaluation report JSON path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    gold = load_json(Path(args.gold))
    prediction = load_json(Path(args.prediction))
    report = evaluate(gold, prediction)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(gold: dict[str, Any], prediction: dict[str, Any]) -> dict[str, Any]:
    gold_tables = gold.get("tables", [])
    predicted_tables = prediction.get("tables", [])
    gold_metrics = metric_names(gold.get("financial_metrics", []))
    predicted_metrics = metric_names(prediction.get("financial_metrics", []))
    schema_issues = validate_structured_schema(prediction)
    numeric_cells = numeric_parse_counts(predicted_tables)
    return {
        "section_structure_accuracy": section_structure_accuracy(gold.get("sections", []), prediction.get("sections", [])),
        "table_detection_precision": precision(len(gold_tables), len(predicted_tables)),
        "table_record_valid_rate": valid_table_record_rate(predicted_tables),
        "financial_metric_hit_rate": hit_rate(gold_metrics, predicted_metrics),
        "numeric_parse_success_rate": ratio(numeric_cells["parsed"], numeric_cells["total"]),
        "unit_normalization_accuracy": unit_normalization_rate(prediction.get("financial_metrics", [])),
        "consistency_check_pass_rate": consistency_pass_rate(prediction.get("consistency_checks", [])),
        "retry_success_rate": retry_success_rate(prediction.get("quality_report", {})),
        "schema_valid_rate": 1.0 if not schema_issues else 0.0,
        "schema_issues": schema_issues,
        "counts": {
            "gold_tables": len(gold_tables),
            "predicted_tables": len(predicted_tables),
            "gold_metrics": len(gold_metrics),
            "predicted_metrics": len(predicted_metrics),
        },
    }


def section_structure_accuracy(gold_sections: list[dict[str, Any]], predicted_sections: list[dict[str, Any]]) -> float:
    gold_titles = section_titles(gold_sections)
    predicted_titles = section_titles(predicted_sections)
    return hit_rate(gold_titles, predicted_titles)


def section_titles(sections: list[dict[str, Any]]) -> set[str]:
    titles: set[str] = set()
    for section in sections:
        title = section.get("title")
        if title:
            titles.add(str(title))
        titles.update(section_titles(section.get("children", [])))
    return titles


def metric_names(metrics: list[dict[str, Any]]) -> set[str]:
    names = set()
    for metric in metrics:
        name = metric.get("metric")
        if name:
            names.add(str(name))
    return names


def precision(expected_count: int, actual_count: int) -> float:
    if actual_count == 0:
        return 1.0 if expected_count == 0 else 0.0
    return round(min(expected_count, actual_count) / actual_count, 4)


def hit_rate(expected: set[str], actual: set[str]) -> float:
    if not expected:
        return 1.0
    return round(len(expected & actual) / len(expected), 4)


def valid_table_record_rate(tables: list[dict[str, Any]]) -> float:
    if not tables:
        return 0.0
    valid = 0
    for table in tables:
        headers = table.get("headers", [])
        records = table.get("records", [])
        if headers and isinstance(records, list) and all(isinstance(record, dict) for record in records):
            valid += 1
    return ratio(valid, len(tables))


def numeric_parse_counts(tables: list[dict[str, Any]]) -> dict[str, int]:
    total = 0
    parsed = 0
    for table in tables:
        total += int(table.get("numeric_cell_count", 0) or 0)
        for record in table.get("records", []):
            for value in record.values():
                if isinstance(value, str) and any(ch.isdigit() for ch in value):
                    parsed += 1
    return {"total": total, "parsed": min(parsed, total) if total else parsed}


def unit_normalization_rate(metrics: list[dict[str, Any]]) -> float:
    if not metrics:
        return 0.0
    normalized = 0
    with_values = 0
    for metric in metrics:
        values = metric.get("normalized_values")
        if values:
            with_values += 1
            normalized += 1
    return ratio(normalized, with_values or len(metrics))


def consistency_pass_rate(checks: list[dict[str, Any]]) -> float:
    if not checks:
        return 0.0
    passed = 0
    for check in checks:
        growth = check.get("growth_check")
        if check.get("status") == "ok" or (growth and growth.get("status") == "pass"):
            passed += 1
    return ratio(passed, len(checks))


def retry_success_rate(quality_report: dict[str, Any]) -> float:
    recovery = quality_report.get("recovery", {})
    if not recovery:
        return 1.0
    return 1.0 if recovery.get("status") == "recovered" else 0.0


def ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return round(numerator / denominator, 4)


if __name__ == "__main__":
    main()
