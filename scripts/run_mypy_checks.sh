#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

pushd "$repo_root" >/dev/null
uv run mypy shared
popd >/dev/null