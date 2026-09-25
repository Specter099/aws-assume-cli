"""AWS assume - CLI for AWS SSO credential management."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("aws-assume-cli")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0"
