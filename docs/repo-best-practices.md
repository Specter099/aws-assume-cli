# Best Practices for Managing Public GitHub Repositories

## Security — Done

- [x] **`.gitignore`** — Comprehensive patterns for secrets, credentials, and dev artifacts.
- [x] **Enable Dependabot** — Weekly scans for GitHub Actions, pip, and npm.
- [x] **Branch protection rules** — Require 1 approving review, dismiss stale reviews on `main`.
- [x] **SECURITY.md** — Responsible disclosure policy with response timelines.
- [x] **Secret scanning and push protection** — Enabled in repository settings.

---

## P1 — Foundation (Do Now)

These are table stakes. Without them, the repo isn't usable by others.

- [x] **LICENSE file** — MIT license.
- [x] **README.md** — Description, install, dev setup, test/lint commands, and CI/license badges.
- [x] **GitHub Actions CI** — Ruff lint + format check, pytest across Python 3.10/3.11/3.12.
- [x] **Required status checks** — `lint`, `test (3.10)`, `test (3.11)`, `test (3.12)` required to merge to `main`.

## P2 — Contributor Experience (Do Soon)

These make the difference between people starring and people contributing.

- [x] **CONTRIBUTING.md** — Workflow, PR guidelines, code style, and links to issue templates.
- [x] **Issue templates** — Bug report and feature request YAML forms (`.github/ISSUE_TEMPLATE/`).
- [x] **PR template** — What/why/testing checklist (`.github/pull_request_template.md`).
- [x] **Labels** — `good first issue`, `help wanted`, `stale`, `pinned`, `security`.
- [x] **CODE_OF_CONDUCT.md** — Contributor Covenant v2.1 (contact method TBD).

## P3 — Operational Maturity (As Project Grows) — Done

- [x] **CODEOWNERS file** — `@Specter099` as default owner.
- [x] **CHANGELOG.md** — Keep a Changelog format, semver.
- [x] **Automated releases** — Tag-based workflow using `softprops/action-gh-release`.
- [x] **Stale bot** — Issues stale at 60 days, PRs at 30 days, close after 14 days.
- [x] **Enable Discussions** — Enabled on the repo.
- [x] **Semantic versioning** — Enforced via changelog format and tag-based releases.

## P4 — Governance & Scale (When It Matters)

These become important for multi-maintainer or high-traffic projects.

- [ ] **Define maintainer roles** — Clarify who can merge, release, and triage.
- [ ] **Decision-making process** — Use RFCs or ADRs for significant changes.
- [ ] **Public roadmap** — Use a project board or pinned issue so users know where things are headed.
- [ ] **Recognize contributors** — Use the All Contributors bot or shoutouts in release notes.

## Ongoing Habits

These aren't one-time tasks — they're practices to maintain continuously.

- **Respond promptly** — Even a "thanks, we'll look into this" matters.
- **Tag `good first issue`** — Lowers the barrier for new contributors.
- **Triage regularly** — Unresponded issues signal an unmaintained project.
- **Clean up regularly** — Remove dead code, stale branches, and unused workflows.
- **Watch traffic and clones** — Use the Insights tab to understand adoption.
- **Audit third-party Actions** — Pin to commit SHAs, not tags, to mitigate supply chain risk.
- **Subscribe to security advisories** for your dependencies.

---

> The biggest differentiator between well-run and poorly-run public repos is **responsiveness**. Even small projects gain trust when maintainers acknowledge issues and PRs in a timely manner.
