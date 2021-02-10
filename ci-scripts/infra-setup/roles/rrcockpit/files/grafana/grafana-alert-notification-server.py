#!/usr/bin/env python

import _thread
import argparse
import json

import irc.bot
from flask import Flask, request
from get_alerts import get_alerts

app = Flask(__name__)


class GrafanaIRCAlertBot(irc.bot.SingleServerIRCBot):
    def __init__(self, grafana_host, grafana_key):
        irc.bot.SingleServerIRCBot.__init__(
            self, [('chat.freenode.net', 6667)], 'ruck-rover-alert',
            'Openstack triplo ci alert bot')
        self.channel = '#tripleo-ci'
        self.grafana_host = grafana_host
        self.grafana_key = grafana_key

    def on_welcome(self, connection, event):
        connection.join(self.channel)

    def on_privmsg(self, c, e):
        self.do_command(e, e.arguments[0])

    def on_pubmsg(self, c, e):
        line = e.arguments[0]
        a = line.split(":", 1)
        if len(a) <= 1:
            a = line.split(",", 1)
        if len(a) > 1 and irc.strings.lower(a[0]) == irc.strings.lower(
                self.connection.get_nickname()):
            self.do_command(e, a[1].strip())
        return

    def send_message(self, message):
        self.connection.privmsg(self.channel, message)

    def send_alert(self, alert):
        if alert['state'] != 'ok':
            self.send_message("[{title}] {message}".format(**alert))

    def filter_alerts(self, alerts, command):
        filtered_alerts = []

        if len(command) <= 1:
            filtered_alerts = alerts
        else:
            for alert in alerts:
                filters = command[1:]
                name = alert['name'].lower()
                message = alert['Message'].lower()
                if any(filter.lower() in name + message for filter in filters):
                    filtered_alerts.append(alert)
        return filtered_alerts

    def do_command(self, e, cmd):
        splitted_cmd = cmd.split()
        action = splitted_cmd[0]
        if action == "alerts":
            alerts = self.filter_alerts(
                get_alerts(self.grafana_host, self.grafana_key), splitted_cmd)
            if alerts:
                for alert in alerts:
                    self.send_alert({
                        'title': alert['name'],
                        'message': alert['Message'],
                        'state': 'alerting'
                    })
            else:
                self.send_message("No alerts")
        else:
            self.send_message("Not understood: " + cmd)


@app.route('/', methods=['POST'])
def alert():
    irc_alert.send_alert(json.loads(request.data))
    return "OK"


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Export grafana as json files")

    parser.add_argument('--grafana-host', required=True)
    parser.add_argument('--grafana-key', required=True)

    args = parser.parse_args()

    irc_alert = GrafanaIRCAlertBot(args.grafana_host, args.grafana_key)
    _thread.start_new_thread(app.run, ())
    irc_alert.start()
