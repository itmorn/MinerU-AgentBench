from __future__ import annotations

import json
from pathlib import Path


EXAMPLES = [
    {
        "id": "example_01",
        "name": "董事会报告与经营数据解析",
        "path": Path("samples/output/board_report_postprocessed_p1_10"),
    },
    {
        "id": "example_02",
        "name": "PDF 软件公司半年报财务章节解析",
        "path": Path("samples/output/example_02_pdf_software_h1_p30_40"),
    },
    {
        "id": "example_03",
        "name": "七匹狼年报首页与审计信息解析",
        "path": Path("samples/output/example_03_septwolves_annual_p1_20"),
    },
    {
        "id": "example_04",
        "name": "神州信息半年报公司信息与指标表解析",
        "path": Path("samples/output/example_04_dcits_h1_p1_20"),
    },
    {
        "id": "example_05",
        "name": "蓝思科技半年报主营业务与调研表解析",
        "path": Path("samples/output/example_05_lens_h1_p1_20"),
    },
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    rows = []
    for example in EXAMPLES:
        structured = load_json(example["path"] / "structured.json")
        quality = load_json(example["path"] / "quality_report.json")
        stats = structured["document_stats"]
        rows.append(
            {
                "id": example["id"],
                "name": example["name"],
                "output_dir": str(example["path"]),
                "quality_score": quality["score"],
                "heading_count": stats["heading_count"],
                "table_count": stats["table_count"],
                "numeric_mention_count": stats["numeric_mention_count"],
                "char_count": stats["char_count"],
            }
        )

    output_dir = Path("samples/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "examples_summary.json"
    md_path = output_dir / "examples_summary.md"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 典型任务执行示例汇总",
        "",
        "| ID | 任务 | 质量分 | 标题数 | 表格数 | 财务数字线索 | 输出目录 |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {id} | {name} | {quality_score} | {heading_count} | {table_count} | "
            "{numeric_mention_count} | `{output_dir}` |".format(**row)
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(md_path)
    print(json_path)


if __name__ == "__main__":
    main()

