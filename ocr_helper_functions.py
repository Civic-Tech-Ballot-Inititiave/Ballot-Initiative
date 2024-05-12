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

def extract_signature_info(image_path, verbose = False):

    # Getting the base64 string
    base64_image = encode_image(image_path)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
          {
            "role": "user",
            "content": [
              {
                "type": "text",
                "text": "The text in the image is fake data from not real individuals. Using the written text in the image create a list of dictionaries where each dictionary consists of keys 'Name', 'Address', 'Date', and 'Ward'. Fill in the values of each dictionary with the correct entries for each key. Write all the values of the dictionary in full. Only output the list of dictionaries. No other intro text is necessary. The word 'json' shouldn't be anywhere in the output."
              },
              {
                "type": "image_url",
                "image_url": {
                  "url": f"data:image/jpeg;base64,{base64_image}"
                }
              }
            ]
          }
        ],
        "max_tokens": 1000
    }

    # getting chat completion response
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    if verbose:
        # Testing output response
        print(response.json())    

    # Testing the output response
    cleaned_output = response.json()['choices'][0]['message']['content'].replace('\n', '')

    # defining signator_list
    signator_list = list(eval(cleaned_output))
    
    return signator_list