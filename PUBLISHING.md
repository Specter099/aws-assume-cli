# Publishing to PyPI

## Automated Publishing (GitHub Actions)

Releases are automatically published to PyPI when you create a GitHub release.

### One-time setup

1. Go to [pypi.org](https://pypi.org/account/register/) and create an account (or log in).

2. Create a PyPI project for `aws-assume-cli` by doing a manual upload first (see [Manual Publishing](#manual-publishing) below), or reserve the name.

3. Configure Trusted Publishing on **PyPI**:
   - Go to [pypi.org](https://pypi.org) > your project > **Settings** > **Publishing**
   - Add a new **GitHub** publisher:
     - **Owner**: `Specter099`
     - **Repository**: `aws-assume-cli`
     - **Workflow name**: `publish.yml`
     - **Environment name**: `pypi`

4. Create a GitHub environment:
   - Go to your repo **Settings** > **Environments**
   - Create an environment named `pypi`
     - Add a required reviewer for production safety
     - Optionally restrict deployment branches to tags only

### Creating a release

1. Update the version in `pyproject.toml`:
   ```toml
   version = "0.2.0"
   ```

2. Commit and push the version bump.

3. Create a GitHub release:
   ```bash
   gh release create v0.2.0 --title "v0.2.0" --generate-notes
   ```

   Or use the GitHub UI: **Releases** > **Draft a new release** > create a tag like `v0.2.0`.

4. The GitHub Action will automatically build and publish to PyPI.

## Manual Publishing

If you need to publish manually (e.g., for the first upload):

1. Install build tools:
   ```bash
   pipx install build twine
   ```

2. Build the package:
   ```bash
   python -m build
   ```

3. Upload to PyPI:
   ```bash
   twine upload dist/*
   ```
   - Username: `__token__`
   - Password: your PyPI API token

### Testing with TestPyPI

The release workflow publishes only to PyPI. To test without affecting the real package index:

1. Create an account at [test.pypi.org](https://test.pypi.org/account/register/).

2. Upload to TestPyPI:
   ```bash
   twine upload --repository testpypi dist/*
   ```

3. Test the install:
   ```bash
   pipx install --pip-args="--index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/" aws-assume-cli
   ```

## Versioning

This project uses [semantic versioning](https://semver.org/):

- **Patch** (0.1.x): Bug fixes, no new features
- **Minor** (0.x.0): New features, backwards compatible
- **Major** (x.0.0): Breaking changes
