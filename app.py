from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent.pipeline import AgentConfig, DocumentAgent


class ParseRequest(BaseModel):
    mode: Literal["auto", "agent-url", "agent-file", "precision-url", "markdown", "mineru-json"] = Field(
        "auto", description="MinerU invocation mode or local markdown mode."
    )
    output_dir: str = Field(..., description="Directory for generated outputs.")
    input_url: str | None = Field(default=None, description="Remote document URL.")
    input_file: str | None = Field(default=None, description="Local input file path.")
    mineru_markdown: str | None = Field(default=None, description="Existing MinerU full.md path.")
    mineru_json: str | None = Field(default=None, description="Existing MinerU JSON/content_list path.")
    task_type: str = "financial_report_structuring"
    language: str = "ch"
    page_range: str = "1-10"
    token_env: str = "MINERU_TOKEN"
    poll_seconds: float = 3.0
    timeout_seconds: float = 600.0
    quality_threshold: float = 0.85
    max_retry: int = 1
    enable_ocr: bool = False
    enable_table: bool = True
    enable_formula: bool = True


class BatchParseRequest(BaseModel):
    tasks: list[ParseRequest] = Field(..., min_length=1)


class ParseResponse(BaseModel):
    task_id: str
    status: str
    output_dir: str
    full_md: str
    structured_json: str
    tables_json: str
    financial_metrics_json: str
    quality_report: str
    run_log: str
    quality_score: float | None


app = FastAPI(
    title="FinDoc MinerU Data Agent",
    description="MinerU enhanced Data Agent for financial document parsing and quality checks.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "mineru-data-agent"}


@app.post("/parse", response_model=ParseResponse)
def parse_document(request: ParseRequest) -> ParseResponse:
    try:
        output_dir = Path(request.output_dir)
        config = AgentConfig(
            mode=request.mode,
            output_dir=output_dir,
            input_url=request.input_url,
            input_file=Path(request.input_file) if request.input_file else None,
            mineru_markdown=Path(request.mineru_markdown) if request.mineru_markdown else None,
            mineru_json=Path(request.mineru_json) if request.mineru_json else None,
            task_type=request.task_type,
            language=request.language,
            page_range=request.page_range,
            token_env=request.token_env,
            poll_seconds=request.poll_seconds,
            timeout_seconds=request.timeout_seconds,
            quality_threshold=request.quality_threshold,
            max_retry=request.max_retry,
            enable_ocr=request.enable_ocr,
            enable_table=request.enable_table,
            enable_formula=request.enable_formula,
        )
        result = DocumentAgent(config).run()
        quality_score = _read_quality_score(result.quality_report)
        return ParseResponse(
            task_id=output_dir.name or "task",
            status="completed",
            output_dir=str(output_dir),
            full_md=str(output_dir / "full.md"),
            structured_json=str(result.structured_json),
            tables_json=str(output_dir / "tables.json"),
            financial_metrics_json=str(output_dir / "financial_metrics.json"),
            quality_report=str(result.quality_report),
            run_log=str(result.run_log),
            quality_score=quality_score,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/batch_parse", response_model=list[ParseResponse])
def batch_parse(request: BatchParseRequest) -> list[ParseResponse]:
    responses: list[ParseResponse] = []
    for index, task in enumerate(request.tasks, start=1):
        try:
            responses.append(parse_document(task))
        except HTTPException as exc:
            responses.append(
                ParseResponse(
                    task_id=Path(task.output_dir).name or f"task_{index}",
                    status=f"failed: {exc.detail}",
                    output_dir=task.output_dir,
                    full_md="",
                    structured_json="",
                    tables_json="",
                    financial_metrics_json="",
                    quality_report="",
                    run_log="",
                    quality_score=None,
                )
            )
    return responses


def _read_quality_score(path: Path) -> float | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    score = data.get("score")
    return float(score) if score is not None else None
