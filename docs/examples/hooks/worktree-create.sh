#!/bin/bash
# WorktreeCreate hook: creates the worktree in <repo>/.worktrees/<name>
# from the freshly fetched origin default branch and copies the gitignored
# files listed in .worktreeinclude.
# Claude Code reads the worktree path from the last line of stdout.
set -euo pipefail

input=$(cat)
name=$(jq -r .name <<<"$input")
repo=$(git -C "$(jq -r .cwd <<<"$input")" rev-parse --show-toplevel)
dir="$repo/.worktrees/$name"

base=HEAD
if git -C "$repo" remote get-url origin >/dev/null 2>&1; then
  git -C "$repo" fetch --quiet origin >&2 || true
  git -C "$repo" remote set-head origin --auto >/dev/null 2>&1 || true
  base=$(git -C "$repo" symbolic-ref --quiet --short refs/remotes/origin/HEAD || echo HEAD)
fi

git -C "$repo" worktree add --no-track -b "worktree-$name" "$dir" "$base" >&2

if [[ -f "$repo/.worktreeinclude" ]]; then
  git -C "$repo" ls-files --others --ignored --exclude-from=.worktreeinclude \
    | git -C "$repo" check-ignore --stdin \
    | rsync -a --files-from=- "$repo/" "$dir/" >&2 || true
fi

echo "$dir"
