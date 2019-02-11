import requests
import logging

def get(url, query={}, timeout=20, json_view=True):

    try:
        response = requests.get(url, params=query, timeout=timeout)
    except Exception as e:
        logging.exception("Cannot get {}".format(url))
        pass
    else:
        if response and response.ok:
            if json_view:
                return response.json()
            return response.text
    return None
