import pytest
from app.settings import load_settings, OpenAiConfig, MistralAiConfig, GeminiAiConfig


def test_error_when_demo_active_without_genai_variables(monkeypatch):
    monkeypatch.setenv("FEATURE_DEMO_MODE", "true")
    with pytest.raises(ValueError) as exc_info:
        load_settings(reload_settings=True)

    assert (
        "Could not find configuration for None. Please check your settings file."
        in str(exc_info.value)
    )


def test_env_mistral_selected_config(monkeypatch):
    monkeypatch.setenv("FEATURE_DEMO_MODE", "true")
    monkeypatch.setenv("DEMO_GENAI_PROVIDER", "mistral_ai")
    monkeypatch.setenv("DEMO_GENAI_API_KEY", "Your Mistral API key")
    monkeypatch.setenv("DEMO_GENAI_MODEL_NAME", "default")

    settings = load_settings(reload_settings=True)
    assert settings.selected_config == MistralAiConfig(
        api_key="Your Mistral API key", model="default"
    )


def test_env_openai_selected_config(monkeypatch):
    monkeypatch.setenv("FEATURE_DEMO_MODE", "true")
    monkeypatch.setenv("DEMO_GENAI_PROVIDER", "open_ai")
    monkeypatch.setenv("DEMO_GENAI_API_KEY", "Your Open AI API key")
    monkeypatch.setenv("DEMO_GENAI_MODEL_NAME", "default")

    settings = load_settings(reload_settings=True)
    assert settings.selected_config == OpenAiConfig(
        api_key="Your Open AI API key", model="default"
    )


def test_env_gemini_selected_config(monkeypatch):
    monkeypatch.setenv("FEATURE_DEMO_MODE", "true")
    monkeypatch.setenv("DEMO_GENAI_PROVIDER", "gemini_ai")
    monkeypatch.setenv("DEMO_GENAI_API_KEY", "Your Gemini AI API key")
    monkeypatch.setenv("DEMO_GENAI_MODEL_NAME", "default")

    settings = load_settings(reload_settings=True)
    assert settings.selected_config == GeminiAiConfig(
        api_key="Your Gemini AI API key", model="default"
    )


def test_env_debug_mode_enabled(monkeypatch):

    monkeypatch.setenv("ENABLE_DEBUG_MODE", "true")
    monkeypatch.setenv("FEATURE_DEMO_MODE", "true")
    monkeypatch.setenv("DEMO_GENAI_PROVIDER", "gemini_ai")
    monkeypatch.setenv("DEMO_GENAI_API_KEY", "Your Gemini AI API key")
    monkeypatch.setenv("DEMO_GENAI_MODEL_NAME", "default")

    settings = load_settings(reload_settings=True)
    assert settings.debug_mode is True
