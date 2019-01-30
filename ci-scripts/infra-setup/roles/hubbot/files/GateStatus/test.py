from supybot.test import PluginTestCase

import json
import subprocess
import time

from . import plugin as GateStatus

mocked_data = [
    {
        'id': 'I100000',
        'branch': 'master',
        'url': 'http://review.example.com/1',
        'comments': [
            {
                'timestamp': int(time.time()) - 25 * 60 * 60,
                'reviewer': {'username': 'ci-bot'},
                'message': 'Old timestamp from a ci-bot, gets filtered\n'
                '- passing-job http://example.com/1 : SUCCESS in 1m 00s\n'
                '- failing-job http://example.com/2 : FAILURE in 1h 01m 00s'
            },
            {
                'timestamp': int(time.time()) - 90,
                'reviewer': {'username': 'foouser'},
                'message': 'Fresh timestamp from random user, gets filtered'
            },
            {
                'timestamp': int(time.time()) - 60,
                'reviewer': {'username': 'good-bot'},
                'message': 'Comment from ci-bot with fresh timestamp:\n'
                '- passing-job http://example.com/1 : SUCCESS in 1m 01s\n'
                '- failing-job http://example.com/2 : FAILURE in 1h 01m 01s\n'
                '- pass-and-fail-job http://example.com/3 : SUCCESS in 01s\n'
                '- filtered-job-nv http://example.com/4 : FAILURE in 02m 01s'
            },
            {
                'timestamp': int(time.time()) - 30,
                'reviewer': {'username': 'good-bot'},
                'message': 'Second comment from ci-bot with fresh timestamp:\n'
                '* passing-job http://example.com/1 : SUCCESS in 1m 02s\n'
                '* failing-job http://example.com/2 : FAILURE in 1h 01m 02s\n'
                '* pass-and-fail-job http://example.com/3 : FAILURE in 01s\n'
                '* filtered-job-nv http://example.com/4 : FAILURE in 02m 01s'
            },
        ],
    },
    {
        'id': 'Ideadbeef',
        'branch': 'stable/queens',
        'url': 'http://review.example.com/2',
        'comments': [
            {
                'timestamp': int(time.time()) - 60,
                'reviewer': {'username': 'good-bot'},
                'message': 'Comment from ci-bot with fresh timestamp:\n'
                '- failing-job-queens http://example.com/2 : '
                'FAILURE in 1h 01m 01s\n'
            },
            {
                'timestamp': int(time.time()) - 30,
                'reviewer': {'username': 'good-bot'},
                'message': 'Second comment from ci-bot with fresh timestamp:\n'
                '* failing-job-queens http://example.com/2 : '
                'FAILURE in 1h 01m 02s\n'
            },
        ],
    }
]


def mock_response(*args, **kwargs):
    # TODO: make this return values according to the IDs in changeIDs
    response = '\n'.join([json.dumps(item) for item in mocked_data])
    response += "\n{'footer': 'doesntmatter'}"
    return response


class GateStatusTestCase(PluginTestCase):
    plugins = ('GateStatus',)
    config = {'supybot.plugins.GateStatus.userFilter': ['good-bot'],
              'supybot.plugins.GateStatus.timeLimit': 24,
              'supybot.plugins.GateStatus.changeIDs': ['I100000', 'Ideadbeef'],
              'supybot.plugins.GateStatus.sshCommand': 'ssh foo@bar'}

    def testFetchData(self):
        subprocess.check_output = mock_response
        gs = GateStatus.GateStatus(self.irc)
        output = gs.fetch_data()
        self.assertEqual(output, mocked_data)

    def testFilterComments(self):
        gs = GateStatus.GateStatus(self.irc)
        output = gs.filter_comments(mocked_data[0]['comments'])
        # from pprint import pprint
        # pprint(output)
        self.assertEqual(len(output), 2)

    def testParseComments(self):
        gs = GateStatus.GateStatus(self.irc)
        output = gs.parse_comments(mocked_data[0]['comments'])
        self.assertEqual(output, {'failing-job': [False, False, False],
                                  'filtered-job-nv': [False, False],
                                  'pass-and-fail-job': [True, False],
                                  'passing-job': [True, True, True]})

    def testProcessQuery(self):
        gs = GateStatus.GateStatus(self.irc)
        output = gs.process_query(mocked_data)
        self.assertEqual(output['I100000']['failing'], ['failing-job'])
        self.assertEqual(output['Ideadbeef']['failing'], ['failing-job-queens'])

    def testJobReport(self):
        subprocess.check_output = mock_response
        gs = GateStatus.GateStatus(self.irc)
        output = gs.job_report()
        self.assertEqual(
            output,
            'FAILING CHECK JOBS on stable/queens: failing-job-queens @ '
            'http://review.example.com/2, master: failing-job @ '
            'http://review.example.com/1')

    def testGateStatus(self):
        subprocess.check_output = mock_response
        self.assertNotError('gatestatus')
        self.assertResponse(
            'gatestatus',
            'FAILING CHECK JOBS on stable/queens: failing-job-queens @ '
            'http://review.example.com/2, master: failing-job @ '
            'http://review.example.com/1')

    def testUserReport(self):
        subprocess.check_output = mock_response
        gs = GateStatus.GateStatus(self.irc)
        output = gs.user_report()
        self.assertEqual(
            output,
            "Current userFilter: ['good-bot']; all users and comments "
            "within the timeLimit: foouser (1), good-bot (4)")

    def testPrintUsers(self):
        subprocess.check_output = mock_response
        self.assertResponse(
            'printusers',
            "Current userFilter: ['good-bot']; all users and comments "
            "within the timeLimit: foouser (1), good-bot (4)")

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
