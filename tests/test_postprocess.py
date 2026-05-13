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


if __name__ == "__main__":
    unittest.main()

