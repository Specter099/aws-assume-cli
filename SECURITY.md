# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in `aws-assume-cli`, please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, please report vulnerabilities via [GitHub Security Advisories](https://github.com/Specter099/aws-assume-cli/security/advisories/new).

### What to include

- A description of the vulnerability
- Steps to reproduce the issue
- Potential impact
- Suggested fix (if any)

### Response timeline

- **Acknowledgement**: Within 48 hours
- **Initial assessment**: Within 1 week
- **Fix or mitigation**: Dependent on severity, but we aim for 30 days for critical issues

### What to expect

- We will acknowledge receipt of your report promptly.
- We will work with you to understand and validate the issue.
- We will keep you informed of our progress toward a fix.
- We will credit you in the release notes (unless you prefer to remain anonymous).

## Security Best Practices for Users

- Never commit AWS credentials to version control.
- Use `aws-assume` with SSO profiles to avoid long-lived access keys.
- Keep `aws-assume-cli` updated to the latest version.
