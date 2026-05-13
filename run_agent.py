from __future__ import annotations

import argparse
from pathlib import Path

from agent.pipeline import AgentConfig, DocumentAgent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the MinerU enhanced Data Agent.")
    parser.add_argument(
        "--mode",
        choices=["agent-url", "agent-file", "precision-url", "markdown"],
        required=True,
        help="MinerU invocation mode or local markdown post-processing mode.",
    )
    parser.add_argument("--input-url", help="Remote document URL for MinerU URL APIs.")
    parser.add_argument("--input-file", help="Local document path for Agent file upload API.")
    parser.add_argument("--mineru-markdown", help="Existing MinerU full.md path.")
    parser.add_argument("--output-dir", required=True, help="Directory for agent outputs.")
    parser.add_argument("--language", default="ch", help="Document language for OCR.")
    parser.add_argument("--page-range", default="1-10", help="Page range for MinerU API.")
    parser.add_argument("--token-env", default="MINERU_TOKEN", help="Env var name for precision API token.")
    parser.add_argument("--poll-seconds", type=float, default=3.0, help="Polling interval.")
    parser.add_argument("--timeout-seconds", type=float, default=600.0, help="Polling timeout.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = AgentConfig(
        mode=args.mode,
        output_dir=Path(args.output_dir),
        input_url=args.input_url,
        input_file=Path(args.input_file) if args.input_file else None,
        mineru_markdown=Path(args.mineru_markdown) if args.mineru_markdown else None,
        language=args.language,
        page_range=args.page_range,
        token_env=args.token_env,
        poll_seconds=args.poll_seconds,
        timeout_seconds=args.timeout_seconds,
    )
    result = DocumentAgent(config).run()
    print(f"structured_json={result.structured_json}")
    print(f"quality_report={result.quality_report}")
    print(f"run_log={result.run_log}")


if __name__ == "__main__":
    main()

