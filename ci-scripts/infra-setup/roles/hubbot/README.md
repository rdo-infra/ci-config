Gerrit Gate Status Plug-in for Limnoria
=======================================

Periodically recheck gate jobs and warn about gate errors using an IRC bot.

This repo contains a [supybot/limnoria](https://github.com/ProgVal/Limnoria)
plug-in and a shell script.

Requirements
------------

The code depends on `jq` command which can be installed on Fedora with

    dnf install jq

Installation
------------

Create a dummy change on Gerrit without any real change on Gerrit and note down
the Change ID. Make sure to alter key files to make sure every necessary gate
job is triggered on this dummy change.

Add the shell script to cron to periodically recheck a dummy Gerrit change. The
script will re-run the gate jobs on it either by commenting "recheck" or
rebasing it. Example cron line to add:

    0 0-23/8 * * * ~/gate-status/gate-recheck.sh

The limnoria plug-in needs to be placed inside the plugins folder of the
bot's configuration directory, then loaded with

    load GateCheck

while chatting with the bot. This adds a new `gatecheck` command, which

* parses the comments of the specified Gerrit change
* selects comments from specific users
* below a specific age (1 day currently) and
* warns about any job where the last two gate jobs failed.

The command can be scheduled using the `Scheduler` plugin.

    load Scheduler
    repeat gate-nag 7200 gatestatus

Check out `help scheduler repeat` for more info.

Configuration
-------------

The following configuration variables can be changed for the plugin by writing
it in a private chat to the bot as:

    config plugins.GateStatus.<config> <value>

Most of these values do not have defaults and are mandatory for the proper
working of the plugin.

* changeID -- Change ID used for reporting.
  (example: `I2e4b8f2db0e245bef73b99e12975ae275104f9c4`, default: none)
* changeURL -- URL to check the results at. This is not used internally, just
  displayed in the bot's report message (example:
  `https://review.openstack.org/472607`, default: none)
* timeLimit -- Maximum comment age in hours that gets parsed. Avoids reporting
  on old and obsolete gate jobs. (default: 24)
* sshCommand -- Command prefix used to fetch data from Gerrit. The bot's user
  should have passwordless ssh set up. (example:
  `ssh -p 29418 myuser@review.openstack.org` (default: none)
* userFilter -- A space separated list of users from which to parse the
  comments for job results. The usernames are not the display values on the
  Gerrit page, they can be found by the `printusers` command from the plugin.
  (example: `zuul jenkins`, default: none)
