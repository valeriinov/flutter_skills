#!/usr/bin/env bash
# Removes linked worktrees whose work is safe on the remote.
# Usage: prune_worktrees.sh [--dry-run] <path>
#   <path> is a linked worktree: check only that worktree.
#   <path> is the main checkout: check every worktree under <main>/.worktrees/.
# A worktree is removed only when it is on a branch, has no tracked or
# untracked changes, and a remote branch contains its HEAD (pushed, or merged
# after the remote branch was deleted). The branch stays.
# Never uses --force.
set -euo pipefail

dry_run=0
if [[ "${1:-}" == "--dry-run" ]]; then
  dry_run=1
  shift
fi
target="${1:?usage: prune_worktrees.sh [--dry-run] <path>}"

target="$(git -C "$target" rev-parse --show-toplevel)"
main="$(git -C "$target" worktree list --porcelain | sed -n '1s/^worktree //p')"

keep() { echo "kept    $1: $2"; }

check() {
  local wt="$1"
  if [[ "$wt" != "$main/.worktrees/"* ]]; then
    keep "$wt" "outside $main/.worktrees/"
    return
  fi
  if ! git -C "$wt" symbolic-ref -q HEAD >/dev/null; then
    keep "$wt" "detached HEAD"
    return
  fi
  if [[ -n "$(git -C "$wt" status --porcelain)" ]]; then
    keep "$wt" "uncommitted or untracked changes"
    return
  fi
  if [[ -z "$(git -C "$wt" branch -r --contains HEAD)" ]]; then
    keep "$wt" "HEAD is on no remote branch"
    return
  fi
  if ((dry_run)); then
    echo "would remove $wt"
    return
  fi
  git -C "$main" worktree remove "$wt"
  echo "removed $wt (branch kept)"
}

if [[ "$target" != "$main" ]]; then
  check "$target"
  exit 0
fi

git -C "$main" worktree list --porcelain | sed -n 's/^worktree //p' | tail -n +2 |
  while IFS= read -r wt; do check "$wt"; done
