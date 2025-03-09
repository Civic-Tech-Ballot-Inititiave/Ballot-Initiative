import tomllib
import os
from dataclasses import dataclass
from typing import Any

@dataclass
class OpenAIConfig:
    api_key: str
    model: str

@dataclass
class MistralAIConfig:
    api_key: str
    model: str

@dataclass
class GeminiAIConfig:
    api_key: str
    model: str

def load_ocr_config(settings_path: str, custom_settings_override: dict[str, Any] = None) -> OpenAIConfig | MistralAIConfig | GeminiAIConfig:
    """
    Load the configuration file from the root directory.

    Args:
        settings_path: The path to the settings file.
        custom_settings: A dictionary with custom settings to use instead of the settings file. For Testing only.

    Returns:
        Config: A container with the configuration settings of a particular OCR engine.
    """

    selected_engine = None
    engine_config = None

    if custom_settings_override:
        selected_engine = custom_settings_override["selected_ocr_engine"]
        engine_config = custom_settings_override[selected_engine]
    else:
        with open(settings_path, "rb") as f:
            settings = tomllib.load(f)
            selected_engine = settings["selected_ocr_engine"]
            engine_config = settings[selected_engine]

    match selected_engine:
        case "open_ai":
            return OpenAIConfig(api_key=engine_config["api_key"], model=engine_config["model"])
        case "mistral_ai":
            return MistralAIConfig(api_key=engine_config["api_key"], model=engine_config["model"])
        case "gemini_ai":
            return GeminiAIConfig(api_key=engine_config["api_key"], model=engine_config["model"])
        case _:
            raise ValueError(f"Could not find configuration for {selected_engine}. Please check your settings file.")