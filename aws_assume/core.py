"""Core logic for resolving AWS SSO credentials and assuming roles."""

from __future__ import annotations

import configparser
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, TokenRetrievalError


@dataclass
class Credentials:
    access_key_id: str
    secret_access_key: str
    session_token: str  # empty string means no session token (static credentials)
    expiration: str
    profile_name: str

    def to_eval(self) -> str:
        """Return shell export statements for eval, safely quoted with shlex."""
        lines = [
            f"export AWS_ACCESS_KEY_ID={shlex.quote(self.access_key_id)}",
            f"export AWS_SECRET_ACCESS_KEY={shlex.quote(self.secret_access_key)}",
        ]
        if self.session_token:
            lines.append(f"export AWS_SESSION_TOKEN={shlex.quote(self.session_token)}")
        lines += [
            f"export AWS_ASSUME_PROFILE={shlex.quote(self.profile_name)}",
            f"export AWS_ASSUME_EXPIRATION={shlex.quote(self.expiration)}",
        ]
        return "\n".join(lines)

    def to_env_file(self) -> str:
        """Return Docker-style .env file content."""
        lines = [
            f"AWS_ACCESS_KEY_ID={self.access_key_id}",
            f"AWS_SECRET_ACCESS_KEY={self.secret_access_key}",
        ]
        if self.session_token:
            lines.append(f"AWS_SESSION_TOKEN={self.session_token}")
        return "\n".join(lines)

    def to_json(self) -> str:
        data: dict[str, str] = {
            "AccessKeyId": self.access_key_id,
            "SecretAccessKey": self.secret_access_key,
            "Expiration": self.expiration,
        }
        if self.session_token:
            data["SessionToken"] = self.session_token
        return json.dumps(data, indent=2)


def _get_aws_config_path() -> Path:
    return Path(os.environ.get("AWS_CONFIG_FILE", "~/.aws/config")).expanduser()


def _get_aws_credentials_path() -> Path:
    return Path(os.environ.get("AWS_SHARED_CREDENTIALS_FILE", "~/.aws/credentials")).expanduser()


def list_profiles() -> list[str]:
    """Return all profile names from ~/.aws/config."""
    config_path = _get_aws_config_path()
    if not config_path.exists():
        return []

    config = configparser.RawConfigParser()
    config.read(config_path)

    profiles = []
    for section in config.sections():
        if section == "default":
            profiles.append("default")
        elif section.startswith("profile "):
            profiles.append(section[len("profile ") :])
    return sorted(profiles)


def _get_profile_config(profile_name: str) -> dict[str, str]:
    """Read a profile's config from ~/.aws/config."""
    config_path = _get_aws_config_path()
    config = configparser.RawConfigParser()
    config.read(config_path)

    section = "default" if profile_name == "default" else f"profile {profile_name}"
    if section not in config:
        raise ValueError(f"Profile '{profile_name}' not found in {config_path}")

    return dict(config[section])


def _trigger_sso_login(profile_name: str) -> None:
    """Run aws sso login for the given profile."""
    sys.stderr.write(
        f"SSO session expired or missing. Logging in for profile '{profile_name}'...\n"
    )
    # Send the aws CLI's output to stderr: stdout is captured by `eval $(aws-assume ...)`.
    try:
        result = subprocess.run(
            ["aws", "sso", "login", "--profile", profile_name],
            stdout=sys.stderr,
            check=False,
        )
    except FileNotFoundError as e:
        raise RuntimeError("AWS CLI not found on PATH; it is required for 'aws sso login'") from e
    if result.returncode != 0:
        raise RuntimeError(f"SSO login failed for profile '{profile_name}'")


def resolve_credentials(
    profile_name: str,
    duration_seconds: int | None = None,
    auto_login: bool = True,
    _seen: frozenset[str] | None = None,
) -> Credentials:
    """
    Resolve credentials for a profile, handling SSO login if needed.

    Supports:
      - SSO profiles (sso_start_url + sso_role_name)
      - Role-assumption profiles (role_arn + source_profile)
      - SSO + role chaining (sso source_profile + role_arn)
    """
    if _seen is None:
        _seen = frozenset()
    if profile_name in _seen:
        raise ValueError(f"Credential chain cycle detected involving profile '{profile_name}'")
    _seen = _seen | {profile_name}

    profile_config = _get_profile_config(profile_name)

    has_sso = "sso_start_url" in profile_config or "sso_session" in profile_config
    has_role_arn = "role_arn" in profile_config and "source_profile" in profile_config

    if has_sso and not has_role_arn:
        return _resolve_sso_credentials(profile_name, auto_login)
    elif has_role_arn:
        return _resolve_role_credentials(
            profile_name, profile_config, duration_seconds, auto_login, _seen
        )
    else:
        return _resolve_boto3_credentials(profile_name)


def _resolve_sso_credentials(profile_name: str, auto_login: bool) -> Credentials:
    """Resolve credentials from an SSO profile."""
    try:
        return _session_credentials(profile_name)
    except (TokenRetrievalError, ClientError) as e:
        if not (auto_login and _is_sso_error(e)):
            raise RuntimeError(f"Failed to resolve SSO credentials: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to resolve SSO credentials: {e}") from e

    _trigger_sso_login(profile_name)
    try:
        return _session_credentials(profile_name)
    except Exception as e:
        raise RuntimeError(f"Failed to resolve SSO credentials after login: {e}") from e


def _resolve_role_credentials(
    profile_name: str,
    profile_config: dict[str, str],
    duration_seconds: int | None,
    auto_login: bool,
    _seen: frozenset[str],
) -> Credentials:
    """Resolve credentials by assuming a role, using source_profile as the base."""
    role_arn = profile_config["role_arn"]
    source_profile = profile_config["source_profile"]

    # Sanitize profile_name for RoleSessionName (STS constraint: [\w+=,.@-]{2,64})
    safe_name = re.sub(r"[^\w+=,.@-]", "-", profile_name)[:40]
    role_session_name = profile_config.get(
        "role_session_name",
        f"aws-assume-{safe_name}-{int(time.time())}",
    )
    external_id = profile_config.get("external_id")

    source_creds = resolve_credentials(source_profile, auto_login=auto_login, _seen=_seen)

    sts = boto3.client(
        "sts",
        aws_access_key_id=source_creds.access_key_id,
        aws_secret_access_key=source_creds.secret_access_key,
        aws_session_token=source_creds.session_token or None,
    )

    assume_kwargs: dict[str, object] = {
        "RoleArn": role_arn,
        "RoleSessionName": role_session_name,
    }
    if duration_seconds is not None:
        assume_kwargs["DurationSeconds"] = duration_seconds
    if external_id:
        assume_kwargs["ExternalId"] = external_id

    try:
        response = sts.assume_role(**assume_kwargs)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "Unknown")
        raise RuntimeError(f"Failed to assume role: {code}") from e

    creds = response["Credentials"]
    return Credentials(
        access_key_id=creds["AccessKeyId"],
        secret_access_key=creds["SecretAccessKey"],
        session_token=creds["SessionToken"],
        expiration=creds["Expiration"].isoformat(),
        profile_name=profile_name,
    )


def _resolve_boto3_credentials(profile_name: str) -> Credentials:
    """Fallback: resolve via boto3 session directly."""
    try:
        return _session_credentials(profile_name)
    except Exception as e:
        raise RuntimeError(
            f"Failed to resolve credentials for profile '{profile_name}': {e}"
        ) from e


def _session_credentials(profile_name: str) -> Credentials:
    """Resolve credentials through a boto3 session for the profile."""
    credentials = boto3.Session(profile_name=profile_name).get_credentials()
    if credentials is None:
        raise RuntimeError(f"No credentials found for profile '{profile_name}'")
    frozen = credentials.get_frozen_credentials()
    # botocore exposes the expiry of refreshable (SSO, role, IMDS) credentials only via this
    # private attribute; static credentials have none.
    expiry = getattr(credentials, "_expiry_time", None)
    return Credentials(
        access_key_id=frozen.access_key,
        secret_access_key=frozen.secret_key,
        session_token=frozen.token or "",
        expiration=expiry.isoformat() if isinstance(expiry, datetime) else "unknown",
        profile_name=profile_name,
    )


def _is_sso_error(e: Exception) -> bool:
    """Check if the exception is an SSO token expiry error."""
    if isinstance(e, TokenRetrievalError):
        return True
    if isinstance(e, ClientError):
        code = e.response.get("Error", {}).get("Code", "")
        return code in ("UnauthorizedException", "ExpiredTokenException")
    return False


_SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")


def _replace_section(text: str, name: str, block: list[str]) -> str:
    """Replace (or append) an INI section, leaving every other line untouched.

    Comments and blank lines inside the replaced section are kept; its key lines are dropped.
    """
    out: list[str] = []
    in_target = replaced = False
    for line in text.splitlines():
        match = _SECTION_RE.match(line)
        if match:
            in_target = match.group(1).strip() == name
            if in_target:
                if not replaced:
                    out.extend(block)
                    replaced = True
                continue
        elif in_target and line.strip() and not line.lstrip().startswith(("#", ";")):
            continue
        out.append(line)
    if not replaced:
        if out and out[-1].strip():
            out.append("")
        out.extend(block)
    return "\n".join(out) + "\n"


def write_credentials_file(creds: Credentials, profile_name: str = "default") -> Path:
    """Write credentials to ~/.aws/credentials under the given profile name.

    Other profiles, comments, and formatting in the file are preserved.
    """
    creds_path = _get_aws_credentials_path()
    creds_path.parent.mkdir(parents=True, exist_ok=True)
    existing = creds_path.read_text() if creds_path.exists() else ""

    block = [
        f"[{profile_name}]",
        f"aws_access_key_id = {creds.access_key_id}",
        f"aws_secret_access_key = {creds.secret_access_key}",
    ]
    if creds.session_token:
        block.append(f"aws_session_token = {creds.session_token}")

    # Write to a temp file (mkstemp creates it 0600), then atomically replace the target
    tmp_fd, tmp_name = tempfile.mkstemp(dir=creds_path.parent, prefix=".aws-assume-")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            f.write(_replace_section(existing, profile_name, block))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, creds_path)
    except Exception:
        Path(tmp_name).unlink(missing_ok=True)
        raise

    return creds_path
