# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CLI tool for AWS SSO credential management across multiple accounts and roles. Resolves SSO, role-assumption, and chained credential profiles from `~/.aws/config`, with output as shell exports, JSON, Docker-style `.env` files, or direct `~/.aws/credentials` writes. Built with Click and boto3, published to PyPI as `aws-assume-cli`.

## Setup

```
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Common Commands

```
# Resolve credentials (default: shell export statements)
eval $(aws-assume my-profile)

# Output as JSON
aws-assume my-profile --json

# Write to .env file (0600 permissions)
aws-assume my-profile --env-file .env

# Write to ~/.aws/credentials
aws-assume my-profile --credentials
aws-assume my-profile --credentials --credentials-profile custom-name

# List available profiles
aws-assume --list

# Custom session duration (900–43200 seconds)
aws-assume my-profile --duration 3600

# Lint
.venv/bin/ruff check .
.venv/bin/ruff format --check .

# Run tests
.venv/bin/pytest
```

## Directory Structure

```
aws_assume/
  __init__.py          # Package version
  cli.py               # Click CLI entry point
  core.py              # Credential resolution logic (SSO, role assumption, chaining)
tests/
  test_cli.py          # CLI integration tests using Click's CliRunner
  test_core.py         # Unit tests for Credentials dataclass and core functions
pyproject.toml         # Build config, dependencies, ruff settings
```

## Architecture

`core.py` resolves credentials through three paths based on profile config:
1. **SSO profiles** (`sso_start_url`) — resolves via boto3 session, auto-triggers `aws sso login` on token expiry
2. **Role assumption** (`role_arn` + `source_profile`) — recursively resolves source credentials, then calls `sts:AssumeRole`
3. **Static/boto3 fallback** — direct boto3 session credential resolution (also covers `role_arn` + `credential_source`)

Cycle detection via `_seen` frozenset prevents infinite recursion in credential chains. Credential file writes use atomic temp-file replacement with 0600 permissions.

## Testing

Tests use pytest with `unittest.mock.patch` to avoid real AWS calls. CI runs against Python 3.10, 3.11, 3.12.

```
.venv/bin/pytest -v
```

## Code Style

Ruff with `line-length = 100`, `target-version = "py310"`. Lint rules: `E`, `F`, `I`, `UP`.

```
.venv/bin/ruff check .
.venv/bin/ruff format .
```
