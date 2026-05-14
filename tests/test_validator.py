from __future__ import annotations

import unittest

from agent.validator import QualityValidator


class QualityValidatorTest(unittest.TestCase):
    def test_diagnose_and_expand_page_range(self) -> None:
        quality = {
            "checks": [
                {"name": "non_empty_markdown", "passed": True},
                {"name": "financial_metric_extraction", "passed": False},
            ]
        }
        validator = QualityValidator()
        diagnosis = validator.diagnose(quality)
        decision = validator.decide_recovery(diagnosis, page_range="1-10")

        self.assertEqual(diagnosis, ["financial_metrics_missing"])
        self.assertEqual(decision.action, "expand_page_range_or_retry_field_extraction")
        self.assertEqual(decision.parse_options["page_range"], "1-20")


if __name__ == "__main__":
    unittest.main()
