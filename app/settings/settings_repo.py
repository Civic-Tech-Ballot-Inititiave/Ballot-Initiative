from typing import Optional
import os
from feature_flags import FeatureFlags
import tomllib
import pathlib
from dataclasses import dataclass
from utils import (
    enable_debug_logging,
    logger,
)

config = {"BASE_THRESHOLD": 85, "TOP_CROP": 0.385, "BOTTOM_CROP": 0.725}


@dataclass
class OpenAiConfig:
    api_key: str
    model: str


@dataclass
class MistralAiConfig:
    api_key: str
    model: str


@dataclass
class GeminiAiConfig:
    api_key: str
    model: str


@dataclass
class SettingsData:
    selected_config: OpenAiConfig | MistralAiConfig | GeminiAiConfig
    debug_mode: bool = False


_current_settings: Optional[SettingsData] = None


def __load_settings_file(custom_path: str = None) -> dict:
    """
    Load settings from a TOML file and return the settings dictionary.

    Args:
        custom_path (str): Path to the TOML file. Defaults to "settings.toml" if not provided.

    Returns:
        dict: Settings loaded from the TOML file.
    """
    path = "./settings.toml"
    if custom_path:
        path = custom_path

    file = pathlib.Path(path)

    with open(file, "rb") as f:
        settings = tomllib.load(f)

    return settings


def load_settings(
    custom_path: str = None, reload_settings: bool = False
) -> SettingsData:
    """
    Load settings from a TOML file and return the selected OCR engine configuration.


    Args:
        custom_path (str): Path to the TOML file. Defaults to "settings.toml" if not provided.

    Returns:
        SettingsData: Container for application including the selected OCR engine configuration.

    Raises:
        ValueError: If the selected engine is not found in the settings file.
    """

    # If settings are already loaded and reload is not requested, return the current settings
    global _current_settings

    if (_current_settings) and (not reload_settings):
        return _current_settings

    selected_engine: str
    model: str
    api_key: str
    is_debug_mode: bool = os.getenv("ENABLE_DEBUG_MODE", "false").lower() == "true"
    feature_flags = FeatureFlags()

    if feature_flags.demo_mode:
        selected_engine = os.getenv("DEMO_GENAI_PROVIDER")
        api_key = os.getenv("DEMO_GENAI_API_KEY")
        model = os.getenv("DEMO_GENAI_MODEL_NAME")
    else:
        # If custom path is provided, use it
        path = "./settings.toml"
        if custom_path:
            path = custom_path

        # Load settings from the TOML file
        settings = __load_settings_file(path)
        selected_engine = settings["selected_ocr_engine"]
        api_key = settings.get(selected_engine, {}).get("api_key", "")
        model = settings.get(selected_engine, {}).get("model", "")
        is_debug_mode = settings.get("debug_mode", False)

    enable_debug_logging(is_debug_mode)

    match selected_engine:
        case "open_ai":
            _current_settings = SettingsData(
                selected_config=OpenAiConfig(
                    api_key=api_key,
                    model=model,
                )
            )
        case "mistral_ai":
            _current_settings = SettingsData(
                selected_config=MistralAiConfig(
                    api_key=api_key,
                    model=model,
                )
            )
        case "gemini_ai":
            _current_settings = SettingsData(
                selected_config=GeminiAiConfig(
                    api_key=api_key,
                    model=model,
                )
            )
        case _:
            raise ValueError(
                f"Could not find configuration for {selected_engine}. Please check your settings file."
            )

    _current_settings.debug_mode = is_debug_mode

    logger.debug(f"Loaded settings: {_current_settings}")
    logger.info(
        "Selected OCR engine {x} with model {y}:".format(x=selected_engine, y=model)
    )

    return _current_settings
