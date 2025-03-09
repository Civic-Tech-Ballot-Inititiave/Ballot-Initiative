import pytest
import tomllib
from app.settings_reader import load_ocr_config, OpenAIConfig, MistralAIConfig, GeminiAIConfig

with open("settings.toml.example", "rb") as f:
    test_settings = tomllib.load(f)

def test_load_ocr_config_open_ai():
    test_settings["selected_ocr_engine"] = "open_ai"
    config = load_ocr_config("open_ai", test_settings)
    assert isinstance(config, OpenAIConfig)
    assert config.api_key == "Your OpenAI API key"
    assert config.model == "default"

def test_load_ocr_config_for_mistral():
    test_settings["selected_ocr_engine"] = "mistral_ai"
    config = load_ocr_config("mistral_ai", test_settings) 
    assert isinstance(config, MistralAIConfig)
    assert config.api_key == "Your Mistral API key"
    assert config.model == "default"

def test_load_ocr_config_for_gemini():
    test_settings["selected_ocr_engine"] = "gemini_ai"
    config = load_ocr_config("gemini_ai", test_settings) 
    assert isinstance(config, GeminiAIConfig)
    assert config.api_key == "Your Gemini API key"
    assert config.model == "default"

def test_load_ocr_raise_error_with_invalid_ai_selected():
    test_settings["selected_ocr_engine"] = "invalid_ai"
    with pytest.raises(KeyError) as exc_info:
        load_ocr_config("invalid_ai", test_settings)

    assert "invalid_ai" in str(exc_info.value)

def test_load_ocr_raise_error_with_misconfigured_config():
    test_settings["selected_ocr_engine"] = "invalid_ai"
    test_settings["invalid_ai"] = {"missing_field_stand_in":"value"}
    with pytest.raises(ValueError) as exc_info:
        load_ocr_config("invalid_ai", test_settings)

    assert "Could not find configuration for invalid_ai. Please check your settings file." in str(exc_info.value)
