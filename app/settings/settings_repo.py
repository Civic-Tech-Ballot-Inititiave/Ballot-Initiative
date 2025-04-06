from typing import Optional
import tomllib
import pathlib
from dataclasses import dataclass
from utils import *


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

    # If custom path is provided, use it
    path = "./settings.toml"
    if custom_path:
        path = custom_path

    file = pathlib.Path(path)

    with open(file, "rb") as f:
        settings = tomllib.load(f)

    selected_engine = settings["selected_ocr_engine"]
    engine_config = settings.get(selected_engine)
    is_debug_mode = settings.get("debug_mode", False)
    enable_debug_logging(is_debug_mode)

    match selected_engine:
        case "open_ai":
            _current_settings = SettingsData(
                selected_config=OpenAiConfig(
                    api_key=engine_config["api_key"],
                    model=engine_config["model"],
                )
            )
        case "mistral_ai":
            _current_settings = SettingsData(
                selected_config=MistralAiConfig(
                    api_key=engine_config["api_key"],
                    model=engine_config["model"],
                )
            )
        case "gemini_ai":
            _current_settings = SettingsData(
                selected_config=GeminiAiConfig(
                    api_key=engine_config["api_key"],
                    model=engine_config["model"],
                )
            )
        case _:
            raise ValueError(
                f"Could not find configuration for {selected_engine}. Please check your settings file."
            )

    _current_settings.debug_mode = settings.get("debug_mode", False)

    logger.debug(f"Loaded settings: {_current_settings}")
    logger.info(
        "Selected OCR engine {x} with model {y}:".format(
            x=selected_engine, y=engine_config["model"]
        )
    )

    return _current_settings
