#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL_SKILLS_DIR="$ROOT_DIR/AI Resources/Claude-Codex-Skills"
LEGACY_SKILLS_DIR="$ROOT_DIR/AI Resources/Skills"
TARGET_CLAUDE_DIR="${CLAUDE_HOME:-$HOME/.claude}/skills"
TARGET_CODEX_DIR="${CODEX_HOME:-$HOME/.codex}/skills"
MODE="${1:-symlink}"

install_skill_dir() {
  local src="$1"
  local dst_root="$2"
  mkdir -p "$dst_root"
  find "$src" -mindepth 1 -maxdepth 1 -type d | while read -r skill_dir; do
    local skill_name
    skill_name="$(basename "$skill_dir")"
    local dst="$dst_root/$skill_name"
    rm -rf "$dst"
    if [[ "$MODE" == "copy" ]]; then
      cp -R "$skill_dir" "$dst"
    else
      ln -s "$skill_dir" "$dst"
    fi
  done
}

install_skill_dir "$LOCAL_SKILLS_DIR" "$TARGET_CLAUDE_DIR"
install_skill_dir "$LOCAL_SKILLS_DIR" "$TARGET_CODEX_DIR"
install_skill_dir "$LEGACY_SKILLS_DIR" "$TARGET_CLAUDE_DIR"
install_skill_dir "$LEGACY_SKILLS_DIR" "$TARGET_CODEX_DIR"

echo "Installed skills into:"
echo "  Claude: $TARGET_CLAUDE_DIR"
echo "  Codex:  $TARGET_CODEX_DIR"
echo "Mode: $MODE"
