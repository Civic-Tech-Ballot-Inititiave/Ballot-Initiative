import pytest
import tomllib

# We're using the example file as our test input
with open("settings.toml.example", "rb") as f:
    settings = tomllib.load(f)


def test_selected_ocr_engine():
    assert settings["selected_ocr_engine"] == "open_ai"


def test_open_ai_api_key():
    assert settings["open_ai"]["api_key"] == "Your OpenAI API key"


def test_open_ai_model_selection():
    assert settings["open_ai"]["model"] == "default"


def test_mistral_api_key():
    assert settings["mistral_ai"]["api_key"] == "Your Mistral API key"


def test_mistral_model_selection():
    assert settings["mistral_ai"]["model"] == "default"


def test_gemini_api_key():
    assert settings["gemini_ai"]["api_key"] == "Your Gemini API key"


def test_gemini_model_selection():
    assert settings["gemini_ai"]["model"] == "default"
