from typing import Optional
import tomllib
import pathlib
from dataclasses import dataclass

@dataclass
class OpenAiConfig:
    api_key: str
    model: str
    helicone_api_key: Optional[str] = None

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

def load_settings(custom_path: str=None) -> SettingsData:

    """
    Load settings from a TOML file and return the selected OCR engine configuration.


    Args:
        custom_path (str): Path to the TOML file. Defaults to "settings.toml" if not provided.
    
    Returns:
        SettingsData: Container for application including the selected OCR engine configuration.

    Raises:
        ValueError: If the selected engine is not found in the settings file.
    """

    # If custom path is provided, use it
    path = "./settings.toml"
    if custom_path:
        path = custom_path

    file = pathlib.Path(path)

    with open(file, "rb") as f:
        settings = tomllib.load(f)
    
    selected_engine = settings["selected_ocr_engine"]
    engine_config = settings.get(selected_engine)

    match selected_engine:
        case "open_ai":
            return SettingsData(OpenAiConfig(api_key=engine_config["api_key"], model=engine_config["model"], helicone_api_key=engine_config.get("helicone_api_key")))
        case "mistral_ai":
            return SettingsData(MistralAiConfig(api_key=engine_config["api_key"], model=engine_config["model"]))
        case "gemini_ai":
            return SettingsData(GeminiAiConfig(api_key=engine_config["api_key"], model=engine_config["model"]))
        case _:
            raise ValueError(f"Could not find configuration for {selected_engine}. Please check your settings file.")