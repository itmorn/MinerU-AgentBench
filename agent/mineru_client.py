from __future__ import annotations

import os
import time
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import requests


class MinerUError(RuntimeError):
    pass


@dataclass(frozen=True)
class MinerUResult:
    markdown: str
    source: str
    raw: dict[str, Any]


class MinerUClient:
    agent_base_url = "https://mineru.net/api/v1/agent"
    precision_base_url = "https://mineru.net/api/v4"

    def __init__(
        self,
        *,
        token_env: str = "MINERU_TOKEN",
        poll_seconds: float = 3.0,
        timeout_seconds: float = 600.0,
    ) -> None:
        self.token_env = token_env
        self.poll_seconds = poll_seconds
        self.timeout_seconds = timeout_seconds

    def parse_agent_url(
        self,
        url: str,
        *,
        language: str,
        page_range: str,
        enable_table: bool = True,
        enable_formula: bool = True,
        is_ocr: bool = False,
    ) -> MinerUResult:
        response = requests.post(
            f"{self.agent_base_url}/parse/url",
            json={
                "url": url,
                "language": language,
                "page_range": page_range,
                "enable_table": enable_table,
                "enable_formula": enable_formula,
                "is_ocr": is_ocr,
            },
            timeout=30,
        )
        task_id = self._task_id(response)
        raw = self._poll_agent(task_id)
        markdown_url = raw["data"].get("markdown_url")
        if not markdown_url:
            raise MinerUError(f"Agent result did not include markdown_url: {raw}")
        markdown = requests.get(markdown_url, timeout=60).text
        return MinerUResult(markdown=markdown, source=markdown_url, raw=raw)

    def parse_agent_file(
        self,
        file_path: Path,
        *,
        language: str,
        page_range: str,
        enable_table: bool = True,
        enable_formula: bool = True,
        is_ocr: bool = False,
    ) -> MinerUResult:
        response = requests.post(
            f"{self.agent_base_url}/parse/file",
            json={
                "file_name": file_path.name,
                "language": language,
                "page_range": page_range,
                "enable_table": enable_table,
                "enable_formula": enable_formula,
                "is_ocr": is_ocr,
            },
            timeout=30,
        )
        data = self._data(response)
        task_id = data["task_id"]
        upload_url = data["file_url"]
        with file_path.open("rb") as f:
            put_response = requests.put(upload_url, data=f, timeout=120)
        if put_response.status_code >= 400:
            raise MinerUError(f"File upload failed: HTTP {put_response.status_code}")
        raw = self._poll_agent(task_id)
        markdown_url = raw["data"].get("markdown_url")
        if not markdown_url:
            raise MinerUError(f"Agent result did not include markdown_url: {raw}")
        markdown = requests.get(markdown_url, timeout=60).text
        return MinerUResult(markdown=markdown, source=markdown_url, raw=raw)

    def parse_precision_url(
        self,
        url: str,
        *,
        language: str,
        page_range: str,
        model_version: str = "vlm",
        enable_table: bool = True,
        enable_formula: bool = True,
        is_ocr: bool = False,
    ) -> MinerUResult:
        token = os.getenv(self.token_env)
        if not token:
            raise MinerUError(f"Missing {self.token_env}; export your MinerU API token first.")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        response = requests.post(
            f"{self.precision_base_url}/extract/task",
            headers=headers,
            json={
                "url": url,
                "language": language,
                "page_ranges": page_range,
                "model_version": model_version,
                "enable_table": enable_table,
                "enable_formula": enable_formula,
                "is_ocr": is_ocr,
            },
            timeout=30,
        )
        task_id = self._task_id(response)
        raw = self._poll_precision(task_id, headers)
        zip_url = raw["data"].get("full_zip_url")
        if not zip_url:
            raise MinerUError(f"Precision result did not include full_zip_url: {raw}")
        markdown = self._download_full_markdown(zip_url)
        return MinerUResult(markdown=markdown, source=zip_url or "precision-api", raw=raw)

    def _poll_agent(self, task_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            response = requests.get(f"{self.agent_base_url}/parse/{task_id}", timeout=30)
            raw = response.json()
            state = raw.get("data", {}).get("state")
            if state == "done":
                return raw
            if state == "failed":
                raise MinerUError(f"MinerU Agent task failed: {raw}")
            time.sleep(self.poll_seconds)
        raise MinerUError(f"Timed out waiting for Agent task {task_id}")

    def _poll_precision(self, task_id: str, headers: dict[str, str]) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            response = requests.get(
                f"{self.precision_base_url}/extract/task/{task_id}",
                headers=headers,
                timeout=30,
            )
            raw = response.json()
            state = raw.get("data", {}).get("state")
            if state == "done":
                return raw
            if state == "failed":
                raise MinerUError(f"MinerU precision task failed: {raw}")
            time.sleep(self.poll_seconds)
        raise MinerUError(f"Timed out waiting for precision task {task_id}")

    def _task_id(self, response: requests.Response) -> str:
        return self._data(response)["task_id"]

    def _data(self, response: requests.Response) -> dict[str, Any]:
        if response.status_code >= 400:
            raise MinerUError(f"MinerU HTTP error {response.status_code}: {response.text[:500]}")
        raw = response.json()
        if raw.get("code") != 0:
            raise MinerUError(f"MinerU API error: {raw}")
        return raw["data"]

    def _download_full_markdown(self, zip_url: str) -> str:
        response = requests.get(zip_url, timeout=120)
        if response.status_code >= 400:
            raise MinerUError(f"Failed to download precision result zip: HTTP {response.status_code}")
        with zipfile.ZipFile(BytesIO(response.content)) as archive:
            names = archive.namelist()
            full_md_candidates = [name for name in names if name.endswith("full.md")]
            if not full_md_candidates:
                raise MinerUError(f"Result zip did not contain full.md. Files: {names[:20]}")
            with archive.open(full_md_candidates[0]) as f:
                return f.read().decode("utf-8")
