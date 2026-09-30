"""Tests for the `[llm]` configuration table (ADR-0012, MIL-010 criterion 6)."""

from pathlib import Path

import pytest

from hotel_booking_analysis.adapters.toml_configuration import (
    CONFIG_FILE_NAME,
    TomlConfigurationLoader,
)
from hotel_booking_analysis.application.configuration import (
    AppConfiguration,
    LlmConfiguration,
    LoadedConfiguration,
)
from hotel_booking_analysis.domain.errors import ConfigurationError
from hotel_booking_analysis.domain.llm import ProviderName


def _load(tmp_path: Path, text: str | None, with_llm: bool = True) -> LoadedConfiguration:
    if text is not None:
        (tmp_path / CONFIG_FILE_NAME).write_text(text, encoding="utf-8")
    return TomlConfigurationLoader(tmp_path, {}).load(None, with_llm)


def _llm(tmp_path: Path, body: str) -> LlmConfiguration:
    configuration: AppConfiguration = _load(tmp_path, f"[llm]\n{body}\n").configuration
    return configuration.llm


def _error(tmp_path: Path, body: str) -> ConfigurationError:
    with pytest.raises(ConfigurationError) as error:
        _load(tmp_path, f"[llm]\n{body}\n")
    return error.value


def test_llm_defaults_match_adr_0012_without_a_file(tmp_path: Path) -> None:
    llm = _load(tmp_path, None).configuration.llm

    assert llm == LlmConfiguration(
        ollama_url="http://localhost:11434",
        lmstudio_url="http://localhost:1234",
        discovery_timeout_seconds=2,
        generation_timeout_seconds=120,
        provider=None,
        model=None,
        allow_remote=False,
        temperature=0,
    )
    assert AppConfiguration().llm == llm


def test_llm_defaults_apply_for_an_empty_llm_table(tmp_path: Path) -> None:
    assert _llm(tmp_path, "") == LlmConfiguration()


def test_llm_values_are_read_from_the_table(tmp_path: Path) -> None:
    llm = _llm(
        tmp_path,
        'ollama_url = "http://127.0.0.1:1"\nlmstudio_url = "https://[::1]:2"\n'
        "discovery_timeout_seconds = 0.5\ngeneration_timeout_seconds = 30\n"
        'provider = "lmstudio"\nmodel = "llama3"\nallow_remote = false\ntemperature = 0.7',
    )

    assert llm == LlmConfiguration(
        "http://127.0.0.1:1",
        "https://[::1]:2",
        0.5,
        30.0,
        ProviderName.LMSTUDIO,
        "llama3",
        False,
        0.7,
    )


def test_llm_provider_empty_means_automatic_and_ollama_is_accepted(tmp_path: Path) -> None:
    assert _llm(tmp_path, 'provider = ""').provider is None
    assert _llm(tmp_path, 'provider = "ollama"').provider is ProviderName.OLLAMA


def test_llm_model_empty_means_automatic(tmp_path: Path) -> None:
    assert _llm(tmp_path, 'model = ""').model is None


def test_llm_remote_url_is_accepted_when_allow_remote_is_true(tmp_path: Path) -> None:
    llm = _llm(tmp_path, 'allow_remote = true\nollama_url = "http://gpu.example.com:11434"')

    assert llm.allow_remote is True
    assert llm.ollama_url == "http://gpu.example.com:11434"


def test_temperature_bounds_are_inclusive(tmp_path: Path) -> None:
    assert _llm(tmp_path, "temperature = 1").temperature == 1.0
    assert _llm(tmp_path, "temperature = 0.0").temperature == 0.0


@pytest.mark.parametrize(
    ("body", "key"),
    [
        ('ollama_url = ""', "llm.ollama_url"),
        ('ollama_url = "   "', "llm.ollama_url"),
        ("ollama_url = 5", "llm.ollama_url"),
        ('ollama_url = "ftp://localhost:1"', "llm.ollama_url"),
        ('ollama_url = "localhost:11434"', "llm.ollama_url"),
        ('ollama_url = "http://"', "llm.ollama_url"),
        ('ollama_url = "http://host:notaport"', "llm.ollama_url"),
        ('ollama_url = "http://example.com:11434"', "llm.ollama_url"),
        ('ollama_url = "http://localhost.evil.com"', "llm.ollama_url"),
        ('ollama_url = "http://localhost@evil.com"', "llm.ollama_url"),
        ('ollama_url = "http://192.168.1.5:11434"', "llm.ollama_url"),
        ('lmstudio_url = ""', "llm.lmstudio_url"),
        ('lmstudio_url = "http://example.com:1234"', "llm.lmstudio_url"),
        ('lmstudio_url = "file:///x"', "llm.lmstudio_url"),
        ('discovery_timeout_seconds = "2"', "llm.discovery_timeout_seconds"),
        ("discovery_timeout_seconds = true", "llm.discovery_timeout_seconds"),
        ("discovery_timeout_seconds = 0", "llm.discovery_timeout_seconds"),
        ("discovery_timeout_seconds = -1", "llm.discovery_timeout_seconds"),
        ("discovery_timeout_seconds = inf", "llm.discovery_timeout_seconds"),
        ("discovery_timeout_seconds = nan", "llm.discovery_timeout_seconds"),
        ("discovery_timeout_seconds = [2]", "llm.discovery_timeout_seconds"),
        ('generation_timeout_seconds = "120"', "llm.generation_timeout_seconds"),
        ("generation_timeout_seconds = false", "llm.generation_timeout_seconds"),
        ("generation_timeout_seconds = 0.0", "llm.generation_timeout_seconds"),
        ('provider = "openai"', "llm.provider"),
        ('provider = "Ollama"', "llm.provider"),
        ("provider = 1", "llm.provider"),
        ("model = 3", "llm.model"),
        ('model = " llama3"', "llm.model"),
        ('model = "llama3 "', "llm.model"),
        ('model = " "', "llm.model"),
        ('allow_remote = "true"', "llm.allow_remote"),
        ("allow_remote = 1", "llm.allow_remote"),
        ("temperature = true", "llm.temperature"),
        ('temperature = "0.5"', "llm.temperature"),
        ("temperature = -0.1", "llm.temperature"),
        ("temperature = 1.1", "llm.temperature"),
        ("temperature = 2", "llm.temperature"),
    ],
)
def test_invalid_llm_value_raises_configuration_error_naming_the_key(
    tmp_path: Path, body: str, key: str
) -> None:
    error = _error(tmp_path, body)

    assert error.code == "CONFIGURATION_ERROR"
    assert error.key == key
    assert key in error.message


def test_invalid_allow_remote_is_reported_before_a_remote_url(tmp_path: Path) -> None:
    error = _error(tmp_path, 'allow_remote = "yes"\nollama_url = "http://example.com"')

    assert error.key == "llm.allow_remote"


def test_invalid_llm_values_are_ignored_without_with_llm(tmp_path: Path) -> None:
    text = '[llm]\nollama_url = "http://example.com"\ntemperature = 9\nprovider = 4\n'

    loaded = _load(tmp_path, text, with_llm=False)

    assert loaded.configuration.llm == LlmConfiguration()
    assert loaded.notices == ()


def test_llm_that_is_not_a_table_raises_naming_llm_with_or_without_with_llm(
    tmp_path: Path,
) -> None:
    (tmp_path / CONFIG_FILE_NAME).write_text('llm = "on"\n', encoding="utf-8")
    loader = TomlConfigurationLoader(tmp_path, {})

    for with_llm in (False, True):
        with pytest.raises(ConfigurationError) as error:
            loader.load(None, with_llm)
        assert error.value.key == "llm"


def test_unknown_llm_keys_are_listed_as_llm_dot_key_in_both_modes(tmp_path: Path) -> None:
    text = '[llm]\ntemprature = 0.2\nmodel = "m"\n[other]\nx = 1\n'

    for with_llm in (False, True):
        loaded = _load(tmp_path, text, with_llm)
        (notice,) = loaded.notices
        assert notice.code == "CONFIG_UNKNOWN_KEYS"
        assert notice.message.endswith("llm.temprature, other")


def test_known_llm_table_is_not_reported_as_unknown(tmp_path: Path) -> None:
    assert _load(tmp_path, '[llm]\nmodel = "m"\n').notices == ()


def test_existing_keys_are_unchanged_by_the_llm_table(tmp_path: Path) -> None:
    text = "[history]\nretention = 3\n[analysis]\nmin_group_size = 5\n[llm]\ntemperature = 0.1\n"

    configuration = _load(tmp_path, text).configuration

    assert configuration.retention.limit == 3
    assert configuration.min_group_size == 5
    assert configuration.llm.temperature == 0.1
