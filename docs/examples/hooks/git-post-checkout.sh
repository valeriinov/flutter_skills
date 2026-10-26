#!/bin/bash
# Git post-checkout hook: after `git worktree add`, copies into the new
# worktree the gitignored files that the main tree's .worktreeinclude lists.
# Git passes the null sha as $1 only when it checks out a new worktree.
set -euo pipefail

if [[ "$1" != "0000000000000000000000000000000000000000" ]]; then
  exit 0
fi

worktree=$(git rev-parse --show-toplevel)
main_tree=$(git worktree list --porcelain | head -n 1 | cut -d ' ' -f 2-)

if [[ "$worktree" == "$main_tree" || ! -f "$main_tree/.worktreeinclude" ]]; then
  exit 0
fi

git -C "$main_tree" ls-files --others --ignored --exclude-from=.worktreeinclude \
  | git -C "$main_tree" check-ignore --stdin \
  | rsync -a --ignore-existing --files-from=- "$main_tree/" "$worktree/" || true
