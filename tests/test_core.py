"""Tests for aws_assume.core"""

from __future__ import annotations

import configparser
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import TokenRetrievalError

from aws_assume import core
from aws_assume.core import (
    Credentials,
    list_profiles,
    resolve_credentials,
    write_credentials_file,
)


@pytest.fixture
def sample_creds() -> Credentials:
    return Credentials(
        access_key_id="AKIAIOSFODNN7EXAMPLE",
        secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        session_token="AQoXnyc4lcK4w//example/token==",
        expiration="2024-12-31T23:59:59+00:00",
        profile_name="my-profile",
    )


class TestCredentials:
    def test_to_eval(self, sample_creds: Credentials) -> None:
        result = sample_creds.to_eval()
        # shlex.quote() omits quotes for safe strings; adds single-quotes for unsafe ones
        assert "export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE" in result
        assert "export AWS_SECRET_ACCESS_KEY=" in result
        assert "export AWS_SESSION_TOKEN=" in result
        assert "export AWS_ASSUME_PROFILE=my-profile" in result

    def test_to_eval_prevents_shell_injection(self) -> None:
        """Verify shell metacharacters in credential values are safely quoted by shlex."""
        creds = Credentials(
            access_key_id="AKID",
            secret_access_key="SECRET",
            session_token="tok$(whoami)",
            expiration="unknown",
            profile_name="myprofile",
        )
        result = creds.to_eval()
        # The raw $() metacharacter must be wrapped in single-quotes, not left bare
        assert "=$(tok$(whoami))" not in result
        assert "'tok$(whoami)'" in result

    def test_to_eval_no_session_token(self) -> None:
        creds = Credentials(
            access_key_id="AKID",
            secret_access_key="SAK",
            session_token="",
            expiration="unknown",
            profile_name="static",
        )
        result = creds.to_eval()
        assert "AWS_SESSION_TOKEN" not in result
        assert "AWS_ACCESS_KEY_ID" in result

    def test_to_env_file(self, sample_creds: Credentials) -> None:
        result = sample_creds.to_env_file()
        assert "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE" in result
        assert "AWS_SECRET_ACCESS_KEY=" in result
        assert "AWS_SESSION_TOKEN=" in result
        # No quotes in env file format
        assert '"' not in result

    def test_to_env_file_no_session_token(self) -> None:
        creds = Credentials(
            access_key_id="AKID",
            secret_access_key="SAK",
            session_token="",
            expiration="unknown",
            profile_name="static",
        )
        result = creds.to_env_file()
        assert "AWS_SESSION_TOKEN" not in result

    def test_to_json(self, sample_creds: Credentials) -> None:
        import json

        result = json.loads(sample_creds.to_json())
        assert result["AccessKeyId"] == "AKIAIOSFODNN7EXAMPLE"
        assert "SecretAccessKey" in result
        assert "SessionToken" in result
        assert "Expiration" in result

    def test_to_json_no_session_token(self) -> None:
        import json

        creds = Credentials(
            access_key_id="AKID",
            secret_access_key="SAK",
            session_token="",
            expiration="unknown",
            profile_name="static",
        )
        result = json.loads(creds.to_json())
        assert "SessionToken" not in result


class TestListProfiles:
    def test_list_profiles(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config"
        config_file.write_text(
            textwrap.dedent("""\
            [default]
            region = us-east-1

            [profile dev]
            sso_start_url = https://my-sso.awsapps.com/start
            sso_region = us-east-1

            [profile prod]
            role_arn = arn:aws:iam::123456789012:role/Admin
            source_profile = dev
        """)
        )

        with patch("aws_assume.core._get_aws_config_path", return_value=config_file):
            profiles = list_profiles()

        assert "default" in profiles
        assert "dev" in profiles
        assert "prod" in profiles

    def test_list_profiles_missing_file(self, tmp_path: Path) -> None:
        with patch("aws_assume.core._get_aws_config_path", return_value=tmp_path / "nonexistent"):
            profiles = list_profiles()
        assert profiles == []


class TestWriteCredentialsFile:
    def test_write_new_file(self, tmp_path: Path, sample_creds: Credentials) -> None:
        creds_file = tmp_path / "credentials"
        with patch("aws_assume.core._get_aws_credentials_path", return_value=creds_file):
            path = write_credentials_file(sample_creds, profile_name="dev")

        assert path == creds_file
        config = configparser.ConfigParser()
        config.read(creds_file)
        assert "dev" in config
        assert config["dev"]["aws_access_key_id"] == "AKIAIOSFODNN7EXAMPLE"

    def test_write_enforces_0600_permissions(
        self, tmp_path: Path, sample_creds: Credentials
    ) -> None:
        creds_file = tmp_path / "credentials"
        with patch("aws_assume.core._get_aws_credentials_path", return_value=creds_file):
            write_credentials_file(sample_creds, profile_name="dev")
        mode = creds_file.stat().st_mode & 0o777
        assert mode == 0o600, f"Expected 0600, got {oct(mode)}"

    def test_write_preserves_existing_profiles(
        self, tmp_path: Path, sample_creds: Credentials
    ) -> None:
        creds_file = tmp_path / "credentials"
        creds_file.write_text(
            textwrap.dedent("""\
            [existing-profile]
            aws_access_key_id = EXISTINGKEY
            aws_secret_access_key = EXISTINGSECRET
        """)
        )

        with patch("aws_assume.core._get_aws_credentials_path", return_value=creds_file):
            write_credentials_file(sample_creds, profile_name="new-profile")

        config = configparser.ConfigParser()
        config.read(creds_file)
        assert "existing-profile" in config
        assert "new-profile" in config
        assert config["existing-profile"]["aws_access_key_id"] == "EXISTINGKEY"

    def test_write_preserves_comments_and_replaces_in_place(
        self, tmp_path: Path, sample_creds: Credentials
    ) -> None:
        creds_file = tmp_path / "credentials"
        creds_file.write_text(
            textwrap.dedent("""\
            # personal keys, do not delete
            [personal]
            aws_access_key_id = PERSONALKEY
            aws_secret_access_key = PERSONALSECRET

            [dev]
            # note about dev
            aws_access_key_id = OLDKEY
            aws_secret_access_key = OLDSECRET
            aws_session_token = OLDTOKEN

            [other]
            aws_access_key_id = OTHERKEY
        """)
        )
        with patch("aws_assume.core._get_aws_credentials_path", return_value=creds_file):
            write_credentials_file(sample_creds, profile_name="dev")

        text = creds_file.read_text()
        assert "# personal keys, do not delete" in text
        assert "# note about dev" in text
        assert "OLD" not in text
        assert text.index("[personal]") < text.index("[dev]") < text.index("[other]")
        config = configparser.RawConfigParser()
        config.read(creds_file)
        assert config["dev"]["aws_access_key_id"] == "AKIAIOSFODNN7EXAMPLE"
        assert config["dev"]["aws_session_token"] == sample_creds.session_token
        assert config["other"]["aws_access_key_id"] == "OTHERKEY"

    def test_write_without_session_token_drops_stale_token(self, tmp_path: Path) -> None:
        creds_file = tmp_path / "credentials"
        creds_file.write_text("[dev]\naws_access_key_id = A\naws_session_token = STALE\n")
        static = Credentials("AKID", "SAK", "", "unknown", "dev")
        with patch("aws_assume.core._get_aws_credentials_path", return_value=creds_file):
            write_credentials_file(static, profile_name="dev")
        assert "STALE" not in creds_file.read_text()


def _write_config(tmp_path: Path, body: str) -> Path:
    config_file = tmp_path / "config"
    config_file.write_text(textwrap.dedent(body))
    return config_file


class TestSessionCredentials:
    def test_reports_credential_expiry(self) -> None:
        expiry = datetime(2030, 1, 1, tzinfo=timezone.utc)
        credentials = MagicMock(_expiry_time=expiry)
        credentials.get_frozen_credentials.return_value = MagicMock(
            access_key="AKID", secret_key="SAK", token="TOK"
        )
        with patch("aws_assume.core.boto3.Session") as session:
            session.return_value.get_credentials.return_value = credentials
            creds = core._session_credentials("dev")
        assert creds.expiration == "2030-01-01T00:00:00+00:00"

    def test_static_credentials_have_unknown_expiry(self) -> None:
        credentials = MagicMock(spec=["get_frozen_credentials"])
        credentials.get_frozen_credentials.return_value = MagicMock(
            access_key="AKID", secret_key="SAK", token=None
        )
        with patch("aws_assume.core.boto3.Session") as session:
            session.return_value.get_credentials.return_value = credentials
            creds = core._session_credentials("dev")
        assert creds.expiration == "unknown"
        assert creds.session_token == ""

    def test_no_credentials(self) -> None:
        with patch("aws_assume.core.boto3.Session") as session:
            session.return_value.get_credentials.return_value = None
            with pytest.raises(RuntimeError, match="Failed to resolve credentials"):
                core._resolve_boto3_credentials("dev")


class TestResolveCredentials:
    def test_role_without_source_profile_uses_boto3(self, tmp_path: Path) -> None:
        """credential_source profiles must not silently fall back to the default profile."""
        config_file = _write_config(
            tmp_path,
            """\
            [profile ec2-role]
            role_arn = arn:aws:iam::123456789012:role/Admin
            credential_source = Ec2InstanceMetadata
            """,
        )
        with (
            patch("aws_assume.core._get_aws_config_path", return_value=config_file),
            patch("aws_assume.core._resolve_boto3_credentials") as boto3_path,
            patch("aws_assume.core._resolve_role_credentials") as role_path,
        ):
            resolve_credentials("ec2-role")
        boto3_path.assert_called_once_with("ec2-role")
        role_path.assert_not_called()

    def test_cycle_detection(self, tmp_path: Path) -> None:
        config_file = _write_config(
            tmp_path,
            """\
            [profile a]
            role_arn = arn:aws:iam::123456789012:role/A
            source_profile = b

            [profile b]
            role_arn = arn:aws:iam::123456789012:role/B
            source_profile = a
            """,
        )
        with patch("aws_assume.core._get_aws_config_path", return_value=config_file):
            with pytest.raises(ValueError, match="cycle"):
                resolve_credentials("a")

    def test_role_session_name_within_sts_limit(self, tmp_path: Path) -> None:
        long_name = "p" * 80
        config_file = _write_config(
            tmp_path,
            f"""\
            [profile {long_name}]
            role_arn = arn:aws:iam::123456789012:role/A
            source_profile = src

            [profile src]
            region = us-east-1
            """,
        )
        source = Credentials("AKID", "SAK", "", "unknown", "src")
        sts = MagicMock()
        sts.assume_role.return_value = {
            "Credentials": {
                "AccessKeyId": "A",
                "SecretAccessKey": "S",
                "SessionToken": "T",
                "Expiration": MagicMock(isoformat=lambda: "2030-01-01T00:00:00+00:00"),
            }
        }
        with (
            patch("aws_assume.core._get_aws_config_path", return_value=config_file),
            patch("aws_assume.core._resolve_boto3_credentials", return_value=source),
            patch("aws_assume.core.boto3.client", return_value=sts),
        ):
            resolve_credentials(long_name)
        session_name = sts.assume_role.call_args.kwargs["RoleSessionName"]
        assert 2 <= len(session_name) <= 64


class TestSsoLogin:
    def test_login_output_goes_to_stderr(self) -> None:
        """aws sso login output must not land on stdout, where eval would execute it."""
        with patch("aws_assume.core.subprocess.run") as run:
            run.return_value.returncode = 0
            core._trigger_sso_login("dev")
        assert run.call_args.kwargs["stdout"] is sys.stderr

    def test_missing_aws_cli(self) -> None:
        with patch("aws_assume.core.subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError, match="AWS CLI not found"):
                core._trigger_sso_login("dev")

    def test_expired_token_triggers_login_then_retries(self) -> None:
        frozen = MagicMock(access_key="AKID", secret_key="SAK", token="TOK")
        session = MagicMock()
        session.get_credentials.side_effect = [
            TokenRetrievalError(provider="sso", error_msg="expired"),
            MagicMock(get_frozen_credentials=MagicMock(return_value=frozen), _expiry_time=None),
        ]
        with (
            patch("aws_assume.core.boto3.Session", return_value=session),
            patch("aws_assume.core._trigger_sso_login") as login,
        ):
            creds = core._resolve_sso_credentials("dev", auto_login=True)
        login.assert_called_once_with("dev")
        assert creds.session_token == "TOK"

    def test_no_auto_login_raises(self) -> None:
        session = MagicMock()
        session.get_credentials.side_effect = TokenRetrievalError(provider="sso", error_msg="x")
        with (
            patch("aws_assume.core.boto3.Session", return_value=session),
            patch("aws_assume.core._trigger_sso_login") as login,
        ):
            with pytest.raises(RuntimeError, match="Failed to resolve SSO credentials"):
                core._resolve_sso_credentials("dev", auto_login=False)
        login.assert_not_called()
