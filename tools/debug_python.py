"""Run an active Python solution with input.txt under debugpy."""
import runpy
import sys
from pathlib import Path

source = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib/python"))
sys.path.insert(0, str(source.parent))
sys.argv = [str(source)]
with (source.parent / "input.txt").open(encoding="utf-8") as data:
    sys.stdin = data
    runpy.run_path(str(source), run_name="__main__")
