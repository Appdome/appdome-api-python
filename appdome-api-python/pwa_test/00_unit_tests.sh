#!/usr/bin/env bash
# Offline unit tests (mocked API). No env.sh or network needed.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m unittest discover -s tests "$@"
