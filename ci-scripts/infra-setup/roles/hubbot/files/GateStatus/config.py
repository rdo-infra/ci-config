import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization
_ = PluginInternationalization('GateStatus')


def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified themself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    # from supybot.questions import something
    conf.registerPlugin('GateStatus', True)


GateStatus = conf.registerPlugin('GateStatus')
conf.registerGlobalValue(
    GateStatus,
    'changeIDs',
    registry.SpaceSeparatedListOfStrings([], _("""Change ID list used for
    reporting.""")))
conf.registerGlobalValue(
    GateStatus,
    'timeLimit',
    registry.NonNegativeInteger(24, _("""Maximum comment age in hours that gets
    parsed. Avoids reporting on old and obsolete gate jobs. Defaults to
    24.""")))
conf.registerGlobalValue(
    GateStatus,
    'sshCommand',
    registry.String('', _("""Command prefix used to fetch data from Gerrit. The
    bot's user should have passwordless ssh set up. Example: ssh -p 29418
    myuser@review.openstack.org""")))
conf.registerGlobalValue(
    GateStatus,
    'jobFilter',
    registry.SpaceSeparatedListOfStrings(['.*-nv$'], _("""List of regexps for job names
    that will be filtered out of the reported failing jobs""")))
conf.registerGlobalValue(
    GateStatus,
    'userFilter',
    registry.SpaceSeparatedListOfStrings([], _("""Only try to parse comment
    from these users""")))

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
