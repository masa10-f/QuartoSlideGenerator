#!/usr/bin/env bash
set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TASK_ID=""
REPO_DIR="."
SINCE=""
UNTIL=""
PATHS=""
EXTRA_GREP=""
INCLUDE_DIFF="false"
MAX_PATCH_LINES="600"
TITLE=""
FORMAT="html"
OUTDIR="slides"
SUMMARY_MODE="ai"
SUMMARY_API_KEY=""
SUMMARY_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --task) TASK_ID="$2"; shift 2;;
    --repo) REPO_DIR="$2"; shift 2;;
    --since) SINCE="$2"; shift 2;;
    --until) UNTIL="$2"; shift 2;;
    --paths) PATHS="$2"; shift 2;;           # comma-separated
    --grep) EXTRA_GREP="$2"; shift 2;;
    --include-diff) INCLUDE_DIFF="true"; shift 1;;
    --max-patch-lines) MAX_PATCH_LINES="$2"; shift 2;;
    --title) TITLE="$2"; shift 2;;
    --format) FORMAT="$2"; shift 2;;         # html | pdf
    --outdir) OUTDIR="$2"; shift 2;;
    --summary-mode) SUMMARY_MODE="$2"; shift 2;;       # none | template | ai | manual
    --summary-api-key) SUMMARY_API_KEY="$2"; shift 2;; # API key for AI mode
    --summary-dir) SUMMARY_DIR="$2"; shift 2;;         # Directory for manual summaries
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

if ! command -v git >/dev/null 2>&1; then echo "git not found"; exit 1; fi
if ! command -v python3 >/dev/null 2>&1; then echo "python3 not found"; exit 1; fi

# Only check for quarto if not in AI mode (AI mode doesn't need quarto immediately)
if [[ "$SUMMARY_MODE" != "ai" ]]; then
  if ! command -v quarto >/dev/null 2>&1; then echo "quarto not found"; exit 1; fi
fi

mkdir -p "$OUTDIR"

# Generate filename based on task_id or range
if [[ -n "$TASK_ID" ]]; then
  QMD_PATH="$OUTDIR/task_${TASK_ID//\//-}.qmd"
else
  # Use timestamp or range-based filename when no task_id
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  QMD_PATH="$OUTDIR/commits_${TIMESTAMP}.qmd"
fi

# Handle AI mode: extract commit info for Claude Code to summarize
if [[ "$SUMMARY_MODE" == "ai" ]]; then
  echo "AI summary mode detected. Extracting commit information..."
  COMMIT_INFO_JSON=$(python3 "$SCRIPT_DIR/gen_task_qmd.py" \
    ${TASK_ID:+--task "$TASK_ID"} --repo "$REPO_DIR" \
    ${SINCE:+--since "$SINCE"} ${UNTIL:+--until "$UNTIL"} \
    ${PATHS:+--paths "$PATHS"} \
    ${EXTRA_GREP:+--grep "$EXTRA_GREP"} \
    --out "$QMD_PATH" \
    --format "$FORMAT" \
    --summary-mode extract)

  # Create summaries directory
  if [[ -z "$SUMMARY_DIR" ]]; then
    SUMMARY_DIR=".commit-summaries"
  fi
  mkdir -p "$SUMMARY_DIR"

  # Save commit info to a temp file for Claude Code to process
  COMMIT_INFO_FILE="$SUMMARY_DIR/.pending_summaries.json"
  echo "$COMMIT_INFO_JSON" > "$COMMIT_INFO_FILE"

  echo ""
  echo "=================================================="
  echo "AI Summary Generation Required"
  echo "=================================================="
  echo ""
  echo "Commit information has been extracted to:"
  echo "  $COMMIT_INFO_FILE"
  echo ""
  echo "Claude Code should now generate summaries for these commits."
  echo "After summaries are generated in $SUMMARY_DIR/, this script"
  echo "will continue with slide generation."
  echo ""
  echo "Please ask Claude Code to:"
  echo "  1. Read the commit info from: $COMMIT_INFO_FILE"
  echo "  2. Generate natural language summaries for each commit"
  echo "  3. Save summaries as: $SUMMARY_DIR/<short-sha>.md"
  echo ""
  echo "Once summaries are ready, re-run with --summary-mode manual"
  echo "=================================================="
  exit 0
fi

# Use SCRIPT_DIR to locate gen_task_qmd.py relative to this script
python3 "$SCRIPT_DIR/gen_task_qmd.py" \
  ${TASK_ID:+--task "$TASK_ID"} --repo "$REPO_DIR" \
  ${SINCE:+--since "$SINCE"} ${UNTIL:+--until "$UNTIL"} \
  ${PATHS:+--paths "$PATHS"} \
  ${EXTRA_GREP:+--grep "$EXTRA_GREP"} \
  ${TITLE:+--title "$TITLE"} \
  --out "$QMD_PATH" \
  --format "$FORMAT" \
  --max-patch-lines "$MAX_PATCH_LINES" \
  --summary-mode "$SUMMARY_MODE" \
  ${SUMMARY_API_KEY:+--summary-api-key "$SUMMARY_API_KEY"} \
  ${SUMMARY_DIR:+--summary-dir "$SUMMARY_DIR"} \
  $( [[ "$INCLUDE_DIFF" == "true" ]] && echo "--include-diff" )

# Quarto render
if [[ "$FORMAT" == "pdf" ]]; then
  quarto render "$QMD_PATH" --to pdf
else
  quarto render "$QMD_PATH" --to revealjs
fi

echo "Done. Output in: $OUTDIR"
