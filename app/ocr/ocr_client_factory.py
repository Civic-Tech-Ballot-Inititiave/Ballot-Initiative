from typing import List
from langchain_openai import ChatOpenAI
from langchain_mistralai import ChatMistralAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import (
    Runnable,
)
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from settings import *
from utils.app_logger import logger
import json


###
## OCR FUNCTIONS
###
class OCREntry(BaseModel):
    """Ballot signatory data"""

    Name: str = Field(description="Name of the petition signer")
    Address: str = Field(description="Address of the petition signatory")
    Date: str = Field(description="Date of the signed")
    Ward: int = Field(description="The area or 'Ward' that the signer belongs to")


class OCRData(BaseModel):
    Data: List[OCREntry]


def _create_ocr_client() -> Runnable:
    """
    Create an OpenAI client with the appropriate settings.

    Returns:
        Runnable: An AI client for OCR extraction.
    """

    ocr_config = load_settings().selected_config

    client: Runnable = None

    match ocr_config:
        case OpenAiConfig():
            client = ChatOpenAI(
                api_key=ocr_config.api_key,
                temperature=0.0,
                openai_api_base="https://oai.helicone.ai/v1",
                model=ocr_config.model,
                default_headers={  # Optionally set default headers or set per request (see below)
                    "Helicone-Auth": f"Bearer {ocr_config.helicone_api_key}",
                },
            ).with_structured_output(OCRData)
        case MistralAiConfig():
            client = ChatMistralAI(
                api_key=ocr_config.api_key,
                temperature=0.0,
                model_name=ocr_config.model,
            ).with_structured_output(OCRData)
        case GeminiAiConfig():
            client = ChatGoogleGenerativeAI(
                api_key=ocr_config.api_key,
                temperature=0.0,
                model=ocr_config.model,
            ).with_structured_output(OCRData)

    logger.debug(f"Creating client {ocr_config}")

    return client


async def extract_from_encoding_async(base64_image: str) -> List[dict]:
    """
    Extracts names and addresses from single ballot image asynchronously.
    Uses base64_image

    Args:
        base64_image: The base64 encoded image to extract data from.

    Returns:
        list: A list of dictionaries with the OCR data.
    """
    logger.debug("Starting OCR extraction for image")

    try:
        # AI client definition
        client = _create_ocr_client()
        # prompt message
        messages = [
            {
                "type": "text",
                "text": """Using the written text in the image create a list of dictionaries where each dictionary consists of keys 'Name', 'Address', 'Date', and 'Ward'. Fill in the values of each dictionary with the correct entries for each key. Write all the values of the dictionary in full. Only output the list of dictionaries. No other intro text is necessary.""",
            },
            {
                "type": "text",
                "text": """Remove the city name 'Washington, DC' and any zip codes from the 'Address' values.""",
            },
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
            },
        ]

        results = await client.ainvoke([HumanMessage(content=messages)])

        parsed_results = results

        # dictionary results
        parsed_list = json.loads(parsed_results.json())["Data"]
        logger.debug(f"Successfully extracted {len(parsed_list)} entries from image")
        return parsed_list

    except Exception as e:
        logger.error(f"Error in OCR extraction: {str(e)}")
        raise
