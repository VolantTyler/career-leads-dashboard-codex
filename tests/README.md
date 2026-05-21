# Test Suite Scaffold

This repository now includes a CI-first testing scaffold:

- `./scripts/run-tests.sh`: detects the stack and runs tests.
- `.github/workflows/ci.yml`: executes the test runner on push and PR.

## Supported project types

- Node.js (`package.json`) → `npm ci && npm test -- --watch=false`
- Python (`pyproject.toml` or `requirements.txt`) → `pytest -q`
- Go (`go.mod`) → `go test ./...`
- Rust (`Cargo.toml`) → `cargo test --all-targets`

## Next steps

1. Add your project-specific tests in this `tests/` directory (or your framework default).
2. Ensure one of the supported manifests exists.
3. Push changes: CI will automatically validate new features.
