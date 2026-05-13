#!/usr/bin/env bash
set -euo pipefail

python run_agent.py \
  --mode precision-url \
  --input-url "https://static.cninfo.com.cn/finalpage/2023-08-30/1217701805.PDF" \
  --page-range "30-40" \
  --output-dir "samples/output/example_02_pdf_software_h1_p30_40" \
  --poll-seconds 5 \
  --timeout-seconds 900

python run_agent.py \
  --mode precision-url \
  --input-url "https://static.cninfo.com.cn/finalpage/2025-04-03/1222989624.PDF" \
  --page-range "1-20" \
  --output-dir "samples/output/example_03_septwolves_annual_p1_20" \
  --poll-seconds 5 \
  --timeout-seconds 900

python run_agent.py \
  --mode precision-url \
  --input-url "https://static.cninfo.com.cn/finalpage/2024-08-31/1221090402.PDF" \
  --page-range "1-20" \
  --output-dir "samples/output/example_04_dcits_h1_p1_20" \
  --poll-seconds 5 \
  --timeout-seconds 900

python run_agent.py \
  --mode precision-url \
  --input-url "https://static.cninfo.com.cn/finalpage/2024-08-26/1220963509.PDF" \
  --page-range "1-20" \
  --output-dir "samples/output/example_05_lens_h1_p1_20" \
  --poll-seconds 5 \
  --timeout-seconds 900

