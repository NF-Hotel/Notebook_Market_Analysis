"""Tests for the configuration loader (ADR-0004, US-001.09)."""

from pathlib import Path

import pytest

from hotel_booking_analysis.adapters.toml_configuration import (
    CONFIG_ENV_VAR,
    CONFIG_FILE_NAME,
    TomlConfigurationLoader,
)
from hotel_booking_analysis.application.configuration import Environment
from hotel_booking_analysis.domain.errors import ConfigurationError


def _loader(tmp_path: Path, environ: dict[str, str] | None = None) -> TomlConfigurationLoader:
    return TomlConfigurationLoader(tmp_path, environ or {})


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _config_error(tmp_path: Path, text: str) -> ConfigurationError:
    _write(tmp_path / CONFIG_FILE_NAME, text)
    with pytest.raises(ConfigurationError) as error:
        _loader(tmp_path).load(None)
    return error.value


def test_missing_file_gives_defaults_and_a_notice(tmp_path: Path) -> None:
    loaded = _loader(tmp_path).load(None)

    config = loaded.configuration
    assert config.retention.limit == 10
    assert config.environment is Environment.PRODUCTION
    assert config.history_path == Path("output/analysis_history.jsonl")
    assert config.holiday_windows_days == (1, 3, 7)
    assert config.min_group_size == 30
    assert [n.code for n in loaded.notices] == ["CONFIG_FILE_NOT_FOUND"]


def test_empty_file_gives_defaults_without_notices(tmp_path: Path) -> None:
    _write(tmp_path / CONFIG_FILE_NAME, "")

    loaded = _loader(tmp_path).load(None)

    assert loaded.configuration.retention.limit == 10
    assert loaded.notices == ()


def test_full_file_values_are_applied(tmp_path: Path) -> None:
    _write(
        tmp_path / CONFIG_FILE_NAME,
        'environment = "development"\n'
        '[history]\nretention = 3\npath = "out/h.jsonl"\n'
        "[analysis]\nholiday_windows_days = [2, 5]\nmin_group_size = 5\n",
    )

    config = _loader(tmp_path).load(None).configuration

    assert config.environment is Environment.DEVELOPMENT
    assert config.retention.limit == 3
    assert config.history_path == Path("out/h.jsonl")
    assert config.holiday_windows_days == (2, 5)
    assert config.min_group_size == 5


def test_omitted_retention_defaults_to_ten_when_other_keys_are_set(tmp_path: Path) -> None:
    _write(tmp_path / CONFIG_FILE_NAME, '[history]\npath = "h.jsonl"\n')

    assert _loader(tmp_path).load(None).configuration.retention.limit == 10


def test_explicit_option_wins_over_environment_variable_and_working_directory(
    tmp_path: Path,
) -> None:
    _write(tmp_path / CONFIG_FILE_NAME, "[history]\nretention = 1\n")
    env_file = _write(tmp_path / "env.toml", "[history]\nretention = 2\n")
    option_file = _write(tmp_path / "option.toml", "[history]\nretention = 3\n")
    loader = _loader(tmp_path, {CONFIG_ENV_VAR: str(env_file)})

    assert loader.load(option_file).configuration.retention.limit == 3
    assert loader.load(None).configuration.retention.limit == 2


def test_working_directory_file_is_used_without_option_or_variable(tmp_path: Path) -> None:
    _write(tmp_path / CONFIG_FILE_NAME, "[history]\nretention = 4\n")

    assert _loader(tmp_path).load(None).configuration.retention.limit == 4


def test_missing_explicit_file_gives_defaults_and_a_notice(tmp_path: Path) -> None:
    loaded = _loader(tmp_path).load(tmp_path / "nope.toml")

    assert loaded.configuration.retention.limit == 10
    assert loaded.notices[0].code == "CONFIG_FILE_NOT_FOUND"


@pytest.mark.parametrize("value", ["0", "-1", "2.5", '"5"', "true", "false", "[1]"])
def test_invalid_retention_is_a_configuration_error_naming_the_key(
    tmp_path: Path, value: str
) -> None:
    error = _config_error(tmp_path, f"[history]\nretention = {value}\n")

    assert error.key == "history.retention"
    assert "history.retention" in error.message


@pytest.mark.parametrize(
    "value", ["[]", "[0]", "[1, 1]", "[1, 2.5]", '["3"]', "[true]", "3", "[-1]"]
)
def test_invalid_holiday_windows_are_rejected(tmp_path: Path, value: str) -> None:
    error = _config_error(tmp_path, f"[analysis]\nholiday_windows_days = {value}\n")

    assert error.key == "analysis.holiday_windows_days"


@pytest.mark.parametrize("value", ["0", "-5", "1.5", '"30"', "true"])
def test_invalid_min_group_size_is_rejected(tmp_path: Path, value: str) -> None:
    error = _config_error(tmp_path, f"[analysis]\nmin_group_size = {value}\n")

    assert error.key == "analysis.min_group_size"


@pytest.mark.parametrize("value", ['"staging"', "1", "true", '"Production"'])
def test_invalid_environment_is_rejected(tmp_path: Path, value: str) -> None:
    error = _config_error(tmp_path, f"environment = {value}\n")

    assert error.key == "environment"


@pytest.mark.parametrize("value", ['""', "5", "true"])
def test_invalid_history_path_is_rejected(tmp_path: Path, value: str) -> None:
    error = _config_error(tmp_path, f"[history]\npath = {value}\n")

    assert error.key == "history.path"


def test_section_that_is_not_a_table_is_rejected(tmp_path: Path) -> None:
    error = _config_error(tmp_path, "history = 5\n")

    assert error.key == "history"


def test_unparsable_file_is_a_configuration_error(tmp_path: Path) -> None:
    error = _config_error(tmp_path, "[history\nretention = ")

    assert error.code == "CONFIGURATION_ERROR"
    assert CONFIG_FILE_NAME in error.message


def test_unknown_keys_are_ignored_and_listed_in_one_notice(tmp_path: Path) -> None:
    _write(
        tmp_path / CONFIG_FILE_NAME,
        'colour = "red"\n[history]\nretention = 2\nfoo = 1\n[extra]\nx = 1\n',
    )

    loaded = _loader(tmp_path).load(None)

    assert loaded.configuration.retention.limit == 2
    assert len(loaded.notices) == 1
    notice = loaded.notices[0]
    assert notice.code == "CONFIG_UNKNOWN_KEYS"
    for key in ("colour", "history.foo", "extra"):
        assert key in notice.message
