#!/usr/bin/env bash
# Helper script to generate AI summaries using Claude Code
# This script is designed to be used interactively with Claude Code

set -euo pipefail

COMMIT_INFO_FILE="${1:-.commit-summaries/.pending_summaries.json}"
SUMMARY_DIR="${2:-.commit-summaries}"

if [[ ! -f "$COMMIT_INFO_FILE" ]]; then
  echo "Error: Commit info file not found: $COMMIT_INFO_FILE"
  echo ""
  echo "Please run task_slides.sh with --summary-mode ai first to extract commit information."
  exit 1
fi

echo "=================================================="
echo "Claude Code: AI Summary Generation Helper"
echo "=================================================="
echo ""
echo "This script helps Claude Code generate summaries for commits."
echo ""
echo "Commit information: $COMMIT_INFO_FILE"
echo "Output directory: $SUMMARY_DIR"
echo ""
echo "Claude Code should:"
echo "  1. Read the JSON file at: $COMMIT_INFO_FILE"
echo "  2. For each commit in the JSON:"
echo "     - Analyze the subject, body, diffstat, and patch"
echo "     - Generate a natural language summary explaining:"
echo "       * What functionality was added/modified/removed"
echo "       * Why the change was made (if inferable)"
echo "       * Key highlights for stakeholders"
echo "  3. Save each summary as: $SUMMARY_DIR/<short-sha>.md"
echo ""
echo "After generating all summaries, the user can re-run task_slides.sh"
echo "with --summary-mode manual to generate the slides."
echo ""
echo "=================================================="
echo ""
echo "Ready for Claude Code to proceed with summary generation."
