IRC bot instance for GateStatus reporting
=========================================

This role sets up an instance for
[Limnoria](https://github.com/ProgVal/Limnoria), a Python based IRC bot, and
adds the GateStatus plugin to it. The plugin is used to periodically check the
statuses of dummy Gerrit changes and report any failing jobs.

A shell script is added to the `centos` user's crontab to periodically recheck
or rebase the dummy changes that supply information to the bot about the gate
statuses.

Preparation
-----------

Create dummy changes on Gerrit for each branch where you want to check the gate
statuses and note down their Change IDs. Make sure to alter relevant files to make
every necessary gate job triggered on the dummy changes.

Configuration
-------------

The instance is set up with a volume under /opt/hubbot, so the bot
configuration persists between instance rebuilds.

After the deployment of a new instance without configuration, it's still
necessary to login to the instance and run as the `centos` user:

    cd /opt/hubbot
    source ~/limnoria_venv/bin/activate
    supybot-wizard

The wizard will create a default config file for the bot. Make sure to add the
"GateStatus" plugin to the loaded list when the wizard asks.

The bot will automatically start after every instance reboot, but should be
started manually for the first time with:

    supybot -d /opt/hubbot/hubbot.conf

After the bot is up and running, the plugin needs to be configured over IRC,
after being identified to the bot as an owner. The following configuration
variables can be changed for the plugin by writing it in a private chat to the
bot as:

    config plugins.GateStatus.<config> <value>

Most of these values do not have defaults and are mandatory for the proper
working of the plugin.

* changeIDs -- A space separated list of Change IDs used for reporting.
  (example: `I2e4b8f2db0e245bef73b99e12975ae275104f9c4`, default: none)
* timeLimit -- Maximum comment age in hours that gets parsed. Avoids reporting
  on old and obsolete gate jobs. (default: 24)
* sshCommand -- Command prefix used to fetch data from Gerrit. The bot's user
  should have passwordless ssh set up. (example:
  `ssh -p 29418 rdo-ci@review.openstack.org` (default: none)
* userFilter -- A space separated list of users from which to parse the
  comments for job results. The usernames are not the display values on the
  Gerrit page, they can be found by the `printusers` command from the plugin.
  (example: `zuul jenkins`, default: none)
* jobFilter -- A space separated list of regular expressions that should be
  excluded from the reporting. (example: `.*experimental.*`, default: `.*-nv$`)

After the configuration a new `gatestatus` command will be available, which

* parses the comments of the specified Gerrit changes
* selects comments from specific users
* below a specific age (24 hours by default)
* filters out unimportant faliling jobs and finally
* warns about any job where the last two gate jobs failed.

The command can be scheduled using the `Scheduler` plugin on a team channel:

    load Scheduler
    repeat gate-nag 7200 gatestatus

Check out `help scheduler repeat` for more info.

Testing
-------

The GateStatus plugin includes unittests. It's advisable to re-run them after
modifying the plugin from the "GateStatus" folder:

    supybot-test --plugins-dir=".." GateStatus
