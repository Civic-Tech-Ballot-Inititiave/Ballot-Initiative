import base64
import requests
import pprint 

import os
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv() 
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# starting Open AI client
client = OpenAI(api_key=OPENAI_API_KEY)

# OpenAI API Key
# From: https://stackoverflow.com/questions/77284901/upload-an-image-to-chat-gpt-using-the-api

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_signature_info(image_path):

    """
    Extracts names and addresses from single ballot image.
    """

    # Getting the base64 string
    base64_image = encode_image(image_path)

    # open AI client definition
    client = OpenAI(api_key= OPENAI_API_KEY)

    # prompt message
    messages = [
          {
            "role": "user",
            "content": [
              {
                "type": "text",
                "text": """Using the written text in the image create a list of dictionaries where each dictionary consists of keys 'Name', 'Address', 'Date', and 'Ward'. Ignore all values in the box labeled "CIRCULATOR'S AFFIDAVIT OF CERTIFCATION". Ignore all values in the box labeled "SIGNATURE". Addresses belong to the name printed in the box to the immediate right of the box labeled "ADDRESS". Fill in the values of each dictionary with the correct entries for each key. Write all the values of the dictionary in full, except in the case of 'Address', which should be truncated to exclude APT and the following Apartment Number. Only output the list of dictionaries. No other intro text is necessary. The output should be in JSON format, and look like
                {'data': [{"Name": "John Doe",
                          "Address": "123 Picket Lane",
                          "Date": "11/23/2024",
                          "Ward": "2"},
                          {"Name": "Jane Plane",
                          "Address": "456 Fence Field",
                          "Date": "11/23/2024",
                          "Ward": "3"},
                          ]} """
              },
              {
                "type": "image_url",
                "image_url": {
                  "url": f"data:image/jpeg;base64,{base64_image}"
                }
              }
            ]
          }
        ]

    # processing result through GPT
    results = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.0,
        response_format={"type": "json_object"}
    )

    # convert json into list
    signator_list = json.loads(results.choices[0].message.content)['data']

    return signator_list