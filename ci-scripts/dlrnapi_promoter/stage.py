"""
This script emulates the state of the environment around promoter as it would be
just before starting a promotion process.

The promotion interacts with:
    - dlrn_api (staged locally as standalone service)
    - docker registries (staged locally with registries on different ports)
    - images server (staged locally as normal sftp via ssh)

It can setup different components independently, the list of components it
handles it's currently defined by the "scenes" variable

This provisioner should produce

- A database usable by dlrnapi that contains hashes, users, votes from jobs
- A hierarchy for overcloud images, so image promotion script can
  sftp to localhost and change the links accordingly
- A containers definition file, oused by container-push
  playbook as a list of containers to promote.
- a yaml file containing reusable information on what this script produced for
  the components called
- A set of images pushed to source registry, so the promoter has the container
  to pull and  push during the promotion run
- A file with all information on what was produced by an executions
"""
import argparse
import logging

from stage_orchestrator import StageOrchestrator
from stage_config import StageConfig


def parse_args(cmd_line=None):
    """
    parses command line arguments
    :param cmd_line: an optional str paramter to simlate a command line.
    Useful for testing this function
    :return: The argparse args namespace object with cli arguments
    """

    defaults = StageConfig.defaults
    parser = argparse.ArgumentParser(description='Staging promoter')
    parser.add_argument('action', choices=['setup', 'teardown'])
    default_scenes = ','.join(defaults.scenes)
    parser.add_argument('--scenes',
                        default=default_scenes,
                        help=("Select scenes to create in the environment "
                              "scenes available {}"
                              "".format(default_scenes))
                        ),
    parser.add_argument('--dry-run', action='store_true', default=False,
                        help="Don't do anything, still create stage-info")
    parser.add_argument('--promoter-user',
                        default=defaults.promoter_user,
                        help="The promoter user")
    parser.add_argument('--stage-config-file',
                        default=defaults.stage_config_file,
                        help=("Config file for stage generation"
                              " (relative to config dir)"))
    parser.add_argument('--stage-info-file',
                        default=defaults.stage_info_file,
                        help=("Config file for stage results"))
    parser.add_argument('--db-data-file',
                        default=defaults.db_data_file,
                        help=("Data file to inject to dlrn server"
                              " (relative to config dir)"))
    parser.add_argument('--promoter-config-file',
                        default=defaults.promoter_config_file,
                        help=("Config file for promoter"
                              " on which to base the stage"
                              " (relative to config dir)"))

    # Parse from the function parameter if present
    if cmd_line is not None:
        args = parser.parse_args(cmd_line.split())
    else:
        args = parser.parse_args()

    if hasattr(args, 'scenes'):
        args.scenes = args.scenes.split(',')

    return args


def main(cmd_line=None):
    """
    The main sets up logging and instantiates the Config object and the staging
    environment object.
    The calls the proper action based on the mandatory action command line
    argument.
    :param cmd_line: an optional parameter to pass to the argument parser
    function
    :return: the configuration produced if a cmd_line has been passed. None
    otherwise. Useful for testing of the main function
    """

    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger("promoter-staging")
    log.setLevel(logging.DEBUG)

    args = parse_args(cmd_line=cmd_line)

    config = StageConfig(source=args.stage_config_file, overrides=args)

    staged_env = StageOrchestrator(config)
    if args.action == 'setup':
        staged_env.setup()
    elif args.action == 'teardown':
        staged_env.teardown()
    else:
        log.error("No action specified")

    if cmd_line is not None:
        return config


if __name__ == "__main__":
    main()
