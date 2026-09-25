# Contributing to aws-assume

Thanks for your interest in contributing! This document explains how to get started.

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/<your-username>/aws-assume.git
   cd aws-assume
   ```
3. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```
4. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

### Running Tests

```bash
pytest
```

### Linting and Formatting

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
ruff check .
ruff format --check .
```

### Code Style

- Follow existing code conventions in the project.
- Ruff is configured in `pyproject.toml` — run it before submitting a PR.
- Target Python 3.10+ (no walrus operators in hot paths, but f-strings and `match` are fine).

## Submitting a Pull Request

1. Ensure all tests pass and linting is clean.
2. Write clear, descriptive commit messages.
3. Open a PR against the `main` branch.
4. Fill out the PR template — describe what changed, why, and how to test it.
5. A maintainer will review your PR. Please be patient and responsive to feedback.

## Reporting Bugs

Use the [bug report template](https://github.com/Specter099/aws-assume-cli/issues/new?template=bug_report.yml) to file a bug. Include:

- Steps to reproduce
- Expected vs. actual behavior
- Python version and OS

## Requesting Features

Use the [feature request template](https://github.com/Specter099/aws-assume-cli/issues/new?template=feature_request.yml). Explain:

- The problem you're trying to solve
- Your proposed solution
- Any alternatives you've considered

## Code of Conduct

This project follows the [Contributor Covenant v2.1](CODE_OF_CONDUCT.md). Please be respectful and constructive.
