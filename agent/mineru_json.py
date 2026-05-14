from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MinerUJsonDocument:
    markdown: str
    layout_blocks: list[dict[str, Any]]
    figures: list[dict[str, Any]]
    paragraphs: list[dict[str, Any]]
    raw: dict[str, Any]


class MinerUJsonParser:
    def parse_path(self, path: Path) -> MinerUJsonDocument:
        return self.parse(json.loads(path.read_text(encoding="utf-8")))

    def parse(self, payload: dict[str, Any]) -> MinerUJsonDocument:
        raw_blocks = self._find_blocks(payload)
        lines: list[str] = []
        layout_blocks: list[dict[str, Any]] = []
        figures: list[dict[str, Any]] = []
        paragraphs: list[dict[str, Any]] = []
        for index, block in enumerate(raw_blocks, start=1):
            markdown = self._block_to_markdown(block)
            if not markdown:
                continue
            start_line = len(lines) + 1
            lines.extend(markdown.splitlines())
            end_line = len(lines)
            normalized = self._normalize_block(block, index, start_line, end_line)
            layout_blocks.append(normalized)
            if normalized["type"] in {"image", "figure"}:
                figures.append(normalized)
            if normalized["type"] in {"text", "paragraph", "title"}:
                paragraphs.append(normalized)
            lines.append("")
        return MinerUJsonDocument(
            markdown="\n".join(lines).strip() + "\n",
            layout_blocks=layout_blocks,
            figures=figures,
            paragraphs=paragraphs,
            raw=payload,
        )

    def _find_blocks(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return []
        for key in ("content_list", "blocks", "layout_blocks", "pdf_info"):
            value = payload.get(key)
            if isinstance(value, list):
                if key == "pdf_info":
                    return self._blocks_from_pages(value)
                return [item for item in value if isinstance(item, dict)]
        data = payload.get("data")
        if isinstance(data, dict):
            return self._find_blocks(data)
        return []

    def _blocks_from_pages(self, pages: list[Any]) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        for page_index, page in enumerate(pages):
            if not isinstance(page, dict):
                continue
            page_blocks = page.get("para_blocks") or page.get("blocks") or page.get("content_list") or []
            for block in page_blocks:
                if isinstance(block, dict):
                    copied = dict(block)
                    copied.setdefault("page_idx", page.get("page_idx", page_index))
                    blocks.append(copied)
        return blocks

    def _block_to_markdown(self, block: dict[str, Any]) -> str:
        block_type = str(block.get("type") or block.get("block_type") or "").lower()
        text = self._text(block)
        if block_type in {"title", "heading"} or block.get("text_level") is not None:
            level = int(block.get("text_level") or block.get("level") or 1)
            level = min(max(level, 1), 6)
            return f"{'#' * level} {text}" if text else ""
        if block_type in {"table", "table_body"}:
            return block.get("table_body") or block.get("html") or block.get("md") or text
        if block_type in {"image", "figure"}:
            caption = block.get("caption") or block.get("img_caption") or text or "figure"
            return f"![{caption}]({block.get('img_path') or block.get('path') or ''})"
        return text

    def _text(self, block: dict[str, Any]) -> str:
        for key in ("text", "content", "markdown", "md"):
            value = block.get(key)
            if isinstance(value, str):
                return value.strip()
        lines = block.get("lines")
        if isinstance(lines, list):
            parts = []
            for line in lines:
                if isinstance(line, dict):
                    parts.append(str(line.get("text", "")))
                elif isinstance(line, str):
                    parts.append(line)
            return "\n".join(part for part in parts if part).strip()
        spans = block.get("spans")
        if isinstance(spans, list):
            return "".join(str(span.get("text", "")) for span in spans if isinstance(span, dict)).strip()
        return ""

    def _normalize_block(self, block: dict[str, Any], index: int, start_line: int, end_line: int) -> dict[str, Any]:
        block_type = str(block.get("type") or block.get("block_type") or "text").lower()
        page = block.get("page_idx", block.get("page", block.get("page_no")))
        return {
            "block_id": str(block.get("id") or block.get("block_id") or f"block_{index:04d}"),
            "type": self._normalize_type(block_type),
            "page": page + 1 if isinstance(page, int) and page == 0 else page,
            "bbox": block.get("bbox") or block.get("poly") or block.get("position"),
            "line_start": start_line,
            "line_end": end_line,
            "confidence": block.get("score") or block.get("confidence"),
            "text": self._text(block)[:500],
        }

    def _normalize_type(self, block_type: str) -> str:
        if block_type in {"title", "heading"}:
            return "title"
        if block_type in {"table", "table_body"}:
            return "table"
        if block_type in {"image", "figure"}:
            return "figure"
        return "paragraph" if block_type in {"text", "para", "paragraph"} else block_type or "text"
