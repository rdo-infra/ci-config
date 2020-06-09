import os
import tempfile
import unittest

from config_legacy import PromoterLegacyConfig
from dlrnapi_promoter import arg_parser
from logic import Promoter

try:
    # Python3 imports
    from unittest.mock import Mock
except ImportError:
    # Python2 imports
    from mock import Mock


# Passwordles ssh key
SSH_CONTENT = """-----BEGIN RSA PRIVATE KEY-----
MIIG5QIBAAKCAYEAoPmVjDOjLAbOfE+8wfWMiaL5II0QQa8sCzgMe5fE8f/jphv6
NuV0b4oyRG3iCQfRyF8mXtKtdWVkGAldKdb0nX23tLPrAXuFoolxM/Ka6z65cIp9
UMlrnjC6O/JmMJG72IEFgn/gr0b7yazwsYnVbKG9TLQ1VW4ErU3PF91isnBU9IBX
7HgH3jNCZrxOVlosTm2UeGcMEEeA3bchVJPikJeqMGrJBXnUyI02t+l6UMvcmkfa
szLs37af0gBSRzeJSlEXFjaMHYM3D4rpWIq36xGiyLgw3OXQhCc1sQwZB8J3K8NR
XLrlYwABpkEq477T4uHYfWONad7HRKvBMsNaZ5rzj4kXqcW2snHwk8hC3fwhWIMw
xMT0BrBh1QOu8j/aaVk+2EL4X4BszHxwFx26b81Cj1Vu1uLj4KJwHVTnBIQUAeqO
mXR7EbXKsKBaX75e+CaBDvuYOIY+JC99YTGjMDaeCOA3YSrA/0ove2m2fhD7f4ii
nyz1JwBRM1DUMcF5AgMBAAECggGAShwduXpcePx5O8oKANHnbcZWI6JOBa97+35G
YPAyf6drSyI+Q9/Hh0J8efyMv9OVxUXpCGa97PpM5rQI7CZGX+ttFAhw/TG9CGN2
dpAOupcaELHxl6vjm+SbGNY0LdAqRza/LqFo88keSm8QMOxgEa8004dztmz8Qj08
RqRpt/T3Z8lesUNhe+7ldx7igebp1wGkBPqMF0KUFX8mHSYofKEWfUvsWFUKnXpF
4s3evivc2DqUeUPMwgH1+lyjhJ4QH86NZpK3nsb32xOfVQvR++Cj8LoroPCH9Yio
9eqClLz/rgsPsI4D+OqREJbFjcVIFBKUCeWL7MZAHr8CUPnfF5fEpzrcahnRAlJv
2pHycvbI7EPnzXcbtbKop+U3R8nu8ELeAOCfgpIH0Cr713x6w6dICpA4hq/RziBC
zhbfwdH4LxXK3LUQWkSUdEOZV3y2+6+ztoDIdHco6k1i5d9oOh8eeEP/1pHvQCV5
gcfjxQhrTvNbmTF+IKldROrK1NWxAoHBANOUxxBDB+SiLU6upLnlcF/EgDlic/Sc
Xj972b8t7Wi8fvG1HlOqq7jnBjKtlHyjw+NiaIzIeJYqtAoawzRJRmgunVtLaM7L
KlDJ3RyqzvPMhrYZH+Bnr52br5kwCbaFKisNlVVe0Kb3siAnVXoHtUBeQgPLxPM9
a5f9SNxc5w3I20HSLyW9AyV4yTYWX+IISgcMe7LSMdqlmTaHJ0T+hFUDRtDMm8uG
usY9smjJ9dgPPrg94WyNvautOS3Qe0vmRwKBwQDCxQZMeZcC9lz83loQNj13htUZ
ng7x4+TcpFALXD+mw9HIRP7ooyzyTDaDFoFJyuIrUvn/qUCWmF+dz4hCueHkSCfr
jFsnfd1tEI4T1DROS3f9s9knKj9QFPKgtfS+SAUsZP7Egalfq1xFVqpBYXsfDsnR
9VvoQlShrtFnGgZWoKohe48uwPZZrtAxQ8eOhwWQa9o0hF1UEo5y0E5YLxBip9jw
LGHVOhYFSTmTLBN8MVEP7qg/gmiSpRLPO5boOj8CgcEApMGQtUgNKGtlLoTuPte8
RsbENmtE8jClb3fo2mdQHKPTkjJAWFRpfgVgHSxvmRMJIdJqqV4eEIlWQxwN73Qz
wEK0Q/gXuBgabmiSppUXrF8Sc1BjMyJqbSdjeL0ggyF08auVIrI/dhUhfspCVFEW
QfZkH4KYbfThCKyyBO7O+Tv0CHA8SH3DqnVA8b5Akcl0o8KDvH7TVXhoMz7RRHeQ
4oY3qbX6h2T1ohM/DzxdFQ7h/yQomphRHxM3mEZlDHhXAoHBAL/STcbJxYmcW66L
ysXGtbjfaUdGnM9stDz98vuNSf8TQqvsD+XMt3qWxuVKJ+EmWKN0oFVEOyFWRm1l
NH0LF0e+LNrWq/v0ATzmHhe3WiB2QWHzW/4vpJVZXDAdpEI3Kikz+ppMXSSk30ZG
+X1U5W6MIQaQkIjpsvJd+0yAnBd7OrOpPjY8wyNGgTLT31km77ryDcDFUCl58SNw
togxKgEP8B9yhpP7Fi70lCi3MyWQaJa5ZKjP5e/vddv1g0WJ/wKBwQCjlJsB5XUq
Do980NT5ly95fOAHWBzak4EzDZhoNT25q2OM4CG0uH4auUO8cA+AdoJo5fl2Q7kn
8b0jYsvOlQrHYTyYjyDdOw2wkhPG9RbXQ/CdG6/Vs2ioyh8s4v8GFIZeXdZ8s2m8
ANVlQh7pYqCrYudNESL0qyGQ+dxcESo3XxCZHHFax4e8+9FeXWN4knRQBsjlGDyb
+sjxQ3Hfl5UZk+GiZpY3Gm79L837QtvJELNn3kz+cK0R0kFOEvlq1W8=
-----END RSA PRIVATE KEY-----"""

# Cases of ini configuration
# TODO: remove together with legacy config
test_ini_configurations = dict(
    not_ini='''
    I am not a ini file
    ''',
    missing_parameters='''
    [main]
    api_url: https://trunk.rdoproject.org/api-centos-master-uc
    username: ciuser
    dry_run: no
    log_file: /dev/nul
    latest_hashes_count: 10
    manifest_push: true

    [promote_from]
    current-tripleo: tripleo-ci-testing

    [current-tripleo]
    periodic-tripleo-centos-7-master-containers-build-push
    ''',
    missing_main='''
    [promote_from]
    current-tripleo: tripleo-ci-testing
    ''',
    missing_promotions_section='''
    [main]
    # missing mandatory parameters and sections
    distro_name: centos
    distro_version: 7
    release: master
    api_url: https://trunk.rdoproject.org/api-centos-master-uc
    username: ciuser
    dry_run: no
    log_file: /dev/null
    latest_hashes_count: 10
    manifest_push: true
    ''',
    missing_criteria_section='''
    [main]
    # missing mandatory parameters and sections
    distro_name: centos
    distro_version: 7
    release: master
    api_url: https://trunk.rdoproject.org/api-centos-master-uc
    username: ciuser
    dry_run: no
    log_file: /dev/null
    latest_hashes_count: 10
    manifest_push: true

    [promote_from]
    current-tripleo: tripleo-ci-testing
    ''',
    criteria_empty='''
    [main]
    distro_name: centos
    distro_version: 7
    release: master
    api_url: https://trunk.rdoproject.org/api-centos-master-uc
    username: ciuser
    dry_run: no
    log_file: /dev/null
    latest_hashes_count: 10
    manifest_push: true

    [promote_from]
    current-tripleo: tripleo-ci-testing

    [current-tripleo]
    ''',
    correct='''
    [main]
    distro_name: centos
    distro_version: 7
    release: master
    api_url: https://trunk.rdoproject.org/api-centos-master-uc
    username: ciuser
    dry_run: no
    log_file: /dev/null
    latest_hashes_count: 10
    manifest_push: true

    [promote_from]
    current-tripleo: tripleo-ci-testing

    [current-tripleo]
    periodic-tripleo-centos-7-master-containers-build-push
    periodic-tripleo-centos-7-master-standalone
    ''',
)


# These are preparation for all the types of dlrn_hashes we are going to test
# on the following test cases.
valid_commitdistro_kwargs = dict(commit_hash='abcd', distro_hash='defg',
                                 timestamp=1)
valid_commitdistro_notimestamp_kwargs = dict(commit_hash='a', distro_hash='b')
invalid_commitdistro_kwargs = dict(commit='a', distro='b')
different_commitdistro_kwargs = dict(commit_hash='b', distro_hash='c',
                                     timestamp=1)
different_commitdistro_notimestamp_kwargs = dict(commit_hash='a',
                                                 distro_hash='b')
valid_aggregate_kwargs = dict(aggregate_hash='abcd', commit_hash='defg',
                              distro_hash='hijk', timestamp=1)
valid_aggregate_notimestamp_kwargs = dict(aggregate_hash='a', commit_hash='b',
                                          distro_hash='c')
invalid_aggregate_kwargs = dict(aggregate='a')
different_aggregate_kwargs = dict(aggregate_hash='c', commit_hash='a',
                                  distro_hash='c', timestamp=1)
different_aggregate_notimestamp_kwargs = dict(aggregate_hash='a',
                                              commit_hash='b',
                                              distro_hash='c')

# Structured way to organize test cases by hash type and source type
# by commitdistro and aggregate hash types and by dict or object source tyep
hashes_test_cases = {
    'commitdistro': {
        "dict": {
            "valid": valid_commitdistro_kwargs,
            "valid_notimestamp":
                valid_commitdistro_notimestamp_kwargs,
            'invalid': invalid_commitdistro_kwargs,
            'different': different_commitdistro_kwargs,
            'different_notimestamp':
                different_commitdistro_notimestamp_kwargs
        },
        "object": {
            "valid": Mock(spec=type, **valid_commitdistro_kwargs),
            "valid_notimestamp":
                Mock(spec=type, **valid_commitdistro_notimestamp_kwargs),
            'invalid': Mock(spec=type, **invalid_commitdistro_kwargs),
            'different': Mock(spec=type, **different_commitdistro_kwargs),
            'different_notimestamp':
                Mock(spec=type, **different_commitdistro_notimestamp_kwargs)
        },
    },
    'aggregate': {
        "dict": {
            "valid": valid_aggregate_kwargs,
            "valid_notimestamp":
                valid_aggregate_notimestamp_kwargs,
            'invalid': invalid_aggregate_kwargs,
            'different': different_aggregate_kwargs,
            'different_notimestamp':
                different_aggregate_notimestamp_kwargs
        },
        "object": {
            "valid": Mock(spec=type, **valid_aggregate_kwargs),
            "valid_notimestamp":
                Mock(spec=type, **valid_aggregate_notimestamp_kwargs),
            'invalid': Mock(spec=type, **invalid_aggregate_kwargs),
            'different': Mock(spec=type, **different_aggregate_kwargs),
            'different_notimestamp':
                Mock(spec=type, **different_aggregate_notimestamp_kwargs),
        },
    },
}


# TODO: remove together with legacy config
class LegacyConfigSetup(unittest.TestCase):

    def setUp(self):
        content = test_ini_configurations['correct']
        fp, self.filepath = tempfile.mkstemp(prefix="instance_test")

        with os.fdopen(fp, "w") as test_file:
            test_file.write(content)

        cli = "--config-file {} promote-all".format(self.filepath)
        os.environ["DLRNAPI_PASSWORD"] = "test"
        overrides = {
            "default_qcow_server": "staging",
            "log_level": "DEBUG",
        }
        overrides_obj = type("FakeArgs", (), overrides)
        args = arg_parser(cmd_line=cli)
        config = PromoterLegacyConfig(args.config_file, overrides=overrides_obj)
        self.promoter = Promoter(config)

    def tearDown(self):
        os.unlink(self.filepath)
