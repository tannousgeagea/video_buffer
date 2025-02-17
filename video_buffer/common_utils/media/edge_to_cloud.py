import requests
import json
import logging

def sync(
    url:str,
    params:dict,
    media_file,
):
    try:
        with open(media_file, 'rb') as file:
            files = {
                'media_file': file
            }

            print(params)
            response = requests.post(url, params=params, files=files)

        # Check if the request was successful
        if response.status_code == 200:
            logging.info("File successfully uploaded:", response.json())
        else:
            raise ValueError(f"Failed to upload file. Status code: {response.status_code}, Response: {response.text}")

    except requests.exceptions.RequestException as e:
        raise ValueError(f"An error occurred: {e}")
    except Exception as e:
        raise ValueError(f"An unexpected error occurred: {e}")