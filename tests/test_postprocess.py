from __future__ import annotations

import unittest

from agent.postprocess import MarkdownPostProcessor


class MarkdownPostProcessorTest(unittest.TestCase):
    def test_html_table_records_and_financial_metrics(self) -> None:
        markdown = """# 一、主营业务分析

单位：元
<table><tr><td>科目</td><td>本期数</td><td>上年同期数</td><td>变动比例(%)</td></tr><tr><td>营业收入</td><td>20,954,284,895.33</td><td>18,056,403,834.00</td><td>16.05</td></tr><tr><td>营业成本</td><td>17,355,286,061.32</td><td>15,043,307,023.27</td><td>15.37</td></tr></table>

报告期内，公司实现营业收入 209.54 亿元，同比增长 16.05%。
"""
        result = MarkdownPostProcessor().process(markdown, source_name="unit.md")
        table = result.structured["tables"][0]

        self.assertEqual(table["headers"], ["科目", "本期数", "上年同期数", "变动比例(%)"])
        self.assertEqual(table["records"][0]["科目"], "营业收入")
        self.assertGreaterEqual(result.structured["document_stats"]["financial_metric_count"], 2)
        self.assertGreaterEqual(len(result.structured["consistency_checks"]), 2)
        self.assertTrue(any(check["name"] == "structured_table_records" for check in result.quality["checks"]))
        self.assertEqual(result.structured["document_meta"]["document_type"], "financial_report")
        self.assertIn("sections", result.structured)

    def test_unit_normalization_growth_check_and_schema(self) -> None:
        markdown = """# 一、主要会计数据

单位：万元
| 项目 | 本期金额 | 上年同期金额 | 同比变动 |
| --- | ---: | ---: | ---: |
| 营业收入 | 20,954.28 | 18,056.40 | 16.05% |
"""
        result = MarkdownPostProcessor().process(markdown, source_name="annual_report.md")
        metric = result.structured["financial_metrics"][0]
        current = metric["normalized_values"]["本期金额"]
        growth = result.structured["consistency_checks"][0]["growth_check"]

        self.assertEqual(current["unit"], "元")
        self.assertAlmostEqual(current["normalized_value"], 209542800.0)
        self.assertEqual(growth["status"], "pass")
        self.assertTrue(any(check["name"] == "schema_valid" and check["passed"] for check in result.quality["checks"]))

    def test_cross_page_like_table_merge(self) -> None:
        markdown = """# 一、财务报表附注

单位：元
| 项目 | 本期金额 | 上期金额 |
| --- | ---: | ---: |
| 营业收入 | 100 | 80 |

续表
| 项目 | 本期金额 | 上期金额 |
| --- | ---: | ---: |
| 营业成本 | 70 | 60 |
"""
        result = MarkdownPostProcessor().process(markdown, source_name="annual_report.md")
        merged = result.structured["merged_tables"][0]

        self.assertEqual(merged["source_tables"], ["table_001", "table_002"])
        self.assertEqual(len(merged["records"]), 2)


if __name__ == "__main__":
    unittest.main()
