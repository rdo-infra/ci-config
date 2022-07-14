import json
import os
import requests

base_url = "https://api.hackmd.io/v1"
auth_token = os.getenv("auth_token")


def get_note(note_id):
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "text/plain",
        "Accept": "application/json"
    }
    response = requests.get(headers=headers,
                            url=base_url + "/notes/" + str(note_id))
    if response.status_code == 200:
        resp_json = json.loads(response.content)
        try:
            note_content = resp_json["content"]
            return note_content
        except KeyError:
            return None
    return None

def update_note(note_id, content):
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Accept": "application/json"
    }
    response = requests.patch(headers = headers,
                              url=base_url + "/notes/" + str(note_id),
                              json={"content": content})
    if response.status_code in range(200, 299):
        return "I have added your review to the Review list"
    else:
        return None