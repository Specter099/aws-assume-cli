# aws-assume

[![CI](https://github.com/Specter099/aws-assume-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Specter099/aws-assume-cli/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/aws-assume-cli)](https://pypi.org/project/aws-assume-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Simple CLI for AWS SSO credential management across multiple accounts and roles.

## Installation

```bash
pip install aws-assume-cli
```

## Usage

```bash
# Eval into your shell (most common usage)
eval $(aws-assume my-profile)

# List available profiles
aws-assume --list

# Output as JSON
aws-assume my-profile --json

# Write to a Docker .env file
aws-assume my-profile --env-file .env

# Write to ~/.aws/credentials
aws-assume my-profile --credentials

# Write credentials under a specific profile name
aws-assume my-profile --credentials --credentials-profile temp-dev

# Set session duration (for role assumption)
aws-assume my-profile --duration 3600

# Skip automatic SSO login prompt
aws-assume my-profile --no-auto-login
```

## How it works

`aws-assume` reads your `~/.aws/config` and supports three profile types:

**SSO profiles** — logs you in via `aws sso login` if the session is expired, then fetches temporary credentials.

```ini
[profile my-sso]
sso_start_url = https://my-org.awsapps.com/start
sso_region = us-east-1
sso_account_id = 123456789012
sso_role_name = AdministratorAccess
region = us-east-1
```

**Role assumption profiles** — assumes a role using another profile as the source.

```ini
[profile prod-admin]
role_arn = arn:aws:iam::999999999999:role/AdminRole
source_profile = my-sso
region = us-east-1
```

**SSO + role chaining** — the source profile itself uses SSO. `aws-assume` handles the chain automatically.

Any other profile (static keys, `credential_source`, `credential_process`, web identity) is resolved by boto3.

## Output modes

| Flag | Output | Use case |
|---|---|---|
| *(default)* | `export VAR=...` | `eval $(aws-assume profile)` in shell |
| `--json` | JSON object | Scripting, piping |
| `--env-file PATH` | Docker `.env` format | `docker run --env-file .env ...` |
| `--credentials` | `~/.aws/credentials` | SDK / tool compatibility |

`--eval` and `--json` both write to stdout and cannot be combined. Files are written with `0600`
permissions; `--credentials` replaces only the target profile and keeps the rest of the file,
including comments.

## Development

```bash
git clone https://github.com/Specter099/aws-assume-cli
cd aws-assume-cli
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## License

MIT
