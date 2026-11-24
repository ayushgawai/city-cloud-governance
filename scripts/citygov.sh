#!/usr/bin/env bash
# Convenience wrapper (the CLI itself is pure-stdlib Python).
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHONPATH=src exec python -m citygov.cli "$@"
