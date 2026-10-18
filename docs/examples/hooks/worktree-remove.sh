#!/bin/bash
# WorktreeRemove hook: removes the worktree and its worktree-* branch.
set -euo pipefail

dir=$(jq -r .worktree_path)
branch=$(git -C "$dir" branch --show-current)
repo=$(dirname "$(git -C "$dir" rev-parse --path-format=absolute --git-common-dir)")

git -C "$repo" worktree remove --force "$dir" >&2
if [[ "$branch" == worktree-* ]]; then
  git -C "$repo" branch -D "$branch" >&2
fi
