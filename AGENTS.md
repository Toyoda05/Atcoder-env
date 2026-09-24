# Competitive programming workspace

- Explain work in Japanese. Use Ubuntu/WSL commands in this project.
- Use `.venv/bin/python tools/cp.py` for preparing, testing and bundling solutions.
- C++ uses GNU C++20, GCC, `lib/cpp` and `third_party/ac-library`.
- Python uses CPython 3.12. Verify judge language/package compatibility separately.
- Self-written Python libraries live in `lib/python/cp_lib`. Use top-level
  `from cp_lib.module import Symbol` imports, without aliases or wildcard imports.
- Self-written C++ headers live in `lib/cpp/cp`, with `#pragma once` and a `cp` namespace.
- Always test the generated standalone file before submitting. Do not treat sample
  success as proof of correctness.
- Run `python3 -m unittest discover -s tests -v` when changing the bundler or libraries.
- Never store account passwords, cookies or tokens in this repository.
- Submission requires an explicit target URL and language ID; preserve the tool's
  interactive confirmation. Do not submit example/test programs to a real account.
- Codex is for environment maintenance and practice. During contests, follow the
  organizer's AI rules; all normal build/test/bundle operations work without AI.
