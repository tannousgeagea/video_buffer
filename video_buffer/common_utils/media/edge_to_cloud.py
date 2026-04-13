import requests
import json
import logging

def sync(
    url:str,
    params:dict,
    media_file,
):
    """
    Upload a media file to the gateway service alongside its metadata.
 
    Parameters
    ----------
    url:
        Full gateway endpoint URL.
    params:
        Metadata fields sent as multipart form fields (NOT query string).
        The 'data' key must already be a JSON string — pass
        model_dump_json() or json.dumps(...) before calling sync().
    media_file:
        Absolute path to the media file to upload.
 
    Notes
    -----
    params are passed to `data=` (multipart form fields), NOT `params=`
    (URL query string). Sending a JSON payload via query string causes
    URL-encoding that the gateway cannot parse, producing:
        "Expecting value: line 1 column 1 (char 0)"
    """

    try:

        # logging.info("Params %s", params)
        with open(media_file, 'rb') as f:
            response = requests.post(
                url, 
                data=params, 
                files={'media_file': f},
            )

        # Check if the request was successful
        if response.ok:
            logging.info("File successfully uploaded:", response.json())
        else:
            raise ValueError(f"Failed to upload file. Status code: {response.status_code}, Response: {response.text}")

    except requests.exceptions.RequestException as e:
        raise ValueError(f"An error occurred: {e}")
    except Exception as e:
        raise ValueError(f"An unexpected error occurred: {e}")