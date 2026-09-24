#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python tools/cp.py run examples/python/main.py
.venv/bin/python tools/cp.py run examples/cpp/main.cpp
.venv/bin/python tools/debug_python.py examples/python/main.py
.venv/bin/python tools/cp.py build examples/cpp/main.cpp --debug
gdb -q -batch -ex "run < examples/cpp/input.txt" .build/debug-main
.venv/bin/python -m pip check
.venv/bin/python -m pip freeze > requirements.lock
git -C third_party/ac-library rev-parse HEAD > ACL_REVISION
if [[ ! -d .git ]]; then
    git init -b main
fi
timeout 40 .venv/bin/oj download https://atcoder.jp/contests/abs/tasks/abc086_a -d .build/atcoder-abs-samples
