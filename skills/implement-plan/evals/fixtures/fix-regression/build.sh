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
cp -R "$fixture/before/." "$dir/"
git_eval add -A
git_eval commit -q -m "Add price converter"
head="$(git -C "$dir" rev-parse HEAD)"

find "$dir" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -R "$fixture/fixed/." "$dir/"

echo "head: $head"
echo "dir: $dir"
