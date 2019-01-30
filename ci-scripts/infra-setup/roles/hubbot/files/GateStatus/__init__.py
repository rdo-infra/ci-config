"""
A module to report gate job status
"""

import supybot
import supybot.world as world

# Use this for the version of this plugin.  You may wish to put a CVS keyword
# in here if you\'re keeping the plugin in CVS or some similar system.
__version__ = "%%VERSION%%"

__author__ = supybot.Author('Attila Darazs')

# This is a dictionary mapping supybot.Author instances to lists of
# contributions.
__contributors__ = {}

from . import config
from . import plugin
from imp import reload
reload(plugin) # noqa: In case we're being reloaded.

if world.testing:
    from . import test  # noqa

Class = plugin.Class
configure = config.configure


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
