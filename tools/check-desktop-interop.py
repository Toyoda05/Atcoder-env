"""Check Windows integration without reading or changing clipboard contents."""
from pathlib import Path
import subprocess

windows = Path("/mnt/c/Windows/System32")
result = subprocess.run(
    [str(windows / "WindowsPowerShell/v1.0/powershell.exe"), "-NoProfile", "-Command",
     "[Console]::WriteLine('WSL_INTEROP_OK')"],
    capture_output=True, check=True,
)
assert b"WSL_INTEROP_OK" in result.stdout, "Windows interop failed"
subprocess.run([str(windows / "clip.exe"), "/?"], capture_output=True, check=True)
print("Windows process launch and clipboard executable: OK (clipboard unchanged)")
