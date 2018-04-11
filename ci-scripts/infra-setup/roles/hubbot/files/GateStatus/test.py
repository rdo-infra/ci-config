from supybot.test import *

import json
import subprocess
import sys
import time

import supybot.world as world

from . import plugin as GateStatus

mocked_data = {
    'I100000': {
        'id': 'I100000',
        'branch': 'master',
        'comments': [
            {
                'timestamp': int(time.time()) - 25*60*60,
                'reviewer': {'username': 'ci-bot'},
                'message': 'Old timestamp from a ci-bot, gets filtered'
            },
            {
                'timestamp': int(time.time()) - 10,
                'reviewer': {'username': 'foouser'},
                'message': 'Fresh timestamp from random user, gets filtered'
            },
            {
                'timestamp': int(time.time()) - 60,
                'reviewer': {'username': 'good-bot'},
                'message': 'Comment from ci-bot with fresh timestamp:\n'
                    'passing-job http://example.com/1 : SUCCESS in 1m 00s\n'
                    'failing-job http://example.com/2 : FAILURE in 1h 01m 00s'
            },
            {
                'timestamp': int(time.time()) - 30,
                'reviewer': {'username': 'good-bot'},
                'message': 'Second comment from ci-bot with fresh timestamp:\n'
                    'passing-job http://example.com/1 : SUCCESS in 1m 00s\n'
                    'failing-job http://example.com/2 : FAILURE in 1h 01m 00s'
            },
        ]
    },
    'Ideadbeef': {
        'id': 'Ideadbeef',
        'branch': 'stable/queens',
        'comments': []
    }
}

def mock_response(*a, **kw):
    response = '\n'.join([json.dumps(mocked_data[key]) for key in mocked_data])
    response += "\n{'footer': 'doesntmatter'}"
    return response

class GateStatusTestCase(PluginTestCase):
    plugins = ('GateStatus',)

    def testFetchComments(self):
        subprocess.check_output = mock_response
        gs = GateStatus.GateStatus(self.irc)
        output = gs.fetch_comments()
        self.assertEqual(output, mocked_data)

    def testFilterComments(self):
        original_users = conf.supybot.plugins.GateStatus.userFilter()
        original_time = conf.supybot.plugins.GateStatus.timeLimit()
        conf.supybot.plugins.GateStatus.userFilter.setValue(['good-bot'])
        conf.supybot.plugins.GateStatus.timeLimit.setValue(24)

        try:
            gs = GateStatus.GateStatus(self.irc)
            output = gs.filter_comments(mocked_data)
        finally:
            conf.supybot.plugins.GateStatus.userFilter.setValue(original_users)
            conf.supybot.plugins.GateStatus.timeLimit.setValue(original_time)
        #print output
        self.assertEqual(len(output['I100000']['comments']), 2)

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
