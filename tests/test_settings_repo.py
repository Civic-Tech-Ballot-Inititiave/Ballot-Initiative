import pytest
from app.settings_repo import GeminiAiConfig, MistralAiConfig, OpenAiConfig, load_settings, SettingsData

def test_open_ai_selected_config():
    settings = load_settings("tests/data/test_settings_open_ai.toml")
    assert settings.selected_config == OpenAiConfig(api_key="Your OpenAI API key", model="default")

def test_gemini_selected_config():
    settings = load_settings("tests/data/test_settings_gemini.toml")
    assert settings.selected_config == GeminiAiConfig(api_key="Your Gemini API key", model="default")

def test_mistral_selected_config():
    settings = load_settings("tests/data/test_settings_mistral.toml")
    assert settings.selected_config == MistralAiConfig(api_key="Your Mistral API key", model="default")

def test_load_ocr_raise_error_with_misconfigured_config():
    with pytest.raises(ValueError) as exc_info:
        load_settings("tests/data/test_settings_invalid.toml")

    assert "Could not find configuration for invalid_selection. Please check your settings file." in str(exc_info.value)
