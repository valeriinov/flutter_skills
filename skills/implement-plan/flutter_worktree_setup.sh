#!/usr/bin/env bash
# Usage: flutter_worktree_setup.sh <worktree-path>
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $(basename "$0") <worktree-path>" >&2
  exit 2
fi

worktree="$(cd "$1" && pwd)"

if [[ ! -f "$worktree/pubspec.yaml" ]]; then
  exit 0
fi

main_tree="$(git -C "$worktree" worktree list --porcelain | head -n 1 | cut -d ' ' -f 2-)"

copy_included_files() {
  local include_list=""
  if [[ -f "$main_tree/.worktreeinclude" ]]; then
    include_list="$main_tree/.worktreeinclude"
  elif [[ -f "$worktree/.worktreeinclude" ]]; then
    include_list="$worktree/.worktreeinclude"
  fi

  if [[ -z "$include_list" ]]; then
    echo "skip: copy (no .worktreeinclude)"
    return
  fi

  local included_files
  included_files="$(mktemp)"
  git -C "$main_tree" ls-files -z --others --ignored --exclude-from="$include_list" > "$included_files"

  local path
  while IFS= read -r -d '' path; do
    local src="$main_tree/$path"
    local dst="$worktree/$path"
    if [[ -L "$src" || -e "$dst" ]]; then
      continue
    fi
    mkdir -p "$(dirname "$dst")"
    cp -p "$src" "$dst"
  done < "$included_files"
  rm "$included_files"
  echo "ok: copy"
}

install_sdk_and_packages() {
  cd "$worktree"
  if [[ -f .fvmrc ]] && command -v fvm > /dev/null; then
    fvm install
    echo "ok: fvm install"
    fvm flutter pub get
    echo "ok: pub get"
    return
  fi

  echo "skip: fvm install (no .fvmrc or fvm)"
  flutter pub get
  echo "ok: pub get"
}

install_pods() {
  if [[ "$(uname)" != "Darwin" ]]; then
    echo "skip: pod install (not macOS)"
    return
  fi
  if [[ ! -f "$worktree/ios/Podfile" ]]; then
    echo "skip: pod install (no ios/Podfile)"
    return
  fi
  if ! command -v pod > /dev/null; then
    echo "skip: pod install (no pod)"
    return
  fi

  (cd "$worktree/ios" && pod install)
  echo "ok: pod install"
}

copy_included_files
install_sdk_and_packages
install_pods
