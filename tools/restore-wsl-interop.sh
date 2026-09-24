#!/usr/bin/env bash
# Restore WSL's standard Windows-executable handler when it is missing.
# Run as root only if Windows .exe invocation fails with Exec format error.
# This changes the current kernel registration, not persistent OS settings.
set -euo pipefail
if [[ ! -f /proc/sys/fs/binfmt_misc/WSLInterop && ! -f /proc/sys/fs/binfmt_misc/WSLInterop-late ]]; then
    if [[ $(id -u) -ne 0 ]]; then
        echo "Run with sudo, or wsl -d Ubuntu-24.04 -u root -- bash <this-script>" >&2
        exit 1
    fi
    test -x /init
    test -w /proc/sys/fs/binfmt_misc/register
    printf '%s\n' ':WSLInterop:M::MZ::/init:PF' > /proc/sys/fs/binfmt_misc/register
    echo "Restored the standard WSLInterop handler."
fi
if [[ -f /proc/sys/fs/binfmt_misc/WSLInterop ]]; then
    cat /proc/sys/fs/binfmt_misc/WSLInterop
else
    cat /proc/sys/fs/binfmt_misc/WSLInterop-late
fi
