import json
import re
import subprocess
import time

import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('GateStatus')

class GateStatus(callbacks.Plugin):
    """This plugin reports gate statuses.
    """
    def __init__(self, irc):
        self.__parent = super(GateStatus, self)
        self.__parent.__init__(irc)

    def fetch_comments(self):
        # only care about comments in the last 24 hours
        limit = time.time() - (60*60*self.registryValue('timeLimit'))

        cmd = (' '.join([self.registryValue('sshCommand'),
                         "gerrit query --format json --comments",
                         self.registryValue('changeID')]))
        output = subprocess.check_output(cmd.split(" "), stderr=subprocess.STDOUT)
        output = json.loads(output.split("\n")[0])

        comments = []
        for comment in output['comments']:
            if comment['reviewer']['username'] in \
                self.registryValue('userFilter') and \
                comment['timestamp'] > limit:
                comments.append(comment)
        return comments

    def check_comments(self, comments):
        results = {}
        for comment in comments:
            for line in comment['message'].split('\n'):
                result = re.match(r'^[*-] (?P<job>.*?) (?P<url>.*?) : (?P<result>[^ ]+) '
                                    '?(?P<comment>.*)$', line)
                if result:
                    success = result.group('result') == 'SUCCESS'
                    job = result.group('job')
                    if job in results:
                        results[job].append(success)
                    else:
                        results[job] = [success]
        return results

    def job_report(self):
        comments = self.fetch_comments()
        results = self.check_comments(comments)
        #import pprint
        #pprint.pprint(results)

        failing_jobs = []

        for job in results.keys():
            if len(results[job]) > 1 and results[job][-2:] == [False, False]:
                failing_jobs.append(job)

        if len(failing_jobs) > 0:
            return "FAILING CHECK JOBS: %s | check logs @ %s " \
                   "and fix them ASAP." % \
                   (', '.join(failing_jobs), self.registryValue('changeURL'))
        else:
            return "Gate jobs are working fine."

    def user_report(self):
        limit = time.time() - (60*60*self.registryValue('timeLimit'))

        cmd = (' '.join([self.registryValue('sshCommand'),
                         "gerrit query --format json --comments",
                         self.registryValue('changeID')]))
        output = subprocess.check_output(cmd.split(" "), stderr=subprocess.STDOUT)
        output = json.loads(output.split("\n")[0])

        users = {}
        for comment in output['comments']:
            if comment['timestamp'] > limit:
                username = comment['reviewer']['username']
                if username in users.keys():
                    users[username] += 1
                else:
                    users[username] = 1
        msg = 'Current userFilter: %s; ' % self.registryValue('userFilter')
        msg += 'all users and comments within the timeLimit: '
        for names, comments in users.items():
            msg += '%s (%s), ' % (names, comments)
        return msg[:-2]

    @internationalizeDocstring
    def gatestatus(self, irc, msg, args):
        """(no arguments)

        Returns the status of the quickstart-extras gate jobs.
        """
        config_missing = []
        for config_name in ["sshCommand", "changeID", "changeURL"]:
            if self.registryValue(config_name) == "":
                config_missing.append(config_name)
        if len(config_missing) > 0:
            msg = ("Missing value for config %s. Use "
                   "'config plugins.GateStatus.<config_name> <value>' "
                   "to setup this plugin. Check "
                   "'config help plugins.GateStatus.<config_name>' "
                   "for detailed help and "
                   "'config list plugins.GateStatus' "
                   "for all available variables."
                   % (', '.join(config_missing)))
            irc.reply(msg)
        else:
            irc.reply(self.job_report(), prefixNick=False)
    gatestatus = wrap(gatestatus)

    @internationalizeDocstring
    def printusers(self, irc, msg, args):
        """(no arguments)

        Print all the users that commented on the test change. Userful for
        figuring out the users for the userFilter variable"""
        irc.reply(self.user_report(), prefixNick=False)

Class = GateStatus

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
