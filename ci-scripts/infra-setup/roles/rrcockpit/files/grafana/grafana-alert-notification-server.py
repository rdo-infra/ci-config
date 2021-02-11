#!/usr/bin/python3

import argparse
import json
import threading
import time

import irc.bot
from flask import Flask, request
from get_alerts import get_alerts, post_alert_irc

app = Flask(__name__)


class ircThread(threading.Thread):
    def __init__(self, irc_object):
        threading.Thread.__init__(self)
        self.name = "irc_bot"
        self.irc = irc_object

    def run(self):
        print("Starting " + self.name)
        self.irc.start()


class getalertThread(threading.Thread):
    def __init__(self, host, key, timeout):
        threading.Thread.__init__(self)
        self.name = "get_alerts"
        self.host = host
        self.key = key
        self.timeout = int(timeout)

    def run(self):
        print("Starting " + self.name)
        while True:
            time.sleep(self.timeout)
            for alert in get_alerts(self.host, self.key):
                post_alert_irc("127.0.0.1", "5000", alert)


class GrafanaIRCAlertBot(irc.bot.SingleServerIRCBot):
    def __init__(self,
                 channel,
                 nickname,
                 server,
                 port=6667):
        irc.bot.SingleServerIRCBot.__init__(self,
                                            [(server, port)],
                                            nickname,
                                            nickname)
        self.channel = channel

    def on_welcome(self, c, e):
        c.join(self.channel)

    def on_privmsg(self, c, e):
        pass

    def on_pubmsg(self, c, e):
        # e.target, e.source, e.arguments, e.type
        print(e.arguments)
        c.privmsg(self.channel, "I'm a bot jim, not a person")

    def send_message(self, message):
        self.connection.privmsg(self.channel, message)

    def send_alert(self, alert):
        if alert['state'] != 'ok':
            self.send_message("[{title}] {message}".format(**alert))


@app.route('/', methods=['POST'])
def alert():
    irc_alert.send_alert(json.loads(request.data))
    return "OK"


if __name__ == "__main__":

    ap = argparse.ArgumentParser("IRC Bot")
    ap.add_argument('--grafana-host', required=True)
    ap.add_argument('--grafana-key', required=True)
    ap.add_argument("--server", default="irc.freenode.net")
    ap.add_argument("--port", type=int, default=6667)
    ap.add_argument("--channel", default="#tripleo-ci")
    ap.add_argument("--nickname", default="ruck-rover-alert")
    ap.add_argument("--timeout", default=14400)
    args = ap.parse_args()

    irc_alert = GrafanaIRCAlertBot(args.channel,
                                   args.nickname,
                                   args.server,
                                   args.port)

    irc_thread = ircThread(irc_alert)
    irc_thread.start()

    # timeout is how often we check and post alerts
    # default is every 4 hours, 14400
    cockpit_alerts = getalertThread(args.grafana_host,
                                    args.grafana_key,
                                    args.timeout)
    cockpit_alerts.start()

    # flask must be started last
    app.run(host="127.0.0.1", port="5000", debug=True)
