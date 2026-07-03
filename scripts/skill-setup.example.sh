#!/bin/bash
set -euo pipefail

DIST="${SKILL_BOARD_SYNC_DIR:-$HOME/Library/Mobile Documents/com~apple~CloudDocs/ai-skills}"

if [ ! -d "$DIST" ]; then
  echo "sync directory does not exist: $DIST"
  echo "Run scripts/skill-push.example.sh first, or set SKILL_BOARD_SYNC_DIR."
  exit 1
fi

mkdir -p "$HOME/.claude" "$HOME/.hermes"
ln -sfn "$DIST" "$HOME/.claude/skills"
ln -sfn "$DIST" "$HOME/.hermes/skills"

echo "Claude Code skills -> $HOME/.claude/skills"
echo "Hermes skills      -> $HOME/.hermes/skills"
echo "For Codex project-level skills, link this folder from your project .agents/skills."
