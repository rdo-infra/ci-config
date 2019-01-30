import json
import re
import subprocess
import time

from supybot.commands import wrap
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('GateStatus')


class GateStatus(callbacks.Plugin):
    """This plugin reports gate statuses.
    """
    def __init__(self, irc):
        self.__parent = super(GateStatus, self)
        self.__parent.__init__(irc)

    def fetch_data(self):
        query = ' OR '.join(self.registryValue('changeIDs'))
        cmd = (' '.join([self.registryValue('sshCommand'),
                         "gerrit query --format json --comments",
                         query]))
        output = subprocess.check_output(
            cmd.split(" "),
            stderr=subprocess.STDOUT)

        query_data = []
        # skip the last line of output, which is a query summary
        for line in output.split("\n")[:-1]:
            parsed_line = json.loads(line)
            if 'comments' in parsed_line:
                query_data.append(parsed_line)
        return query_data

    def filter_comments(self, comments):
        '''Filter the comments by username and timestamp'''

        limit = time.time() - (60 * 60 * self.registryValue('timeLimit'))

        filtered = [
            comment for comment in comments if
            comment['reviewer']['username'] in
            self.registryValue('userFilter') and comment['timestamp'] > limit]
        return filtered

    def parse_comments(self, comments):
        results = {}
        for comment in comments:
            for line in comment['message'].split('\n'):
                result = re.match(
                    r'^[*-] (?P<job>.*?) (?P<url>.*?) : (?P<result>[^ ]+) '
                    '?(?P<comment>.*)$', line)
                if result:
                    success = result.group('result') == 'SUCCESS'
                    job = result.group('job')
                    if job in results:
                        results[job].append(success)
                    else:
                        results[job] = [success]
        return results

    def filter_failing(self, results):
        failing = []
        for job in results.keys():
            if len(results[job]) > 1 and results[job][-2:] == [False, False]:
                failing.append(job)

        exclude_patterns = self.registryValue('jobFilter')
        filtered = []
        for job in failing:
            exclude_job = False
            for regexp in exclude_patterns:
                if re.match(regexp, job):
                    exclude_job = True
            if not exclude_job:
                filtered.append(job)

        return filtered

    def process_query(self, query_data):
        processed = {}
        for change in query_data:
            filtered_comments = self.filter_comments(change['comments'])
            parsed_results = self.parse_comments(filtered_comments)
            failing_jobs = self.filter_failing(parsed_results)
            processed[change['id']] = {'branch': change['branch'],
                                       'url': change['url'],
                                       'failing': failing_jobs}
        return processed

    def job_report(self):
        query_data = self.fetch_data()
        processed_data = self.process_query(query_data)

        failing_list = []
        for change in processed_data:
            failing_list += processed_data[change]['failing']
        # failing_list = []
        if not failing_list:
            return "All check jobs are working fine on %s." % \
                (', '.join([processed_data[change]['branch']
                 for change in processed_data]))
        msg = "FAILING CHECK JOBS on "
        for change in processed_data:
            if processed_data[change]['failing']:
                msg += processed_data[change]['branch'] + ': '
                msg += ', '.join(processed_data[change]['failing'])
                msg += ' @ ' + processed_data[change]['url'] + ', '
        return msg[:-2]

    def user_report(self):
        limit = time.time() - (60 * 60 * self.registryValue('timeLimit'))

        query_data = self.fetch_data()

        users = {}
        for change in query_data:
            for comment in change['comments']:
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
        for config_name in ["sshCommand", "changeIDs"]:
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
