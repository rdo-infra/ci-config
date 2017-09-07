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
* `dlrn_base_url` -- The base URL where all the repositories are stored for a
  given release. This directory should contains the various promted links.
* `username` -- The username to access the DLRN API
* `dry_run` -- When true, skip promotion even if all the promotion requirements
  are satisfied.

`[promote_from]` section:

Create pairs as `promotion_link_name: current_link_name`. The script will try
tocheck the successfully finished jobs of `current_link_name` and if all
thelisted jobs from the `[promotion_link_name]` section (see below) are
present, itwill promote the repository as `promoted_link_name`.

`[promotion_link_name]` section:

A list of job IDs that need to successfully complete before the link can be
promoted as `promoted_link_name`. The source is defined in the `[promote_from]`
section.

Installation
------------

Create a virtualenv to run the script and install the requirements before the
first run:

    virtualenv /tmp/promoter
    source /tmp/promoter/bin/activate
    pip install -r requirements.txt

Running
-------

It's recommended to run the script with various release configurations
periodically from crontab, specifying the config file as the first argument of
the script:

    python promoter.py config/master.conf
