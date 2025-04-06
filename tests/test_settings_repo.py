import pytest
from app.settings import load_settings, OpenAiConfig, MistralAiConfig, GeminiAiConfig


def test_open_ai_selected_config():
    settings = load_settings(
        "tests/data/test_settings_open_ai.toml", reload_settings=True
    )
    assert settings.selected_config == OpenAiConfig(
        api_key="Your OpenAI API key", model="default"
    )


def test_gemini_selected_config():
    settings = load_settings(
        "tests/data/test_settings_gemini.toml", reload_settings=True
    )
    assert settings.selected_config == GeminiAiConfig(
        api_key="Your Gemini API key", model="default"
    )


def test_mistral_selected_config():
    settings = load_settings(
        "tests/data/test_settings_mistral.toml", reload_settings=True
    )
    assert settings.selected_config == MistralAiConfig(
        api_key="Your Mistral API key", model="default"
    )


def test_load_ocr_raise_error_with_misconfigured_config():
    with pytest.raises(ValueError) as exc_info:
        load_settings("tests/data/test_settings_invalid.toml", reload_settings=True)

    assert (
        "Could not find configuration for invalid_selection. Please check your settings file."
        in str(exc_info.value)
    )


def test_load_settings_with_debug_mode_enabled():
    settings = load_settings(
        "tests/data/test_settings_debug_enabled.toml", reload_settings=True
    )
    assert settings.debug_mode is True


def test_load_settings_with_debug_mode_not_enabled():
    settings = load_settings(
        "tests/data/test_settings_default.toml", reload_settings=True
    )
    assert settings.debug_mode is False


def test_return_same_settings_if_no_reload():
    settings = load_settings(
        "tests/data/test_settings_default.toml", reload_settings=True
    )
    second_settings = load_settings("tests/data/test_settings_invalid.toml")
    assert settings == second_settings
