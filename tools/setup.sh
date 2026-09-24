#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
if [[ -f requirements.lock ]]; then
    .venv/bin/python -m pip install -r requirements.lock
else
    .venv/bin/python -m pip install -r requirements.txt
fi
mkdir -p third_party
if [[ ! -d third_party/ac-library ]]; then
    git clone https://github.com/atcoder/ac-library.git third_party/ac-library
    if [[ -f ACL_REVISION ]]; then
        git -C third_party/ac-library checkout --detach "$(cat ACL_REVISION)"
    fi
fi
.venv/bin/python tools/cp.py doctor
