#!/bin/env python

from flask import Flask, request
import json
import irc.client
import logging
import sys

ALERT_IRC_CHANNEL='#tripleo-ci'
IRC_USER_NAME='ruck-rover-alert'

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

def send_to_irc(message):

    try:
        server.privmsg(ALERT_IRC_CHANNEL, message)
        client.process_once()
    except irc.client.ServerConnectionError as x:
        print(x)
        sys.exit(1)

@app.route('/',methods=['POST'])
def foo():
   data = json.loads(request.data)
   send_to_irc(json.dumps(data))
   return "OK"

if __name__ == '__main__':

    client = irc.client.Reactor()
    server = client.server()
    server.connect('irc.freenode.net', 6667, IRC_USER_NAME)
    server.join(ALERT_IRC_CHANNEL)
    app.run()
