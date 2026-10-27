#!/bin/bash
# The "Имплементировать план" button under Claude Desktop must open nothing itself: serve stops and
# reports the folder and the prompt, so the agent proposes the implementation session as a card.
# Outside Desktop the button opens a terminal with the prompt.
export LC_ALL=en_US.UTF-8
tool="$(cd "$(dirname "$0")/.." && pwd)/plan_tool.py"
case_dir="$(cd "$(dirname "$0")" && pwd)/cases/ok"
work=$(cd "$(mktemp -d)" && pwd -P)
trap 'kill "$serve_pid" 2>/dev/null; rm -rf "$work"' EXIT
port=$((8800 + RANDOM % 100))

fail() {
  echo "fail $1: got '$2'"
  exit 1
}

mkdir -p "$work/bin" "$work/project/plan"
cp -R "$case_dir" "$work/project/plan/sample"
mv "$work/project/plan/sample/lib" "$work/project/lib"
cat > "$work/bin/open" <<EOF
#!/bin/bash
printf '%s\n' "\$*" >> "$work/open.log"
EOF
cat > "$work/bin/osascript" <<EOF
#!/bin/bash
printf '%s\n' "\$*" >> "$work/osascript.log"
EOF
chmod +x "$work/bin/open" "$work/bin/osascript"

start_serve() {
  rm -f "$work/open.log" "$work/osascript.log"
  PATH="$work/bin:$PATH" CLAUDE_CODE_ENTRYPOINT="$1" \
    python3 "$tool" serve "$work/project/plan/sample/plan.md" --no-open --port "$port" > "$work/serve.out" 2>&1 &
  serve_pid=$!
  for _ in $(seq 50); do
    curl -s "http://127.0.0.1:$port/alive" > /dev/null && return
    sleep 0.1
  done
  fail "serve start" "$(cat "$work/serve.out")"
}

start_serve claude-desktop
printf -- '- [ ] [Пункт 1] open question\n' > "$work/project/plan/sample/comments.md"
status=$(curl -s -o "$work/body" -w '%{http_code}' -X POST "http://127.0.0.1:$port/implement")
[ "$status" = "409" ] || fail "open comment blocks the button" "$status $(cat "$work/body")"
[ ! -f "$work/open.log" ] || fail "nothing opens with an open comment" "$(cat "$work/open.log")"

rm "$work/project/plan/sample/comments.md"
body=$(curl -s -X POST "http://127.0.0.1:$port/implement")
[[ "$body" == *'"where": "desktop"'* ]] || fail "desktop start" "$body"
wait "$serve_pid"

[ ! -f "$work/open.log" ] || fail "desktop opens nothing" "$(cat "$work/open.log")"
[ ! -f "$work/osascript.log" ] || fail "desktop opens no terminal" "$(cat "$work/osascript.log")"
grep -q '^implementation started: desktop$' "$work/serve.out" || fail "serve report" "$(cat "$work/serve.out")"
grep -qx "folder: $work/project" "$work/serve.out" || fail "folder is the project root" "$(cat "$work/serve.out")"
grep -qx "prompt: имплементируй план $work/project/plan/sample" "$work/serve.out" || fail "prompt names the plan" "$(cat "$work/serve.out")"

start_serve cli
printf '#!/bin/bash\nexit 1\n' > "$work/bin/open"
body=$(curl -s -X POST "http://127.0.0.1:$port/implement")
[[ "$body" == *'"where": "terminal"'* ]] || fail "terminal outside desktop" "$body"
grep -q 'имплементируй план' "$work/osascript.log" || fail "terminal gets the prompt" "$(cat "$work/osascript.log" 2>/dev/null)"
wait "$serve_pid"

echo "ok implement_button_test"
