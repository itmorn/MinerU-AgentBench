from __future__ import annotations

import unittest
from pathlib import Path

from agent.mineru_json import MinerUJsonParser
from agent.postprocess import MarkdownPostProcessor


class MinerUJsonParserTest(unittest.TestCase):
    def test_content_list_to_structured_with_source_blocks(self) -> None:
        parsed = MinerUJsonParser().parse_path(Path("samples/mock/mineru_content_list.json"))
        result = MarkdownPostProcessor().process(
            parsed.markdown,
            source_name="mineru_content_list.json",
            layout_blocks=parsed.layout_blocks,
            figures=parsed.figures,
            paragraphs=parsed.paragraphs,
        )
        table = result.structured["tables"][0]

        self.assertGreaterEqual(len(result.structured["layout_blocks"]), 3)
        self.assertEqual(len(result.structured["figures"]), 1)
        self.assertEqual(table["source_blocks"][0]["block_id"], "table_1")
        self.assertEqual(table["fields"][0]["field_type"], "metric")
        self.assertTrue(any(field["normalized_name"] == "current" for field in table["fields"]))


if __name__ == "__main__":
    unittest.main()
