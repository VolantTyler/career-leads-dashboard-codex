#!/usr/bin/env bash
set -euo pipefail

ran_any=false

run_if_present() {
  local file="$1"
  shift
  if [[ -f "$file" ]]; then
    echo "==> Running: $*"
    "$@"
    ran_any=true
  fi
}

# JavaScript/TypeScript
if [[ -f package.json ]]; then
  if command -v npm >/dev/null 2>&1; then
    echo "==> Detected package.json"
    npm ci
    npm test -- --watch=false
    ran_any=true
  else
    echo "package.json found, but npm is not installed" >&2
    exit 1
  fi
fi

# Python (pytest)
if [[ -f pyproject.toml || -f requirements.txt ]]; then
  if command -v python3 >/dev/null 2>&1; then
    echo "==> Detected Python project"
    python3 -m pip install -U pip
    if [[ -f requirements.txt ]]; then
      python3 -m pip install -r requirements.txt
    fi
    python3 -m pip install pytest
    pytest -q
    ran_any=true
  else
    echo "Python project detected, but python3 is not installed" >&2
    exit 1
  fi
fi

# Go
run_if_present go.mod go test ./...

# Rust
run_if_present Cargo.toml cargo test --all-targets

if [[ "$ran_any" == false ]]; then
  echo "No recognized test configuration found."
  echo "Add one of: package.json, pyproject.toml, requirements.txt, go.mod, Cargo.toml"
  if [[ "${REQUIRE_TESTS:-false}" == "true" ]]; then
    exit 1
  fi
  exit 0
fi
