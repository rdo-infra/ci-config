#!/usr/bin/env python

import argparse

import requests

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Print created api key")

    parser.add_argument('--url', default="http://admin:admin@localhost:8080")
    parser.add_argument('--key-name', required=True)

    args = parser.parse_args()

    response = requests.post(
        args.url + "/api/auth/keys",
        json={
            "name": args.key_name,
            "role": "Admin"
        })

    if response.ok:
        print(response.json()['key'])
    else:
        print(response.content)
        exit(1)
