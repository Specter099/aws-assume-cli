"""Tests for aws_assume.cli"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from aws_assume import __version__
from aws_assume.cli import cli
from aws_assume.core import Credentials


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def mock_creds() -> Credentials:
    return Credentials(
        access_key_id="AKIAIOSFODNN7EXAMPLE",
        secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        session_token="AQoXnyc4lcK4w//example/token==",
        expiration="2024-12-31T23:59:59+00:00",
        profile_name="dev",
    )


class TestCLI:
    def test_no_args_shows_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "Usage" in result.output

    def test_version(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_eval_output_default(self, runner: CliRunner, mock_creds: Credentials) -> None:
        with patch("aws_assume.cli.resolve_credentials", return_value=mock_creds):
            result = runner.invoke(cli, ["dev"])
        assert result.exit_code == 0
        assert "export AWS_ACCESS_KEY_ID" in result.output
        assert "export AWS_SECRET_ACCESS_KEY" in result.output
        assert "export AWS_SESSION_TOKEN" in result.output

    def test_json_output(self, runner: CliRunner, mock_creds: Credentials) -> None:
        import json

        with patch("aws_assume.cli.resolve_credentials", return_value=mock_creds):
            result = runner.invoke(cli, ["dev", "--json"])
        assert result.exit_code == 0
        import re

        match = re.search(r"{.*?}", result.output, re.DOTALL)
        assert match, f"No JSON found in output: {result.output!r}"
        data = json.loads(match.group())
        assert data["AccessKeyId"] == "AKIAIOSFODNN7EXAMPLE"

    def test_env_file_output(
        self, runner: CliRunner, mock_creds: Credentials, tmp_path: Path
    ) -> None:
        env_file = tmp_path / ".env"
        with patch("aws_assume.cli.resolve_credentials", return_value=mock_creds):
            result = runner.invoke(cli, ["dev", "--env-file", str(env_file)])
        assert result.exit_code == 0
        content = env_file.read_text()
        assert "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE" in content
        assert '"' not in content  # no quotes in env file

    def test_env_file_permissions(
        self, runner: CliRunner, mock_creds: Credentials, tmp_path: Path
    ) -> None:
        env_file = tmp_path / ".env"
        with patch("aws_assume.cli.resolve_credentials", return_value=mock_creds):
            runner.invoke(cli, ["dev", "--env-file", str(env_file)])
        mode = env_file.stat().st_mode & 0o777
        assert mode == 0o600, f"Expected 0600, got {oct(mode)}"

    def test_env_file_tightens_existing_permissions(
        self, runner: CliRunner, mock_creds: Credentials, tmp_path: Path
    ) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("OLD=1\n")
        env_file.chmod(0o644)
        with patch("aws_assume.cli.resolve_credentials", return_value=mock_creds):
            result = runner.invoke(cli, ["dev", "--env-file", str(env_file)])
        assert result.exit_code == 0
        assert env_file.stat().st_mode & 0o777 == 0o600
        assert "OLD=1" not in env_file.read_text()

    def test_env_file_refuses_symlink(
        self, runner: CliRunner, mock_creds: Credentials, tmp_path: Path
    ) -> None:
        target = tmp_path / "target"
        target.write_text("")
        link = tmp_path / ".env"
        link.symlink_to(target)
        with patch("aws_assume.cli.resolve_credentials", return_value=mock_creds):
            result = runner.invoke(cli, ["dev", "--env-file", str(link)])
        assert result.exit_code == 1
        assert target.read_text() == ""

    def test_invalid_credentials_profile_rejected(self, runner: CliRunner) -> None:
        with patch("aws_assume.cli.resolve_credentials") as resolve:
            result = runner.invoke(
                cli, ["dev", "--credentials", "--credentials-profile", "x]\n[default"]
            )
        assert result.exit_code == 1
        resolve.assert_not_called()

    @pytest.mark.parametrize("name", ["user@example.com", "team/dev", "a:b", "dev+admin"])
    def test_valid_profile_names_accepted(
        self, runner: CliRunner, mock_creds: Credentials, name: str
    ) -> None:
        with patch("aws_assume.cli.resolve_credentials", return_value=mock_creds):
            result = runner.invoke(cli, [name])
        assert result.exit_code == 0

    @pytest.mark.parametrize("name", ["dev\n", "a]b", "[x", "tab\tname"])
    def test_unsafe_profile_names_rejected(self, runner: CliRunner, name: str) -> None:
        with patch("aws_assume.cli.resolve_credentials") as resolve:
            result = runner.invoke(cli, [name])
        assert result.exit_code == 1
        resolve.assert_not_called()

    def test_eval_and_json_are_exclusive(self, runner: CliRunner) -> None:
        with patch("aws_assume.cli.resolve_credentials") as resolve:
            result = runner.invoke(cli, ["dev", "--eval", "--json"])
        assert result.exit_code == 1
        resolve.assert_not_called()

    def test_list_profiles(self, runner: CliRunner) -> None:
        with patch("aws_assume.cli.list_profiles", return_value=["default", "dev", "prod"]):
            result = runner.invoke(cli, ["--list"])
        assert result.exit_code == 0
        assert "dev" in result.output
        assert "prod" in result.output

    def test_unknown_profile_error(self, runner: CliRunner) -> None:
        with patch(
            "aws_assume.cli.resolve_credentials",
            side_effect=ValueError("Profile 'nonexistent' not found"),
        ):
            with patch("aws_assume.cli.list_profiles", return_value=["dev"]):
                result = runner.invoke(cli, ["nonexistent"])
        assert result.exit_code == 1

    def test_invalid_profile_name_rejected(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["profile with spaces"])
        assert result.exit_code == 1
        output = result.output + (result.stderr if hasattr(result, "stderr") else "")
        assert "Invalid profile name" in output

    def test_credentials_file_output(
        self, runner: CliRunner, mock_creds: Credentials, tmp_path: Path
    ) -> None:
        with patch("aws_assume.cli.resolve_credentials", return_value=mock_creds):
            with patch(
                "aws_assume.cli.write_credentials_file", return_value=tmp_path / "credentials"
            ) as mock_write:
                result = runner.invoke(cli, ["dev", "--credentials"])
        assert result.exit_code == 0
        mock_write.assert_called_once_with(mock_creds, profile_name="dev")

    def test_duration_range_validation(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["dev", "--duration", "100"])
        assert result.exit_code != 0  # below minimum of 900
