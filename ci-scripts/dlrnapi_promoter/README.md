DLRN API Promoter
=================

This script takes a config file and tries to promote an existing DLRN link to a
new one in case all the defined jobs posted a successful result for the current
link.

For more information about the DLRN API, see
[dlrnapi_client](https://github.com/softwarefactory-project/dlrnapi_client/).

Configuration
-------------

Set the following variables in the `[main]` section:

* `api_url` -- The full URL for the DLRN API
* `username` -- The username to access the DLRN API. The password is taken from
  the `DLRNAPI_PASSWORD` environment variable to avoid exposing it in the logs.
* `dry_run` -- When true, skip promotion even if all the promotion requirements
  are satisfied.
* `log_file` -- The path for a file where the script logs its activities.

`[promote_from]` section:

List of the intended promotion names (on the left) and the link to promote
from (on the right). This allows to build out multiple chains of promotions
easily.

Create pairs as `promotion_link_name: current_link_name`. The script will try
to check the successfully finished jobs of `current_link_name` and if all the
listed jobs from the `[promotion_link_name]` section (see below) are present,
it will promote the repository as `promotion_link_name`.

Tip: It is easy to disable a specific promotion step by commenting out a line
here, the promotion requirements can stay in the file.

Example:

    [promote_from]
    phase1-link: newest-but-unstable-link
    phase2-link: phase1-link
    alternative-phase2-link: phase-1-link
    phase3-link: phase2-link

`[promotion_link_name]` section:

A list of job IDs that need to successfully complete before the link can be
promoted as `promotion_link_name`. The source is defined in the `[promote_from]`
section.

Example:

    [phase1-link]
    promotion-job-for-phase1-featureset001
    promotion-job-for-phase1-featureset002

    [phase2-link]
    promotion-job-for-phase2-featureset001-baremetal
    promotion-job-for-phase2-featureset002-baremetal
    promotion-job-for-phase2-featureset003-baremetal

Installation
------------

Create a virtualenv to run the script and install the requirements before the
first run:

    virtualenv /tmp/dlrnapi_promoter
    source /tmp/dlrnapi_promoter/bin/activate
    pip install -r requirements.txt

Running
-------

It's recommended to run the script with various release configurations
periodically from crontab, specifying the config file as the first argument of
the script:

    python dlrnapi_promoter.py --config-file config/CentOS-8/master.yaml promote-all
