#!/bin/env python

from flask import Flask, request
import thread
import json
import irc.client
import logging
import sys


app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

class GrafanaIRCAlert(irc.client.SimpleIRCClient):
    def __init__(self):
        irc.client.SimpleIRCClient.__init__(self)
        self.channel = '#tripleo-ci'
        self.connect('irc.freenode.net', 6667, 'ruck-rover-alert')
        self.connection.set_keepalive(10)

    def on_welcome(self, connection, event):
        connection.join(self.channel)

    def send(self, alert):
        if alert['state'] is 'ok':
            alert_message = "{tittle}"
        else:
            alert_message = "{tittle}: {message}"
        self.connection.privmsg(self.channel, alert_message.format(**alert))

@app.route('/',methods=['POST'])
def alert():
   irc_alert.send(json.loads(request.data))
   return "OK"

if __name__ == '__main__':

    irc_alert = GrafanaIRCAlert()
    thread.start_new_thread(app.run, ())
    irc_alert.start()
