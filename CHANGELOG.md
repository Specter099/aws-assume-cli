# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- `aws sso login` output now goes to stderr so it is no longer captured by `eval $(aws-assume ...)`.
- `--env-file` is created with 0600 permissions from the start and refuses to follow symlinks.
- `--credentials-profile` is validated like the profile argument.
- Profiles using `role_arn` with `credential_source` (no `source_profile`) are resolved by boto3
  instead of silently using the `default` profile.
- Generated `RoleSessionName` is truncated to the STS 64-character limit.
- `--version` reports the installed package version.
- A clear error is shown when the AWS CLI is not installed.

### Removed

- Unused `Credentials.to_env_vars()` and duplicate Markdown issue templates.

## [0.1.0] - 2025-05-01

### Added

- Initial release of `aws-assume-cli`.
- Support for SSO profiles, role assumption profiles, and SSO + role chaining.
- Output modes: shell eval (default), `--json`, `--env-file`, `--credentials`.
- `--list` flag to list available profiles.
- `--duration` flag for custom session duration.
- `--no-auto-login` flag to skip automatic SSO login.
- `--credentials-profile` flag to write credentials under a custom profile name.

[0.1.0]: https://github.com/Specter099/aws-assume-cli/releases/tag/v0.1.0
