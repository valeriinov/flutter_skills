#!/usr/bin/env bash
set -euo pipefail

fixture="$(cd "$(dirname "$0")" && pwd)"
dir="${1:-$(mktemp -d)}"
if [ -n "$(ls -A "$dir" 2>/dev/null)" ]; then
  echo "build.sh: $dir is not empty" >&2
  exit 1
fi
mkdir -p "$dir"

git_eval() {
  git -C "$dir" -c user.name=eval -c user.email=eval@example.invalid "$@"
}

git -C "$dir" init -q
git_eval commit -q --allow-empty -m "Initial commit"
base="$(git -C "$dir" rev-parse HEAD)"

cp -R "$fixture/stage-1/." "$dir/"
git_eval add -A
git_eval commit -q -m "Add stock report"

find "$dir" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -R "$fixture/stage-2/." "$dir/"
git_eval add -A
git_eval commit -q -m "Add restock, sale and import services"
head="$(git -C "$dir" rev-parse HEAD)"

echo "range: $base...$head"
echo "dir: $dir"
